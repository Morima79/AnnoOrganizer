"""Verify that independent exporters and public demos embed the real logo assets."""
import base64
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.logos = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'img' and attributes.get('class') == 'game-logo':
            self.logos.append(attributes)


class BrandingTests(unittest.TestCase):
    def test_demo_branding_and_repository_links_use_current_project(self):
        for language in ('de', 'en'):
            resources = json.loads((ROOT / 'templates/locales' / (language + '.json')).read_text(encoding='utf-8'))
            for key in ('nav.demos', 'demo.title', 'demo.meta', 'demo.eyebrow', 'demo.footer'):
                with self.subTest(language=language, key=key):
                    self.assertIn('AnnoOrganizer', resources[key])
        for page in (ROOT / 'site').rglob('index.html'):
            with self.subTest(page=page):
                text = page.read_text(encoding='utf-8')
                self.assertFalse('AnnoTools' in text, f'Obsolete project name in {page}')
                self.assertIn('annotools.gallery.language', text)
        landing = (ROOT / 'site/index.html').read_text(encoding='utf-8')
        self.assertIn('https://github.com/Morima79/AnnoOrganizer/releases/latest', landing)

    def assert_logo(self, page, game):
        parser = Images()
        parser.feed(page)
        self.assertEqual(len(parser.logos), 1)
        image = parser.logos[0]
        self.assertIn('Anno ', image['alt'])
        self.assertTrue(image['src'].startswith('data:image/png;base64,'))
        data = base64.b64decode(image['src'].split(',', 1)[1], validate=True)
        self.assertEqual(data, (ROOT / game / 'docs/images/game-logo.png').read_bytes())
        self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_each_independent_exporter_embeds_its_logo(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            with self.subTest(game=game):
                spec = importlib.util.spec_from_file_location('branding_' + game,
                                                              ROOT / game / 'tools/anno_gallery.py')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.assert_logo(module.render_gallery('<header><h1>Demo</h1></header>', game, 'map'), game)

    def test_all_five_public_galleries_include_the_correct_logo(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            for page in (ROOT / 'site' / game).rglob('index.html'):
                with self.subTest(page=page):
                    self.assert_logo(page.read_text(encoding='utf-8'), game)


if __name__ == '__main__':
    unittest.main()
