"""Check shared catalogue exports, card metadata and interactive regressions."""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Catalog(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.cards = []
        self.groups = []
        self.seeds = []
        self.bindings = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article':
            self.cards.append(attrs)
        if attrs.get('class') == 'stat-group':
            self.groups.append(attrs)
        if 'data-filter' in attrs:
            self.seeds.append(attrs['data-filter'])
        if attrs.get('data-i18n') == 'map.showSeeds':
            self.bindings.append(json.loads(attrs['data-i18n-params']))


class MapCatalogTests(unittest.TestCase):
    def test_exported_cards_keep_profile_and_sort_data_with_statistics(self):
        for game in ('anno117', 'anno1800'):
            with self.subTest(game=game):
                page = (ROOT/'site'/game/'maps/index.html').read_text(encoding='utf-8')
                parsed = Catalog(page)
                self.assertTrue(parsed.cards)
                self.assertEqual(len(parsed.groups), 4 * len(parsed.cards))
                self.assertTrue(all('open' not in attrs for attrs in parsed.groups))
                for attrs in parsed.cards:
                    self.assertTrue(json.loads(attrs['data-profiles']))
                    for key in ('seed', 'variant', 'first', 'latest', 'record-date', 'record-time', 'latest-time'):
                        self.assertIsInstance(float(attrs['data-' + key]), float)
                self.assertEqual(set(parsed.seeds), {attrs['data-seed'] for attrs in parsed.cards})
                self.assertEqual(parsed.bindings, [{'count': len(parsed.seeds)}])
                # The newly shipped cards deliberately omit the obsolete paragraph.
                self.assertNotIn('<p class="profiles"', page)

    def test_game_exporters_share_the_card_and_page_renderer(self):
        for game in ('anno117', 'anno1800'):
            source = (ROOT/game/'tools/analyze_saves.py').read_text(encoding='utf-8')
            self.assertIn('from anno_map_catalog import render_card, render_catalog_page', source)
            self.assertIn('parts.append(render_card(' if game == 'anno1800' else 'cards.append(render_card(', source)
            self.assertNotIn('map_gallery_template.html', source)
        self.assertFalse((ROOT/'anno117/tools/map_gallery_template.html').exists())

    def test_catalogue_renders_in_an_isolated_game_bundle(self):
        for game in ('anno117', 'anno1800'):
            with self.subTest(game=game), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)/game
                tools = project/'tools'
                tools.mkdir(parents=True)
                (project/'docs/images').mkdir(parents=True)
                for name in ('anno_gallery.py', 'anno_i18n.py', 'anno_save_summary.py', 'anno_map_catalog.py'):
                    shutil.copyfile(ROOT/game/'tools'/name, tools/name)
                shutil.copytree(ROOT/game/'tools/gallery_templates', tools/'gallery_templates')
                shutil.copyfile(ROOT/game/'docs/images/game-logo.png', project/'docs/images/game-logo.png')
                program = '''
from datetime import datetime, timezone
from anno_map_catalog import render_card, render_catalog_page
name = '<private> @@CARDS@@'
card = render_card(7, 1, 'Sandkasten', [name], name,
                   dict(first=1, latest=2, recordTime=3), [], 1, '', '', '')
page = render_catalog_page(GAME, [card], [7], 1, datetime.now(timezone.utc), '0:01:00', '')
assert '&lt;private&gt; @@CARDS@@' in page
assert 'id="map-catalog-runtime"' in page
assert 'id="gallery-language-resources"' in page
assert 'class="seed-list"' in page
'''.replace('GAME', repr(game))
                result = subprocess.run([sys.executable, '-X', 'utf8', '-c', program], cwd=tools,
                                        capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for catalogue runtime tests')
    def test_runtime_search_profile_navigation_and_sorting(self):
        subprocess.run(['node', '--test', str(ROOT/'tests/map_catalog_runtime.cjs')], cwd=ROOT,
                       check=True, capture_output=True, text=True, encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
