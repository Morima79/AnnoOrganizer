"""Check generated online/offline guides, screenshot assets and language handling."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from sync_gallery_templates import render_page, render_user_guide
from build_desktop import payload_files


class GuideImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))


class UserGuideTests(unittest.TestCase):
    def test_online_and_offline_guides_are_generated_from_the_same_markdown(self):
        for name, online in [('site/guide/index.html', True), ('docs/user-guide.html', False)]:
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding='utf-8')
                self.assertEqual(text, render_user_guide(render_page, online=online))
                self.assertIn('data-guide-language="de"', text)
                self.assertIn('data-guide-language="en" hidden', text)
                self.assertNotIn('<pre>', text)
                self.assertNotIn('@@', text)
                images = GuideImages()
                images.feed(text)
                self.assertEqual(len(images.images), 8)
                for image in images.images:
                    self.assertTrue(image.get('alt'))
                    self.assertTrue((ROOT / name).parent.joinpath(image['src']).is_file())
        for source in (ROOT / 'docs/images').glob('user-guide-117-*.jpg'):
            self.assertEqual(source.read_bytes(), (ROOT / 'site/guide/images' / source.name).read_bytes())

    def test_landing_page_links_to_the_manual_and_packaging_includes_offline_html(self):
        self.assertIn('href="guide/"', (ROOT / 'site/index.html').read_text(encoding='utf-8'))
        guide_files = ['docs/user-guide.html', 'docs/desktop-reference.md', 'docs/desktop-reference.de.md']
        guide_files += [p.relative_to(ROOT).as_posix() for p in (ROOT / 'docs/images').glob('user-guide-117-*.jpg')]
        required = ['desktop/app.py', 'desktop/locales/de.json', 'desktop/locales/en.json',
                    'desktop/assets/annoorganizer.ico', 'LICENSE']
        required += [game + '/tools/anno_worker.py' for game in ('anno117', 'anno1800', 'anno1404')]
        selected = payload_files(ROOT, required + guide_files)
        self.assertTrue(set(guide_files).issubset(selected))

    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for guide runtime tests')
    def test_runtime_language_selection(self):
        subprocess.run(['node', '--test', str(ROOT / 'tests/user_guide_runtime.cjs')], cwd=ROOT,
                       check=True, capture_output=True, text=True, encoding='utf-8')
