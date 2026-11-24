"""Protect independent gallery bundles and preserve domain data when sharing frames."""
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from sync_gallery_templates import sync


def load_renderer(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GalleryTemplateTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for stamp viewer runtime tests')
    def test_stamp_viewer_history_runtime(self):
        subprocess.run(['node', '--test', str(ROOT / 'tests/stamp_viewer_runtime.cjs')],
                       cwd=ROOT, check=True, capture_output=True, text=True, encoding='utf-8')

    def test_bundled_templates_match_the_canonical_sources(self):
        sync(check=True)

    def test_each_game_renders_without_the_repository_template_folder(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            with self.subTest(game=game), tempfile.TemporaryDirectory() as directory:
                project = Path(directory) / game
                (project / 'tools').mkdir(parents=True)
                (project / 'docs/images').mkdir(parents=True)
                shutil.copyfile(ROOT / game / 'tools/anno_gallery.py', project / 'tools/anno_gallery.py')
                shutil.copyfile(ROOT / game / 'tools/anno_i18n.py', project / 'tools/anno_i18n.py')
                shutil.copytree(ROOT / game / 'tools/gallery_templates', project / 'tools/gallery_templates')
                shutil.copyfile(ROOT / game / 'docs/images/game-logo.png', project / 'docs/images/game-logo.png')
                module = load_renderer(project / 'tools/anno_gallery.py', 'standalone_' + game)
                page = module.render_gallery('<header><h1>Demo</h1></header><article>Map</article>', game, 'map')
                self.assertIn('class="gallery gallery-map"', page)
                self.assertIn('<article>Map</article>', page)
                self.assertIn('src="data:image/png;base64,', page)
                self.assertNotIn('@@SHARED_CSS@@', page)

    def test_stamp_frame_preserves_filters_data_scripts_and_timestamp(self):
        module = load_renderer(ROOT / 'anno1800/tools/anno_gallery.py', 'stamp_frame_test')
        script = '<script>const inventory=[{"name":"Custom layout"}];</script>'
        content = '<input id="search"><article data-townhall="yes">Custom layout</article>'
        source = ('<html><style>.preview{cursor:zoom-in}</style><header><h1>Stamps</h1></header>'
                  '<main>' + content + '<footer>Aktualisiert: 21.11.2026 22:00 · Old instructions</footer></main>'
                  + script + '</html>')
        page = module.render_gallery(source, 'anno1800', 'stamp')
        self.assertIn(content, page)
        self.assertIn(script, page)
        self.assertIn('.preview{cursor:zoom-in}', page)
        self.assertIn('<footer class="gallery-footer">', page)
        self.assertIn('Stand: 21.11.2026 22:00', page)
        self.assertNotIn('Old instructions', page)
        self.assertIn('--gallery-background:#173345', page)
        self.assertEqual(page, module.render_gallery(page, 'anno1800', 'stamp'))

    def test_stamp_headers_share_totals_without_nested_badges(self):
        for game in ('anno117', 'anno1800'):
            module = load_renderer(ROOT / game / 'tools/anno_gallery.py', 'totals_' + game)
            for cards, count, regions in [('', 0, 0),
                ('<article class="card" data-region="Latium &amp; Albion"></article>', 1, 1),
                ('<article class="card" data-region="A"></article>'
                 '<article class="card" data-region="A" hidden></article>'
                 '<article class="card other" data-region="B"></article>', 3, 2)]:
                source = ('<header><h1>Stamps</h1><div class="summary"><span><span>99 Stempel</span>'
                          '</span><span>99 Regionen</span></div></header>' + cards
                          + '<footer>Stand: 24.11.2026 12:00</footer>')
                page = module.render_gallery(source, game, 'stamp')
                header = module.marker(page, 'header')
                self.assertEqual(header.count('class="stamp-total"'), 2)
                self.assertNotIn('class="summary"', header)
                self.assertNotIn('<span><span', header)
                for key, value in [('stamp.total', count), ('stamp.regions', regions)]:
                    self.assertIn('data-i18n="' + key + ('.one' if value == 1 else '') + '"', header)
                    self.assertIn('&quot;count&quot;:' + str(value), header)
                self.assertEqual(page, module.render_gallery(page, game, 'stamp'))

    def test_all_public_snapshots_use_the_current_shared_frame(self):
        for game in ('anno117', 'anno1800', 'anno1404'):
            module = load_renderer(ROOT / game / 'tools/anno_gallery.py', 'snapshot_' + game)
            for kind in (('map',) if game == 'anno1404' else ('map', 'stamp')):
                folder = 'maps' if kind == 'map' else 'stamps'
                page = ROOT / 'site' / game / folder / 'index.html'
                text = page.read_text(encoding='utf-8')
                with self.subTest(page=page):
                    self.assertEqual(text, module.render_gallery(text, game, kind))
                    self.assertEqual(len(re.findall('class="game-logo"', text)), 1)
                    self.assertNotIn('class="game-logo" style=', text)


if __name__ == '__main__':
    unittest.main()
