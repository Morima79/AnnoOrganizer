"""Check cross-game preflight, sequential dispatch and batch cancellation."""
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.batch import prepare_all
from desktop.settings_store import ConfigDocument, GAMES, SettingsStore


def configured_games(folder):
    store = SettingsStore(folder / 'gui')
    documents = {}
    for game in GAMES:
        sources = folder / 'sources' / game
        sources.mkdir(parents=True)
        marker = 'config.rda' if game == 'anno117' else 'data0.rda'
        (sources / marker).write_bytes(b'preflight fixture, not parsed')
        data = dict(version=1, game=game, timezone='Europe/Zurich', game_data=str(sources),
                    account=str(sources), stamps=str(sources), save_folders=[str(sources)],
                    output=str(folder / 'outputs' / game))
        document = ConfigDocument(game, store.default_path(game), data)
        document.save()
        documents[game] = document
    return store, documents


class BatchPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store, self.documents = configured_games(self.folder)

    def test_all_five_jobs_use_loaded_drafts_and_unopened_saved_configurations(self):
        draft = self.documents['anno1404']
        draft.data['report_output'] = str(self.folder / 'draft-reports')
        jobs = prepare_all(self.store, {'anno1404': draft})
        self.assertEqual([(job.game, job.action) for job in jobs], [
            ('anno117', 'analyze'), ('anno117', 'stamps'), ('anno1800', 'analyze'),
            ('anno1800', 'stamps'), ('anno1404', 'analyze')])
        self.assertIs(jobs[-1].document, draft)
        self.assertFalse((self.folder / 'outputs').exists())

    def test_invalid_inputs_are_reported_for_each_game_before_any_work(self):
        self.documents['anno117'].data['stamps'] = str(self.folder / 'missing-stamps')
        self.documents['anno1404'].data['save_folders'] = []
        with self.assertRaises(ValueError) as error:
            prepare_all(self.store, self.documents)
        self.assertIn('anno117', str(error.exception))
        self.assertIn('anno1404', str(error.exception))
        self.assertFalse((self.folder / 'outputs').exists())

    def test_outputs_cannot_overlap_other_games_outputs_or_inputs(self):
        for target in [self.documents['anno117'].view().output,
                       self.documents['anno117'].view().path('account') / 'nested-output']:
            self.documents['anno1800'].data['report_output'] = str(target)
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'overlapping paths'):
                prepare_all(self.store, self.documents)


@unittest.skipUnless(os.name == 'nt', 'Windows Tk desktop')
class BatchUITests(unittest.TestCase):
    def setUp(self):
        from desktop.app import DesktopApp
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store, self.documents = configured_games(self.folder)
        self.before = {game: doc.path.read_bytes() for game, doc in self.documents.items()}
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app = DesktopApp(self.root, directory=self.store.directory, game='anno1404')
        self.started = []
        self.start_patch = patch.object(self.app.client, 'start', side_effect=self.start)
        self.start_patch.start()
        self.addCleanup(self.start_patch.stop)
        self.error_patch = patch('desktop.app.messagebox.showerror')
        self.error = self.error_patch.start()
        self.addCleanup(self.error_patch.stop)
        self.addCleanup(self.app.cleanup_snapshot)

    def start(self, game, action, config):
        self.started.append((game, action, Path(config)))
        self.app.client.running = True

    def finish(self, status='success', galleries=None):
        self.app.client.running = False
        self.app.client.events.put(dict(type='completed', payload=dict(status=status,
            galleries=galleries or [], logs=[], partial_output=False,
            message='fixture failure' if status == 'failed' else '')))
        self.app.poll()

    def test_five_workers_run_in_sequence_with_frozen_drafts_and_retained_settings(self):
        self.app.fields['report_output'].set(str(self.folder / 'unsaved-reports'))
        self.app.generate_all()
        self.assertEqual(len(self.started), 1)
        snapshot = Path(self.app.snapshot.name)
        config = ConfigDocument.load('anno1404', snapshot / 'anno1404/settings.json')
        self.assertEqual(config.view().report_output, self.folder / 'unsaved-reports')
        self.assertTrue(self.app.update_all_button.instate(['disabled']))
        for number in range(5):
            self.assertEqual(len(self.started), number + 1)
            self.finish()
        self.assertEqual([(game, action) for game, action, _ in self.started], [
            ('anno117', 'analyze'), ('anno117', 'stamps'), ('anno1800', 'analyze'),
            ('anno1800', 'stamps'), ('anno1404', 'analyze')])
        self.assertEqual(self.app.status, 'success')
        self.assertEqual(len(self.app.last_result['jobs']), 5)
        self.assertEqual(self.app.action.get(), 'analyze')
        self.assertIsNone(self.app.snapshot)
        self.assertFalse(snapshot.exists())
        for game, doc in self.documents.items():
            self.assertEqual(doc.path.read_bytes(), self.before[game])
        report = json.loads((self.store.directory / 'logs/all-games-last-run.json').read_text(encoding='utf-8'))
        self.assertEqual(len(report['result']['jobs']), 5)
        self.error.assert_not_called()

    def test_preflight_failure_does_not_start_a_worker(self):
        self.app.folder_fields[0].set(str(self.folder / 'missing-saves'))
        self.app.generate_all()
        self.assertEqual(self.started, [])
        self.assertIsNone(self.app.snapshot)
        self.assertEqual(self.app.status, 'failed')
        self.error.assert_called_once()

    def test_cancellation_stops_queue_even_if_current_worker_completes_successfully(self):
        self.app.generate_all()
        self.app.cancel()
        self.finish(galleries=['already-published.html'])
        self.assertEqual(len(self.started), 1)
        self.assertEqual(self.app.status, 'cancelled')
        self.assertEqual(self.app.last_result['galleries'], ['already-published.html'])
        self.assertTrue(self.app.last_result['partial_output'])
        self.assertIsNone(self.app.batch)
        self.assertIsNone(self.app.snapshot)

    def test_failure_preserves_completed_outputs_and_stops_remaining_workers(self):
        self.app.generate_all()
        self.finish(galleries=['already-published.html'])
        self.finish('failed')
        self.assertEqual(len(self.started), 2)
        self.assertEqual(self.app.status, 'failed')
        self.assertTrue(self.app.last_result['partial_output'])
        self.assertIn('anno117 / stamps', self.app.details)
        self.assertEqual(self.app.last_result['galleries'], ['already-published.html'])
        self.assertIsNone(self.app.snapshot)

    def test_worker_start_failure_after_a_completed_job_is_reported_as_partial(self):
        self.app.generate_all()
        self.app.client.start.side_effect = OSError('Cannot start next worker')
        self.finish(galleries=['already-published.html'])
        self.assertEqual(self.app.status, 'failed')
        self.assertTrue(self.app.last_result['partial_output'])
        self.assertIn('Cannot start next worker', self.app.details)
        self.assertEqual(len(self.app.last_result['jobs']), 2)
        self.assertIsNone(self.app.snapshot)


if __name__ == '__main__':
    unittest.main()
