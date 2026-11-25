"""Exercise the non-interactive service and standalone launcher boundaries."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'anno117/tools'))
import anno_execution as execution
from anno_settings import Settings


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def settings(self, game):
        data = dict(version=1, game=game, output='./output/' + game,
                    report_output='./private-reports', log_output='./private-logs',
                    custom_key={'preserve': True})
        if game != 'anno1404':
            folder = self.root / game
            folder.mkdir()
            (folder / ('config.rda' if game == 'anno117' else 'data0.rda')).touch()
            data['game_data'] = str(folder)
        filename = self.root / (game + '.json')
        filename.write_text(json.dumps(data), encoding='utf-8')
        return Settings(game, filename)

    def test_prepare_all_demos_is_read_only_and_preserves_settings(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            with self.subTest(game=game):
                settings = self.settings(game)
                before = settings.filename.read_bytes()
                data = dict(settings.data)
                with patch('builtins.input', side_effect=AssertionError('Unexpected prompt')):
                    plan = execution.prepare_execution(settings, ROOT / game, 'demo')
                self.assertEqual(plan.tasks, ('analyze',) if game == 'anno1404'
                                 else ('analyze', 'stamps'))
                self.assertEqual(plan.settings.output, settings.output / 'demo')
                self.assertEqual(plan.settings.report_output, settings.output / 'demo/reports')
                self.assertEqual(plan.settings.log_output, settings.output / 'demo/logs')
                self.assertEqual(plan.settings.data['custom_key'], data['custom_key'])
                self.assertEqual(settings.data, data)
                self.assertEqual(settings.filename.read_bytes(), before)
                self.assertFalse(settings.output.exists())

    def test_invalid_jobs_and_missing_inputs_do_not_write(self):
        settings = self.settings('anno1404')
        for action, rescan in (('stamps', False), ('unknown', False), ('analyze', False)):
            with self.subTest(action=action), self.assertRaises(ValueError):
                execution.prepare_execution(settings, ROOT / 'anno1404', action, rescan)
        settings = self.settings('anno117')
        with self.assertRaises(ValueError):
            execution.prepare_execution(settings, ROOT / 'anno117', 'stamps', True)
        self.assertFalse((self.root / 'output').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows execution backend')
    def test_demo_partial_failure_reports_completed_galleries_and_keeps_config(self):
        settings = self.settings('anno117')
        before = settings.filename.read_bytes()
        plan = execution.prepare_execution(settings, ROOT / 'anno117', 'demo')
        events = []
        gallery = plan.settings.report_output / 'map-gallery.html'
        with patch.object(execution, '_run_task', side_effect=[gallery, ValueError('failed')]):
            with self.assertRaisesRegex(ValueError, 'failed'):
                execution.execute_plan(plan, on_event=events.append)
        self.assertEqual([event['type'] for event in events],
                         ['started', 'stage', 'stage', 'finished'])
        self.assertEqual(len({event['run_id'] for event in events}), 1)
        self.assertTrue(all(event['protocol_version'] == 1 for event in events))
        self.assertEqual(events[-1]['payload']['status'], 'failed')
        self.assertTrue(events[-1]['payload']['partial_output'])
        self.assertEqual(events[-1]['payload']['galleries'], [str(gallery)])
        self.assertEqual(settings.filename.read_bytes(), before)
        self.assertEqual(plan.settings.filename, settings.filename)
        with execution.updating(plan.settings.output):
            pass

    @unittest.skipUnless(os.name == 'nt', 'Windows execution backend')
    def test_return_without_gallery_is_a_failure(self):
        settings = self.settings('anno1404')
        plan = execution.prepare_execution(settings, ROOT / 'anno1404', 'demo')
        events = []
        with patch.object(execution, 'load_generator'):
            with self.assertRaisesRegex(ValueError, 'Galerie nach Aktualisierung nicht gefunden'):
                execution.execute_plan(plan, on_event=events.append)
        self.assertEqual(events[-1]['payload']['status'], 'failed')
        self.assertEqual(events[-1]['payload']['galleries'], [])

    @unittest.skipUnless(os.name == 'nt', 'Windows execution service')
    def test_service_uses_explicit_settings_and_rescan_without_a_python_child(self):
        settings = self.settings('anno1404')
        plan = execution.prepare_execution(settings, ROOT / 'anno1404', 'demo', rescan=True)
        gallery = plan.settings.report_output / 'map-gallery.html'
        events = []
        output = []

        def generate(config, *, rescan):
            self.assertIs(config, plan.settings)
            self.assertTrue(rescan)
            print('Processing complete')
            print('Final fragment', end='')
            gallery.parent.mkdir(parents=True)
            gallery.write_text('New gallery', encoding='utf-8')

        with patch.object(execution, 'load_generator') as loader:
            loader.return_value.run.side_effect = generate
            result = execution.execute_plan(plan, on_event=events.append, on_output=output.append)
        self.assertEqual(result.galleries, (gallery,))
        self.assertEqual(events[-1]['payload']['status'], 'success')
        self.assertEqual(output, ['Processing complete\n', 'Final fragment'])
        self.assertFalse((plan.settings.output / 'demo-settings.json').exists())
        self.assertEqual(result.logs[0].read_text(encoding='utf-8'),
                         'Processing complete\nFinal fragment')

    @unittest.skipUnless(os.name == 'nt', 'Windows execution service')
    def test_generator_failure_does_not_accept_a_stale_gallery(self):
        settings = self.settings('anno1404')
        plan = execution.prepare_execution(settings, ROOT / 'anno1404', 'demo')
        gallery = plan.settings.report_output / 'map-gallery.html'
        gallery.parent.mkdir(parents=True)
        gallery.write_text('Previous successful run', encoding='utf-8')
        events = []
        with patch.object(execution, 'load_generator') as loader:
            loader.return_value.run.side_effect = ValueError('Processing failed')
            with self.assertRaisesRegex(ValueError, 'Processing failed'):
                execution.execute_plan(plan, on_event=events.append)
        self.assertEqual(events[-1]['payload']['status'], 'failed')
        self.assertTrue(events[-1]['payload']['partial_output'])
        self.assertEqual(events[-1]['payload']['galleries'], [])
        self.assertEqual(gallery.read_text(encoding='utf-8'), 'Previous successful run')

    def test_importing_all_generators_does_not_load_configuration(self):
        program = """
