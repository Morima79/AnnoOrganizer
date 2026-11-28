"""Verify raw artifact extraction without the deprecated Node ZIP reader."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from extract_desktop_artifact import extract_desktop_artifact


class ReleaseArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.download = self.root / 'download'
        self.download.mkdir()
        self.output = self.root / 'dist'
        self.version = 'v0.1.16'
        self.name = f'AnnoOrganizer-{self.version}-windows-x64.zip'
        self.checksum = str(Path(self.name).with_suffix('.sha256'))
        self.content = b'portable desktop package'
        digest = hashlib.sha256(self.content).hexdigest()
        self.entries = {self.name: self.content,
                        self.checksum: f'{digest}  {self.name}\n'.encode('ascii')}

    def write_artifact(self, entries=None):
        # The service chooses the download filename through Content-Disposition.
        with zipfile.ZipFile(self.download / 'service-selected-name', 'w') as artifact:
            for name, content in (self.entries if entries is None else entries).items():
                artifact.writestr(name, content)

    def test_extracts_verified_pair_and_preserves_source_release(self):
        self.write_artifact()
        self.output.mkdir()
        source = self.output / f'AnnoOrganizer-{self.version}.zip'
        source.write_bytes(b'source release')
        extract_desktop_artifact(self.download, self.version, self.output)
        self.assertEqual((self.output / self.name).read_bytes(), self.content)
        self.assertEqual((self.output / self.checksum).read_bytes(), self.entries[self.checksum])
        self.assertEqual(source.read_bytes(), b'source release')
        self.assertEqual(len(list(self.output.iterdir())), 3)

    def test_rejects_changed_archive_or_wrong_checksum_filename_before_writing(self):
        for content in (b'wrong digest', self.entries[self.checksum].replace(self.name.encode(), b'other.zip')):
            with self.subTest(content=content):
                self.write_artifact(dict(self.entries, **{self.checksum: content}))
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    extract_desktop_artifact(self.download, self.version, self.output)
                self.assertFalse(self.output.exists())

    def test_rejects_unexpected_paths_missing_files_and_wrong_versions(self):
        for name in ('../outside.txt', '/absolute.txt', 'nested/file', 'extra.txt', self.name.upper()):
            with self.subTest(name=name):
                self.write_artifact(dict(self.entries, **{name: b'unexpected'}))
                with self.assertRaisesRegex(ValueError, 'Unexpected desktop artifact'):
                    extract_desktop_artifact(self.download, self.version, self.output)
                self.assertFalse(self.output.exists())
        self.write_artifact({self.name: self.content})
        with self.assertRaisesRegex(ValueError, 'Unexpected desktop artifact'):
            extract_desktop_artifact(self.download, self.version, self.output)
        self.write_artifact()
        with self.assertRaisesRegex(ValueError, 'Unexpected desktop artifact'):
            extract_desktop_artifact(self.download, 'v0.1.17', self.output)

    def test_rejects_duplicate_entries_and_invalid_zip(self):
        self.write_artifact()
        # Duplicate members could otherwise make the expected pair ambiguous.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.download / 'service-selected-name', 'a') as artifact:
                artifact.writestr(self.name, self.content)
        with self.assertRaisesRegex(ValueError, 'Unexpected desktop artifact'):
            extract_desktop_artifact(self.download, self.version, self.output)
        (self.download / 'service-selected-name').write_bytes(b'not a ZIP')
        with self.assertRaises(zipfile.BadZipFile):
            extract_desktop_artifact(self.download, self.version, self.output)
        self.assertFalse(self.output.exists())

    def test_requires_one_download_and_does_not_overwrite_existing_files(self):
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            extract_desktop_artifact(self.download, self.version, self.output)
        self.write_artifact()
        extra = self.download / 'extra'
        extra.write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            extract_desktop_artifact(self.download, self.version, self.output)
        extra.unlink()
        self.output.mkdir()
        existing = self.output / self.name
        existing.write_bytes(b'keep existing')
        with self.assertRaisesRegex(ValueError, 'already exist'):
            extract_desktop_artifact(self.download, self.version, self.output)
        self.assertEqual(existing.read_bytes(), b'keep existing')
        self.assertFalse((self.output / self.checksum).exists())

    def test_workflow_uses_raw_download_with_digest_validation(self):
        workflow = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')
        download = workflow.split('uses: actions/download-artifact@v8', 1)[1].split('      - name:', 1)[0]
        self.assertIn('skip-decompress: true', download)
        self.assertIn('digest-mismatch: error', download)
        self.assertIn('path: ${{ runner.temp }}/desktop-artifact', download)
        self.assertIn('NODE_OPTIONS: --throw-deprecation', download)
        self.assertIn('python scripts/extract_desktop_artifact.py', workflow)
        self.assertNotRegex(workflow, r'NODE_NO_WARNINGS|--no-warnings|--no-deprecation')
        self.assertIn("if: github.event_name == 'push'", workflow)

    def test_save_manager_pair_is_verified_without_replacing_desktop_files(self):
        name = 'AnnoSaveManager.zip'
        checksum = 'AnnoSaveManager.sha256'
        content = b'save-manager package'
        entries = {name: content, checksum: (hashlib.sha256(content).hexdigest() + '  ' + name + '\n').encode()}
        self.write_artifact(entries)
        self.output.mkdir()
        desktop = self.output / self.name
        desktop.write_bytes(b'keep desktop')
        extract_desktop_artifact(self.download, self.version, self.output, 'save-manager')
        self.assertEqual((self.output / name).read_bytes(), content)
        self.assertEqual(desktop.read_bytes(), b'keep desktop')
        entries[checksum] = b'wrong digest'
        self.write_artifact(entries)
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            extract_desktop_artifact(self.download, self.version, self.root / 'bad', 'save-manager')
        self.assertFalse((self.root / 'bad').exists())

    def test_save_manager_workflow_builds_and_publishes_a_verified_pair(self):
        workflow = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')
        self.assertIn('needs: [tests, desktop, save-manager]', workflow)
        self.assertIn('python scripts/build_save_manager.py --version', workflow)
        self.assertIn('dist/AnnoSaveManager.zip', workflow)
        self.assertIn('dist/AnnoSaveManager.sha256', workflow)
        self.assertIn('--package save-manager', workflow)
        self.assertEqual(workflow.count('skip-decompress: true'), 2)
        self.assertEqual(workflow.count('digest-mismatch: error'), 2)
