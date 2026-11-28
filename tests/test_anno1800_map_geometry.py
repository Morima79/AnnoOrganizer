"""Map graphics must use saved island origins and local terrain bounds."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class IslandImageBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'map1800_geometry', ROOT / 'anno1800/tools/analyze_saves.py')
        cls.exporter = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(ROOT / 'anno1800/tools'), *sys.path]):
            spec.loader.exec_module(cls.exporter)

    def test_continents_reach_the_upper_right_corner_in_the_reported_save(self):
        # Crown Falls and Manola use 768-tile terrain and 64-tile image margins.
        for origin, rotation, session_size in [(1152, 1, 1920), (1472, 0, 2240)]:
            with self.subTest(origin=origin):
                left, bottom, width, height = self.exporter.island_image_bounds(
                    (origin, origin), rotation, (768, 768),
                    (0, 0, 768, 768), (1792, 1792))
                self.assertEqual((left + 64, bottom + 64), (origin, origin))
                self.assertEqual((left + width - 64, bottom + height - 64),
                                 (session_size, session_size))

    def test_asymmetric_active_rect_rotates_inside_the_terrain_bounds(self):
        expected = [(148, 196, 100, 80), (344, 248, 80, 100),
                    (252, 444, 100, 80), (96, 352, 80, 100)]
        for rotation, bounds in enumerate(expected):
            with self.subTest(rotation=rotation):
                self.assertEqual(self.exporter.island_image_bounds(
                    (100, 200), rotation, (300, 320),
                    (64, 16, 132, 56), (200, 160)), bounds)

    def test_regular_island_keeps_the_active_rect_offset_and_image_padding(self):
        self.assertEqual(self.exporter.island_image_bounds(
            (1272, 544), 0, (320, 320), (8, 0, 320, 320), (880, 896)),
            (1216, 480, 440, 448))

    def test_translucent_black_shadow_is_reduced_without_changing_terrain(self):
        from PIL import Image
        image = Image.new('RGBA', (7, 1))
        pixels = [(0, 0, 0, 0), (0, 0, 0, 128), (0, 0, 0, 253),
                  (0, 0, 0, 255), (12, 10, 8, 128),
                  (130, 160, 80, 255), (130, 160, 80, 128)]
        image.putdata(pixels)
        result = self.exporter.reduce_island_shadow(image)
        self.assertEqual(result.size, image.size)
        self.assertEqual(result.getpixel((1, 0)), (0, 0, 0, 32))
        self.assertEqual(result.getpixel((2, 0)), (0, 0, 0, 63))
        for x in (0, 3, 4, 5, 6):
            self.assertEqual(result.getpixel((x, 0)), pixels[x])
        self.assertEqual(image.getpixel((1, 0)), pixels[1])

    def test_reduced_shadow_blends_into_the_sea_without_changing_the_coast(self):
        from PIL import Image
        source = Image.new('RGBA', (2, 1))
        source.putdata([(0, 0, 0, 200), (110, 140, 70, 255)])
        sea = Image.new('RGBA', source.size, (18, 58, 76, 255))
        before = Image.alpha_composite(sea, source)
        after = Image.alpha_composite(sea, self.exporter.reduce_island_shadow(source))
        self.assertEqual(after.getpixel((1, 0)), before.getpixel((1, 0)))
        self.assertGreater(after.getpixel((0, 0))[2], before.getpixel((0, 0))[2])

    def test_enbesa_trims_all_sides_with_a_margin_around_the_saved_terrain(self):
        boxes = [(320, 328, 900, 1000), (1000, 1100, 1704, 1728)]
        view = self.exporter.island_map_view(112132, (2048, 2048), boxes)
        self.assertEqual(view, (256, 264, 1768, 1792))
        for left, bottom, right, top in boxes:
            self.assertLessEqual(view[0], left - 64)
            self.assertLessEqual(view[1], bottom - 64)
            self.assertGreaterEqual(view[2], right + 64)
            self.assertGreaterEqual(view[3], top + 64)

    def test_arctic_trims_left_and_bottom_and_keeps_mainland_edges(self):
        view = self.exporter.island_map_view(
            180045, (1920, 1920), [(336, 408, 1000, 1200), (1152, 1152, 1920, 1920)])
        self.assertEqual(view, (272, 344, 1920, 1920))

    def test_regional_views_preserve_edge_islands_and_fall_back_without_bounds(self):
        for guid in (112132, 180045):
            with self.subTest(guid=guid):
                self.assertEqual(self.exporter.island_map_view(guid, (1920, 1920), []),
                                 (0, 0, 1920, 1920))
                self.assertEqual(self.exporter.island_map_view(guid, (1920, 1920),
                                                              [(20, 24, 1900, 1900)]),
                                 (0, 0, 1920, 1920))
        self.assertEqual(self.exporter.island_map_view(180023, (2048, 2048),
                                                      [(400, 400, 1600, 1600)]),
                         (0, 0, 2048, 2048))


if __name__ == '__main__':
    unittest.main()
