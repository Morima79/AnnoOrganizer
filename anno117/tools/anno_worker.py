"""Run one explicit game job using versioned JSON lines on stdout."""
import argparse
import json
from pathlib import Path
import sys
from threading import Event, Thread
from uuid import uuid4

from anno_execution import ExecutionCancelled, execute_plan, prepare_execution
from anno_settings import Settings


class WorkerParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def read_commands(stream, cancelled, run_id):
    """Accept only matching cancellation requests; EOF does not cancel a job."""
    for line in stream:
        try:
            command = json.loads(line)
        except ValueError:
            continue
        if (isinstance(command, dict) and command.get('protocol_version') == 1
                and command.get('run_id') == run_id and command.get('type') == 'cancel'):
            cancelled.set()


def main(project, game, argv=None, *, stdin=None, stdout=None):
    """Return 0/1/2/130 for success, processing failure, invalid job or cancellation."""
    source = stdin if stdin is not None else sys.stdin
    target = stdout if stdout is not None else sys.stdout
    run_id = str(uuid4())
    finished = False

    def emit(event):
        nonlocal finished
        finished = finished or event['type'] == 'finished'
        target.write(json.dumps(event, ensure_ascii=False) + '\n')
        target.flush()

    def event(kind, **payload):
        emit(dict(protocol_version=1, run_id=run_id, type=kind, payload=payload))

    parser = WorkerParser(add_help=False)
    parser.add_argument('--action', required=True, choices=('demo', 'analyze', 'stamps'))
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--rescan', action='store_true')
    try:
        args = parser.parse_args(argv)
        settings = Settings(game, args.config)
        plan = prepare_execution(settings, project, args.action, args.rescan)
    except Exception as exc:
        event('started', game=game, tasks=[])
        event('finished', status='failed', galleries=[], logs=[], partial_output=False,
              message=str(exc), error_code='invalid_job')
        return 2

    cancelled = Event()
    # The isolated worker exits after one job; a blocked stdin reader is daemonized.
    reader = Thread(target=read_commands, args=(source, cancelled, run_id), daemon=True)
    reader.start()
    try:
        execute_plan(plan, on_event=emit, cancel_requested=cancelled.is_set, run_id=run_id)
    except (ExecutionCancelled, KeyboardInterrupt):
        return 130
    except (Exception, SystemExit) as exc:
        if not finished:
            event('finished', status='failed', galleries=[], logs=[], partial_output=True,
                  message=str(exc), error_code='worker_error')
        return 1
    return 0
