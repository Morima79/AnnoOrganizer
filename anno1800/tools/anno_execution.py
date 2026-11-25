"""Prepare and execute explicit jobs without prompts or browser side effects.

The script backend is transitional: generators still load settings at import time.
This module must be used within one game process, like the standalone launchers.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from anno_demo import demo_settings


SCRIPTS = {'analyze': 'analyze_saves.py', 'stamps': 'build_stamp_gallery.py'}


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


def _run_task(plan, action, filename, on_output):
    settings = plan.settings
    command = [sys.executable, str(plan.project / 'tools' / SCRIPTS[action])]
    if plan.rescan and action == 'analyze':
        command.append('--rescan')
    env = dict(os.environ, ANNOTOOLS_SETTINGS=str(filename),
               PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    logs = settings.log_output
    logs.mkdir(parents=True, exist_ok=True)
    logfile = logs / (action + '.log')
    with logfile.open('w', encoding='utf-8') as log:
        with subprocess.Popen(command, cwd=plan.project, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                              errors='replace', creationflags=subprocess.CREATE_NO_WINDOW) as process:
            for line in process.stdout:
                log.write(line)
                log.flush()
                if on_output is not None:
                    on_output(line)
            status = process.wait()
    if status:
        raise ValueError(f'Aktualisierung fehlgeschlagen. Protokoll: {logfile}')
    gallery = (settings.stamp_output / 'stamp-gallery.html' if action == 'stamps'
               else settings.report_output / 'map-gallery.html')
    if not gallery.is_file():
        raise ValueError('Galerie nach Aktualisierung nicht gefunden: ' + str(gallery))
    return gallery


def execute_plan(plan, on_event=None, on_output=None):
    """Run a prepared job, returning output paths; callbacks run on this thread.

    Events use the proposed version-1 envelope, but this is not a worker transport.
    Exceptions propagate after a failed completion event; completed demo actions
    are reported as partial outputs. Cancellation is not implemented here yet.
    """
    if getattr(sys, 'frozen', False):
        raise ValueError('Der Skript-Backend unterstützt noch keine paketierte EXE.')
    settings = plan.settings
    run_id = str(uuid4())
    galleries = []
    logs = []

    def emit(kind, **payload):
        if on_event is not None:
            on_event(dict(protocol_version=1, run_id=run_id, type=kind, payload=payload))

    emit('started', game=settings.game, tasks=list(plan.tasks))
    try:
        dependencies()
        # Revalidate in case inputs or output markers changed after preparation.
        for task in plan.tasks:
            settings.validate(task)
        with updating(settings.output):
            for task in plan.tasks:
                settings.validate(task)
            filename = settings.filename
            if plan.demo:
                filename = settings.output / 'demo-settings.json'
                filename.write_text(json.dumps(settings.data, ensure_ascii=False, indent=2)
                                    + '\n', encoding='utf-8')
            (settings.output / '.annotools-game.json').write_text(
                json.dumps({'game': settings.game}), encoding='utf-8')
            for task in plan.tasks:
                logs.append(settings.log_output / (task + '.log'))
                emit('stage', action=task, log=str(logs[-1]))
                galleries.append(_run_task(plan, task, filename, on_output))
    except (Exception, KeyboardInterrupt) as exc:
        emit('finished', status='cancelled' if isinstance(exc, KeyboardInterrupt) else 'failed',
             galleries=[str(p) for p in galleries], logs=[str(p) for p in logs],
             partial_output=bool(logs), message=str(exc))
        raise
    emit('finished', status='success', galleries=[str(p) for p in galleries],
         logs=[str(p) for p in logs], partial_output=False)
    return ExecutionResult(tuple(galleries), tuple(logs))
