"""Check process reservations and failure-safe stamp publication on real files."""
import errno
import json
import shutil
import os
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'anno117/tools'))
from anno_output_lock import reserve_paths
from anno_output_transaction import (stamp_transaction, files_in, StagedTree,
                                     staging_directory, temporary_directory, publish_files)
from anno_settings import Settings


@unittest.skipUnless(os.name == 'nt', 'Windows output reservations')
class OutputLockTests(unittest.TestCase):
    def test_other_process_cannot_reserve_equal_or_nested_targets(self):
        program = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from anno_output_lock import reserve_paths
try:
    with reserve_paths([Path(sys.argv[3])], directory=Path(sys.argv[2])):
        pass
except ValueError:
    sys.exit(7)
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / 'registry'
            with reserve_paths([root / 'reports'], directory=registry):
                for target in (root / 'reports', root / 'reports/images', root):
                    result = subprocess.run([sys.executable, '-c', program, str(ROOT / 'anno117/tools'),
                                             str(registry), str(target)], capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 7, result.stderr)
                result = subprocess.run([sys.executable, '-c', program, str(ROOT / 'anno117/tools'),
                                         str(registry), str(root / 'other')], capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(list(registry.glob('job-*.json')))

    def test_crashed_owner_leaves_no_permanent_reservation(self):
        program = '''
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from anno_output_lock import reserve_paths
with reserve_paths([Path(sys.argv[3])], directory=Path(sys.argv[2])):
    os._exit(9)
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = subprocess.run([sys.executable, '-c', program, str(ROOT / 'anno117/tools'),
                                     str(root / 'registry'), str(root / 'output')], timeout=20)
            self.assertEqual(result.returncode, 9)
            with reserve_paths([root / 'output'], directory=root / 'registry'):
                pass
            self.assertFalse(list((root / 'registry').glob('job-*.json')))


class StampTransactionTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows read-only directory attributes')
    def test_copied_readonly_directories_publish_and_cleanup_without_changing_references(self):
        references = self.stamps / 'references'
        references.chmod(stat.S_IREAD)
        self.cache.chmod(stat.S_IREAD)
        try:
            with stamp_transaction(self.settings, lambda: None) as staged:
                self.assertFalse((staged.report_output / 'stamp-gallery').stat().st_file_attributes & 1)
                self.generate(staged)
            self.assertEqual((self.stamps / 'references/user.json').read_text(), 'keep reference')
            self.assertTrue(references.stat().st_file_attributes & 1)
            self.assertFalse(list(self.settings.output.rglob('.annoorganizer-stage-*')))
        finally:
            references.chmod(stat.S_IWRITE)
            self.cache.chmod(stat.S_IWRITE)

    @unittest.skipUnless(os.name == 'nt', 'Windows read-only cleanup')
    def test_cleanup_retries_readonly_working_directories(self):
        tree = StagedTree(self.cache, 'reports/stamp-gallery')
        tree.stage.chmod(stat.S_IREAD)
        tree.cleanup()
        self.assertFalse(tree.root.exists())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.working = self.root / 'temporary'
        self.working.mkdir()
        self.temp_patch = patch.dict(os.environ, {'ANNOORGANIZER_TEMP_DIR': str(self.working)})
        self.temp_patch.start()
        self.addCleanup(self.temp_patch.stop)
        self.settings = Settings.from_data('anno117', self.root / 'settings.json', dict(
            version=1, game='anno117', output='./output'))
        self.stamps = self.settings.stamp_output
        self.cache = self.settings.report_output / 'stamp-gallery'
        for target in (self.stamps, self.cache):
            target.mkdir(parents=True)
        (self.stamps / 'stamp-gallery.html').write_text('old gallery', encoding='utf-8')
        (self.stamps / 'references').mkdir()
        (self.stamps / 'references/user.json').write_text('keep reference', encoding='utf-8')
        (self.cache / 'inventory.json').write_text('old inventory', encoding='utf-8')
        self.before = files_in(self.settings.output)

    def generate(self, staged):
        (staged.stamp_output / 'library').mkdir(exist_ok=True)
        (staged.stamp_output / 'library/new.png').write_bytes(b'new resource')
        (staged.stamp_output / 'stamp-gallery.html').write_text('new gallery', encoding='utf-8')
        (staged.report_output / 'stamp-gallery/inventory.json').write_text('new inventory', encoding='utf-8')

    def test_generation_failure_keeps_all_existing_outputs(self):
        with self.assertRaisesRegex(ValueError, 'cancelled'):
            with stamp_transaction(self.settings, lambda: None) as staged:
                self.generate(staged)
                raise ValueError('cancelled')
        self.assertEqual(files_in(self.settings.output), self.before)
        self.assertFalse(list(self.settings.output.rglob('.annoorganizer-stage-*')))

    def test_success_publishes_and_preserves_user_references(self):
        with stamp_transaction(self.settings, lambda: None) as staged:
            self.generate(staged)
        self.assertEqual((self.stamps / 'stamp-gallery.html').read_text(), 'new gallery')
        self.assertEqual((self.cache / 'inventory.json').read_text(), 'new inventory')
        self.assertEqual((self.stamps / 'references/user.json').read_text(), 'keep reference')

    def test_publication_failure_rolls_back_resources_and_inventory(self):
        real_replace = os.replace
        def replace(source, target):
            if str(source).endswith('stamps' + os.sep + 'stamp-gallery.html') and 'rollback' not in str(source):
                raise PermissionError('locked gallery')
            return real_replace(source, target)
        with patch('anno_output_transaction.os.replace', side_effect=replace):
            with self.assertRaisesRegex(PermissionError, 'locked gallery'):
                with stamp_transaction(self.settings, lambda: None) as staged:
                    self.generate(staged)
        self.assertEqual(files_in(self.settings.output), self.before)

    def test_external_edit_aborts_before_publication(self):
        with self.assertRaisesRegex(ValueError, 'extern geändert'):
            with stamp_transaction(self.settings, lambda: None) as staged:
                self.generate(staged)
                (self.cache / 'inventory.json').write_text('external edit', encoding='utf-8')
        self.assertEqual((self.stamps / 'stamp-gallery.html').read_text(), 'old gallery')
        self.assertEqual((self.cache / 'inventory.json').read_text(), 'external edit')

    def test_failed_rollback_retains_recovery_data(self):
        real_replace = os.replace
        def replace(source, target):
            source = Path(source)
            if source.name == 'stamp-gallery.html' or 'rollback' in source.parts:
                raise PermissionError('locked output')
            return real_replace(source, target)
        with patch('anno_output_transaction.os.replace', side_effect=replace):
            with self.assertRaisesRegex(OSError, 'Sicherungsdaten bleiben erhalten'):
                with stamp_transaction(self.settings, lambda: None) as staged:
                    self.generate(staged)
        manifests = list(self.working.rglob('RECOVERY.json'))
        self.assertEqual(len(manifests), 1)
        record = json.loads(manifests[0].read_text(encoding='utf-8'))[0]
        self.assertEqual(Path(record['backup']).read_text(), 'old inventory')
        self.assertTrue(Path(record['backup']).is_relative_to(self.working))

    def test_staging_is_outside_outputs_and_cleaned_after_success(self):
        with stamp_transaction(self.settings, lambda: None) as staged:
            work = staged.stamp_output.parent
            self.assertTrue(work.name.startswith('.annoorganizer-stage-'))
            self.assertTrue(work.is_relative_to(self.working))
            self.assertFalse(work.is_relative_to(self.settings.output))
            self.generate(staged)
        self.assertFalse(work.exists())

    def test_cross_volume_publication_and_removal(self):
        obsolete = self.stamps / 'obsolete.txt'
        obsolete.write_text('obsolete')
        with patch('anno_output_transaction.os.replace', side_effect=OSError(errno.EXDEV, 'different volume')):
            with stamp_transaction(self.settings, lambda: None) as staged:
                self.generate(staged)
                (staged.stamp_output / 'obsolete.txt').unlink()
        self.assertFalse(obsolete.exists())
        self.assertEqual((self.stamps / 'stamp-gallery.html').read_text(), 'new gallery')
        self.assertFalse(list(self.working.iterdir()))

    def test_partial_cross_volume_copy_rolls_back(self):
        copy = shutil.copyfile
        failed = False
        def partial_copy(source, target, **kwargs):
            nonlocal failed
            if not failed and Path(target) == self.cache / 'inventory.json':
                failed = True
                Path(target).write_text('partial')
                raise OSError('copy interrupted')
            return copy(source, target, **kwargs)
        with patch('anno_output_transaction.os.replace', side_effect=OSError(errno.EXDEV, 'different volume')), \
                patch('anno_output_transaction.shutil.copyfile', side_effect=partial_copy):
            with self.assertRaisesRegex(OSError, 'copy interrupted'):
                with stamp_transaction(self.settings, lambda: None) as staged:
                    self.generate(staged)
        self.assertEqual(files_in(self.settings.output), self.before)
        self.assertFalse(list(self.working.iterdir()))

    def test_map_partial_copy_restores_old_output(self):
        target = self.stamps / 'stamp-gallery.html'
        copy = shutil.copyfile
        with temporary_directory('.anno-map-') as name:
            stage = Path(name)
            source = stage / 'map.html'
            source.write_text('new map')
            def partial_copy(origin, destination, **kwargs):
                if Path(origin) == source:
                    Path(destination).write_text('partial map')
                    raise OSError('map interrupted')
                return copy(origin, destination, **kwargs)
            with patch('anno_output_transaction.os.replace', side_effect=OSError(errno.EXDEV, 'different volume')), \
                    patch('anno_output_transaction.shutil.copyfile', side_effect=partial_copy):
                with self.assertRaisesRegex(OSError, 'map interrupted'):
                    publish_files([(source, target)], stage / 'previous')
            self.assertEqual(target.read_text(), 'old gallery')
        self.assertFalse(stage.exists())

    def test_map_failed_restore_keeps_backup_even_if_manifest_write_fails(self):
        target = self.stamps / 'stamp-gallery.html'
        with self.assertRaisesRegex(OSError, 'Sicherungsdaten bleiben erhalten'):
            with temporary_directory('.anno-map-') as name:
                stage = Path(name)
                source = stage / 'map.html'
                source.write_text('new map')
                def fail_replace(origin, destination):
                    Path(destination).write_text('partial map')
                    raise PermissionError('locked output')
                write = Path.write_text
                def fail_manifest(path, *args, **kwargs):
                    if path.name == 'RECOVERY.json':
                        raise PermissionError('manifest blocked')
                    return write(path, *args, **kwargs)
                with patch('anno_output_transaction.os.replace', side_effect=fail_replace), \
                        patch.object(Path, 'write_text', fail_manifest):
                    publish_files([(source, target)], stage / 'previous')
        self.assertEqual((stage / 'previous/0').read_text(), 'old gallery')


class TemporaryStorageTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {'ANNOORGANIZER_TEMP_DIR': ''})
        environment.start()
        self.addCleanup(environment.stop)

    def test_default_uses_user_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('anno_output_transaction.tempfile.gettempdir', return_value=directory):
                with temporary_directory('.anno-test-') as name:
                    self.assertEqual(Path(name).parent, Path(directory).resolve())

    def test_override_takes_precedence_over_user_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            preferred = Path(directory) / 'custom-temp'
            preferred.mkdir()
            with patch.dict(os.environ, {'ANNOORGANIZER_TEMP_DIR': str(preferred)}), \
                    patch('anno_output_transaction.tempfile.gettempdir', return_value=directory):
                with temporary_directory('.anno-test-') as name:
                    self.assertEqual(Path(name).parent, preferred.resolve())

    def test_missing_override_falls_back_to_user_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.dict(os.environ, {'ANNOORGANIZER_TEMP_DIR': str(base / 'missing')}), \
                    patch('anno_output_transaction.tempfile.gettempdir', return_value=directory):
                with temporary_directory('.anno-test-') as name:
                    self.assertEqual(Path(name).parent, base.resolve())
                self.assertFalse(Path(name).exists())

    def test_unwritable_override_falls_back_to_user_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            preferred = base / 'preferred'
            preferred.mkdir()
            allocate = tempfile.mkdtemp
            def denied(*args, **kwargs):
                if kwargs.get('dir') == preferred:
                    raise PermissionError('custom temp denied')
                return allocate(*args, **kwargs)
            with patch.dict(os.environ, {'ANNOORGANIZER_TEMP_DIR': str(preferred)}), \
                    patch('anno_output_transaction.tempfile.gettempdir', return_value=directory), \
                    patch('anno_output_transaction.tempfile.mkdtemp', side_effect=denied):
                with temporary_directory('.anno-test-') as name:
                    self.assertEqual(Path(name).parent, base.resolve())

    def test_onedrive_override_falls_back_to_user_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cloud = base / 'cloud'
            cloud.mkdir()
            with patch.dict(os.environ, {'ANNOORGANIZER_TEMP_DIR': str(cloud), 'OneDrive': str(cloud)}), \
                    patch('anno_output_transaction.tempfile.gettempdir', return_value=directory):
                with temporary_directory('.anno-test-') as name:
                    self.assertEqual(Path(name).parent, base.resolve())
                self.assertFalse(list(cloud.iterdir()))

    def test_relative_override_falls_back_to_user_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'ANNOORGANIZER_TEMP_DIR': '.'}), \
                    patch('anno_output_transaction.tempfile.gettempdir', return_value=directory):
                with temporary_directory('.anno-test-') as name:
                    self.assertEqual(Path(name).parent, Path(directory).resolve())

    def test_onedrive_temp_is_rejected_without_creating_work_files(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch('anno_output_transaction.tempfile.gettempdir', return_value=directory), \
                    patch.dict(os.environ, {'OneDrive': directory}):
                with self.assertRaisesRegex(OSError, 'ausserhalb von OneDrive'):
                    staging_directory()
            self.assertFalse(list(base.iterdir()))


if __name__ == '__main__':
    unittest.main()
