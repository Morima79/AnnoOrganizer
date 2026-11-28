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


def filedb_rows(rows, version=2):
    tags = {part for path, value in rows for part in path[:-1]}
    attrs = {path[-1] for path, value in rows}
    tag_ids = {name: i + 2 for i, name in enumerate(sorted(tags))}
    attr_ids = {name: i + 0x8001 for i, name in enumerate(sorted(attrs))}
    if version == 1:
        def varint(value):
            out = bytearray()
            while value >= 128:
                out.append((value & 127) | 128)
                value >>= 7
            return bytes(out + bytes([value]))
        raw = bytearray()
        for path, value in rows:
            for part in path[:-1]:
                raw += struct.pack('<H', tag_ids[part])
            raw += struct.pack('<H', attr_ids[path[-1]]) + varint(len(value)) + value
            raw += b'\0\0' * (len(path) - 1)
        end = len(raw)
        for lookup in (tag_ids, attr_ids):
            raw += varint(len(lookup))
            for name, code in lookup.items():
                raw += name.encode() + b'\0' + struct.pack('<H', code)
        raw += struct.pack('<I', end)
        return zlib.compress(raw, 9) + zlib.compress(b'', 9) + struct.pack('<I', len(raw))
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


def account(root, game='anno117'):
    result = root / 'accounts/account'
    result.mkdir(parents=True)
    (result / editor.game_format(game)['marker']).write_bytes(b'private account marker')
    return result


def save(game='anno117', version=2):
    raw = bytearray(792)
    raw[:18] = b'Resource File V2.2'
    blocks = []
    payloads = []
    for member in editor.MEMBERS:
        rows = [(('Unrelated',), b'KEEP')]
        if member in editor.PROFILE_PATHS[game]:
            text = 'Manual 8' if member == 'meta.a7s' else 'Old'
            rows.append((editor.PROFILE_PATHS[game][member], (text + '\0').encode('utf-16-le')))
        if member in editor.PLAYER_PATHS[game]:
            encoding = 'utf-16-le' if member == 'data.a7s' else 'utf-8'
            rows.append((editor.PLAYER_PATHS[game][member], 'Old Praetor'.encode(encoding)))
            if member == 'data.a7s':
                rows += [(editor.PLAYER_PATHS[game][member], b'\1'), (editor.PLAYER_PATHS[game][member], b''),
                         (editor.PLAYER_PATHS[game][member], b'\0')]
        payloads.append(filedb_rows(rows, version))
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
    def setUp(self):
        process_check = patch.object(editor, 'running_process_names', return_value=set())
        process_check.start()
        self.addCleanup(process_check.stop)

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
                changed = editor.transform(original, player=text)
                self.assertEqual(editor.player_name(changed), text)
                for (name, _, old), (_, _, new) in zip(editor.archive_entries(original), editor.archive_entries(changed), strict=True):
                    if name == 'meta.a7s':
                        self.assertEqual(old, new)
                        continue
                    before = [(p, bytes(v)) for p, v in editor.fields(editor.inflate(old))]
                    encoding = 'utf-16-le' if name == 'data.a7s' else 'utf-8'
                    expected = [(p, text.encode(encoding) if p == editor.PLAYER_PATHS['anno117'][name]
                                 and v == 'Old Praetor'.encode(encoding) else v) for p, v in before]
                    self.assertEqual([(p, bytes(v)) for p, v in editor.fields(editor.inflate(new))], expected)
                self.assertEqual(editor.transform(changed, player=text), changed)
                self.assertEqual(editor.inspect_save(changed), editor.inspect_save(original))

    def test_praetor_rejects_ambiguous_player_instead_of_guessing(self):
        raw = bytes(editor.inflate(filedb_rows([(editor.PLAYER_PATHS['anno117']['data.a7s'], b'A\0'),
                                              (editor.PLAYER_PATHS['anno117']['data.a7s'], b'A\0')])))
        with self.assertRaisesRegex(ValueError, 'mehrdeutig'):
            editor.patch_filedb(raw, editor.PLAYER_PATHS['anno117']['data.a7s'], 'New', expected_value=b'A\0')
        for text in ('', ' A', 'A\0B', 'A\nB'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                editor.validate_player_name(text)

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
                                     player='New Praetor', edit_in_place=True)
            for source in sources:
                self.assertEqual(editor.player_name(source.read_bytes()), 'New Praetor')
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
                                    player='Another Praetor', edit_in_place=True)
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
        for member in editor.PROFILE_PATHS['anno117']:
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


