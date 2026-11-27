"""Validate portable resource selection, checksums and frozen worker routing."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT))
from build_desktop import payload_files, hidden_imports, pyinstaller_command
from smoke_desktop import extract
from desktop.worker_client import WorkerClient
from desktop.settings_store import game_api
from desktop.settings_store import SettingsStore, atomic_save


class DesktopPackageTests(unittest.TestCase):
    def test_frozen_demo_fixture_outputs_are_rebased_before_validation(self):
        from desktop.self_test import seed_demo_settings
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, '_MEIPASS', str(ROOT), create=True):
                seed_demo_settings(Path(directory))
                for game in ('anno117', 'anno1800', 'anno1404'):
                    document = SettingsStore(Path(directory)).open_game(game)
                    self.assertEqual(document.view().output, Path(directory).resolve() / game / 'local-data')

    def test_only_tracked_public_resources_are_selected(self):
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().rstrip('\0').split('\0')
        tracked = sorted(set(tracked) | {'desktop/assets/annoorganizer.ico'})
        names = payload_files(ROOT, tracked)
        self.assertIn('desktop/assets/annoorganizer.ico', names)
        self.assertIn('anno1404/demo/manifest.json', names)
        self.assertIn('anno117/tools/anno_output_transaction.py', names)
        self.assertFalse(any('local-data' in name or name.endswith('/settings.json') for name in names))
        with self.assertRaisesRegex(ValueError, 'Private or generated'):
            payload_files(ROOT, [*tracked, 'anno117/tools/settings.json'])

    def test_executable_and_runtime_share_a_multiresolution_icon(self):
        from PIL import Image
        command = pyinstaller_command(ROOT, Path('work'), Path('payload'))
        icon = Path(command[command.index('--icon') + 1])
        self.assertEqual(icon, ROOT / 'desktop/assets/annoorganizer.ico')
        with Image.open(icon) as image:
            self.assertEqual(image.format, 'ICO')
            self.assertTrue({(16, 16), (32, 32), (48, 48), (256, 256)} <= image.ico.sizes())

    def test_colliding_game_modules_are_data_not_frozen_hidden_imports(self):
        imports = hidden_imports(ROOT, ['anno117/tools/analyze_saves.py',
                                        'anno1800/tools/analyze_saves.py',
                                        'anno117/tools/anno_settings.py',
                                        'anno117/tools/anno_file_formats.py'])
        self.assertIn('xml', {module.split('.')[0] for module in imports})
        self.assertNotIn('anno_settings', imports)
        self.assertNotIn('anno_file_formats', imports)

    def test_frozen_client_restarts_executable_in_worker_mode(self):
        client = WorkerClient()
        with patch.object(sys, 'frozen', True, create=True), \
                patch('desktop.worker_client.Thread') as thread:
            client.start('anno1404', 'demo', 'settings.json')
        command = thread.call_args.kwargs['args'][0]
        self.assertEqual(command[:4], [sys.executable, '--worker', '--game', 'anno1404'])
        self.assertFalse(any(argument.endswith('launch.py') for argument in command))

    def test_frozen_resources_cannot_be_used_as_writable_output(self):
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, '_MEIPASS', str(resources), create=True):
                with self.assertRaisesRegex(ValueError, 'interne Programmverzeichnis'):
                    game_api('anno1404').protect_output(resources / 'new-output', [])

    def test_frozen_settings_cannot_write_inside_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, '_MEIPASS', str(resources), create=True):
                with self.assertRaises(ValueError):
                    SettingsStore(resources / 'private-data')
                with self.assertRaises(ValueError):
                    atomic_save(resources / 'private.json', {}, None)
            self.assertFalse(list(resources.iterdir()))

    def test_frozen_first_run_saves_settings_outside_resources_with_documents_output(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, '_MEIPASS', str(ROOT), create=True), \
                    patch.object(game_api('anno1404'), 'documents_folder', return_value=Path(directory) / 'Documents'):
                document = SettingsStore(Path(directory)).open_game('anno1404')
                self.assertEqual(document.view().output, Path(directory).resolve() / 'Documents/AnnoOrganizer/Anno 1404')
                self.assertTrue(document.path.exists())

    def test_portable_entry_rejects_invalid_game_using_structured_events(self):
        result = subprocess.run([sys.executable, str(ROOT / 'desktop_entry.py'), '--worker',
                                 '--game', 'unknown'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(events[-1]['payload']['error_code'], 'invalid_job')

    def test_extract_rejects_wrong_checksum_before_running_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'app.zip'
            archive.write_bytes(b'not a zip')
            archive.with_suffix('.sha256').write_text('0' * 64 + '  app.zip', encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                extract(archive, root / 'extract')

    def test_extract_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'app.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('../outside.txt', 'must not escape')
            archive.with_suffix('.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest(), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'Unsafe archive entry'):
                extract(archive, root / 'extract')
            self.assertFalse((root / 'outside.txt').exists())


if __name__ == '__main__':
    unittest.main()
