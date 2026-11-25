"""Preserve personal settings and path semantics through desktop editing/import."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.settings_store import ConfigDocument, SettingsConflict, SettingsStore, game_api


class DesktopSettingsTests(unittest.TestCase):
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

    def test_all_new_configs_are_read_only_until_saved_and_use_bundled_demos(self):
        store = SettingsStore(self.folder / 'appdata')
        for game in ('anno117', 'anno1800', 'anno1404'):
            doc = store.open_game(game)
            view = doc.view()
            self.assertEqual(view.output, (store.directory / game / 'local-data').resolve())
            self.assertEqual(game_api(game).PROJECT, ROOT / game)
            if game == 'anno1404':
                self.assertEqual(view.saves(), [ROOT / game / 'demo/saves'])
            else:
                self.assertEqual(view.path('account'), ROOT / game / 'demo/saves')
        self.assertFalse(store.directory.exists())

    def test_validation_rejects_malformed_values_and_code_or_input_outputs(self):
        doc = self.document()
        for key, value in [('save_folders', 'not a list'), ('report_output', ['./bad']),
                           ('output', str(ROOT / 'anno1800/tools/new-output')),
                           ('output', './My Saves/out')]:
            data = dict(doc.data, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                ConfigDocument(doc.game, doc.path, data)

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
