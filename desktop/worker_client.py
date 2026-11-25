"""Consume one worker process off the UI thread; confirm exit before reporting success."""
import json
from pathlib import Path
from queue import Queue
import subprocess
import sys
import tempfile
from threading import Lock, Thread

from desktop.settings_store import ROOT, GAMES


class WorkerClient:
    def __init__(self):
        self.events = Queue()
        self.running = False
        self._process = None
        self._run_id = None
        self._cancelled = False
        self._lock = Lock()

    def start(self, game, action, config, rescan=False):
        if self.running:
            raise ValueError('Ein Auftrag läuft bereits.')
        if game not in GAMES or action not in ('demo', 'analyze', 'stamps'):
            raise ValueError('Ungültiger Auftrag.')
        if getattr(sys, 'frozen', False):
            raise ValueError('Der paketierte Desktop-Worker ist noch nicht verfügbar.')
        command = [sys.executable, str(ROOT / game / 'launch.py'), '--worker',
                   '--action', action, '--config', str(Path(config).resolve())]
        if rescan:
            command.append('--rescan')
        self.running = True
        self._run_id, self._cancelled = None, False
        self.thread = Thread(target=self._run, args=(command,), daemon=True)
        self.thread.start()

    def cancel(self):
        with self._lock:
            self._cancelled = True
            self._send_cancel()

    def _send_cancel(self):
        if self._process is not None and self._run_id is not None and self._cancelled:
            try:
                self._process.stdin.write(json.dumps(dict(protocol_version=1, run_id=self._run_id,
                                                         type='cancel')) + '\n')
                self._process.stdin.flush()
            except (OSError, ValueError):
                pass

    def _run(self, command):
        finished = None
        error = None
        try:
            with tempfile.TemporaryFile(mode='w+b') as diagnostics:
                with subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=diagnostics, text=True, encoding='utf-8',
                                      creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)) as process:
                    with self._lock:
                        self._process = process
                    for line in process.stdout:
                        try:
                            event = json.loads(line)
                            if not isinstance(event, dict) or event.get('protocol_version') != 1:
                                raise ValueError('Ungültiges Worker-Protokoll.')
                            kind, run_id = event.get('type'), event.get('run_id')
                            if not isinstance(event.get('payload'), dict) or not isinstance(run_id, str) or not run_id:
                                raise ValueError('Unvollständiges Worker-Ereignis.')
                            if finished is not None:
                                raise ValueError('Worker-Ereignis nach Abschluss.')
                            if self._run_id is None:
                                if kind != 'started':
                                    raise ValueError('Worker-Start fehlt.')
                                with self._lock:
                                    self._run_id = run_id
                                    self._send_cancel()
                            elif run_id != self._run_id or kind == 'started':
                                raise ValueError('Worker-Auftragskennung stimmt nicht überein.')
                            if kind == 'finished':
                                finished = event['payload']
                            elif kind in ('started', 'stage', 'progress', 'diagnostic'):
                                self.events.put(event)
                            else:
                                raise ValueError('Unbekanntes Worker-Ereignis.')
                        except (ValueError, TypeError) as exc:
                            error = str(exc)
                    code = process.wait()
                    diagnostics.seek(0)
                    stderr = diagnostics.read().decode('utf-8', 'replace')[-16000:]
                    if finished is None:
                        raise ValueError(error or stderr or 'Worker-Ende ohne Abschlussereignis.')
                    status = finished.get('status')
                    expected = {'success': (0,), 'failed': (1, 2), 'cancelled': (130,)}
                    if code not in expected.get(status, ()):
                        error = 'Worker-Abschluss und Exitcode stimmen nicht überein.'
                    for key in ('galleries', 'logs'):
                        if not isinstance(finished.get(key), list) or any(
                                not isinstance(p, str) for p in finished[key]):
                            error = 'Worker-Ausgabepfade fehlen.'
                    if type(finished.get('partial_output')) is not bool:
                        error = 'Worker-Teilergebnisstatus fehlt.'
                    if error:
                        raise ValueError(error)
                    if stderr:
                        finished['diagnostics'] = stderr
        except Exception as exc:
            finished = dict(status='failed', galleries=[], logs=[], partial_output=True,
                            message=str(exc))
        finally:
            with self._lock:
                self._process = None
            self.running = False
            self.events.put(dict(type='completed', payload=finished))
