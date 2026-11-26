"""Launch a local AnnoOrganizer task or the bundled demo."""
import argparse
import json
import os
from pathlib import Path
import sys

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from anno_settings import Settings, initialize_settings
from anno_execution import dependencies, prepare_execution, execute_plan
from anno_installation import resolve_game_data

GAME = 'anno1404'
SCRIPTS = {'analyze': 'analyze_saves.py'}
LABELS = {'demo': 'Demo mit den mitgelieferten Beispielen', 'stamps': 'Stempelgalerie der konfigurierten Daten',
          'analyze': 'Karten und Spielstände der konfigurierten Daten'}


def choose():
    options = ['demo', *SCRIPTS]
    print('ANNO - Organizer – ' + GAME.replace('anno', 'Anno '))
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('demo', 'stamps', 'analyze'))
    parser.add_argument('--config', type=Path, default=ROOT / 'settings.json')
    parser.add_argument('--init-settings', action='store_true', help='Fehlende Einstellungen anlegen; vorhandene erhalten')
    parser.add_argument('--check', action='store_true', help='Prüfen, ohne Einstellungen oder Ausgaben anzulegen')
    parser.add_argument('--no-open', action='store_true', help='Galerie nach Erfolg nicht im Browser öffnen')
    parser.add_argument('--rescan', action='store_true', help='Spielstand-Zwischenspeicher ignorieren')
    parser.add_argument('--non-interactive', action='store_true',
                        help='Keine Abfragen oder automatische Einstellungsanlage; --action erforderlich')
    args = parser.parse_args()
    if args.non_interactive and (not args.action or args.init_settings):
        parser.error('--non-interactive braucht --action und erlaubt kein --init-settings.')
    example = ROOT / 'settings.example.json'
    if args.init_settings:
        created = initialize_settings(args.config, example)
        print(('Einstellungen angelegt: ' if created else 'Vorhandene Einstellungen bleiben erhalten: ') + str(args.config))
        return 0
    if os.name != 'nt':
        raise ValueError('ANNO - Organizer unterstützt derzeit Windows.')
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
        elif args.non_interactive:
            raise ValueError('Einstellungsdatei nicht gefunden: ' + str(selected))
        else:
            initialize_settings(selected, example)
    settings = Settings(GAME, selected)
    dependencies()
    ensure_installation(settings, args.check or args.non_interactive)
    plan = prepare_execution(settings, ROOT, action, args.rescan)
    if plan.demo:
        print('Demo: ausschliesslich die mitgelieferten Beispiele werden eingelesen.')
    print('Ausgabe: ' + str(plan.settings.output))
    if args.check:
        print('Prüfung erfolgreich.')
        return 0
    result = execute_plan(plan, on_output=lambda line: print(line, end='', flush=True))
    galleries = result.galleries
    for gallery in galleries:
        print('Galerie: ' + str(gallery))
    if not args.no_open:
        for gallery in galleries:
            os.startfile(gallery)
    return 0


if __name__ == '__main__':
    if '--worker' in sys.argv[1:]:
        from anno_worker import main as worker_main
        worker_args = list(sys.argv[1:])
        worker_args.remove('--worker')
        sys.exit(worker_main(ROOT, GAME, worker_args))
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit('Abgebrochen.')
    except (ValueError, OSError, ImportError, EOFError) as exc:
        sys.exit('ANNO - Organizer: ' + str(exc))
