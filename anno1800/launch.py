"""Launch a local AnnoTools task or the bundled demo."""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from anno_settings import Settings, initialize_settings
from anno_demo import demo_settings
from anno_installation import resolve_game_data

GAME = 'anno1800'
SCRIPTS = {'analyze': 'analyze_saves.py', 'stamps': 'build_stamp_gallery.py'}
LABELS = {'demo': 'Demo mit den mitgelieferten Beispielen', 'stamps': 'Stempelgalerie der konfigurierten Daten',
          'analyze': 'Karten und Spielstände der konfigurierten Daten'}


def dependencies():
    missing = [package for package in ('PIL', 'xlsxwriter', 'tzdata') if importlib.util.find_spec(package) is None]
    if missing:
        raise ValueError('Python-Pakete fehlen: ' + ', '.join(missing) + '. Bitte Launch.cmd öffnen oder python -m pip install -r requirements.txt ausführen.')


@contextmanager
def updating(output):
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


def choose():
    options = ['demo', *SCRIPTS]
    print('AnnoTools – ' + GAME.replace('anno', 'Anno '))
    for number, action in enumerate(options, 1):
        print(f'{number}: {LABELS[action]}')
    try:
        answer = input('Auswahl [1 = Demo]: ').strip()
        choice = int(answer) if answer else 1
    except ValueError as exc:
        raise ValueError('Bitte eine der angezeigten Nummern eingeben.') from exc
    if not 1 <= choice <= len(options):
        raise ValueError('Bitte eine der angezeigten Nummern eingeben.')
    return options[choice - 1]


def ensure_installation(settings, check):
    if GAME == 'anno1404':
        return
    game_data = settings.path('game_data')
    marker = 'config.rda' if GAME == 'anno117' else 'data0.rda'
    if game_data is not None and (game_data / marker).is_file():
        print('Spielinstallation: ' + str(game_data))
        return
    if check:
        raise ValueError('Spielinstallation nicht gefunden. Nur game_data in settings.json anpassen; Spielordner oder maindata sind möglich.')
    print('Bitte den Installationsordner des Spiels oder dessen maindata-Ordner angeben.')
    try:
        answer = input('Spielpfad: ').strip().strip('"')
    except EOFError as exc:
        raise ValueError('Bitte game_data in settings.json anpassen oder Launch.cmd interaktiv öffnen.') from exc
    if not answer:
        raise ValueError('Es wurde kein Spielpfad angegeben.')
    candidate = resolve_game_data(settings.expand(answer), GAME)
    if not (candidate / marker).is_file():
        raise ValueError('Keine passende Spielinstallation gefunden: ' + str(candidate))
    data = dict(settings.data)
    data['game_data'] = str(candidate)
    temporary = settings.filename.with_name(settings.filename.name + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, settings.filename)
    settings.data = settings.values = data


def run_task(settings, action, rescan=False):
    command = [sys.executable, str(ROOT / 'tools' / SCRIPTS[action])]
    if rescan and action == 'analyze':
        command.append('--rescan')
    env = dict(os.environ, ANNOTOOLS_SETTINGS=str(settings.filename), PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    with updating(settings.output):
        settings.validate(action)
        (settings.output / '.annotools-game.json').write_text(json.dumps({'game': GAME}), encoding='utf-8')
        logs = settings.output / 'logs'
        logs.mkdir(exist_ok=True)
        logfile = logs / (action + '.log')
        with logfile.open('w', encoding='utf-8') as log:
            with subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW) as process:
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    print(line, end='', flush=True)
                status = process.wait()
    if status:
        raise ValueError(f'Aktualisierung fehlgeschlagen. Protokoll: {logfile}')
    gallery = settings.output / ('stamps/stamp-gallery.html' if action == 'stamps' else 'reports/map-gallery.html')
    if not gallery.is_file():
        raise ValueError('Galerie nach Aktualisierung nicht gefunden: ' + str(gallery))
    print('Galerie: ' + str(gallery))
    return gallery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('demo', 'stamps', 'analyze'))
    parser.add_argument('--config', type=Path, default=ROOT / 'settings.json')
    parser.add_argument('--init-settings', action='store_true', help='Fehlende Einstellungen anlegen; vorhandene erhalten')
    parser.add_argument('--check', action='store_true', help='Prüfen, ohne Einstellungen oder Ausgaben anzulegen')
    parser.add_argument('--no-open', action='store_true', help='Galerie nach Erfolg nicht im Browser öffnen')
    parser.add_argument('--rescan', action='store_true', help='Spielstand-Zwischenspeicher ignorieren')
    args = parser.parse_args()
    example = ROOT / 'settings.example.json'
    if args.init_settings:
        created = initialize_settings(args.config, example)
        print(('Einstellungen angelegt: ' if created else 'Vorhandene Einstellungen bleiben erhalten: ') + str(args.config))
        return 0
    if os.name != 'nt':
        raise ValueError('AnnoTools unterstützt derzeit Windows.')
    action = args.action or choose()
    if action != 'demo' and action not in SCRIPTS:
        parser.error('Anno 1404 bietet bisher nur die Karten-/Spielstandauswertung.')
    if args.rescan and action == 'stamps':
        parser.error('--rescan gilt für die Spielstandauswertung.')
    selected = args.config
    if not selected.is_file():
        if args.check:
            if selected.resolve() != (ROOT / 'settings.json').resolve():
                raise ValueError('Einstellungsdatei nicht gefunden: ' + str(selected))
            selected = example
        else:
            initialize_settings(selected, example)
    settings = Settings(GAME, selected)
    dependencies()
    ensure_installation(settings, args.check)
    tasks = list(SCRIPTS) if action == 'demo' else [action]
    if action == 'demo':
        settings = demo_settings(settings, ROOT)
        print('Demo: ausschliesslich die mitgelieferten Beispiele werden eingelesen.')
    for task in tasks:
        settings.validate(task)
    print('Ausgabe: ' + str(settings.output))
    if args.check:
        print('Prüfung erfolgreich.')
        return 0
    if action == 'demo':
        settings.output.mkdir(parents=True, exist_ok=True)
        effective = settings.output / 'demo-settings.json'
        effective.write_text(json.dumps(settings.data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        settings.filename = effective
    galleries = [run_task(settings, task, args.rescan) for task in tasks]
    if not args.no_open:
        for gallery in galleries:
            os.startfile(gallery)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit('Abgebrochen.')
    except (ValueError, OSError, ImportError, EOFError) as exc:
        sys.exit('AnnoTools: ' + str(exc))
