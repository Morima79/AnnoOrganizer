"""Check uniform sea colours and refresh existing maps after renderer changes."""
from array import array
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('map1404_colors', ROOT / 'anno1404/tools/analyze_saves.py')
maps = importlib.util.module_from_spec(spec)
# Standalone game modules must not replace another game's settings in the suite.
with patch.object(sys, 'path', [str(ROOT / 'anno1404/tools'), *sys.path]), patch.dict(sys.modules):
    for name in list(sys.modules):
        if name.startswith('anno_'):
            del sys.modules[name]
    spec.loader.exec_module(maps)


class MapColourTests(unittest.TestCase):
    def test_open_sea_and_island_water_share_a_colour_without_changing_land(self):
        values = array('h', [-32768, -4097, -4096, -1, 0, 1, 339, 340, 1100, 2500, 4000])
        if sys.byteorder != 'little':
            values.byteswap()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'map.png'
            maps.draw_map(target, len(values), 1, memoryview(values.tobytes()))
            with Image.open(target) as image:
                self.assertEqual(image.size, (len(values), 1))
                self.assertEqual([image.getpixel((x, 0)) for x in range(len(values))], [maps.WATER_COLOR] * 5 + [
                    (203, 183, 129), (203, 183, 129), (116, 151, 85),
                    (85, 119, 66), (115, 113, 82), (161, 148, 113)])

    def test_old_cache_and_explicit_rescan_redraw_existing_images(self):
        source = ROOT / 'anno1404/demo/saves/Demo-03/demo-03.sww'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = root / 'initial'
            output = root / 'output'
            for folder in (initial, output):
                (folder / 'map-images').mkdir(parents=True)
            data = maps.read_save(source, initial, output)
            (output / data['map']).write_bytes(b'previously rendered map')
            stat = source.stat()
            item = dict(fingerprint=[stat.st_mtime_ns, stat.st_size], data=data)
            for version, refresh in ((maps.CACHE_VERSION - 1, False), (maps.CACHE_VERSION, True)):
                with self.subTest(version=version, refresh=refresh):
                    (output / maps.CACHE).write_text(json.dumps(dict(
                        version=version, files={str(source.resolve()): item})), encoding='utf-8')
                    stage = root / str(version)
                    (stage / 'map-images').mkdir(parents=True)
                    saves, count = maps.collect([source.parent], stage, output, refresh)
                    self.assertEqual(count, 1)
                    self.assertEqual(saves[0]['variant'], data['variant'])
                    with Image.open(stage / data['map']) as image:
                        self.assertEqual(image.getpixel((0, 0)), maps.WATER_COLOR)