class Anno1800SaveEditorTests(unittest.TestCase):
    def setUp(self):
        process_check = patch.object(editor, 'running_process_names', return_value=set())
        process_check.start()
        self.addCleanup(process_check.stop)

    def test_legacy_v1_names_cross_varint_length_boundaries_without_changing_other_fields(self):
        original = save('anno1800', version=1)
        for profile, player in (('A', 'B'), ('P' * 70, 'Ö' * 80)):
            changed = editor.transform(original, profile, player=player, game='anno1800')
            self.assertEqual(editor.player_name(changed, 'anno1800'), player)
            self.assertEqual(editor.inspect_save(changed, 'anno1800')['header.a7s'], profile)
            for (member, _, old), (_, _, new) in zip(editor.archive_entries(original), editor.archive_entries(changed), strict=True):
                if member == 'meta.a7s':
                    self.assertEqual(old, new)
                    continue
                before = [(p, bytes(v)) for p, v in editor.fields(editor.inflate(old))]
                expected = []
                encoding = 'utf-16-le' if member == 'data.a7s' else 'utf-8'
                for path, value in before:
                    if path == editor.PROFILE_PATHS['anno1800'].get(member):
                        value = (profile + '\0').encode('utf-16-le')
                    elif path == editor.PLAYER_PATHS['anno1800'][member] and value == 'Old Praetor'.encode(encoding):
                        value = player.encode(encoding)
                    expected.append((path, value))
                self.assertEqual([(p, bytes(v)) for p, v in editor.fields(editor.inflate(new))], expected)
            self.assertEqual(editor.transform(changed, profile, player=player, game='anno1800'), changed)

    def test_1800_profile_and_player_fields_preserve_unrelated_data(self):
        original = save('anno1800')
        for name in ('A', 'Längerer Spielername 漢字'):
            edited = editor.transform(original, 'New Profile', player=name, game='anno1800')
            self.assertEqual(editor.player_name(edited, 'anno1800'), name)
            self.assertEqual(editor.inspect_save(edited, 'anno1800'),
                             {'header.a7s': 'New Profile', 'gamesetup.a7s': 'New Profile', 'meta.a7s': 'Manual 8'})
            for (member, _, before), (_, _, after) in zip(editor.archive_entries(original), editor.archive_entries(edited), strict=True):
                if member == 'meta.a7s':
                    self.assertEqual(before, after)
                    continue
                rows = [(p, bytes(v)) for p, v in editor.fields(editor.inflate(before))]
                encoding = 'utf-16-le' if member == 'data.a7s' else 'utf-8'
                expected = []
                for path, value in rows:
                    if path == editor.PROFILE_PATHS['anno1800'].get(member):
                        value = 'New Profile\0'.encode('utf-16-le')
                    elif path == editor.PLAYER_PATHS['anno1800'][member] and value == 'Old Praetor'.encode(encoding):
                        value = name.encode(encoding)
                    expected.append((path, value))
                self.assertEqual([(p, bytes(v)) for p, v in editor.fields(editor.inflate(after))], expected)
        profile_only = editor.transform(original, 'New', game='anno1800')
        self.assertEqual(editor.archive_entries(profile_only)[3][2], editor.archive_entries(original)[3][2])
        with self.assertRaises(ValueError):
            editor.inspect_save(original, 'anno117')

    def test_1800_move_rename_and_bulk_names_with_verified_backup(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory), 'anno1800')
            folder = root / 'Old'
            folder.mkdir()
            for filename in ('One.a7s', 'Two.a7s'):
                (folder / filename).write_bytes(save('anno1800'))
            backup_root = Path(directory) / 'backups'
            editor.transfer([folder / 'One.a7s'], root / 'Moved', backup_root, move=True, game='anno1800')
            self.assertTrue((folder / 'Two.a7s').exists())
            self.assertFalse((folder / 'One.a7s').exists())
            editor.transfer([folder / 'Two.a7s'], root / 'Renamed', backup_root,
                            move=True, rename_folder=True, game='anno1800')
            self.assertFalse(folder.exists())
            target = root / 'Renamed'
            (target / 'Three.a7s').write_bytes(editor.transform(save('anno1800'), 'Renamed',
                                                               player='Other old name', game='anno1800'))
            extra = target / 'notes.txt'
            extra.write_text('keep', encoding='utf-8')
            sources = editor.profile_saves(target, 'anno1800')
            before = {p.name: p.read_bytes() for p in sources}
            backup = editor.transfer(sources, target, backup_root, player='Renamed Player',
                                     edit_in_place=True, game='anno1800')
            with zipfile.ZipFile(backup) as archive:
                for source in sources:
                    self.assertEqual(archive.read(source.name), before[source.name])
            for source in sources:
                self.assertEqual(editor.player_name(source.read_bytes(), 'anno1800'), 'Renamed Player')
                self.assertEqual(editor.inspect_save(source.read_bytes(), 'anno1800')['header.a7s'], 'Renamed')
            self.assertEqual(extra.read_text(encoding='utf-8'), 'keep')
            (target / 'Nested').mkdir()
            with self.assertRaisesRegex(ValueError, 'Unterordner'):
                editor.profile_saves(target, 'anno1800')
            with self.assertRaises(ValueError):
                editor.transfer(sources, target / 'Nested', backup_root, game='anno1800')

    def test_bulk_name_failure_restores_all_1800_saves(self):
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            root = account(Path(directory), 'anno1800')
            folder = root / 'Old'
            folder.mkdir()
            sources = [folder / 'One.a7s', folder / 'Two.a7s']
            for source in sources:
                source.write_bytes(save('anno1800'))
            restore = editor.restore_times
            calls = []
            def fail_second(path, record):
                calls.append(path)
                if len(calls) == 2:
                    raise OSError('simulated second-file failure')
                restore(path, record)
            with patch.object(editor, 'restore_times', fail_second):
                with self.assertRaisesRegex(RuntimeError, 'Originale erhalten'):
                    editor.transfer(sources, folder, Path(directory) / 'backups', player='New Player',
                                    edit_in_place=True, game='anno1800')
            for source in sources:
                self.assertEqual(source.read_bytes(), save('anno1800'))


