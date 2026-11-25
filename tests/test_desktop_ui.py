"""Exercise display-language choice, worker integrity and Tk state transitions."""
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.language import choose_language, resources
from desktop.worker_client import WorkerClient


class LanguageTests(unittest.TestCase):
    def test_display_language_and_saved_override(self):
        for language in ('de', 'de-DE', 'de-CH', 'de_AT', 'DE-ch'):
            self.assertEqual(choose_language(display_language=language), 'de')
        for language in ('', None, 'fr-CH', 'en-DE', 'it-CH'):
            with patch('desktop.language.windows_display_language', return_value=''):
                self.assertEqual(choose_language(display_language=language), 'en')
        self.assertEqual(choose_language('en', 'de-CH'), 'en')
        self.assertEqual(choose_language('de', 'en-US'), 'de')

    def test_resources_have_matching_keys_and_placeholders(self):
        de, en = resources('de'), resources('en')
        self.assertEqual(de.keys(), en.keys())
        for key in de:
            self.assertEqual(set(re.findall(r'{([^}]+)}', de[key])),
                             set(re.findall(r'{([^}]+)}', en[key])), key)


class WorkerClientTests(unittest.TestCase):
    def events(self, status='success'):
        return [dict(protocol_version=1, run_id='job', type='started', payload={}),
                dict(protocol_version=1, run_id='job', type='finished',
                     payload=dict(status=status, galleries=[], logs=[], partial_output=False))]

    def run_fake(self, events, code):
        client = WorkerClient()
        with patch('desktop.worker_client.subprocess.Popen') as popen:
            process = popen.return_value.__enter__.return_value
            process.stdout = io.StringIO('\n'.join(json.dumps(e) for e in events))
            process.wait.return_value = code
            client._run(['fixture'])
        received = []
        while not client.events.empty():
            received.append(client.events.get_nowait())
        return received[-1]['payload']

    def test_success_requires_consistent_exit_and_complete_protocol(self):
        self.assertEqual(self.run_fake(self.events(), 0)['status'], 'success')
        self.assertEqual(self.run_fake(self.events(), 1)['status'], 'failed')
        self.assertEqual(self.run_fake(self.events()[:1], 0)['status'], 'failed')
        events = self.events()
        events[-1]['run_id'] = 'other'
        self.assertEqual(self.run_fake(events, 0)['status'], 'failed')
        self.assertEqual(self.run_fake([*self.events(), self.events()[0]], 0)['status'], 'failed')
        events = self.events()
        events[-1]['payload']['logs'] = None
        self.assertEqual(self.run_fake(events, 0)['status'], 'failed')

    def test_second_start_is_rejected(self):
        client = WorkerClient()
        client.running = True
        with self.assertRaises(ValueError):
            client.start('anno1404', 'demo', 'unused.json')


