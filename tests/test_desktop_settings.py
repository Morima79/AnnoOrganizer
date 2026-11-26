"""Preserve personal settings and path semantics through desktop editing/import."""
import json
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.settings_store import ConfigDocument, SettingsConflict, SettingsStore, game_api, gui_session


class DesktopSettingsTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows session lock')
    def test_gui_profile_lock_rejects_another_process_and_releases_on_close(self):
        code = 'from desktop.settings_store import gui_session\nimport sys\nwith gui_session(sys.argv[1]):\n    pass\n'
        profile = self.folder / 'gui-session'
        with gui_session(profile):
            result = subprocess.run([sys.executable, '-c', code, str(profile)], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('SettingsConflict', result.stderr)
        result = subprocess.run([sys.executable, '-c', code, str(profile)], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()

    def document(self, game='anno117'):
        path = self.folder / 'source/settings.json'
        path.parent.mkdir(exist_ok=True)
        data = dict(version=1, game=game, account='./My Saves', stamps='${HOME}/Stamps',
                    save_folders=['./Saves 1404'], archive='', custom={'path': './keep-this'})
        path.write_text(json.dumps(data), encoding='utf-8')
        return ConfigDocument.load(game, path)

    def test_import_preserves_known_and_implicit_destinations_and_unknown_keys(self):
        source = self.document()
        before = source.path.read_bytes()
        imported = source.copy_to(self.folder / 'new/settings.json')
        self.assertEqual(imported.view().output, source.view().output)
        self.assertEqual(imported.view().path('account'), source.view().path('account'))
        self.assertEqual(imported.view().path('stamps'), source.view().path('stamps'))
        self.assertEqual(imported.view().saves(), source.view().saves())
        self.assertEqual(imported.data['archive'], '')
        self.assertEqual(imported.data['custom'], {'path': './keep-this'})
        self.assertEqual(source.path.read_bytes(), before)
        self.assertFalse(imported.path.exists())

    def test_first_launch_saves_system_paths_and_documents_outputs(self):
        store = SettingsStore(self.folder / 'appdata')
        documents = self.folder / 'Redirected Documents'
        (documents / 'Anno 1404/Savegames').mkdir(parents=True)
        (documents / 'ANNO 1404 Venedig/Savegames').mkdir(parents=True)
        with ExitStack() as stack:
            for game in ('anno117', 'anno1800', 'anno1404'):
                stack.enter_context(patch.object(game_api(game), 'documents_folder', return_value=documents))
                stack.enter_context(patch.object(game_api(game), 'find_game_data', return_value=None))
            for game in ('anno117', 'anno1800', 'anno1404'):
                doc = store.open_game(game)
                view = doc.view()
                self.assertEqual(view.output, documents / 'AnnoOrganizer' / game.replace('anno', 'Anno '))
                self.assertTrue(doc.path.is_file())
                self.assertEqual(json.loads(doc.path.read_text(encoding='utf-8')), doc.data)
                self.assertEqual(game_api(game).PROJECT, ROOT / game)
                if game == 'anno1404':
                    self.assertEqual(view.saves(), [documents / 'Anno 1404/Savegames',
                                                    documents / 'ANNO 1404 Venedig/Savegames'])
                else:
                    name = 'Anno 117 - Pax Romana' if game == 'anno117' else 'Anno 1800'
                    self.assertEqual(view.path('account'), documents / name / 'accounts')
                    self.assertEqual(view.path('stamps'), documents / name / 'stamps')
        self.assertFalse((documents / 'AnnoOrganizer').exists())

    def test_existing_configuration_is_never_replaced_by_system_detection(self):
        doc = self.document()
        store = SettingsStore(self.folder / 'appdata')
        store.select(doc)
        before = doc.path.read_bytes()
        with patch('desktop.first_run.system_settings', side_effect=AssertionError('Must not detect')):
            loaded = store.open_game(doc.game)
        self.assertEqual(loaded.data, doc.data)
        self.assertEqual(doc.path.read_bytes(), before)

    def test_first_run_detects_installation_and_existing_documents_name_variant(self):
        documents = self.folder / 'Documents'
        home = documents / 'Anno 117 Pax Romana'
        home.mkdir(parents=True)
        installation = self.folder / 'Games/Anno 117/maindata'
        installation.mkdir(parents=True)
        (installation / 'config.rda').write_bytes(b'fixture')
        api = game_api('anno117')
        with patch.object(api, 'documents_folder', return_value=documents), \
                patch.object(api, 'find_game_data', return_value=installation):
            document = SettingsStore(self.folder / 'gui').open_game('anno117')
        self.assertEqual(document.view().path('game_data'), installation)
        self.assertEqual(document.data['account'], str(home / 'accounts'))
        self.assertFalse((home / 'accounts').exists())

    def test_missing_standard_input_folders_are_not_created(self):
        api = game_api('anno1404')
        documents = self.folder / 'Documents'
        with patch.object(api, 'documents_folder', return_value=documents):
            document = SettingsStore(self.folder / 'gui').open_game('anno1404')
        self.assertEqual(document.view().saves(), [documents / 'Anno 1404/Savegames'])
        self.assertFalse(documents.exists())

    def test_validation_rejects_malformed_values_and_code_or_input_outputs(self):
        doc = self.document()
        for key, value in [('save_folders', 'not a list'), ('report_output', ['./bad']),
                           ('output', str(ROOT / 'anno1800/tools/new-output')),
                           ('output', './My Saves/out')]:
            data = dict(doc.data, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                ConfigDocument(doc.game, doc.path, data)

    def test_import_cannot_replace_its_own_source(self):
        doc = self.document()
        before = doc.path.read_bytes()
        with self.assertRaises(ValueError):
            doc.copy_to(doc.path)
        self.assertEqual(doc.path.read_bytes(), before)

    def test_windows_documents_and_unicode_paths_share_cli_resolution(self):
        doc = self.document()
        data = dict(doc.data, account='${DOCUMENTS}/Änno Spielstände')
        api = game_api(doc.game)
        with patch.object(api, 'documents_folder', return_value=self.folder / 'Redirected Documents'):
            view = ConfigDocument(doc.game, doc.path, data).view()
            self.assertEqual(view.path('account'), self.folder / 'Redirected Documents/Änno Spielstände')

    @unittest.skipUnless(os.name == 'nt', 'Windows edit lock')
    def test_save_backs_up_and_detects_external_changes(self):
        doc = self.document()
        before = doc.path.read_bytes()
        doc.data['timezone'] = 'Europe/Berlin'
        doc.save()
        self.assertEqual([p.read_bytes() for p in (doc.path.parent / 'backups').glob('*.bak')], [before])
        external = b'{"external":true}'
        doc.path.write_bytes(external)
        with self.assertRaises(SettingsConflict):
            doc.save()
        self.assertEqual(doc.path.read_bytes(), external)
        self.assertFalse(list(doc.path.parent.glob('*.tmp')))

    @unittest.skipUnless(os.name == 'nt', 'Windows edit lock')
    def test_existing_import_destination_is_never_overwritten_implicitly(self):
        doc = self.document()
        destination = self.folder / 'existing.json'
        destination.write_bytes(b'{"keep":true}')
        imported = doc.copy_to(destination)
        with self.assertRaises(SettingsConflict):
            imported.save()
        self.assertEqual(destination.read_bytes(), b'{"keep":true}')

    @unittest.skipUnless(os.name == 'nt', 'Windows edit lock')
    def test_external_selection_and_unknown_preferences_survive_restart(self):
        doc = self.document()
        store = SettingsStore(self.folder / 'appdata')
        store.preferences['custom'] = {'keep': True}
        store.select(doc)
        reopened = SettingsStore(store.directory)
        self.assertEqual(reopened.open_game(doc.game).path, doc.path)
        self.assertEqual(reopened.preferences['custom'], {'keep': True})
        doc.path.unlink()
        with self.assertRaises(FileNotFoundError):
            reopened.open_game(doc.game)
        self.assertFalse(doc.path.exists())


if __name__ == '__main__':
    unittest.main()
