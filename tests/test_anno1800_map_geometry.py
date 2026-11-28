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


if __name__ == '__main__':
    unittest.main()