class RunningGameTests(unittest.TestCase):
    def test_selected_game_only_and_detection_failure(self):
        with patch.object(editor, 'running_process_names', return_value={'Anno1800.EXE', 'UbisoftConnect.exe'}):
            editor.ensure_game_closed('anno117')
            with self.assertRaisesRegex(ValueError, 'Anno 1800 läuft noch'):
                editor.ensure_game_closed('anno1800')
        with patch.object(editor, 'running_process_names', return_value={'Anno117.exe'}):
            with self.assertRaisesRegex(ValueError, 'Anno 117 läuft noch'):
                editor.ensure_game_closed('anno117')
        with patch.object(editor, 'running_process_names', side_effect=OSError('snapshot failed')):
            with self.assertRaisesRegex(ValueError, 'nicht geprüft'):
                editor.ensure_game_closed('anno117')

    def test_running_game_blocks_before_backup_or_destination_writes(self):
        for game in ('anno117', 'anno1800'):
            with self.subTest(game=game), tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
                root = account(Path(directory), game)
                source = root / ('Old/Save' + editor.game_format(game)['extension'])
                source.parent.mkdir()
                original = save(game)
                source.write_bytes(original)
                backup = Path(directory) / 'backups'
                for snapshots in ([{game + '.exe'}], [set(), {game + '.exe'}]):
                    with patch.object(editor, 'running_process_names', side_effect=snapshots):
                        with self.assertRaisesRegex(ValueError, 'läuft noch'):
                            editor.transfer([source], root / 'New', backup, move=True, game=game)
                    self.assertEqual(source.read_bytes(), original)
                    self.assertFalse((root / 'New').exists())
                self.assertEqual(len(list(backup.glob('*.zip'))), 1)

    @unittest.skipUnless(os.name == 'nt', 'Windows process snapshot')
    def test_windows_snapshot_detects_a_named_process(self):
        import shutil
        import subprocess
        with tempfile.TemporaryDirectory(dir=editor.temporary_root()) as directory:
            executable = Path(directory) / 'Anno117.exe'
            shutil.copyfile(Path(os.environ['SystemRoot']) / 'System32/cmd.exe', executable)
            process = subprocess.Popen([str(executable), '/d', '/q', '/k'], stdin=subprocess.PIPE,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                self.assertIn('anno117.exe', editor.running_process_names())
                with self.assertRaisesRegex(ValueError, 'läuft noch'):
                    editor.ensure_game_closed('anno117')
            finally:
                process.terminate()
                process.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main()
