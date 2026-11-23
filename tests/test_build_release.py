"""Verify renamed release packages against an isolated Git snapshot."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class ReleaseArchiveTests(unittest.TestCase):
    def test_renamed_archive_preserves_snapshot_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            shutil.copyfile(ROOT / 'scripts/build_release.py', root / 'scripts/build_release.py')
            original = b'# Snapshot\n'
            (root / 'README.md').write_bytes(original)
            (root / '.gitignore').write_text('settings.json\nlocal-data/\ndist/\n', encoding='utf-8')
            (root / '.gitattributes').write_text('* text eol=lf\n', encoding='utf-8')
            for args in (['init', '--quiet'], ['add', '.'],
                         ['-c', 'user.name=Release Test', '-c', 'user.email=test@example.invalid',
                          '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Test snapshot']):
                subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
            # Packaging must retain HEAD bytes and exclude local settings and outputs.
            (root / 'README.md').write_text('Uncommitted change', encoding='utf-8')
            (root / 'settings.json').write_text('{"private":true}', encoding='utf-8')
            (root / 'local-data').mkdir()
            (root / 'local-data/report.html').write_text('Private output', encoding='utf-8')
            result = subprocess.run([sys.executable, 'scripts/build_release.py', '--version', 'v1.2.3'],
                                    cwd=root, check=True, capture_output=True, text=True, encoding='utf-8')
            archive = root / 'dist/AnnoOrganizer-v1.2.3.zip'
            self.assertIn(archive.name, result.stdout)
            with zipfile.ZipFile(archive) as package:
                self.assertIsNone(package.testzip())
                self.assertEqual(package.read('AnnoOrganizer-v1.2.3/README.md'), original)
                self.assertEqual(sorted(name for name in package.namelist() if not name.endswith('/')),
                                 ['AnnoOrganizer-v1.2.3/.gitattributes', 'AnnoOrganizer-v1.2.3/.gitignore',
                                  'AnnoOrganizer-v1.2.3/README.md',
                                  'AnnoOrganizer-v1.2.3/scripts/build_release.py'])
            self.assertEqual(archive.with_suffix('.sha256').read_text(encoding='ascii'),
                             hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')


if __name__ == '__main__':
    unittest.main()
