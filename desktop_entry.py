"""Portable GUI entry point; route a worker before importing any Tk UI."""
import argparse
import ctypes
import io
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent


def pipe_stream(identifier, mode):
    """Duplicate an inherited Windows pipe for a windowed PyInstaller worker."""
    import msvcrt
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
                                      ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.DuplicateHandle.restype = wintypes.BOOL
    handle = kernel.GetStdHandle(identifier & 0xffffffff)
    duplicate = wintypes.HANDLE()
    process = kernel.GetCurrentProcess()
    if not handle or handle == wintypes.HANDLE(-1).value or not kernel.DuplicateHandle(
            process, handle, process, ctypes.byref(duplicate), 0, False, 2):
        raise OSError('Der Worker benötigt umgeleitete Standardstreams.')
    flags = os.O_RDONLY if mode == 'r' else os.O_WRONLY
    descriptor = msvcrt.open_osfhandle(duplicate.value, flags | os.O_BINARY)
    return io.TextIOWrapper(os.fdopen(descriptor, mode + 'b', buffering=0),
                            encoding='utf-8', errors='replace', write_through=True)


def main(argv=None):
    if getattr(sys, 'frozen', False):
        sys.dont_write_bytecode = True
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--worker' in argv:
        for name, identifier, mode in (('stdin', -10, 'r'), ('stdout', -11, 'w'), ('stderr', -12, 'w')):
            if getattr(sys, name) is None:
                setattr(sys, name, pipe_stream(identifier, mode))
        class Parser(argparse.ArgumentParser):
            def error(self, message):
                raise ValueError(message)
        parser = Parser(add_help=False)
        parser.add_argument('--worker', action='store_true')
        parser.add_argument('--game', required=True, choices=('anno117', 'anno1800', 'anno1404'))
        try:
            args, remaining = parser.parse_known_args(argv)
        except ValueError as exc:
            run_id = str(uuid4())
            for kind, payload in [('started', {}), ('finished', dict(status='failed', galleries=[], logs=[],
                    partial_output=False, error_code='invalid_job', message=str(exc)))]:
                print(json.dumps(dict(protocol_version=1, run_id=run_id, type=kind, payload=payload)), flush=True)
            return 2
        sys.path.insert(0, str(ROOT / args.game / 'tools'))
        from anno_worker import main as worker_main
        return worker_main(ROOT / args.game, args.game, remaining)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', choices=('anno117', 'anno1800', 'anno1404'), default='anno117')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--gui-data-dir', type=Path)
    parser.add_argument('--ui-smoke', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--ui-smoke-all', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.ui_smoke:
        from desktop.self_test import run
        return run(args.ui_smoke, args.gui_data_dir or args.ui_smoke.parent / 'gui-state', all_games=args.ui_smoke_all)
    if args.ui_smoke_all:
        parser.error('--ui-smoke-all requires --ui-smoke')
    from desktop.app import main as gui_main
    return gui_main(directory=args.gui_data_dir, game=args.game, config=args.config)


if __name__ == '__main__':
    sys.exit(main())
