'Select an independent AnnoOrganizer game project.'
import argparse
import subprocess
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
GAMES = ('anno117', 'anno1800', 'anno1404')
OPTIONS = [('anno117', 'demo'), ('anno1800', 'demo'), ('anno1404', 'demo'), ('anno117', 'stamps'), ('anno117', 'analyze'), ('anno1800', 'stamps'), ('anno1800', 'analyze'), ('anno1404', 'analyze')]
LABELS = {'demo': 'Demo mit den mitgelieferten Beispielen', 'stamps': 'Stempelgalerie der konfigurierten Daten', 'analyze': 'Karten und Spielstände der konfigurierten Daten'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', choices=GAMES)
    parser.add_argument('--action', choices=('demo', 'stamps', 'analyze'))
    parser.add_argument('--config', type=Path)
    parser.add_argument('--init-settings', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-open', '--update-only', action='store_true')
    parser.add_argument('--rescan', action='store_true')
    parser.add_argument('--non-interactive', action='store_true')
    args = parser.parse_args()
    if args.non_interactive and (not args.game or not args.action or args.init_settings):
        parser.error('--non-interactive braucht --game und --action und erlaubt kein --init-settings.')
    if args.init_settings:
        if args.config and not args.game:
            parser.error('--config braucht hier --game.')
        games = [args.game] if args.game else GAMES
        status = 0
        for game in games:
            command = [sys.executable, str(ROOT / game / 'launch.py'), '--init-settings']
            if args.config:
                command += ['--config', str(args.config.resolve())]
            status = max(status, subprocess.call(command))
        return status
    if bool(args.game) != bool(args.action):
        parser.error('--game und --action gemeinsam angeben.')
    game, action = args.game, args.action
    if not game:
        print('AnnoOrganizer')
        for index, (game, action) in enumerate(OPTIONS, 1):
            print(f'{index}: {game.replace("anno", "Anno ")} – {LABELS[action]}')
        try:
            answer = input('Auswahl [1 = Anno 117 Demo]: ').strip()
            choice = int(answer) if answer else 1
        except ValueError:
            parser.error('Bitte eine der angezeigten Nummern eingeben.')
        if not 1 <= choice <= len(OPTIONS):
            parser.error('Bitte eine der angezeigten Nummern eingeben.')
        game, action = OPTIONS[choice - 1]
    command = [sys.executable, str(ROOT / game / 'launch.py'), '--action', action]
    if args.config:
        command += ['--config', str(args.config.resolve())]
    for flag in ['check', 'no_open', 'rescan', 'non_interactive']:
        if getattr(args, flag):
            command.append('--' + flag.replace('_', '-'))
    return subprocess.call(command)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit('Abgebrochen.')
