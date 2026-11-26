"""Load per-game settings and protect source data from overlapping output paths."""
from pathlib import Path
import copy
import ctypes
import json
import os
import sys
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
        selected = filename or os.environ.get('ANNOORGANIZER_SETTINGS') or PROJECT / 'settings.json'
        self.filename = Path(selected).resolve()
        if not self.filename.is_file():
            raise ValueError('Einstellungen fehlen. settings.example.json als settings.json kopieren und Pfade anpassen.')
        try:
            data = json.loads(self.filename.read_text(encoding='utf-8-sig'))
            self._configure(data)
        except (ValueError, OSError) as exc:
            raise ValueError(f'Einstellungen nicht lesbar: {self.filename}: {exc}') from exc

    @classmethod
    def from_data(cls, game, filename, data):
        """Resolve an unsaved configuration without creating files or outputs."""
        if game not in GAMES:
            raise ValueError('Unbekanntes Spiel: ' + str(game))
        instance = cls.__new__(cls)
        instance.game = game
        instance.filename = Path(filename).resolve()
        instance._configure(data)
        return instance

    def _configure(self, data):
        if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
            raise ValueError('Die Einstellungen benötigen version: 1.')
        self.data = copy.deepcopy(data)
        if self.data.get('game') != self.game:
            raise ValueError('Die Einstellungsdatei gehört nicht zu ' + self.game + '.')
        self.values = self.data
        self.zone = self.data.get('timezone', 'Europe/Zurich')
        ZoneInfo(self.zone)
        self.output = self.expand(self.values.get('output', './local-data'))

    @property
    def report_output(self):
        return self.path('report_output') or self.output / 'reports'

    @property
    def stamp_output(self):
        return self.path('stamp_output') or self.output / 'stamps'

    @property
    def log_output(self):
        return self.path('log_output') or self.output / 'logs'

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
        marker = self.output / '.annoorganizer-game.json'
        if marker.exists():
            data = json.loads(marker.read_text(encoding='utf-8'))
            if data.get('game') != self.game:
                raise ValueError('Dieser Ausgabeordner wird bereits von einer anderen Anno-Version verwendet.')
        for destination in (self.output, self.report_output, self.stamp_output, self.log_output):
            protect_output(destination, self.all_sources())
        return self

    def all_sources(self):
        paths = [self.path(key) for key in ('game_data', 'account', 'stamps', 'archive')]
        paths = [path for path in paths if path is not None]
        return paths + self.saves()


def protect_output(output, sources):
    output = Path(output).resolve()
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        if output.is_relative_to(Path(sys._MEIPASS).resolve()):
            raise ValueError('Ausgaben dürfen nicht in das interne Programmverzeichnis geschrieben werden.')
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
