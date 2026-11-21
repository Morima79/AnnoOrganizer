"""Load per-game settings and protect source data from overlapping output paths."""
from pathlib import Path
import ctypes
import json
import os
from zoneinfo import ZoneInfo
from anno_installation import find_game_data, resolve_game_data

PROJECT = Path(__file__).resolve().parents[1]
GAMES = ('anno117', 'anno1800', 'anno1404')


def documents_folder():
    if os.name == 'nt':
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / 'Documents'


def initialize_settings(destination, example):
    """Create a settings file without replacing an existing configuration."""
    destination = Path(destination).resolve()
    if destination.exists():
        return False
    data = json.loads(Path(example).read_text(encoding='utf-8-sig'))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as file:
        file.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return True


class Settings:
    def __init__(self, game, filename=None):
        if game not in GAMES:
            raise ValueError('Unbekanntes Spiel: ' + str(game))
        self.game = game
        selected = filename or os.environ.get('ANNOTOOLS_SETTINGS') or PROJECT / 'settings.json'
        self.filename = Path(selected).resolve()
        if not self.filename.is_file():
            raise ValueError('Einstellungen fehlen. settings.example.json als settings.json kopieren und Pfade anpassen.')
        try:
            self.data = json.loads(self.filename.read_text(encoding='utf-8-sig'))
            if not isinstance(self.data, dict) or self.data.get('version') != 1:
                raise ValueError('Die Einstellungen benötigen version: 1.')
        except (ValueError, OSError) as exc:
            raise ValueError(f'Einstellungen nicht lesbar: {self.filename}: {exc}') from exc
        if self.data.get('game') != game:
            raise ValueError('Die Einstellungsdatei gehört nicht zu ' + game + '.')
        self.values = self.data
        self.zone = self.data.get('timezone', 'Europe/Zurich')
        ZoneInfo(self.zone)
        self.output = self.expand(self.values.get('output', './local-data'))

    def expand(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Ein Pfad muss eine nicht leere Zeichenfolge sein.')
        value = value.replace('${DOCUMENTS}', str(documents_folder())).replace('${HOME}', str(Path.home()))
        path = Path(os.path.expandvars(os.path.expanduser(value)))
        return (self.filename.parent / path).resolve() if not path.is_absolute() else path.resolve()

    def path(self, key):
        value = self.values.get(key)
        if key == 'game_data':
            return resolve_game_data(self.expand(value), self.game) if value else find_game_data(self.game)
        return self.expand(value) if value else None

    def saves(self):
        values = self.values.get('save_folders', [])
        if not isinstance(values, list):
            raise ValueError('save_folders muss eine Liste von Ordnern sein.')
        return [self.expand(value) for value in values]

    def validate(self, action):
        if action not in ('stamps', 'analyze'):
            raise ValueError('Unbekannte Aktion: ' + str(action))
        if action == 'stamps' and self.game == 'anno1404':
            raise ValueError('Für Anno 1404 ist keine Stempelgalerie implementiert.')
        if self.game == 'anno1404':
            if not any(p.is_dir() for p in self.saves()):
                raise ValueError('Kein konfigurierter Anno-1404-Spielstandordner vorhanden.')
        else:
            key = 'stamps' if action == 'stamps' else 'account'
            source = self.path(key)
            if source is None or not source.is_dir():
                raise ValueError(f'{self.game}: {key} fehlt oder ist kein Ordner. settings.json anpassen.')
            game = self.path('game_data')
            marker = 'config.rda' if self.game == 'anno117' else 'data0.rda'
            if game is None or not (game / marker).is_file():
                raise ValueError(f'{self.game}: game_data muss auf maindata mit {marker} zeigen.')
        marker = self.output / '.annotools-game.json'
        if marker.exists():
            data = json.loads(marker.read_text(encoding='utf-8'))
            if data.get('game') != self.game:
                raise ValueError('Dieser Ausgabeordner wird bereits von einer anderen Anno-Version verwendet.')
        protect_output(self.output, self.all_sources())
        return self

    def all_sources(self):
        paths = [self.path(key) for key in ('game_data', 'account', 'stamps', 'archive')]
        paths = [path for path in paths if path is not None]
        return paths + self.saves()


def protect_output(output, sources):
    output = Path(output).resolve()
    if output == PROJECT or PROJECT.is_relative_to(output):
        raise ValueError('Der Ausgabeordner darf nicht das Projekt oder dessen Oberordner sein.')
    for folder in [PROJECT / name for name in ('tools', 'tests', 'docs', '.venv')]:
        if output.is_relative_to(folder) or folder.is_relative_to(output):
            raise ValueError('Ausgabe und Quellcodeordner dürfen sich nicht überschneiden.')
    for source in sources:
        if source is None:
            continue
        source = Path(source).resolve()
        if output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError(f'Ausgabe und Eingabedaten dürfen sich nicht überschneiden: {source}')


def settings_for(game):
    return Settings(game)
