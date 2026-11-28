"""Regression tests for isolated save edits, collisions and transfer rollback."""
import importlib.util
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'anno117/tools'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    spec = importlib.util.spec_from_file_location('anno117_save_editor', TOOLS / 'anno_save_editor.py')
    editor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(editor)


def filedb_rows(rows):
    tags = {part for path, value in rows for part in path[:-1]}
    attrs = {path[-1] for path, value in rows}
    tag_ids = {name: i + 2 for i, name in enumerate(sorted(tags))}
    attr_ids = {name: i + 0x8001 for i, name in enumerate(sorted(attrs))}
    raw = bytearray()
    for path, value in rows:
        for part in path[:-1]:
            raw += struct.pack('<II', 0, tag_ids[part])
        raw += struct.pack('<II', len(value), attr_ids[path[-1]])
        raw += value.ljust((len(value) + 7) & ~7, b'\0')
        for part in path[:-1]:
            raw += struct.pack('<II', 0, 0)
    offsets = []
    for lookup in (tag_ids, attr_ids):
        offsets.append(len(raw))
        raw += struct.pack('<I', len(lookup))
        for name, code in lookup.items():
            raw += struct.pack('<H', code)
        for name in lookup:
            raw += name.encode() + b'\0'
    raw += struct.pack('<5I', 0, *offsets, 0, 0xfffffffe)
    return zlib.compress(raw, 9) + zlib.compress(b'', 9) + struct.pack('<I', len(raw))


def account(root):
    result = root / 'accounts/account'
    result.mkdir(parents=True)
    (result / 'accountdata.a8s').write_bytes(b'private account marker')
    return result


def save():
    raw = bytearray(792)
    raw[:18] = b'Resource File V2.2'
    blocks = []
    payloads = []
    for member in editor.MEMBERS:
        rows = [(('Unrelated',), b'KEEP')]
        if member in editor.PROFILE_PATHS:
            text = 'Manual 8' if member == 'meta.a7s' else 'Old'
            rows.append((editor.PROFILE_PATHS[member], (text + '\0').encode('utf-16-le')))
        if member in editor.PRAETOR_PATHS:
            encoding = 'utf-16-le' if member == 'data.a7s' else 'utf-8'
            rows.append((editor.PRAETOR_PATHS[member], 'Old Praetor'.encode(encoding)))
            if member == 'data.a7s':
                rows += [(editor.PRAETOR_PATHS[member], b'\1'), (editor.PRAETOR_PATHS[member], b''),
                         (editor.PRAETOR_PATHS[member], b'\0')]
        payloads.append(filedb_rows(rows))
    for name, payload in zip(editor.MEMBERS, payloads, strict=True):
        start = len(raw)
        raw += payload
        header = bytearray(560)
        encoded = name.encode('utf-16-le')
        header[:len(encoded)] = encoded
        struct.pack_into('<QQQ', header, 520, start, len(payload), len(payload))
        raw += header
        blocks.append(len(raw))
        raw += struct.pack('<IIQQQ', 0, 1, 560, 560, 0)
    struct.pack_into('<Q', raw, 784, blocks[0])
    for i, position in enumerate(blocks):
        struct.pack_into('<Q', raw, position + 24, blocks[i + 1] if i + 1 < len(blocks) else len(raw))
    return bytes(raw)


class SaveEditorTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows directory attributes')
    def test_folder_rename_preserves_readonly_attribute_without_removing_directory(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.SetFileAttributesW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD)
        kernel.SetFileAttributesW.restype = wintypes.BOOL
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            old, new = root / 'Old', root / 'New'
            old.mkdir()
            sources = [old / 'One.a8s', old / 'Two.a8s']
            for path in sources:
                path.write_bytes(save())
            attributes = old.stat().st_file_attributes
            if not kernel.SetFileAttributesW(str(old), attributes | 1):
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                with patch.object(Path, 'rmdir', side_effect=AssertionError('Directory removal must not be used')):
                    editor.transfer(sources, new, Path(directory) / 'backups', move=True, rename_folder=True)
                self.assertFalse(old.exists())
                self.assertEqual(new.stat().st_file_attributes, attributes | 1)
                for path in sources:
                    self.assertEqual(editor.inspect_save((new / path.name).read_bytes())['gamesetup.a7s'], 'New')
            finally:
                for folder in (old, new):
                    if folder.exists():
                        kernel.SetFileAttributesW(str(folder), attributes)

    def test_folder_rename_rolls_back_directory_and_original_saves_after_write_failure(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            old, new = root / 'Old', root / 'New'
            old.mkdir()
            sources = [old / 'One.a8s', old / 'Two.a8s']
            for path in sources:
                path.write_bytes(save())
            restore = editor.restore_times
            calls = []
            def fail_second(path, record):
                calls.append(path)
                if len(calls) == 2:
                    raise PermissionError('simulated failure after rename and second write')
                restore(path, record)
            with patch.object(editor, 'restore_times', fail_second):
                with self.assertRaisesRegex(RuntimeError, 'Originale erhalten'):
                    editor.transfer(sources, new, Path(directory) / 'backups', move=True, rename_folder=True)
            self.assertTrue(old.is_dir())
            self.assertFalse(new.exists())
            for path in sources:
                self.assertEqual(path.read_bytes(), save())

    def test_praetor_changes_all_three_fields_and_preserves_others(self):
        original = save()
        for text in ('A', 'Prätor: 長い名前 mit längerer Bezeichnung'):
            with self.subTest(text=text):
                changed = editor.transform(original, praetor=text)
                self.assertEqual(editor.praetor_name(changed), text)
                for (name, _, old), (_, _, new) in zip(editor.archive_entries(original), editor.archive_entries(changed), strict=True):
                    if name == 'meta.a7s':
                        self.assertEqual(old, new)
                        continue
                    before = [(p, bytes(v)) for p, v in editor.fields(editor.inflate(old))]
                    encoding = 'utf-16-le' if name == 'data.a7s' else 'utf-8'
                    expected = [(p, text.encode(encoding) if p == editor.PRAETOR_PATHS[name]
                                 and v == 'Old Praetor'.encode(encoding) else v) for p, v in before]
                    self.assertEqual([(p, bytes(v)) for p, v in editor.fields(editor.inflate(new))], expected)
                self.assertEqual(editor.transform(changed, praetor=text), changed)
                self.assertEqual(editor.inspect_save(changed), editor.inspect_save(original))

    def test_praetor_rejects_ambiguous_player_instead_of_guessing(self):
        raw = bytes(editor.inflate(filedb_rows([(editor.PRAETOR_PATHS['data.a7s'], b'A\0'),
                                              (editor.PRAETOR_PATHS['data.a7s'], b'A\0')])))
        with self.assertRaisesRegex(ValueError, 'mehrdeutig'):
            editor.patch_filedb(raw, editor.PRAETOR_PATHS['data.a7s'], 'New', expected_value=b'A\0')
        for text in ('', ' A', 'A\0B', 'A\nB'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                editor.validate_praetor(text)

    def test_nested_and_foreign_profile_destinations_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            source = root / 'Old/Save.a8s'
            source.parent.mkdir()
            source.write_bytes(save())
            other = root / 'Other'
            other.mkdir()
            for destination in (root / 'Old/Nested', other / 'Nested', root,
                                root.parent / 'foreign/New', root / 'Old'):
                with self.subTest(destination=destination), self.assertRaises(ValueError):
                    editor.transfer([source], destination, Path(directory) / 'backups')
                self.assertFalse((destination / source.name).exists() and destination != source.parent)
            nested = root / 'Old/Nested'
            nested.mkdir()
            misplaced = nested / source.name
            misplaced.write_bytes(save())
            with self.assertRaisesRegex(ValueError, 'Unterordner'):
                editor.transfer([misplaced], root / 'New', Path(directory) / 'backups')
            with self.assertRaisesRegex(ValueError, 'ausserhalb des Spielkontos'):
                editor.transfer([source], root / 'New', root / 'backups')
            self.assertEqual(source.read_bytes(), save())

    def test_in_place_praetor_edit_and_rollback_after_partial_failure(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            folder = root / 'Old'
            folder.mkdir()
            sources = [folder / 'One.a8s', folder / 'Two.a8s']
            for source in sources:
                source.write_bytes(save())
            backup = editor.transfer(sources, folder, Path(directory) / 'backups',
                                     praetor='New Praetor', edit_in_place=True)
            for source in sources:
                self.assertEqual(editor.praetor_name(source.read_bytes()), 'New Praetor')
            with zipfile.ZipFile(backup) as archive:
                self.assertEqual(archive.read('One.a8s'), save())
            before = [source.read_bytes() for source in sources]
            restore = editor.restore_times
            calls = []
            def fail_second(path, record):
                calls.append(path)
                if len(calls) == 2:
                    raise PermissionError('simulated failure after second write')
                restore(path, record)
            with patch.object(editor, 'restore_times', fail_second):
                with self.assertRaisesRegex(RuntimeError, 'Originale erhalten'):
                    editor.transfer(sources, folder, Path(directory) / 'backups',
                                    praetor='Another Praetor', edit_in_place=True)
            self.assertEqual([p.read_bytes() for p in sources], before)
            self.assertEqual({p.name for p in folder.iterdir()}, {'One.a8s', 'Two.a8s'})

    def test_shorter_longer_unicode_names_preserve_unrelated_bytes(self):
        original = save()
        old = editor.archive_entries(original)
        for name in ('A', 'Long profile name äöü 漢字', 'Profile 123'):
            with self.subTest(name=name):
                changed = editor.transform(original, name)
                names = editor.inspect_save(changed)
                self.assertEqual(names, {'header.a7s': name, 'gamesetup.a7s': name, 'meta.a7s': 'Manual 8'})
                new = editor.archive_entries(changed)
                self.assertEqual(old[0][2], new[0][2])
                self.assertEqual(old[3][2], new[3][2])
                self.assertEqual(editor.transform(changed, name), changed)

    def test_each_field_is_independently_editable(self):
        original = save()
        old = editor.archive_entries(original)
        for member in editor.PROFILE_PATHS:
            with self.subTest(member=member):
                changed = editor.transform(original, overrides={member: 'Distinct marker'})
                self.assertEqual(editor.inspect_save(changed)[member], 'Distinct marker')
                for (name, _, before), (_, _, after) in zip(old, editor.archive_entries(changed), strict=True):
                    if name != member:
                        self.assertEqual(before, after)

    def test_unsupported_archive_and_names_are_rejected(self):
        for name in ('../x', 'NUL', 'con.txt', 'A.', 'A ', 'a/b', '', 'LPT¹'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                editor.validate_name(name)
        for raw in (b'', save()[:-1], save() + b'extra'):
            with self.assertRaises((ValueError, struct.error)):
                editor.transform(raw, 'New')

    def test_move_backup_content_and_timestamps(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            source = root / 'Old' / 'Save.a8s'
            source.parent.mkdir()
            source.write_bytes(save())
            os.utime(source, ns=(1600000000000000000, 1600000000000000000))
            stat = source.stat()
            backup = editor.transfer([source], root / 'New', root.parent.parent / 'backups', move=True)
            self.assertFalse(source.exists())
            target = root / 'New/Save.a8s'
            self.assertEqual(target.stat().st_mtime_ns, stat.st_mtime_ns)
            if os.name == 'nt':
                self.assertEqual(target.stat().st_birthtime_ns, stat.st_birthtime_ns)
            with zipfile.ZipFile(backup) as archive:
                self.assertEqual(archive.read('Save.a8s'), save())
            self.assertEqual(editor.inspect_save(target.read_bytes())['header.a7s'], 'New')

    def test_collision_and_partial_publication_failure_preserve_sources(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            old, new = root / 'Old', root / 'New'
            old.mkdir()
            new.mkdir()
            sources = [old / 'One.a8s', old / 'Two.a8s']
            for source in sources:
                source.write_bytes(save())
            target = new / 'One.a8s'
            target.write_bytes(b'existing user data')
            with self.assertRaises(ValueError):
                editor.transfer(sources, new, root.parent.parent / 'backups', move=True)
            self.assertEqual(target.read_bytes(), b'existing user data')
            target.unlink()
            with patch.object(editor, 'restore_times', side_effect=OSError('simulated locked file')):
                with self.assertRaisesRegex(RuntimeError, 'Originale erhalten'):
                    editor.transfer(sources, new, root.parent.parent / 'backups', move=True)
            self.assertEqual(list(new.iterdir()), [])
            for source in sources:
                self.assertEqual(source.read_bytes(), save())

    def test_partial_source_removal_failure_restores_originals(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            old = root / 'Old'
            old.mkdir()
            sources = [old / 'One.a8s', old / 'Two.a8s']
            for source in sources:
                source.write_bytes(save())
            unlink = Path.unlink
            def fail_second(path, *args, **kwargs):
                if path == sources[1]:
                    raise PermissionError('simulated source lock')
                return unlink(path, *args, **kwargs)
            with patch.object(Path, 'unlink', fail_second):
                with self.assertRaisesRegex(RuntimeError, 'Originale erhalten'):
                    editor.transfer(sources, root / 'New', root.parent.parent / 'backups', move=True)
            self.assertFalse((root / 'New').exists())
            for source in sources:
                self.assertEqual(source.read_bytes(), save())

    def test_folder_rename_rejects_extra_files_and_then_renames(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory))
            old = root / 'Old'
            old.mkdir()
            source = old / 'Save.a8s'
            source.write_bytes(save())
            extra = old / 'custom.txt'
            extra.write_text('keep', encoding='utf-8')
            with self.assertRaises(ValueError):
                editor.transfer([source], root / 'New', root.parent.parent / 'backups', move=True, rename_folder=True)
            extra.unlink()
            editor.transfer([source], root / 'New', root.parent.parent / 'backups', move=True, rename_folder=True)
            self.assertFalse(old.exists())
            self.assertTrue((root / 'New/Save.a8s').is_file())


if __name__ == '__main__':
    unittest.main()
