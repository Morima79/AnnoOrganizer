"""Conservative Anno 117 save editing and backed-up profile transfers."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import tempfile
import uuid
import zipfile
import zlib

from anno_file_formats import fields, inflate

PROFILE_PATHS = {
    'header.a7s': ('CorporationProfile', 'SavegameProfileDisplayName'),
    'gamesetup.a7s': ('GameSetupManager', 'SavegameProfileDisplayName'),
    'meta.a7s': ('CorporationSaveGameName',),
}
MEMBERS = ('meta.a7s', 'header.a7s', 'gamesetup.a7s', 'data.a7s')
PRAETOR_PATHS = {
    'header.a7s': ('CorporationProfile', 'SetupSlots', 'Slot', 'CompanyName'),
    'gamesetup.a7s': ('GameSetupManager', 'SetupSlots', 'Slot', 'CompanyName'),
    'data.a7s': ('MetaGameManager', 'MetaGameObjectManager', 'MetaObjectMap', '[]',
                 'MetaParticipant', 'CustomCompanyName', '[]'),
}


def temporary_root():
    """Resolve a disposable location outside configured OneDrive accounts."""
    roots = [Path(os.environ[key]).resolve() for key in
             ('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial') if os.environ.get(key)]
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\OneDrive\Accounts') as accounts:
                i = 0
                while True:
                    try:
                        name = winreg.EnumKey(accounts, i)
                    except OSError:
                        break
                    i += 1
                    with winreg.OpenKey(accounts, name) as account:
                        try:
                            roots.append(Path(winreg.QueryValueEx(account, 'UserFolder')[0]).resolve())
                        except OSError:
                            pass
        except OSError:
            pass
    candidates = [Path(os.environ[key]) for key in ('TEMP', 'TMP') if os.environ.get(key)]
    if os.name != 'nt':
        candidates.append(Path('/tmp'))
    candidates.append(Path('D:/Workspace/Temp'))
    for candidate in candidates:
        candidate = candidate.resolve()
        if any(candidate == root or root in candidate.parents for root in roots):
            continue
        if candidate.is_dir():
            return candidate
    raise ValueError('Kein temporärer Ordner ausserhalb OneDrive verfügbar.')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_name(name):
    """Accept one portable Windows filename component, including Unicode."""
    if (not name or len(name.encode('utf-16-le')) > 240 or name != name.strip()
            or name.endswith('.') or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name in ('.', '..') or re.fullmatch(
                r'(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?', name)):
        raise ValueError('Ungültiger Windows-Name: ' + repr(name))
    return name


def validate_praetor(name):
    """Keep punctuation allowed in player names, including the tested colon."""
    if (not name or name != name.strip() or any(ord(c) < 32 for c in name)
            or len(name.encode('utf-16-le')) > 240):
        raise ValueError('Bitte einen Prätornamen ohne Rand-Leerzeichen oder Steuerzeichen angeben (höchstens 120 UTF-16-Zeichen).')
    return name


def validate_profile_name(name):
    """Explain the flat-profile requirement instead of reporting a filename error."""
    if '/' in name or '\\' in name:
        raise ValueError('Bitte im Feld «Ziel-Profilname» nur einen Profilnamen eingeben, zum Beispiel «Mein Profil». '
                         'Pfade und Unterordner sind hier nicht erlaubt. Das Zielprofil wird direkt im Kontoordner angelegt.')
    return validate_name(name)


def account_directory(profile):
    """Identify an account by its accountdata marker, then enforce one profile level."""
    profile = Path(profile).resolve()
    candidates = [p for p in profile.parents if p.parent.name.casefold() == 'accounts'
                  and (p / 'accountdata.a8s').is_file()]
    if len(candidates) != 1:
        raise ValueError('Anno-117-Konto nicht erkannt: Profil direkt unter accounts/<Konto> mit accountdata.a8s auswählen.')
    account = candidates[0]
    if profile.parent != account:
        raise ValueError('Saves müssen direkt im Profilordner liegen. Unterordner innerhalb eines Profils sind nicht erlaubt.')
    return account


def validate_destination(sources, destination, *, edit_in_place=False):
    """Reject nested, foreign-account and unresolved profile targets before any write."""
    sources = [Path(p).resolve(strict=True) for p in sources]
    if not sources or len(set(sources)) != len(sources):
        raise ValueError('Bitte unterschiedliche Saves auswählen.')
    parent = sources[0].parent
    if any(p.parent != parent or not p.is_file() or p.suffix.lower() != '.a8s'
           or p.name.casefold().startswith('accountdata') for p in sources):
        raise ValueError('Nur .a8s-Saves direkt aus einem Profilordner auswählen.')
    account = account_directory(parent)
    destination = Path(destination).resolve()
    validate_profile_name(destination.name)
    if destination.parent != account:
        raise ValueError('Ziel muss ein direkter Profilordner desselben Kontos sein. Keine Unterordner in Profilen anlegen.')
    if edit_in_place:
        if destination != parent:
            raise ValueError('Prätor ohne Verschieben nur im ursprünglichen Profilordner ändern.')
    elif destination == parent:
        raise ValueError('Für eine Übertragung einen anderen Profilordner wählen.')
    if destination.exists() and not destination.is_dir():
        raise ValueError('Der Zielpfad ist kein Ordner.')
    return account


def archive_entries(blob):
    """Only accept the exact nonresident four-member save layout we can preserve."""
    if len(blob) < 792 or blob[:18] != b'Resource File V2.2':
        raise ValueError('Kein unterstützter Anno-117-Spielstand (RDA V2.2).')
    position = struct.unpack_from('<Q', blob, 784)[0]
    result, seen = [], set()
    end = 792
    while position < len(blob):
        if position in seen or position < end + 560 or position + 32 > len(blob):
            raise ValueError('Ungültige RDA-Blockposition.')
        seen.add(position)
        flags, count, packed, plain, following = struct.unpack_from('<IIQQQ', blob, position)
        if (flags, count, packed, plain) != (0, 1, 560, 560):
            raise ValueError('Unbekannte RDA-Blockstruktur; keine Bearbeitung.')
        header = blob[position - 560:position]
        name = header[:520].decode('utf-16-le').split('\0', 1)[0]
        offset, size, unpacked = struct.unpack_from('<QQQ', header, 520)
        if offset != end or size != unpacked or offset + size != position - 560:
            raise ValueError('Ungültige RDA-Dateigrenzen.')
        result.append((name, header, blob[offset:offset + size]))
        end = position + 32
        if following != len(blob) and following <= position:
            raise ValueError('Ungültige RDA-Verkettung.')
        position = following
    if position != len(blob) or end != len(blob) or tuple(r[0] for r in result) != MEMBERS:
        raise ValueError('Unerwartete Save-Mitglieder oder zusätzliche Daten.')
    return result


def inspect_save(blob):
    """Read the three independent UTF-16 save names without guessing encodings."""
    result = {}
    for name, _, payload in archive_entries(blob):
        if name not in PROFILE_PATHS:
            continue
        hits = [bytes(value) for path, value in fields(inflate(payload))
                if path == PROFILE_PATHS[name]]
        if len(hits) != 1:
            raise ValueError('Namensfeld fehlt oder ist mehrdeutig: ' + name)
        result[name] = hits[0].decode('utf-16-le').rstrip('\0')
    return result


def praetor_name(blob):
    """Only accept a single consistent player slot; never guess among multiple players."""
    names = []
    for name, _, payload in archive_entries(blob):
        if name not in ('header.a7s', 'gamesetup.a7s'):
            continue
        hits = [bytes(v).decode('utf-8').rstrip('\0') for p, v in fields(inflate(payload))
                if p == PRAETOR_PATHS[name]]
        if len(hits) != 1 or not hits[0]:
            raise ValueError('Prätor nicht eindeutig erkennbar; mehrere Spieler oder unbekanntes Save-Format.')
        names.append(hits[0])
    if len(names) != 2 or names[0] != names[1]:
        raise ValueError('Prätornamen in header und gamesetup stimmen nicht überein.')
    return names[0]


def patch_filedb(raw, path, text, *, encoding='utf-16-le', expected_value=None):
    """Replace one exact field, preserving other bytes and updating dictionary offsets."""
    if len(raw) < 20 or struct.unpack_from('<I', raw, len(raw) - 4)[0] not in (0xfffffffd, 0xfffffffe):
        raise ValueError('Nur FileDB V2 wird bearbeitet.')
    before = [(p, bytes(v)) for p, v in fields(raw)]
    hits = [(i, v) for i, (p, v) in enumerate(before) if p == path
            and (expected_value is None or v == expected_value)]
    if len(hits) != 1:
        raise ValueError('Namensfeld fehlt oder ist mehrdeutig: ' + '/'.join(path))
    index, old = hits[0]
    if old.decode(encoding).rstrip('\0') == text:
        return raw
    terminator = '\0'.encode(encoding)
    new = text.encode(encoding) + (terminator if old.endswith(terminator) else b'')
    tags, attrs = struct.unpack_from('<II', raw, len(raw) - 16)
    if not 0 < tags < attrs < len(raw) - 20:
        raise ValueError('Ungültige FileDB-Wörterbücher.')
    # Match the field index from the full structured reader to its byte offset.
    pos, ordinal = 0, 0
    while pos + 8 <= tags:
        size, code = struct.unpack_from('<IH', raw, pos)
        if code & 0x8000:
            if ordinal == index:
                break
            ordinal += 1
            pos += 8 + ((size + 7) & ~7)
        else:
            pos += 8
    else:
        raise ValueError('Feldposition nicht gefunden.')
    if raw[pos + 8:pos + 8 + size] != old:
        raise ValueError('FileDB-Feldprüfung fehlgeschlagen.')
    old_size, new_size = (len(old) + 7) & ~7, (len(new) + 7) & ~7
    delta = new_size - old_size
    edited = bytearray(raw[:pos] + struct.pack('<I', len(new)) + raw[pos + 4:pos + 8]
                       + new.ljust(new_size, b'\0') + raw[pos + 8 + old_size:])
    struct.pack_into('<II', edited, len(edited) - 16, tags + delta, attrs + delta)
    expected = before.copy()
    expected[index] = (path, new)
    if [(p, bytes(v)) for p, v in fields(edited)] != expected:
        raise ValueError('Andere FileDB-Felder wurden verändert.')
    restored = bytearray(edited[:pos] + raw[pos:pos + 8 + old_size] + edited[pos + 8 + new_size:])
    restored[-16:-8] = raw[-16:-8]
    if restored != raw:
        raise ValueError('Unerwartete Änderung ausserhalb des Namensfeldes.')
    return bytes(edited)


def transform(blob, profile=None, overrides=None, *, praetor=None):
    """Set both profile fields, or explicit independent names for isolated test copies."""
    changes = {} if profile is None else {
        'header.a7s': validate_profile_name(profile), 'gamesetup.a7s': profile}
    for member, text in (overrides or {}).items():
        if member not in PROFILE_PATHS:
            raise ValueError('Unbekanntes Namensfeld.')
        changes[member] = validate_name(text)
    old_praetor = None
    if praetor is not None:
        validate_praetor(praetor)
        old_praetor = praetor_name(blob)
    original = archive_entries(blob)
    output, positions = bytearray(blob[:792]), []
    for name, header, payload in original:
        if name in changes or praetor is not None and name in PRAETOR_PATHS:
            raw = bytes(inflate(payload))
            edited = patch_filedb(raw, PROFILE_PATHS[name], changes[name]) if name in changes else raw
            if praetor is not None and name in PRAETOR_PATHS:
                encoding = 'utf-16-le' if name == 'data.a7s' else 'utf-8'
                candidates = [bytes(v) for p, v in fields(edited) if p == PRAETOR_PATHS[name]
                              and bytes(v) in (old_praetor.encode(encoding), (old_praetor + '\0').encode(encoding))]
                if len(candidates) != 1:
                    raise ValueError('Prätor im Spielzustand nicht eindeutig zuordenbar; keine Änderung ausgeführt.')
                edited = patch_filedb(edited, PRAETOR_PATHS[name], praetor,
                                     encoding=encoding, expected_value=candidates[0])
            if edited != raw:
                payload = zlib.compress(edited, 9) + zlib.compress(b'', 9) + struct.pack('<I', len(edited))
        offset = len(output)
        output.extend(payload)
        header = bytearray(header)
        struct.pack_into('<QQQ', header, 520, offset, len(payload), len(payload))
        output.extend(header)
        positions.append(len(output))
        output.extend(struct.pack('<IIQQQ', 0, 1, 560, 560, 0))
    struct.pack_into('<Q', output, 784, positions[0])
    for i, position in enumerate(positions):
        struct.pack_into('<Q', output, position + 24,
                         positions[i + 1] if i + 1 < len(positions) else len(output))
    result = bytes(output)
    for (name, old_header, old), (_, new_header, new) in zip(original, archive_entries(result), strict=True):
        if old_header[:520] != new_header[:520] or old_header[544:] != new_header[544:]:
            raise ValueError('RDA-Metadaten wurden verändert.')
        if name not in changes and not (praetor is not None and name in PRAETOR_PATHS) and new != old:
            raise ValueError('Unbeteiligtes Save-Mitglied wurde verändert.')
    names = inspect_save(result)
    if any(names[key] != value for key, value in changes.items()):
        raise ValueError('Namensprüfung fehlgeschlagen.')
    if praetor is not None and praetor_name(result) != praetor:
        raise ValueError('Prätorprüfung fehlgeschlagen.')
    return result


def restore_times(path, record):
    """Preserve modification and creation times so the game retains save chronology."""
    os.utime(path, ns=(record['atime_ns'], record['mtime_ns']))
    if os.name == 'nt' and 'birthtime_ns' in record:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                     wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.SetFileTime.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
                                      ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.CreateFileW(str(path), 0x100, 7, None, 3, 0x80, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        ticks = record['birthtime_ns'] // 100 + 116444736000000000
        value = wintypes.FILETIME(ticks & 0xffffffff, ticks >> 32)
        try:
            if not kernel.SetFileTime(handle, ctypes.byref(value), None, None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(handle)


def _rename_profile(parent, destination, sources, staging, records, backup):
    """Rename the directory itself, retaining Windows/OneDrive folder attributes."""
    renamed = False
    changed = []
    try:
        if set(parent.iterdir()) != set(sources):
            raise ValueError('Der Quellordner wurde zwischenzeitlich verändert.')
        for source, record in zip(sources, records, strict=True):
            if digest(source.read_bytes()) != record['sha256']:
                raise ValueError('Ein Save wurde vor der Ordnerumbenennung verändert.')
        if destination.exists():
            raise ValueError('Der neue Profilordner existiert bereits.')
        # Removing an empty read-only Windows directory fails; renaming it works
        # and preserves attributes without changing user/cloud metadata.
        parent.rename(destination)
        renamed = True
        for i, (source, record) in enumerate(zip(sources, records, strict=True)):
            target = destination / source.name
            with target.open('r+b') as handle:
                if digest(handle.read()) != record['sha256']:
                    raise ValueError('Ein Save wurde während der Ordnerumbenennung verändert.')
                changed.append(target)
                handle.seek(0)
                handle.write((staging / str(i)).read_bytes())
                handle.truncate()
                handle.flush()
                os.fsync(handle.fileno())
            restore_times(target, record)
            if digest(target.read_bytes()) != record['output_sha256']:
                raise ValueError('Umbenannter Spielstand konnte nicht bestätigt werden.')
    except Exception as exc:
        try:
            if renamed:
                with zipfile.ZipFile(backup) as archive:
                    for target in changed:
                        record = records[next(i for i, p in enumerate(sources) if p.name == target.name)]
                        with target.open('wb') as handle:
                            handle.write(archive.read(target.name))
                        restore_times(target, record)
                destination.rename(parent)
        except Exception as rollback:
            raise RuntimeError(f'Wiederherstellung unvollständig. Sicherung: {backup}. {rollback}') from exc
        raise RuntimeError(f'Abgebrochen; Originale erhalten. Sicherung: {backup}. {exc}') from exc


def transfer(sources, destination, backup_root, *, move=False, rename_folder=False,
             praetor=None, edit_in_place=False):
    """Validate and stage every save before backup, exclusive publication and removal.

    Backups are intentional durable outputs, never deleted automatically. Existing
    destinations are never overwritten; source originals are removed only for moves.
    """
    original_paths = [Path(p).absolute() for p in sources]
    if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in original_paths):
        raise ValueError('Verknüpfte Quelldateien werden nicht bearbeitet.')
    sources = [p.resolve(strict=True) for p in original_paths]
    destination, backup_root = Path(destination).resolve(), Path(backup_root).resolve()
    account = validate_destination(sources, destination, edit_in_place=edit_in_place)
    if edit_in_place and (move or rename_folder or praetor is None):
        raise ValueError('Prätoränderung ohne Verschieben benötigt einen neuen Prätornamen.')
    parent = sources[0].parent
    if any(p.parent != parent or p.suffix.lower() != '.a8s' or p.name.lower().startswith('accountdata')
           for p in sources):
        raise ValueError('Nur .a8s-Saves aus einem Profilordner auswählen.')
    if rename_folder:
        if not move or destination.parent != parent.parent or destination.exists():
            raise ValueError('Ein neuer benachbarter Profilordner ist erforderlich.')
        if set(parent.iterdir()) != set(sources):
            raise ValueError('Der Profilordner enthält weitere Dateien oder Unterordner.')
    if any(p.name.casefold() in {q.name.casefold() for q in sources[:i]} for i, p in enumerate(sources)):
        raise ValueError('Mehrdeutige Dateinamen.')
    if not edit_in_place and destination.exists() and any((destination / p.name).exists() for p in sources):
        raise ValueError('Zieldatei existiert bereits; nichts wurde überschrieben.')
    if backup_root == account or account in backup_root.parents:
        raise ValueError('Die Sicherung muss ausserhalb des Spielkontos liegen.')
    records = []
    with tempfile.TemporaryDirectory(prefix='anno117-transfer-', dir=temporary_root()) as staging:
        staging = Path(staging)
        for i, source in enumerate(sources):
            stat = source.stat()
            original = source.read_bytes()
            record = dict(source=str(source), sha256=digest(original), atime_ns=stat.st_atime_ns,
                          mtime_ns=stat.st_mtime_ns)
            if hasattr(stat, 'st_birthtime_ns'):
                record['birthtime_ns'] = stat.st_birthtime_ns
            edited = transform(original, destination.name, praetor=praetor)
            (staging / str(i)).write_bytes(edited)
            record['output_sha256'] = digest(edited)
            records.append(record)
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / ('Anno117-' + datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8] + '.zip')
        with zipfile.ZipFile(backup, 'x', zipfile.ZIP_STORED) as archive:
            for source, record in zip(sources, records, strict=True):
                original = source.read_bytes()
                if digest(original) != record['sha256']:
                    raise ValueError('Quelldatei wurde während der Vorbereitung geändert.')
                archive.writestr(source.name, original)
            archive.writestr('transfer-manifest.json', json.dumps(dict(destination=str(destination),
                move=move, rename_folder=rename_folder, edit_in_place=edit_in_place,
                praetor=praetor, files=records), ensure_ascii=False, indent=2))
        with zipfile.ZipFile(backup) as archive:
            if archive.testzip() is not None or any(digest(archive.read(p.name)) != r['sha256']
                                                  for p, r in zip(sources, records, strict=True)):
                raise ValueError('Sicherungsprüfung fehlgeschlagen.')
        if rename_folder:
            _rename_profile(parent, destination, sources, staging, records, backup)
            return backup
        created, deleted = [], []
        existed = destination.exists()
        try:
            destination.mkdir(parents=False, exist_ok=True)
            validate_destination(sources, destination, edit_in_place=edit_in_place)
            for i, (source, record) in enumerate(zip(sources, records, strict=True)):
                if digest(source.read_bytes()) != record['sha256']:
                    raise ValueError('Quelldatei wurde zwischenzeitlich geändert.')
                target = destination / source.name
                if edit_in_place:
                    # Stage outside OneDrive; the verified durable backup also
                    # permits recovery after interruption during an in-place write.
                    with target.open('r+b') as handle:
                        if digest(handle.read()) != record['sha256']:
                            raise ValueError('Quelle wurde vor der Prätoränderung verändert.')
                        created.append(target)
                        handle.seek(0)
                        handle.write((staging / str(i)).read_bytes())
                        handle.truncate()
                        handle.flush()
                        os.fsync(handle.fileno())
                    restore_times(target, record)
                    if digest(target.read_bytes()) != record['output_sha256']:
                        raise ValueError('Ausgabedatei konnte nicht bestätigt werden.')
                    continue
                with target.open('xb') as handle:
                    created.append(target)
                    handle.write((staging / str(i)).read_bytes())
                    handle.flush()
                    os.fsync(handle.fileno())
                if digest(target.read_bytes()) != record['output_sha256']:
                    raise ValueError('Ausgabedatei konnte nicht bestätigt werden.')
                restore_times(target, record)
            if move:
                if any(digest(p.read_bytes()) != r['sha256'] for p, r in zip(sources, records, strict=True)):
                    raise ValueError('Quelle wurde vor dem Verschieben geändert.')
                for source in sources:
                    source.unlink()
                    deleted.append(source)
        except Exception as exc:
            # Restore removed originals before removing any verified destination copies.
            try:
                with zipfile.ZipFile(backup) as archive:
                    if edit_in_place:
                        for target in created:
                            record = records[sources.index(target)]
                            with target.open('wb') as handle:
                                handle.write(archive.read(target.name))
                            restore_times(target, record)
                    for source in deleted:
                        with source.open('xb') as handle:
                            handle.write(archive.read(source.name))
                        restore_times(source, records[sources.index(source)])
                if not edit_in_place:
                    for target in created:
                        target.unlink()
                if not existed and destination.is_dir() and not any(destination.iterdir()):
                    destination.rmdir()
            except Exception as rollback:
                raise RuntimeError(f'Wiederherstellung unvollständig. Sicherung: {backup}. {rollback}') from exc
            raise RuntimeError(f'Abgebrochen; Originale erhalten. Sicherung: {backup}. {exc}') from exc
    return backup
