"""Reserve overlapping Windows output trees across CLI and desktop processes."""
from contextlib import contextmanager
from contextvars import ContextVar
import ctypes
import json
import os
from pathlib import Path
import time
from uuid import uuid4

_held = ContextVar('anno_reserved_outputs', default=())


def registry_directory():
    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 28, None, 0, buffer) != 0:
        raise OSError('LocalAppData konnte nicht ermittelt werden.')
    return Path(buffer.value) / 'AnnoOrganizer' / 'reservations'


def canonical(path):
    return Path(os.path.normcase(str(Path(path).resolve())))


def overlaps(first, second):
    return first.is_relative_to(second) or second.is_relative_to(first)


def output_paths(settings, tasks):
    paths = [settings.output, settings.log_output]
    if 'analyze' in tasks:
        paths.append(settings.report_output)
    if 'stamps' in tasks:
        paths.extend((settings.stamp_output, settings.report_output / 'stamp-gallery'))
    return paths


@contextmanager
def guard(directory):
    import msvcrt
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'registry.lock').open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        deadline = time.monotonic() + 5
        while True:
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError('Die Ausgabesperren werden gerade geprüft. Bitte erneut versuchen.')
                time.sleep(0.02)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


@contextmanager
def reserve_paths(paths, *, directory=None):
    """Reserve all paths atomically; OS-owned byte locks identify live jobs.

    Unlocked reservation files are stale, including after a process crash. No PID
    guessing or manual stale-lock deletion is required. Nested service calls can
    reuse a reservation only if their complete write set is already covered.
    """
    import msvcrt
    paths = tuple(sorted(set(canonical(path) for path in paths)))
    held = _held.get()
    if paths and all(any(path.is_relative_to(parent) for parent in held) for path in paths):
        yield
        return
    directory = Path(directory) if directory is not None else registry_directory()
    reservation = directory / ('job-' + uuid4().hex + '.json')
    owner = None
    with guard(directory):
        for filename in directory.glob('job-*.json'):
            if filename.is_symlink():
                raise ValueError('Ungültige Ausgabesperre: ' + str(filename))
            stale = False
            with filename.open('r+b') as stream:
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    stream.seek(1)
                    try:
                        record = json.loads(stream.read().decode('utf-8'))
                        active = [canonical(p) for p in record['paths']]
                        if not active:
                            raise ValueError('Empty reservation')
                    except (ValueError, KeyError, TypeError) as exc:
                        raise ValueError('Eine aktive Ausgabesperre ist nicht lesbar.') from exc
                    if any(overlaps(path, existing) for path in paths for existing in active):
                        raise ValueError('Diese Ausgabe oder ein übergeordneter Ordner wird bereits aktualisiert.')
                else:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    stale = True
            if stale:
                filename.unlink()
        try:
            owner = reservation.open('x+b')
            owner.write(b'0' + json.dumps(dict(paths=[str(p) for p in paths], pid=os.getpid())).encode('utf-8'))
            owner.flush()
            owner.seek(0)
            msvcrt.locking(owner.fileno(), msvcrt.LK_NBLCK, 1)
        except BaseException:
            if owner is not None:
                owner.close()
                reservation.unlink(missing_ok=True)
            raise
    token = _held.set((*held, *paths))
    try:
        yield
    finally:
        _held.reset(token)
        # Closing releases the OS lock even if registry maintenance fails.
        owner.close()
        with guard(directory):
            reservation.unlink(missing_ok=True)
