"""Use runtime DDS graphics consistently and reuse matching decoded terrain."""
from io import BytesIO
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('map117_terrain', ROOT / 'anno117/tools/analyze_saves.py')
maps = importlib.util.module_from_spec(spec)
with patch.object(sys, 'path', [str(ROOT / 'anno117/tools'), *sys.path]), patch.dict(sys.modules):
    for name in list(sys.modules):
        if name.startswith('anno_'):
            del sys.modules[name]
    spec.loader.exec_module(maps)


ISLAND = 'islands/roman_island_continental_01/roman_island_continental_01.a7m'
KEY = 'islands/roman_island_continental_01/_gamedata/roman_island_continental_01/gamemapimage'


def graphic(color):
    stream = BytesIO()
    Image.new('RGBA', (24, 24), color).save(stream, format='PNG')
    return stream.getvalue()


def mapper(root):
    result = maps.Maps.__new__(maps.Maps)
    result.directory = root / 'images'
    result.cache_directory = root / 'cache'
    result.assets = {KEY + '_0.dds': (str(root / 'game.rda'), 'dds'),
                     KEY + '.png': (str(root / 'game.rda'), 'png')}
    return result


class TerrainGraphicsTests(unittest.TestCase):
    def test_region_palettes_keep_dark_terrain_below_the_previous_brightness(self):
        from PIL import ImageStat
        image = Image.new('RGBA', (5, 1))
        image.putdata([(value, value, value, 255) for value in (80, 110, 140, 170, 200)])
        for province, expected in (('roman', 155), ('celtic', 145), ('egypt', 165)):
            with self.subTest(province=province):
                result = maps.harmonize_terrain(image, province)
                self.assertAlmostEqual(ImageStat.Stat(result.convert('L')).mean[0], expected, delta=1)
                self.assertEqual(result.getchannel('A').tobytes(), image.getchannel('A').tobytes())

    def test_all_three_provinces_apply_their_palette_when_loading_dds(self):
        with tempfile.TemporaryDirectory() as directory:
            for province in ('roman', 'celtic', 'egypt'):
                with self.subTest(province=province):
                    instance = mapper(Path(directory))
                    instance.cache_directory = None
                    island = f'data/base/provinces/{province}/islands/sample/sample.a7m'
                    key = f'data/base/provinces/{province}/islands/sample/_gamedata/sample/gamemapimage_0.dds'
                    instance.assets = {key: ('game.rda', 'dds')}
                    with patch.object(maps, 'read_asset', return_value=graphic('green')), \
                            patch.object(maps, 'harmonize_terrain', wraps=maps.harmonize_terrain) as match:
                        self.assertIsNotNone(instance.tile(island))
                        match.assert_called_once()
                        self.assertEqual(match.call_args.args[1], province)

    def test_aegyptus_frames_all_four_quadrants_without_top_or_right_water(self):
        from PIL import ImageFont
        default_font = ImageFont.load_default()
        colors = {'x0_y0': 'blue', 'x0_y1': 'red', 'x1_y0': 'yellow', 'x1_y1': 'green'}
        def quadrant(island):
            name = Path(island).stem[-5:]
            return Image.new('RGBA', (16, 16), colors[name])
        region = dict(guid=149679, size=[2560, 2560], shift=[0, 0], islands=[])
        with tempfile.TemporaryDirectory() as directory:
            instance = mapper(Path(directory))
            instance.directory.mkdir()
            with patch.object(instance, 'tile', side_effect=quadrant), \
                    patch('PIL.ImageFont.truetype', return_value=default_font):
                result = instance.render(region)
            with Image.open(instance.directory / Path(result['path']).name) as image:
                self.assertEqual(image.size, (868, 924))
                for point, color in (((100, 100), (255, 0, 0)), ((800, 100), (0, 128, 0)),
                                     ((100, 800), (0, 0, 255)), ((800, 800), (255, 255, 0))):
                    self.assertEqual(image.getpixel(point), color)
        self.assertEqual(region['size'], [2560, 2560])
        self.assertEqual(maps.map_view_size(dict(guid=3245, size=[2688, 2688])), (2688, 2688))
        self.assertEqual(maps.map_view_size(dict(guid=6627, size=[2032, 2032])), (2032, 2032))

    def test_tone_matching_reduces_the_gap_between_bright_and_dark_terrain(self):
        from PIL import ImageStat
        images = []
        for values in ((50, 80, 110, 140, 170), (130, 160, 190, 220, 250)):
            image = Image.new('RGBA', (5, 1))
            image.putdata([(value, value, value, 255) for value in values])
            images.append(image)
        before = [ImageStat.Stat(image.convert('L')).mean[0] for image in images]
        after = [ImageStat.Stat(maps.harmonize_terrain(image).convert('L')).mean[0]
                 for image in images]
        self.assertLess(abs(after[1] - after[0]), abs(before[1] - before[0]) / 4)

    def test_tone_matching_preserves_alpha_neutral_rocks_and_shading_order(self):
        image = Image.new('RGBA', (6, 1))
        pixels = [(40, 40, 40, 0), (60, 60, 60, 128),
                  (80, 80, 80, 255), (120, 120, 120, 255),
                  (160, 160, 160, 255), (200, 200, 200, 255)]
        image.putdata(pixels)
        result = maps.harmonize_terrain(image)
        self.assertEqual(result.getchannel('A').tobytes(), image.getchannel('A').tobytes())
        levels = []
        for x in range(6):
            red, green, blue, _ = result.getpixel((x, 0))
            self.assertEqual((red, green), (blue, blue))
            levels.append(red)
        self.assertEqual(levels, sorted(set(levels)))
        self.assertEqual(image.getpixel((2, 0)), pixels[2])

    def test_black_placeholders_do_not_bias_tone_matching(self):
        terrain = Image.new('RGBA', (10, 10), (100, 130, 60, 255))
        padded = Image.new('RGBA', (100, 100), (0, 0, 0, 255))
        padded.paste(terrain, (0, 0))
        result = maps.harmonize_terrain(padded)
        self.assertEqual(result.getpixel((0, 0)), maps.harmonize_terrain(terrain).getpixel((0, 0)))
        self.assertEqual(result.getpixel((99, 99)), (0, 0, 0, 255))

    def test_runtime_dds_is_required_even_when_a_png_preview_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for use_dds in (True, False):
                instance = mapper(root)
                instance.cache_directory = None
                if not use_dds:
                    del instance.assets[KEY + '_0.dds']
                with patch.object(maps, 'read_asset', return_value=graphic('green')) as read:
                    image = instance.tile(ISLAND)
                    if use_dds:
                        self.assertEqual(image.getpixel((0, 0)), (0, 128, 0, 255))
                        self.assertEqual(read.call_args.args[0][-1], 'dds')
                    else:
                        self.assertIsNone(image)
                        read.assert_not_called()

    def test_regular_islands_are_cached_across_exporters_too(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'game.rda').write_bytes(b'game')
            regular = ISLAND.replace('continental', 'small')
            key = KEY.replace('continental', 'small')
            with patch.object(maps, 'read_asset', return_value=graphic('green')) as read:
                for _ in range(2):
                    instance = mapper(root)
                    instance.assets = {key + '_0.dds': (str(root / 'game.rda'), 'dds')}
                    self.assertIsNotNone(instance.tile(regular))
                self.assertEqual(read.call_count, 1)

    def test_continent_cache_survives_exporters_and_invalidates_after_game_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'game.rda'
            archive.write_bytes(b'game version one')
            with patch.object(maps, 'read_asset', return_value=graphic('green')) as read:
                mapper(root).tile(ISLAND)
                mapper(root).tile(ISLAND)
                self.assertEqual(read.call_count, 1)
                archive.write_bytes(b'game version two with changed resources')
                mapper(root).tile(ISLAND)
                self.assertEqual(read.call_count, 2)

    def test_damaged_cached_image_is_regenerated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'game.rda').write_bytes(b'game')
            with patch.object(maps, 'read_asset', return_value=graphic('green')) as read:
                mapper(root).tile(ISLAND)
                next((root / 'cache').glob('*.png')).write_bytes(b'incomplete cache')
                image = mapper(root).tile(ISLAND)
                self.assertEqual(image.getpixel((0, 0)), (0, 128, 0, 255))
                self.assertEqual(read.call_count, 2)

    def test_aegyptus_softens_land_overlap_without_changing_water_or_placeholders(self):
        tile = Image.new('RGBA', (40, 40), (200, 180, 140, 255))
        for background in ((100, 90, 70, 255), (100, 90, 70, 128),
                           (0, 0, 0, 0), (0, 0, 0, 255)):
            with self.subTest(background=background):
                layer = Image.new('RGBA', (60, 60), background)
                maps.composite_terrain(layer, tile, (10, 10))
                self.assertEqual(layer.getpixel((30, 30)), tile.getpixel((20, 20)))
                self.assertEqual(layer.getpixel((0, 0)), background)
                if background[0] == 100 and background[3] == 255:
                    edge = layer.getpixel((10, 30))
                    self.assertTrue(100 < edge[0] < 200)
                    self.assertEqual(edge[3], 255)
                else:
                    self.assertEqual(layer.getpixel((10, 30)), tile.getpixel((0, 20)))


if __name__ == '__main__':
    unittest.main()
