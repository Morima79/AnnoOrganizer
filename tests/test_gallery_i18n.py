"""Check portable localisation, message coverage and identity preservation."""
from html import escape
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('i18n_tests', ROOT / 'templates/anno_i18n.py')
i18n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i18n)


class Bindings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.options = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for name, key in attrs.items():
            if name == 'data-i18n' or name in ('data-i18n-placeholder', 'data-i18n-alt', 'data-i18n-title', 'data-i18n-aria-label', 'data-i18n-content'):
                self.messages.append((key, json.loads(attrs.get(name + '-params', '{}'))))
        if tag == 'option':
            self.options.append(attrs)


class GalleryLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources = i18n.load_resources(ROOT / 'templates/locales')

    def test_incomplete_translation_or_parameters_fail_before_export(self):
        for change in ('key', 'placeholder'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                data = {language: dict(messages) for language, messages in self.resources.items()}
                if change == 'key':
                    del data['en']['stamp.count']
                else:
                    data['en']['stamp.count'] = '{wrong} stamps'
                for language, messages in data.items():
                    (Path(directory) / (language + '.json')).write_text(json.dumps(messages), encoding='utf-8')
                with self.assertRaises(ValueError):
                    i18n.load_resources(directory)

    def test_named_identities_and_filter_values_are_not_translated(self):
        source = ('<article data-profiles="[&quot;Klein&quot;]" data-folder="Alle Ordner">'
                  '<h2>Klein</h2><p class="crumb">Alte Welt / Alle Ordner</p>'
                  '<p class="profiles">Klein</p><p class="source">Klein</p>'
                  '<a data-profile-filter="Klein">Klein</a>'
                  '<p data-i18n-ignore>Klein</p><span>Keine CDLC</span></article>'
                  '<select><option>Sandkasten</option><option value="no">Keine CDLC</option></select>')
        page = i18n.bind_messages(source, self.resources, 'stamp')
        for identity in ('<h2>Klein</h2>', '<p class="profiles">Klein</p>', '<p class="source">Klein</p>',
                         '<a data-profile-filter="Klein">Klein</a>', '<p data-i18n-ignore>Klein</p>'):
            self.assertIn(identity, page)
        self.assertIn(' / Alle Ordner</p>', page)
        parser = Bindings()
        parser.feed(page)
        self.assertEqual([option['value'] for option in parser.options], ['Sandkasten', 'no'])
        self.assertIn('data-i18n="stamp.noCdlc"', page)
        self.assertEqual(page, i18n.bind_messages(page, self.resources, 'stamp'))

    def test_placeholder_data_is_escaped_and_keeps_user_names(self):
        name = 'Klein </script><img src=x onerror=alert(1)> " &'
        source = '<button aria-label="' + escape('Bauplan ' + name + ' öffnen', quote=True) + '">Open</button>'
        page = i18n.bind_messages(source, self.resources, 'stamp')
        parser = Bindings()
        parser.feed(page)
        self.assertIn(('stamp.open', {'name': name}), parser.messages)
        self.assertNotIn('<img', page)
        encoded = i18n.script_json({'name': name})
        self.assertNotIn('</script', encoded)
        self.assertEqual(json.loads(encoded)['name'], name)

    def test_text_entities_and_self_closing_images_keep_valid_bindings(self):
        page = i18n.bind_messages('<p>A &amp; B: 92 statt 60 Feldkacheln</p>'
                                 '<p data-i18n-ignore>&lt;img src=x onerror=alert(1)&gt;</p>'
                                 '<img src="test.png" alt="Bauplan A &amp; B"/>', self.resources, 'stamp')
        parser = Bindings()
        parser.feed(page)
        self.assertIn(('stamp.fieldDetails', {'name': 'A & B', 'actual': '92', 'normal': '60'}), parser.messages)
        self.assertIn(('stamp.alt', {'name': 'A & B'}), parser.messages)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', page)
        self.assertNotIn('/ data-i18n', page)
        self.assertEqual(page, i18n.bind_messages(page, self.resources, 'stamp'))

    def test_all_six_demo_pages_embed_complete_resources_and_valid_bindings(self):
        pages = list((ROOT / 'site').rglob('index.html'))
        self.assertEqual(len(pages), 6)
        for page in pages:
            with self.subTest(page=page):
                text = page.read_text(encoding='utf-8')
                resources = re.search(r'<script id="gallery-language-resources" type="application/json">(.*?)</script>', text, re.S)
                self.assertIsNotNone(resources)
                self.assertEqual(json.loads(resources[1]), self.resources)
                self.assertEqual(text.count('id="gallery-i18n"'), 1)
                switches = 2 if page.parent != ROOT / 'site' else 1
                self.assertEqual(text.count('data-gallery-language="de"'), switches)
                self.assertEqual(text.count('data-gallery-language="en"'), switches)
                self.assertNotRegex(text, r'<script[^>]+src=')
                self.assertIn('gallerylanguagechange', text)
                parser = Bindings()
                parser.feed(text)
                self.assertGreater(len(parser.messages), 15 if page.parent == ROOT / 'site' else 30)
                for key, params in parser.messages:
                    self.assertIn(key, self.resources['de'])
                    # Missing substitutions must be detected, rather than shown as braces.
                    self.resources['en'][key].format(**params)
                for key in re.findall(r"galleryI18n\.t\('([^']+)'", text):
                    self.assertIn(key, self.resources['de'])

    def test_landing_page_is_generated_from_shared_resources_and_keeps_five_links(self):
        spec = importlib.util.spec_from_file_location('landing_sync', ROOT / 'scripts/sync_gallery_templates.py')
        sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        text = (ROOT / 'site/index.html').read_text(encoding='utf-8')
        self.assertEqual(text, sync.render_landing_page())
        self.assertIn('<html lang="de-CH">', text)
        self.assertIn('data-i18n-content="demo.meta"', text)
        self.assertIn('annotools.gallery.language', text)
        self.assertNotIn('Gallery text is currently German', text)
        self.assertNotIn('Die Galerien sind auf Deutsch', text)
        links = re.findall(r'href="(anno\d+/(?:maps|stamps)/)"', text)
        self.assertEqual(sorted(links), ['anno117/maps/', 'anno117/stamps/', 'anno1404/maps/',
                                         'anno1800/maps/', 'anno1800/stamps/'])

    def test_renderer_preserves_domain_scripts_and_data_on_refresh(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            spec = importlib.util.spec_from_file_location('render_' + game, ROOT / game / 'tools/anno_gallery.py')
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)
            for folder in ('maps', 'stamps') if game != 'anno1404' else ('maps',):
                text = (ROOT / 'site' / game / folder / 'index.html').read_text(encoding='utf-8')
                self.assertEqual(text, renderer.render_gallery(text, game, 'map' if folder == 'maps' else 'stamp'))

    def test_all_five_exporters_create_bilingual_pages_without_game_data(self):
        # Separate interpreters preserve each standalone game's import environment.
        program = '''
import importlib.util, sys, tempfile, os, json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
game, kind = sys.argv[1:]
tools = Path(game) / 'tools'
sys.path.insert(0, str(tools.resolve()))
source = tools / ('analyze_saves.py' if kind == 'map' else 'build_stamp_gallery.py')
spec = importlib.util.spec_from_file_location('exporter_fixture', source)
module = importlib.util.module_from_spec(spec)
with tempfile.TemporaryDirectory() as directory:
    stage = Path(directory)
    settings = json.loads((Path(game) / 'settings.example.json').read_text(encoding='utf-8'))
    (stage / 'settings.json').write_text(json.dumps(settings), encoding='utf-8')
    os.environ['ANNOTOOLS_SETTINGS'] = str(stage / 'settings.json')
    spec.loader.exec_module(module)
    if kind == 'stamp':
        module.CONFIG = SimpleNamespace(stamp_output=stage)
        module.write_gallery([])
    elif game == 'anno117':
        module.write_html([], 0, stage, datetime.now(timezone.utc), '0:00:00', [])
    elif game == 'anno1404':
        module.write_html(stage, dict(ranking=[], rows=[], editions={}, sources=[], updated='22.11.2026 10:00', total='0:00:00', note='0 Seeds · 0 Kartenvarianten · 0 Spielstände'))
    else:
        module.index_game = lambda: {}
        module.ACCOUNT = stage / 'accounts'
        module.render_catalog([], [], [], stage, datetime.now(timezone.utc), '0:00:00', [])
    page = (stage / ('map-gallery.html' if kind == 'map' else 'stamp-gallery.html')).read_text(encoding='utf-8')
    assert 'id="gallery-language-resources"' in page
    assert 'gallerylanguagechange' in page
    assert 'galleryI18n.t(' in page
    assert 'data-gallery-language="en"' in page
    assert '@@' not in page
    assert '__COUNT__' not in page
    assert '__INVENTORY__' not in page
'''
        for game in ('anno117', 'anno1800', 'anno1404'):
            for kind in ('map', 'stamp') if game != 'anno1404' else ('map',):
                with self.subTest(game=game, kind=kind):
                    result = subprocess.run([sys.executable, '-X', 'utf8', '-c', program, game, kind],
                                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed to execute the browser runtime unit tests')
    def test_javascript_runtime_offline_storage_and_state(self):
        subprocess.run(['node', '--test', str(ROOT / 'tests/gallery_i18n_runtime.cjs')],
                       cwd=ROOT, check=True, capture_output=True, text=True, encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
