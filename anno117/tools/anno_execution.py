"""Prepare and execute explicit jobs without prompts or browser side effects.

This module must be used within one game process, like the standalone launchers.
"""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from contextvars import ContextVar
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

from anno_demo import demo_settings


SCRIPTS = {'analyze': 'analyze_saves.py', 'stamps': 'build_stamp_gallery.py'}
_cancellation = ContextVar('anno_cancellation', default=None)


class ExecutionCancelled(Exception):
    """A cooperative cancellation reached a safe boundary."""


def checkpoint():
    """Check the current job without interrupting an atomic operation."""
    requested = _cancellation.get()
    if requested is not None and requested():
        raise ExecutionCancelled('Aktualisierung abgebrochen.')


@dataclass(frozen=True)
class ExecutionPlan:
    settings: object
    project: Path
    tasks: tuple
    demo: bool
    rescan: bool


@dataclass(frozen=True)
class ExecutionResult:
    galleries: tuple
    logs: tuple


def dependencies():
    """Check dependencies without installing packages or changing settings."""
    missing = [name for name in ('PIL', 'xlsxwriter', 'tzdata')
               if importlib.util.find_spec(name) is None]
    if missing:
        raise ValueError('Python-Pakete fehlen: ' + ', '.join(missing)
                         + '. Bitte Launch.cmd öffnen oder python -m pip install -r requirements.txt ausführen.')


def prepare_execution(settings, project, action, rescan=False):
    """Validate all tasks before writing anything; preserve the supplied settings."""
    project = Path(project).resolve()
    if settings.game not in ('anno117', 'anno1800', 'anno1404'):
        raise ValueError('Unbekanntes Spiel: ' + str(settings.game))
    tasks = ('analyze',) if settings.game == 'anno1404' else ('analyze', 'stamps')
    if action not in ('demo', *tasks):
        raise ValueError('Diese Aktion wird für das gewählte Spiel nicht unterstützt: ' + str(action))
    if rescan and action == 'stamps':
        raise ValueError('--rescan gilt für die Spielstandauswertung.')
    effective = demo_settings(settings, project) if action == 'demo' else settings
    selected = tasks if action == 'demo' else (action,)
    for task in selected:
        effective.validate(task)
    return ExecutionPlan(effective, project, selected, action == 'demo', rescan)


@contextmanager
def updating(output):
    """Retain the existing output-root lock until broader reservations are added."""
    import msvcrt
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.annotools.lock').open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise ValueError('Diese Ausgabe wird bereits aktualisiert.') from exc
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def load_generator(project, action):
    """Load a fresh generator; configuration is bound only by its run service."""
    path = project / 'tools' / SCRIPTS[action]
    spec = importlib.util.spec_from_file_location('anno_generator_' + action, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LogOutput:
    """Persist text and forward complete lines without mixing event output."""
    def __init__(self, log, callback):
        self.log = log
        self.callback = callback
        self.pending = ''
        self.stdout, self.stderr = sys.stdout, sys.stderr

    def notify(self, text):
        if self.callback is not None:
            with redirect_stdout(self.stdout), redirect_stderr(self.stderr):
                self.callback(text)

    def write(self, text):
        self.log.write(text)
        self.log.flush()
        self.pending += text
        while '\n' in self.pending:
            line, self.pending = self.pending.split('\n', 1)
            self.notify(line + '\n')
        return len(text)

    def flush(self):
        self.log.flush()

    def finish(self):
        if self.pending:
            self.notify(self.pending)
        self.pending = ''


def _run_task(plan, action, on_output):
    settings = plan.settings
    logs = settings.log_output
    logs.mkdir(parents=True, exist_ok=True)
    logfile = logs / (action + '.log')
    with logfile.open('w', encoding='utf-8') as log:
        stream = LogOutput(log, on_output)
        try:
            with redirect_stdout(stream), redirect_stderr(stream):
                module = load_generator(plan.project, action)
                module.run(settings, rescan=plan.rescan and action == 'analyze')
        finally:
            stream.finish()
    gallery = (settings.stamp_output / 'stamp-gallery.html' if action == 'stamps'
               else settings.report_output / 'map-gallery.html')
    if not gallery.is_file():
        raise ValueError('Galerie nach Aktualisierung nicht gefunden: ' + str(gallery))
    return gallery


def execute_plan(plan, on_event=None, on_output=None, *, cancel_requested=None, run_id=None):
    """Run a prepared job, returning output paths; callbacks run on this thread.

    Events use the proposed version-1 envelope, but this is not a worker transport.
    Exceptions propagate after a failed completion event; completed demo actions
    are reported as partial outputs. Cancellation is checked at safe boundaries.
    """
    settings = plan.settings
    run_id = run_id or str(uuid4())
    galleries = []
    logs = []

    def emit(kind, **payload):
        if on_event is not None:
            on_event(dict(protocol_version=1, run_id=run_id, type=kind, payload=payload))

    emit('started', game=settings.game, tasks=list(plan.tasks))
    token = _cancellation.set(cancel_requested)
    try:
        checkpoint()
        dependencies()
        # Revalidate in case inputs or output markers changed after preparation.
        for task in plan.tasks:
            settings.validate(task)
        with updating(settings.output):
            for task in plan.tasks:
                settings.validate(task)
            (settings.output / '.annotools-game.json').write_text(
                json.dumps({'game': settings.game}), encoding='utf-8')
            for task in plan.tasks:
                checkpoint()
                logs.append(settings.log_output / (task + '.log'))
                emit('stage', action=task, log=str(logs[-1]))
                galleries.append(_run_task(plan, task, on_output))
                checkpoint()
    except (Exception, KeyboardInterrupt, SystemExit) as exc:
        emit('finished', status='cancelled' if isinstance(exc, (KeyboardInterrupt, ExecutionCancelled)) else 'failed',
             galleries=[str(p) for p in galleries], logs=[str(p) for p in logs],
             partial_output=bool(logs), message=str(exc))
        raise
    finally:
        _cancellation.reset(token)
    emit('finished', status='success', galleries=[str(p) for p in galleries],
         logs=[str(p) for p in logs], partial_output=False)
    return ExecutionResult(tuple(galleries), tuple(logs))