@unittest.skipUnless(os.name == 'nt', 'Windows Tk desktop')
class DesktopUITests(unittest.TestCase):
    def setUp(self):
        from desktop.app import DesktopApp
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        with patch('desktop.app.choose_language', return_value='de'):
            self.app = DesktopApp(self.root, directory=self.folder / 'gui', game='anno1404')
        self.errors = []
        self.app.error = lambda exc: self.errors.append(str(exc))

    def test_language_switch_preserves_draft_and_selected_tab_and_persists(self):
        self.app.fields['output'].set(str(self.folder / 'Äusserer Ordner'))
        self.app.folder_text.insert('end', '\n' + str(self.folder / 'More Saves'))
        self.app.notebook.select(1)
        self.app.change_language('en')
        self.assertEqual(self.app.fields['output'].get(), str(self.folder / 'Äusserer Ordner'))
        self.assertIn('More Saves', self.app.folder_text.get('1.0', 'end'))
        self.assertEqual(self.app.notebook.index('current'), 1)
        self.assertEqual(json.loads(self.app.store.preferences_path.read_text(encoding='utf-8'))['language'], 'en')
        self.assertFalse(self.app.document.path.exists())
        self.assertEqual(self.errors, [])

    def test_game_switch_preserves_unsaved_fields_and_rejects_1404_stamps(self):
        self.app.fields['output'].set(str(self.folder / 'Changed'))
        self.app.switch_game('anno117')
        self.app.action.set('stamps')
        self.app.switch_game('anno1404')
        self.assertEqual(self.app.action.get(), 'demo')
        self.assertEqual(self.app.fields['output'].get(), str(self.folder / 'Changed'))

    def test_save_retains_unknown_values(self):
        self.app.document.data['custom'] = {'keep': True}
        self.assertTrue(self.app.save())
        data = json.loads(self.app.document.path.read_text(encoding='utf-8'))
        self.assertEqual(data['custom'], {'keep': True})
        self.assertFalse(self.app.dirty())
        self.assertEqual(self.errors, [])

    def test_use_then_import_external_config_preserves_source_and_destinations(self):
        source = self.folder / 'external.json'
        data = dict(version=1, game='anno1404', save_folders=['./Saves'],
                    output='./Private Output', custom={'keep': True})
        source.write_text(json.dumps(data), encoding='utf-8')
        before = source.read_bytes()
        with patch('desktop.app.filedialog.askopenfilename', return_value=str(source)), \
                patch('desktop.app.messagebox.askyesno', return_value=True):
            self.app.use_file()
            self.assertEqual(self.app.document.path, source.resolve())
            expected = self.app.document.view().output
            self.app.import_file()
        self.assertEqual(self.app.document.path, self.app.store.default_path('anno1404').resolve())
        self.assertEqual(self.app.document.view().output, expected)
        self.assertEqual(self.app.document.data['custom'], {'keep': True})
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(self.errors, [])

    def test_demo_runs_without_writing_personal_config_and_restores_controls(self):
        self.app.generate()
        self.assertTrue(self.app.generate_button.instate(['disabled']))
        self.assertFalse(self.app.document.path.exists())
        deadline = time.monotonic() + 20
        while self.app.snapshot is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertIsNone(self.app.snapshot)
        self.assertEqual(self.app.status, 'success', self.app.details)
        self.assertTrue(self.app.gallery_button.instate(['!disabled']))
        self.assertTrue(self.app.generate_button.instate(['!disabled']))
        self.assertFalse(self.app.document.path.exists())
        self.assertTrue(all(Path(p).is_file() for p in self.app.last_result['galleries']))
        self.assertFalse(list((self.app.store.directory / 'runs').glob('job-*')))
        self.assertEqual(self.errors, [])

    def test_cancel_waits_for_completion_before_restoring_controls(self):
        def start(*args):
            self.app.client.running = True
        with patch.object(self.app.client, 'start', side_effect=start):
            self.app.generate()
        self.app.cancel()
        self.assertEqual(self.app.status, 'cancelling')
        self.assertTrue(self.app.generate_button.instate(['disabled']))
        self.app.client.running = False
        self.app.client.events.put(dict(type='completed', payload=dict(
            status='cancelled', galleries=[], logs=[], partial_output=False)))
        self.app.poll()
        self.assertEqual(self.app.status, 'cancelled')
        self.assertTrue(self.app.generate_button.instate(['!disabled']))
        self.assertTrue(self.app.gallery_button.instate(['disabled']))
        self.assertIsNone(self.app.snapshot)

    def test_invalid_configuration_cannot_keep_an_old_success_state(self):
        self.app.last_result = dict(status='success', galleries=['previous.html'], logs=[], partial_output=False)
        self.app.status = 'success'
        self.app.fields['output'].set(str(ROOT / 'desktop'))
        self.app.generate()
        self.assertEqual(self.app.status, 'failed')
        self.assertTrue(self.app.gallery_button.instate(['disabled']))
        self.assertIsNone(self.app.snapshot)
        self.assertFalse(self.app.client.running)
        self.assertTrue(self.errors)

    def test_noninteractive_gui_smoke_covers_first_launch_and_worker(self):
        from desktop.self_test import run
        report = self.folder / 'gui-smoke.json'
        self.assertEqual(run(report, self.folder / 'self-test-state'), 0)
        self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'success')


if __name__ == '__main__':
    unittest.main()
