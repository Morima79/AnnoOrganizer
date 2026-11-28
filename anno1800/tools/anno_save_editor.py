"""Conservative Anno 117/1800 save editing and backed-up profile transfers."""
from datetime import datetime
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path
import re
import struct
import tempfile
import uuid
import zipfile
import zlib

from anno_file_formats import fields, inflate, members

GAME_FORMATS = {
    'anno117': dict(extension='.a8s', marker='accountdata.a8s', label='Anno 117',
                    documents=('Anno 117 - Pax Romana', 'Anno 117 Pax Romana', 'Anno 117')),
    'anno1800': dict(extension='.a7s', marker='accountdata.a7s', label='Anno 1800',
                     documents=('Anno 1800', 'Anno1800')),
}
PROFILE_PATHS = {
    'anno117': {
        'header.a7s': ('CorporationProfile', 'SavegameProfileDisplayName'),
        'gamesetup.a7s': ('GameSetupManager', 'SavegameProfileDisplayName'),
        'meta.a7s': ('CorporationSaveGameName',),
    },
    'anno1800': {
        'header.a7s': ('CorporationProfile', 'GameSetup', 'SavegameFolderW'),
        'gamesetup.a7s': ('GameSetupManager', 'SavegameFolderW'),
        'meta.a7s': ('CorporationSaveGameName',),
    },
}
MEMBERS = ('meta.a7s', 'header.a7s', 'gamesetup.a7s', 'data.a7s')
PLAYER_PATHS = {
    'anno117': {
        'header.a7s': ('CorporationProfile', 'SetupSlots', 'Slot', 'CompanyName'),
        'gamesetup.a7s': ('GameSetupManager', 'SetupSlots', 'Slot', 'CompanyName'),
        'data.a7s': ('MetaGameManager', 'MetaGameObjectManager', 'MetaObjectMap', '[]',
                     'MetaParticipant', 'CustomCompanyName', '[]'),
    },
    'anno1800': {
        'header.a7s': ('CorporationProfile', 'GameSetup', 'Peers', 'Peer', 'Values', 'Available',
                       'ParticipantType', 'Values', 'Human', 'CompanyName'),
        'gamesetup.a7s': ('GameSetupManager', 'Peers', 'Peer', 'Values', 'Available',
                          'ParticipantType', 'Values', 'Human', 'CompanyName'),
        'data.a7s': ('MetaGameManager', 'MetaGameObjectManager', 'MetaObjectMap', '[]',
                     'MetaProfile', 'CustomCompanyName', '[]'),
    },
}