import importlib.util, os, sys
from pathlib import Path
from unittest.mock import patch
project = Path(sys.argv[1])
sys.path.insert(0, str(project / 'tools'))
with patch('anno_settings.settings_for', side_effect=AssertionError('Configuration read on import')):
    for name in ('analyze_saves.py', 'build_stamp_gallery.py'):
        path = project / 'tools' / name
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location('fixture', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.CONFIG is None
        assert callable(module.run)
"""
        for game in ('anno117', 'anno1800', 'anno1404'):
            with self.subTest(game=game):
                result = subprocess.run([sys.executable, '-c', program, str(ROOT / game)],
                                        cwd=self.root, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_non_interactive_request_is_required(self):
        for script in (ROOT / 'launch.py', ROOT / 'anno1404/launch.py'):
            result = subprocess.run([sys.executable, str(script), '--non-interactive'],
                                    stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 2, result.stderr)

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher')
    def test_non_interactive_missing_config_is_not_created(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            filename = self.root / (game + '.json')
            result = subprocess.run([sys.executable, str(ROOT / 'launch.py'), '--game', game,
                                     '--action', 'demo', '--non-interactive', '--no-open',
                                     '--config', str(filename)], stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(filename.exists())
        self.assertFalse((self.root / 'output').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher')
    def test_non_interactive_invalid_installation_does_not_prompt_or_save(self):
        for game in ('anno117', 'anno1800'):
            settings = self.settings(game)
            data = dict(settings.data, game_data='./missing-game')
            settings.filename.write_text(json.dumps(data), encoding='utf-8')
            before = settings.filename.read_bytes()
            result = subprocess.run([sys.executable, str(ROOT / 'launch.py'), '--game', game,
                                     '--action', 'demo', '--non-interactive', '--no-open',
                                     '--config', str(settings.filename)], stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, encoding='utf-8', timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Spielinstallation nicht gefunden', result.stderr)
            self.assertNotIn('Spielpfad:', result.stdout)
            self.assertEqual(settings.filename.read_bytes(), before)
            self.assertFalse(settings.output.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher')
    def test_standalone_1404_demo_runs_from_another_working_directory(self):
        project = self.root / 'standalone'
        shutil.copytree(ROOT / 'anno1404', project,
                        ignore=shutil.ignore_patterns('settings.json', '.venv', '__pycache__',
                                                     'local-data', 'LokaleDaten'))
        settings = self.settings('anno1404')
        before = settings.filename.read_bytes()
        result = subprocess.run([sys.executable, str(project / 'launch.py'), '--action', 'demo',
                                 '--non-interactive', '--no-open', '--config', str(settings.filename)],
                                cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, encoding='utf-8', timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((settings.output / 'demo/reports/map-gallery.html').is_file())
        self.assertTrue((settings.output / 'demo/logs/analyze.log').is_file())
        self.assertFalse((self.root / 'private-reports').exists())
        self.assertEqual(settings.filename.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
