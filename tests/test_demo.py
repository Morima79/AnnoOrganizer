import copy
import hashlib
import json
import shutil
import subprocess
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'anno117/tools'))
from anno_settings import Settings
from anno_demo import demo_settings
from anno_installation import resolve_game_data, steam_libraries


class DemoTests(unittest.TestCase):
    def test_demo_preserves_personal_settings_and_uses_bundled_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game_data = root / 'game/maindata'
            game_data.mkdir(parents=True)
            (game_data / 'config.rda').touch()
            data = {'version': 1, 'game': 'anno117', 'game_data': str(game_data),
                    'account': './my-private-saves', 'stamps': './my-private-stamps',
                    'output': './my-output', 'custom_option': {'enabled': True}}
            filename = root / 'settings.json'
            filename.write_text(json.dumps(data), encoding='utf-8')
            before = filename.read_bytes()
            settings = Settings('anno117', filename)
            demo = demo_settings(settings, ROOT / 'anno117')
            demo.validate('analyze')
            demo.validate('stamps')
            self.assertEqual(settings.data, data)
            self.assertEqual(filename.read_bytes(), before)
            self.assertEqual(demo.path('account'), ROOT / 'anno117/demo/saves')
            self.assertEqual(demo.path('stamps'), ROOT / 'anno117/demo/stamps')
            self.assertEqual(demo.output, root / 'my-output/demo')
            self.assertEqual(demo.data['custom_option'], data['custom_option'])
            self.assertFalse(demo.output.exists())

    def test_game_path_accepts_installation_root_or_maindata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'maindata').mkdir()
            (root / 'maindata/config.rda').touch()
            self.assertEqual(resolve_game_data(root, 'anno117'), root / 'maindata')
            self.assertEqual(resolve_game_data(root / 'maindata', 'anno117'), root / 'maindata')

    def test_additional_steam_library_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'steamapps').mkdir()
            extra = str(root / 'another-library').replace('\\', '\\\\')
            (root / 'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "1" { "path" "' + extra + '" } }', encoding='utf-8')
            self.assertIn(root / 'another-library', steam_libraries(root))

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher')
    def test_first_demo_check_creates_no_settings_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'anno1404'
            shutil.copytree(ROOT / 'anno1404', project,
                            ignore=shutil.ignore_patterns('settings.json', '.venv', '__pycache__', 'local-data', 'LokaleDaten'))
            result = subprocess.run([sys.executable, str(project / 'launch.py'), '--action', 'demo', '--check'],
                                    cwd=directory, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((project / 'settings.json').exists())
            self.assertFalse((project / 'local-data').exists())

    def test_public_demo_files_match_their_manifests(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            folder = ROOT / game / 'demo'
            manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(len(manifest['saves']), 3)
            self.assertEqual(len(manifest['stamps']), 0 if game == 'anno1404' else 5)
            for item in manifest['saves'] + manifest['stamps']:
                with self.subTest(game=game, file=item['file']):
                    source = (folder / item['file']).resolve()
                    self.assertTrue(source.is_relative_to(folder.resolve()))
                    self.assertEqual(source.stat().st_size, item['bytes'])
                    self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), item['sha256'])


if __name__ == '__main__':
    unittest.main()