def running_process_names():
    """Read Windows executable names without opening a console or processes."""
    if os.name != 'nt':
        raise OSError('Die Spielprüfung ist nur unter Windows verfügbar.')
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD),
                    ('pid', wintypes.DWORD), ('heap', ctypes.c_size_t),
                    ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                    ('parent', wintypes.DWORD), ('priority', wintypes.LONG),
                    ('flags', wintypes.DWORD), ('exe', wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = kernel.Process32FirstW.argtypes
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = ProcessEntry()
        entry.size = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        names = {entry.exe.casefold()}
        while kernel.Process32NextW(snapshot, ctypes.byref(entry)):
            names.add(entry.exe.casefold())
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
        return names
    finally:
        kernel.CloseHandle(snapshot)


def ensure_game_closed(game):
    """Block editing when the selected game runs or process detection fails."""
    game_format(game)
    try:
        names = running_process_names()
    except OSError as exc:
        raise ValueError('Es konnte nicht geprüft werden, ob das Spiel läuft. '
                         'Bitte die Aktion erneut versuchen. Es wurden keine Saves bearbeitet.') from exc
    executable = {'anno117': 'anno117.exe', 'anno1800': 'anno1800.exe'}[game]
    if executable in {name.casefold() for name in names}:
        raise ValueError(game_format(game)['label'] + ' läuft noch. Bitte das Spiel vollständig schliessen '
                         'und die Cloud-Synchronisierung abwarten. Danach die Aktion erneut ausführen. '
                         'Es wurden keine Saves bearbeitet.')


def game_format(game):
    if game not in GAME_FORMATS:
        raise ValueError('Dieses Spiel wird noch nicht unterstützt.')
    return GAME_FORMATS[game]


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


def validate_player_name(name):
    """Keep punctuation allowed in player names, including the tested colon."""
    if (not name or name != name.strip() or any(ord(c) < 32 for c in name)
            or len(name.encode('utf-16-le')) > 240):
        raise ValueError('Bitte einen Spielernamen ohne Rand-Leerzeichen oder Steuerzeichen angeben (höchstens 120 UTF-16-Zeichen).')
    return name


def validate_profile_name(name):
    """Explain the flat-profile requirement instead of reporting a filename error."""
    if '/' in name or '\\' in name:
        raise ValueError('Bitte im Feld «Ziel-Profilname» nur einen Profilnamen eingeben, zum Beispiel «Mein Profil». '
                         'Pfade und Unterordner sind hier nicht erlaubt. Das Zielprofil wird direkt im Kontoordner angelegt.')
    return validate_name(name)


def account_directory(profile, game='anno117'):
    """Identify an account by its accountdata marker, then enforce one profile level."""
    marker = game_format(game)['marker']
    profile = Path(profile).resolve()
    candidates = [p for p in profile.parents if p.parent.name.casefold() == 'accounts'
                  and (p / marker).is_file()]
    if len(candidates) != 1:
        raise ValueError(game_format(game)['label'] + '-Konto nicht erkannt: Profil direkt unter accounts/<Konto> mit ' + marker + ' auswählen.')
    account = candidates[0]
    if profile.parent != account:
        raise ValueError('Saves müssen direkt im Profilordner liegen. Unterordner innerhalb eines Profils sind nicht erlaubt.')
    return account


def profile_saves(folder, game='anno117'):
    """Collect all direct saves, refusing to silently omit nested profile folders."""
    folder = Path(folder).resolve(strict=True)
    account_directory(folder, game)
    children = list(folder.iterdir())
    if any(p.is_dir() for p in children):
        raise ValueError('Der Profilordner enthält Unterordner. Bitte diese zuerst prüfen; Namen werden nur direkt im Profil geändert.')
    saves = sorted(p for p in children if p.is_file() and p.suffix.casefold() == game_format(game)['extension']
                   and not p.name.casefold().startswith('accountdata'))
    if not saves:
        raise ValueError('Keine passenden Spielstände direkt im Profilordner gefunden.')
    return saves


def validate_destination(sources, destination, *, edit_in_place=False, game='anno117'):
    """Reject nested, foreign-account and unresolved profile targets before any write."""
    sources = [Path(p).resolve(strict=True) for p in sources]
    if not sources or len(set(sources)) != len(sources):
        raise ValueError('Bitte unterschiedliche Saves auswählen.')
    parent = sources[0].parent
    if any(p.parent != parent or not p.is_file() or p.suffix.lower() != game_format(game)['extension']
           or p.name.casefold().startswith('accountdata') for p in sources):
        raise ValueError('Nur ' + game_format(game)['extension'] + '-Saves direkt aus einem Profilordner auswählen.')
    account = account_directory(parent, game)
    destination = Path(destination).resolve()
    validate_profile_name(destination.name)
    if destination.parent != account:
        raise ValueError('Ziel muss ein direkter Profilordner desselben Kontos sein. Keine Unterordner in Profilen anlegen.')
    if edit_in_place:
        if destination != parent:
            raise ValueError('Spielername ohne Verschieben nur im ursprünglichen Profilordner ändern.')
    elif destination == parent:
        raise ValueError('Für eine Übertragung einen anderen Profilordner wählen.')
    if destination.exists() and not destination.is_dir():
        raise ValueError('Der Zielpfad ist kein Ordner.')
    return account


def archive_entries(blob):
    """Only accept the exact nonresident four-member save layout we can preserve."""
    if len(blob) < 792 or blob[:18] != b'Resource File V2.2':
        raise ValueError('Kein unterstützter Spielstand (RDA V2.2).')
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


def inspect_save(blob, game='anno117'):
    """Read the three independent UTF-16 save names without guessing encodings."""
    game_format(game)
    parts = {name: inflate(payload) for name, _, payload in archive_entries(blob)
             if name in PROFILE_PATHS[game]}
    return _profile_names(parts, game)


def _profile_names(parts, game):
    paths = PROFILE_PATHS[game]
    result = {}
    for name in paths:
        hits = [bytes(value) for path, value in fields(parts[name])
                if path == paths[name]]
        if len(hits) != 1:
            raise ValueError('Namensfeld fehlt oder ist mehrdeutig: ' + name)
        result[name] = hits[0].decode('utf-16-le').rstrip('\0')
    return result


def player_name(blob, game='anno117'):
    """Only accept a single consistent player slot; never guess among multiple players."""
    game_format(game)
    parts = {name: inflate(payload) for name, _, payload in archive_entries(blob)
             if name in ('header.a7s', 'gamesetup.a7s')}
    return _player_name(parts, game)


def _player_name(parts, game):
    paths = PLAYER_PATHS[game]
    names = []
    for name in ('header.a7s', 'gamesetup.a7s'):
        hits = [bytes(v).decode('utf-8').rstrip('\0') for p, v in fields(parts[name])
                if p == paths[name]]
        if len(hits) != 1 or not hits[0]:
            raise ValueError('Spielername nicht eindeutig erkennbar; mehrere Spieler oder unbekanntes Save-Format.')
        names.append(hits[0])
    if len(names) != 2 or names[0] != names[1]:
        raise ValueError('Spielernamen in header und gamesetup stimmen nicht überein.')
    return names[0]


def read_summary(path, game='anno117'):
    """Read only metadata for the list, avoiding large world-data reads per save."""
    game_format(game)
    parts = dict(members(Path(path), set(PROFILE_PATHS[game])))
    names = _profile_names(parts, game)
    try:
        player = _player_name(parts, game)
    except ValueError:
        player = 'Nicht eindeutig zuordenbar'
    return names, player


def _find_field(raw, path, expected_value):
    hits = [(i, bytes(v)) for i, (p, v) in enumerate(fields(raw))
            if p == path and (expected_value is None or v == expected_value)]
    if len(hits) != 1:
        raise ValueError('Namensfeld fehlt oder ist mehrdeutig: ' + '/'.join(path))
    return hits[0]


def _verify_fields(raw, edited, index, path, new):
    """Compare fields as a stream so large world states need no object catalogue."""
    for i, (before, after) in enumerate(zip_longest(fields(raw), fields(edited))):
        expected = (path, new) if i == index else before
        if after != expected:
            raise ValueError('Andere FileDB-Felder wurden verändert.')


def _patch_legacy_filedb(raw, path, text, encoding, expected_value):
    """Replace one FileDB V1 value, retaining its dictionaries and all other bytes."""
    if len(raw) < 4:
        raise ValueError('Unvollständige FileDB-V1-Daten.')
    end = struct.unpack_from('<I', raw, len(raw) - 4)[0]
    if not 0 < end < len(raw) - 4:
        raise ValueError('Ungültiges FileDB-V1-Verzeichnis.')
    index, old = _find_field(raw, path, expected_value)
    if old.decode(encoding).rstrip('\0') == text:
        return raw
    terminator = '\0'.encode(encoding)
    new = text.encode(encoding) + (terminator if old.endswith(terminator) else b'')
    position, ordinal = 0, 0
    while position + 2 <= end:
        code = struct.unpack_from('<H', raw, position)[0]
        position += 2
        if code & 0x8000:
            length_start = position
            size = 0
            for shift in range(0, 35, 7):
                if position >= end:
                    raise ValueError('Unvollständige FileDB-V1-Länge.')
                byte = raw[position]
                position += 1
                size |= (byte & 127) << shift
                if not byte & 128:
                    break
            else:
                raise ValueError('Ungültige FileDB-V1-Länge.')
            if position + size > end:
                raise ValueError('Unvollständiges FileDB-V1-Feld.')
            if ordinal == index:
                break
            ordinal += 1
            position += size
    else:
        raise ValueError('FileDB-V1-Feldposition nicht gefunden.')
    if raw[position:position + size] != old:
        raise ValueError('FileDB-V1-Feldprüfung fehlgeschlagen.')
    encoded_length = bytearray()
    remaining = len(new)
    while remaining >= 128:
        encoded_length.append((remaining & 127) | 128)
        remaining >>= 7
    encoded_length.append(remaining)
    replacement = bytes(encoded_length) + new
    old_segment = raw[length_start:position + size]
    delta = len(replacement) - len(old_segment)
    edited = bytearray(memoryview(raw)[:length_start])
    edited.extend(replacement)
    edited.extend(memoryview(raw)[position + size:])
    struct.pack_into('<I', edited, len(edited) - 4, end + delta)
    _verify_fields(raw, edited, index, path, new)
    if (memoryview(edited)[:length_start] != memoryview(raw)[:length_start]
            or memoryview(edited)[length_start + len(replacement):-4]
            != memoryview(raw)[position + size:-4]):
        raise ValueError('Unerwartete Änderung ausserhalb des FileDB-V1-Namensfeldes.')
    return bytes(edited)


def patch_filedb(raw, path, text, *, encoding='utf-16-le', expected_value=None):
    """Replace one exact field, preserving other bytes and updating dictionary offsets."""
    if len(raw) < 20 or struct.unpack_from('<I', raw, len(raw) - 4)[0] not in (0xfffffffd, 0xfffffffe):
        return _patch_legacy_filedb(raw, path, text, encoding, expected_value)
    index, old = _find_field(raw, path, expected_value)
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
    edited = bytearray(memoryview(raw)[:pos])
    edited.extend(struct.pack('<I', len(new)) + raw[pos + 4:pos + 8])
    edited.extend(new.ljust(new_size, b'\0'))
    edited.extend(memoryview(raw)[pos + 8 + old_size:])
    struct.pack_into('<II', edited, len(edited) - 16, tags + delta, attrs + delta)
    _verify_fields(raw, edited, index, path, new)
    if (memoryview(edited)[:pos] != memoryview(raw)[:pos]
            or memoryview(edited)[pos + 8 + new_size:-16] != memoryview(raw)[pos + 8 + old_size:-16]
            or edited[-20:-16] != raw[-20:-16] or edited[-8:] != raw[-8:]):
        raise ValueError('Unerwartete Änderung ausserhalb des Namensfeldes.')
    return bytes(edited)


def transform(blob, profile=None, overrides=None, *, player=None, game='anno117'):
    """Set the selected game's profile fields and optionally its three player-name fields."""
    game_format(game)
    profile_paths = PROFILE_PATHS[game]
    player_paths = PLAYER_PATHS[game]
    changes = {} if profile is None else {
        'header.a7s': validate_profile_name(profile), 'gamesetup.a7s': profile}
    for member, text in (overrides or {}).items():
        if member not in profile_paths:
            raise ValueError('Unbekanntes Namensfeld.')
        changes[member] = validate_name(text)
    old_player = None
    if player is not None:
        validate_player_name(player)
        old_player = player_name(blob, game)
    original = archive_entries(blob)
    output, positions = bytearray(blob[:792]), []
    for name, header, payload in original:
        if name in changes or player is not None and name in player_paths:
            raw = bytes(inflate(payload))
            edited = patch_filedb(raw, profile_paths[name], changes[name]) if name in changes else raw
            if player is not None and name in player_paths:
                encoding = 'utf-16-le' if name == 'data.a7s' else 'utf-8'
                candidates = [bytes(v) for p, v in fields(edited) if p == player_paths[name]
                              and bytes(v) in (old_player.encode(encoding), (old_player + '\0').encode(encoding))]
                if len(candidates) != 1:
                    raise ValueError('Spielername im Spielzustand nicht eindeutig zuordenbar; keine Änderung ausgeführt.')
                edited = patch_filedb(edited, player_paths[name], player,
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
        if name not in changes and not (player is not None and name in player_paths) and new != old:
            raise ValueError('Unbeteiligtes Save-Mitglied wurde verändert.')
    names = inspect_save(result, game)
    if any(names[key] != value for key, value in changes.items()):
        raise ValueError('Namensprüfung fehlgeschlagen.')
    if player is not None and player_name(result, game) != player:
        raise ValueError('Prüfung des Spielernamens fehlgeschlagen.')
    return result


def creation_time_ns(stat):
    """Python 3.11 exposes Windows creation time through st_ctime_ns."""
    if hasattr(stat, 'st_birthtime_ns'):
        return stat.st_birthtime_ns
    return stat.st_ctime_ns if os.name == 'nt' else None


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
             player=None, edit_in_place=False, game='anno117'):
    """Validate and stage every save before backup, exclusive publication and removal.

    Backups are intentional durable outputs, never deleted automatically. Existing
    destinations are never overwritten; source originals are removed only for moves.
    """
    ensure_game_closed(game)
    original_paths = [Path(p).absolute() for p in sources]
    if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in original_paths):
        raise ValueError('Verknüpfte Quelldateien werden nicht bearbeitet.')
    sources = [p.resolve(strict=True) for p in original_paths]
    destination, backup_root = Path(destination).resolve(), Path(backup_root).resolve()
    account = validate_destination(sources, destination, edit_in_place=edit_in_place, game=game)
    if edit_in_place and (move or rename_folder or player is None):
        raise ValueError('Namensänderung ohne Verschieben benötigt einen neuen Spielernamen.')
    parent = sources[0].parent
    if any(p.parent != parent or p.suffix.lower() != game_format(game)['extension'] or p.name.lower().startswith('accountdata')
           for p in sources):
        raise ValueError('Nur ' + game_format(game)['extension'] + '-Saves aus einem Profilordner auswählen.')
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
    with tempfile.TemporaryDirectory(prefix='anno-save-transfer-', dir=temporary_root()) as staging:
        staging = Path(staging)
        for i, source in enumerate(sources):
            stat = source.stat()
            original = source.read_bytes()
            record = dict(source=str(source), sha256=digest(original), atime_ns=stat.st_atime_ns,
                          mtime_ns=stat.st_mtime_ns)
            birthtime = creation_time_ns(stat)
            if birthtime is not None:
                record['birthtime_ns'] = birthtime
            edited = transform(original, destination.name, player=player, game=game)
            (staging / str(i)).write_bytes(edited)
            record['output_sha256'] = digest(edited)
            records.append(record)
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / (game_format(game)['label'].replace(' ', '') + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8] + '.zip')
        with zipfile.ZipFile(backup, 'x', zipfile.ZIP_STORED) as archive:
            for source, record in zip(sources, records, strict=True):
                original = source.read_bytes()
                if digest(original) != record['sha256']:
                    raise ValueError('Quelldatei wurde während der Vorbereitung geändert.')
                archive.writestr(source.name, original)
            archive.writestr('transfer-manifest.json', json.dumps(dict(destination=str(destination),
                game=game, move=move, rename_folder=rename_folder, edit_in_place=edit_in_place,
                player=player, files=records), ensure_ascii=False, indent=2))
        with zipfile.ZipFile(backup) as archive:
            if archive.testzip() is not None or any(digest(archive.read(p.name)) != r['sha256']
                                                  for p, r in zip(sources, records, strict=True)):
                raise ValueError('Sicherungsprüfung fehlgeschlagen.')
        ensure_game_closed(game)
        if rename_folder:
            _rename_profile(parent, destination, sources, staging, records, backup)
            return backup
        created, deleted = [], []
        existed = destination.exists()
        try:
            destination.mkdir(parents=False, exist_ok=True)
            validate_destination(sources, destination, edit_in_place=edit_in_place, game=game)
            for i, (source, record) in enumerate(zip(sources, records, strict=True)):
                if digest(source.read_bytes()) != record['sha256']:
                    raise ValueError('Quelldatei wurde zwischenzeitlich geändert.')
                target = destination / source.name
                if edit_in_place:
                    # Stage outside OneDrive; the verified durable backup also
                    # permits recovery after interruption during an in-place write.
                    with target.open('r+b') as handle:
                        if digest(handle.read()) != record['sha256']:
                            raise ValueError('Quelle wurde vor der Namensänderung verändert.')
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
