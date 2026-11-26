import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'anno117/tools'))
from anno_settings import Settings, protect_output
PROJECT = ROOT / 'anno117'


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.inputs = self.root / 'inputs'
        for name in ['game', 'stamps', 'accounts']:
            (self.inputs / name).mkdir(parents=True, exist_ok=True)
        (self.inputs / 'game/config.rda').touch()
        self.config = self.root / 'settings.json'
        self.data = {'version': 1, 'game': 'anno117', 'output': './outputs/anno117',
                     'game_data': './inputs/game', 'stamps': './inputs/stamps', 'account': './inputs/accounts'}
        self.save()

    def save(self):
        self.config.write_text(json.dumps(self.data), encoding='utf-8')

    def test_current_settings_environment_variable(self):
        with patch.dict(os.environ, {'ANNOORGANIZER_SETTINGS': str(self.config)}):
            self.assertEqual(Settings('anno117').filename, self.config)

    def test_obsolete_settings_environment_variable_is_ignored(self):
        alternate = self.root / 'alternate.json'
        alternate.write_text(json.dumps(self.data), encoding='utf-8')
        with patch.dict(os.environ, {'ANNOORGANIZER_SETTINGS': '', 'ANNO' + 'TOOLS_SETTINGS': str(alternate)}), \
                patch('anno_settings.PROJECT', self.root):
            self.assertEqual(Settings('anno117').filename, self.config)

    def test_relative_paths_use_configuration_directory(self):
        config = Settings('anno117', self.config).validate('stamps')
        self.assertEqual(config.path('stamps'), (self.inputs / 'stamps').resolve())
        self.assertEqual(config.output, (self.root / 'outputs/anno117').resolve())
        self.assertFalse(config.output.exists())

    def test_external_output_directories_are_relative_to_settings(self):
        self.data.update(report_output='./Auswertung', stamp_output='./Stempel', log_output='./logs')
        self.save()
        config = Settings('anno117', self.config).validate('stamps')
        self.assertEqual(config.report_output, self.root / 'Auswertung')
        self.assertEqual(config.stamp_output, self.root / 'Stempel')
        self.assertEqual(config.log_output, self.root / 'logs')
        self.assertFalse(config.report_output.exists())

    def test_custom_output_cannot_overlap_source(self):
        for key in ('report_output', 'stamp_output', 'log_output'):
            with self.subTest(key=key):
                self.data[key] = './inputs/stamps'
                self.save()
                with self.assertRaises(ValueError):
                    Settings('anno117', self.config).validate('stamps')
                del self.data[key]

    def test_demo_keeps_custom_outputs_separate(self):
        from anno_demo import demo_settings
        self.data.update(report_output='./Auswertung', stamp_output='./Stempel', log_output='./logs')
        self.save()
        config = Settings('anno117', self.config)
        demo = demo_settings(config, PROJECT)
        self.assertEqual(demo.report_output, config.output / 'demo/reports')
        self.assertEqual(demo.stamp_output, config.output / 'demo/stamps')
        self.assertEqual(demo.log_output, config.output / 'demo/logs')
        self.assertEqual(config.report_output, self.root / 'Auswertung')

    def test_stamps_do_not_require_an_account(self):
        del self.data['account']
        self.save()
        Settings('anno117', self.config).validate('stamps')
        with self.assertRaises(ValueError):
            Settings('anno117', self.config).validate('analyze')

    def test_input_output_overlap_is_rejected_in_both_directions(self):
        for output in [self.inputs, self.inputs / 'stamps', self.inputs / 'stamps/output']:
            with self.subTest(output=output), self.assertRaises(ValueError):
                protect_output(output, [self.inputs / 'stamps'])

    def test_code_output_is_rejected(self):
        for output in [PROJECT, ROOT, PROJECT / 'tools/result']:
            with self.subTest(output=output), self.assertRaises(ValueError):
                protect_output(output, [])

    def test_different_games_cannot_reuse_existing_output(self):
        output = self.root / 'outputs/anno117'
        output.mkdir(parents=True)
        (output / '.annoorganizer-game.json').write_text('{"game":"anno1800"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            Settings('anno117', self.config).validate('stamps')

    def test_marker_missing_is_rejected_without_writing(self):
        (self.inputs / 'game/config.rda').unlink()
        with self.assertRaises(ValueError):
            Settings('anno117', self.config).validate('stamps')
        self.assertFalse((self.root / 'outputs').exists())

    def test_bom_supported_and_unknown_version_rejected(self):
        self.config.write_text(json.dumps(self.data), encoding='utf-8-sig')
        Settings('anno117', self.config)
        self.data['version'] = 99
        self.save()
        with self.assertRaises(ValueError):
            Settings('anno117', self.config)

    def test_home_placeholder(self):
        self.assertEqual(Settings('anno117', self.config).expand('${HOME}/test'), Path.home() / 'test')

    @unittest.skipUnless(os.name == 'nt', 'Windows starter')
    def test_check_command_does_not_create_output(self):
        result = subprocess.run([sys.executable, str(ROOT / 'launch.py'), '--game', 'anno117',
                                 '--action', 'stamps', '--check', '--config', str(self.config)],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'outputs').exists())

    def test_create_settings_keeps_existing_file(self):
        before = self.config.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / 'launch.py'), '--game', 'anno117', '--init-settings',
                                 '--config', str(self.config)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
