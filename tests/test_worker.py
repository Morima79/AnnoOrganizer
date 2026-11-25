"""Validate worker transport, exit codes and cooperative cancellation."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Event
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'anno117/tools'))
from anno_worker import read_commands
from anno_execution import ExecutionCancelled, execute_plan, prepare_execution, checkpoint
from anno_settings import Settings


class WorkerTests(unittest.TestCase):
    def test_cancel_requires_matching_version_and_job(self):
        requested = Event()
        invalid = ['not json', '[]', '{"type":"cancel"}',
                   json.dumps(dict(protocol_version=2, run_id='job', type='cancel')),
                   json.dumps(dict(protocol_version=1, run_id='other', type='cancel'))]
        read_commands(io.StringIO('\n'.join(invalid)), requested, 'job')
        self.assertFalse(requested.is_set())
        read_commands(io.StringIO(json.dumps(dict(protocol_version=1, run_id='job', type='cancel'))),
                      requested, 'job')
        self.assertTrue(requested.is_set())

    def config(self, folder):
        path = folder / 'settings.json'
        path.write_text(json.dumps(dict(version=1, game='anno1404', output='./output')),
                        encoding='utf-8')
        return path

    def test_cancel_before_execution_creates_no_outputs_and_resets_context(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings('anno1404', self.config(Path(directory)))
            plan = prepare_execution(settings, ROOT / 'anno1404', 'demo')
            events = []
            with self.assertRaises(ExecutionCancelled):
                execute_plan(plan, on_event=events.append, cancel_requested=lambda: True)
            self.assertEqual(events[-1]['payload']['status'], 'cancelled')
            self.assertFalse(events[-1]['payload']['partial_output'])
            self.assertFalse(settings.output.exists())
            checkpoint()

    @unittest.skipUnless(os.name == 'nt', 'Windows worker')
    def test_real_worker_demo_stdout_contains_events_only(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            config = self.config(folder)
            result = subprocess.run([sys.executable, str(ROOT / 'anno1404/launch.py'), '--worker',
                                     '--action', 'demo', '--config', str(config)], cwd=folder,
                                    stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            events = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([event['type'] for event in events], ['started', 'stage', 'finished'])
            self.assertEqual(len({e['run_id'] for e in events}), 1)
            self.assertTrue(all(e['protocol_version'] == 1 for e in events))
            finished = events[-1]['payload']
            self.assertEqual(finished['status'], 'success')
            self.assertTrue(all(Path(p).is_file() for p in finished['galleries'] + finished['logs']))

    @unittest.skipUnless(os.name == 'nt', 'Windows worker')
    def test_worker_invalid_requests_are_structured_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            config = self.config(folder)
            invalid_zone = folder / 'invalid-zone.json'
            invalid_zone.write_text(json.dumps(dict(version=1, game='anno1404', output='./output',
                                                    timezone='Invalid/Timezone')), encoding='utf-8')
            for arguments in ([], ['--action', 'stamps', '--config', str(config)],
                              ['--action', 'demo', '--config', str(folder / 'missing.json')],
                              ['--action', 'demo', '--config', str(invalid_zone)]):
                result = subprocess.run([sys.executable, str(ROOT / 'anno1404/launch.py'), '--worker',
                                         *arguments], cwd=folder, stdin=subprocess.DEVNULL,
                                        capture_output=True, text=True, encoding='utf-8', timeout=20)
                self.assertEqual(result.returncode, 2, result.stderr)
                events = [json.loads(line) for line in result.stdout.splitlines()]
                self.assertEqual(events[-1]['payload']['error_code'], 'invalid_job')
                self.assertFalse(events[-1]['payload']['partial_output'])
                self.assertFalse((folder / 'output').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows worker')
    def test_cancel_command_reaches_generator_without_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            project = folder / 'standalone'
            shutil.copytree(ROOT / 'anno1404', project,
                            ignore=shutil.ignore_patterns('settings.json', '.venv', '__pycache__',
                                                         'local-data', 'LokaleDaten'))
            generator = project / 'tools/analyze_saves.py'
            generator.write_text('from anno_execution import checkpoint\nimport time\n'
                                 'def run(settings, *, rescan=False):\n'
                                 '    for _ in range(500):\n'
                                 '        checkpoint()\n        time.sleep(0.01)\n', encoding='utf-8')
            config = self.config(folder)
            process = subprocess.Popen([sys.executable, str(project / 'launch.py'), '--worker',
                                        '--action', 'demo', '--config', str(config)], cwd=folder,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8')
            try:
                started = json.loads(process.stdout.readline())
                stage = json.loads(process.stdout.readline())
                self.assertEqual(stage['type'], 'stage')
                command = dict(protocol_version=1, run_id=started['run_id'], type='cancel')
                output, error = process.communicate(json.dumps(command) + '\n', timeout=15)
                self.assertEqual(process.returncode, 130, error)
                self.assertEqual(json.loads(output.splitlines()[-1])['payload']['status'], 'cancelled')
                self.assertFalse((folder / 'output/demo/reports/map-gallery.html').exists())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()


if __name__ == '__main__':
    unittest.main()
