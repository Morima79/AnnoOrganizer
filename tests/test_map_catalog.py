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
        self.campaigns = []
        self.top_links = []
        self.selected_sort = []
        self.details_depth = 0
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details':
            self.details_depth += 1
        if tag == 'section' and attrs.get('class') == 'campaign-statistics':
            self.campaigns.append(attrs['data-campaign'])
        if tag == 'a' and attrs.get('href') == '#gallery-top':
            self.top_links.append(self.details_depth)
        if tag == 'option' and 'selected' in attrs:
            self.selected_sort.append(attrs['value'])
        if tag == 'article':
            self.cards.append(attrs)
        if attrs.get('class') == 'stat-group':
            self.groups.append(attrs)
        if 'data-filter' in attrs:
            self.seeds.append(attrs['data-filter'])
        if attrs.get('data-i18n') == 'map.showSeeds':
            self.bindings.append(json.loads(attrs['data-i18n-params']))

    def handle_endtag(self, tag):
        if tag == 'details':
            self.details_depth -= 1


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
                    for key in ('seed', 'variant', 'first', 'latest', 'total-time'):
                        self.assertIsInstance(float(attrs['data-' + key]), float)
                self.assertEqual(set(parsed.seeds), {attrs['data-seed'] for attrs in parsed.cards})
                self.assertEqual(parsed.bindings, [{'count': len(parsed.seeds)}])
                # The newly shipped cards deliberately omit the obsolete paragraph.
                self.assertNotIn('<p class="profiles"', page)
                self.assertEqual(len(parsed.campaigns), len(set(parsed.campaigns)))
                self.assertEqual(parsed.selected_sort, ['latest'])
                dates = [float(attrs['data-latest']) for attrs in parsed.cards]
                self.assertEqual(dates, sorted(dates, reverse=True))

    def test_every_map_card_has_an_unconditional_native_link_to_the_top(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            page = (ROOT/'site'/game/'maps/index.html').read_text(encoding='utf-8')
            parsed = Catalog(page)
            self.assertIn('id="gallery-top"', page)
            self.assertEqual(parsed.top_links, [0] * len(parsed.cards))

    def test_game_exporters_share_the_card_and_page_renderer(self):
        for game in ('anno117', 'anno1800'):
            source = (ROOT/game/'tools/analyze_saves.py').read_text(encoding='utf-8')
            self.assertIn('from anno_map_catalog import render_card, render_catalog_page', source)
            self.assertIn('parts.append(render_card(' if game == 'anno1800' else 'cards.append(render_card(', source)
            self.assertNotIn('map_gallery_template.html', source)
        self.assertFalse((ROOT/'anno117/tools/map_gallery_template.html').exists())

    def test_exporters_keep_current_dates_and_values_in_their_own_variant(self):
        program = '''
import importlib.util, json, os, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
game = sys.argv[1]
sys.path.insert(0, str((Path(game)/'tools').resolve()))
with tempfile.TemporaryDirectory() as directory:
    stage = Path(directory)
    config = stage/'settings.json'
    config.write_text((Path(game)/'settings.example.json').read_text(encoding='utf-8'), encoding='utf-8')
    os.environ['ANNOORGANIZER_SETTINGS'] = str(config)
    spec = importlib.util.spec_from_file_location('exporter', Path(game)/'tools/analyze_saves.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from anno_save_statistics import empty_statistics
    summaries = {}
    for campaign, stamp, population, money in [(1, 20, 100, 200), (2, 30, 300, 400)]:
        values = empty_statistics()
        values.update(population=population, money=money, houses=population//10, ships=campaign)
        summaries[f'7:{campaign}'] = dict(campaign=f'7:{campaign}', seed=7, source=f'{campaign}.sav',
                                        profile=f'Player {campaign}', values=values,
                                        date=datetime.fromtimestamp(stamp, timezone.utc).strftime('%d.%m.%Y %H:%M:%S'))
    data = []
    for campaign, stamp, map_type in [(1, 10, 1), (1, 20, 1), (2, 30, 2)]:
        if game == 'anno117':
            setup = dict(GameSeed=[7], SetupMapTemplateType=[map_type])
            if stamp > 10:
                setup.update(ActiveDLCs=[99], SetupContinentalIslandStart=[0])
        else:
            setup = [[['GameSeed'], 7], [['SetupMapType', 'value', 'id'], map_type]]
            if stamp > 10:
                setup += [[['ActiveDLCs', 'DLC'], 99], [['SetupStartWithKontor', 'value', 'id'], 1]]
        data.append(dict(seed=7, campaign_id=campaign, stamp=stamp, time=stamp,
                         play=stamp*1000, play_ms=stamp*1000, active=True, source='Spielkonto',
                         path=f'Player {campaign}/{stamp}.sav', signature=[1, 2, 3, 4], setup=setup))
    if game == 'anno117':
        module.maps_for = lambda path: []
        rows, _ = module.prepare({r['path']: r for r in data}, stage, SimpleNamespace(), timezone.utc, {}, summaries)
        module.write_html(rows, 3, stage, datetime.now(timezone.utc), '0:00:30', [])
    else:
        module.index_game = lambda: {}
        module.ACCOUNT = stage/'accounts'
        rows = module.render_catalog(data, module.bucket(data), [], stage,
                                     datetime.now(timezone.utc), '0:00:30', [], summaries)
    assert len(rows) == 2
    assert {tuple(e['campaign'] for e in r['statistics']) for r in rows} == {('7:1',), ('7:2',)}
    page = (stage/'map-gallery.html').read_text(encoding='utf-8')
    for campaign in ('7:1', '7:2'):
        assert page.count('data-campaign="' + campaign + '"') == 1
    assert '01.01.1970 00:00:20' in page
    assert '01.01.1970 00:00:30' in page
'''
        for game in ('anno117', 'anno1800'):
            with self.subTest(game=game):
                result = subprocess.run([sys.executable, '-X', 'utf8', '-c', program, game], cwd=ROOT,
                                        capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)

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
