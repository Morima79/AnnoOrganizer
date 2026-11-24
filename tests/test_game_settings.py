"""Protect game-specific enum IDs, localisation contexts and unknown raw values."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('game_labels_test', ROOT/'templates/anno_game_settings.py')
labels = importlib.util.module_from_spec(spec)
spec.loader.exec_module(labels)


class GameSettingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT/'templates/game_settings.json').read_text(encoding='utf-8'))
        cls.messages = {lang: json.loads((ROOT/'templates/locales'/f'{lang}.json').read_text(encoding='utf-8'))
                        for lang in ('de', 'en')}

    def test_catalog_keys_are_bilingual_and_have_enum_provenance(self):
        for game, options in self.catalog['games'].items():
            self.assertTrue(options)
            for key, option in options.items():
                with self.subTest(game=game, option=key):
                    for lang in ('de', 'en'):
                        self.assertIn(option['label'], self.messages[lang])
                    if option['label_origin'] == 'game':
                        self.assertIsNotNone(option['label_id'])
                    for value in option['values'].values():
                        self.assertTrue(value['enum'])
                        self.assertIn(value['key'], self.messages['de'])
                        self.assertIn(value['key'], self.messages['en'])

    def test_117_setup_island_size_and_generated_island_size_use_different_enums(self):
        self.assertEqual(labels.value('anno117', 'SetupStartSessionIslandSize', [0]), 'Groß')
        self.assertEqual(labels.value('anno117', 'GeneratedIslandSize', [0]), 'Klein')
        self.assertEqual(labels.value('anno117', 'SetupStartSessionIslandSize', [2]), 'Klein')
        self.assertEqual(labels.value('anno117', 'SetupResearchSpeed', [7]), 'Normal')
        self.assertEqual(labels.value('anno117', 'SetupRelocateBuildings', [2]), 'Gebührenpflichtig')

    def test_1800_island_sizes_are_not_world_size_labels(self):
        self.assertEqual(labels.value('anno1800', 'SetupStartSession', [0]), 'Klein')
        self.assertEqual(labels.value('anno1800', 'SetupStartSessionIslandSize', [0]), 'Mehrheitlich klein')
        self.assertEqual(labels.name('anno1800', 'SetupRawMaterial'), 'Erzvorkommen')
        self.assertEqual(labels.value('anno1800', 'SetupFertility', [0]), 'Spärlich')

    def test_1404_choices_use_declared_zero_based_order_and_keep_unknown_masks_raw(self):
        self.assertEqual(labels.value('anno1404', 'WorldSize', ['3']), 'riesig')
        self.assertEqual(labels.value('anno1404', 'StartCredit', ['3']), 'sehr viel')
        self.assertEqual(labels.value('anno1404', 'IslandDifficulty', ['1']), 'normal')
        self.assertIn('99', labels.value('anno1404', 'WorldSize', ['99'], html=True))
        self.assertIn('setting.unknownValue', labels.value('anno1404', 'Disasters', ['31'], html=True))

    def test_unknown_values_and_identity_like_strings_are_never_relabelled(self):
        raw = '<Player & "1">'
        html = labels.value('anno117', 'UnknownSetting', [raw], html=True)
        self.assertIn('&lt;Player &amp; &quot;1&quot;&gt;', html)
        self.assertIn('data-i18n-ignore', html)
        self.assertIn('setting.unknownValue', html)
        self.assertNotIn('<Player', html)
        self.assertIn('stats.unavailable', labels.value('anno117', 'SetupFertility', [], html=True))

    def test_each_game_loads_labels_without_the_repository_or_game_installation(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            with self.subTest(game=game), tempfile.TemporaryDirectory() as directory:
                tools = Path(directory)/'tools'
                folder = tools/'gallery_templates'
                (folder/'locales').mkdir(parents=True)
                shutil.copyfile(ROOT/game/'tools/anno_game_settings.py', tools/'anno_game_settings.py')
                shutil.copyfile(ROOT/game/'tools/gallery_templates/game_settings.json', folder/'game_settings.json')
                shutil.copyfile(ROOT/game/'tools/gallery_templates/locales/de.json', folder/'locales/de.json')
                isolated_spec = importlib.util.spec_from_file_location('isolated_labels', tools/'anno_game_settings.py')
                module = importlib.util.module_from_spec(isolated_spec)
                isolated_spec.loader.exec_module(module)
                key = 'WorldSize' if game == 'anno1404' else 'SetupFertility'
                self.assertTrue(module.name(game, key))
                self.assertIn('data-i18n=', module.value(game, key, [0], html=True))

    def test_scoped_normal_translations_do_not_change_generic_message_binding(self):
        i18n_spec = importlib.util.spec_from_file_location('settings_i18n', ROOT/'templates/anno_i18n.py')
        i18n = importlib.util.module_from_spec(i18n_spec)
        i18n_spec.loader.exec_module(i18n)
        page = i18n.bind_messages('<p>Normal</p>' + labels.value('anno117', 'SetupFertility', [1], html=True)
                                  + labels.value('anno1404', 'IslandDifficulty', [1], html=True), self.messages, 'map')
        self.assertIn('data-i18n="value.normal"', page)
        self.assertIn('gameSetting.anno117.SetupFertility.value.1', page)
        self.assertIn('gameSetting.anno1404.IslandDifficulty.value.1', page)
        self.assertEqual(self.messages['en']['gameSetting.anno117.SetupFertility.value.1'], 'Regular')
        self.assertEqual(self.messages['en']['gameSetting.anno1404.IslandDifficulty.value.1'], 'medium')


if __name__ == '__main__':
    unittest.main()
