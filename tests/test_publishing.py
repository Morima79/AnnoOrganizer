"""Check the safety and integrity gates for the public demo snapshots."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_site import validate_site


class SiteValidationTests(unittest.TestCase):
    def fixture(self, root, extra):
        pages = ['index.html', 'guide/index.html', 'save-manager-guide/index.html', 'anno117/maps/index.html', 'anno117/stamps/index.html',
                 'anno1800/maps/index.html', 'anno1800/stamps/index.html', 'anno1404/maps/index.html']
        for name in pages:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<!doctype html><title>Demo</title>' + (extra if name == 'index.html' else ''),
                            encoding='utf-8')

    def test_public_demo_snapshot_has_complete_links(self):
        validate_site(ROOT / 'site')

    def test_missing_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, '<img src="missing.png">')
            with self.assertRaisesRegex(ValueError, 'missing target'):
                validate_site(root)

    def test_link_outside_public_site_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, '<a href="../settings.json">Private</a>')
            with self.assertRaisesRegex(ValueError, 'escapes site'):
                validate_site(root)

    def test_local_windows_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, '<p>C:/Users/player/demo.sww</p>')
            with self.assertRaisesRegex(ValueError, 'Local machine path'):
                validate_site(root)

    def test_arbitrary_workbooks_and_archives_remain_excluded(self):
        for suffix in ('.xlsx', '.zip'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, '')
                (root / ('private' + suffix)).write_bytes(b'private')
                with self.assertRaisesRegex(ValueError, 'Unexpected public file'):
                    validate_site(root)


if __name__ == '__main__':
    unittest.main()
