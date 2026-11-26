"""Read, import and safely save desktop configuration without processing inputs."""
from contextlib import contextmanager
import copy
import ctypes
from datetime import datetime, timezone
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
GAMES = ('anno117', 'anno1800', 'anno1404')
PATH_KEYS = ('game_data', 'account', 'stamps', 'archive', 'output',
             'report_output', 'stamp_output', 'log_output')


class SettingsConflict(ValueError):
    """The file changed since it was loaded, or another editor holds its lock."""


def local_app_data():
    """Resolve the actual Windows LocalAppData directory without writing to it."""
    if os.name != 'nt':
        raise OSError('Die Desktop-Anwendung benötigt Windows.')
    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 28, None, 0, buffer) != 0:
        raise OSError('LocalAppData konnte nicht ermittelt werden.')
    return Path(buffer.value) / 'AnnoOrganizer'


@lru_cache(maxsize=3)
def game_api(game):
    """Load each Settings class with its own project root; no configuration is read."""
    if game not in GAMES:
        raise ValueError('Unbekanntes Spiel: ' + str(game))
    tools = ROOT / game / 'tools'
    # Resolve the standalone module's dependency without leaving imports on sys.path.
    previous = sys.modules.get('anno_installation')
    try:
        spec = importlib.util.spec_from_file_location('anno_installation', tools / 'anno_installation.py')
        installation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installation)
        sys.modules['anno_installation'] = installation
        spec = importlib.util.spec_from_file_location('desktop_settings_' + game, tools / 'anno_settings.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop('anno_installation', None)
        else:
            sys.modules['anno_installation'] = previous


def read_json(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('Die Einstellungen müssen ein JSON-Objekt sein.')
    return data, raw


def relocated_data(settings):
    """Resolve known path targets before moving a configuration to another folder."""
    data = copy.deepcopy(settings.data)
    for key in PATH_KEYS:
        if data.get(key):
            data[key] = str(settings.expand(data[key]))
    data['output'] = str(settings.output)
    if 'save_folders' in data:
        data['save_folders'] = [str(path) for path in settings.saves()]
    return data


@contextmanager
def edit_lock(path):
    """Serialize desktop saves; keep the lock file to avoid inode/handle races."""
    import msvcrt
    with path.with_name(path.name + '.edit.lock').open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise SettingsConflict('Die Einstellungen werden bereits bearbeitet.') from exc
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


@contextmanager
def gui_session(directory):
    """Hold an OS-owned lock for one GUI session per preferences directory."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with edit_lock(directory / 'gui-session'):
        yield


def atomic_save(path, data, expected):
    """Back up and replace JSON, detecting changes immediately before replacement."""
    path = Path(path).resolve()
    if getattr(sys, 'frozen', False) and path.is_relative_to(Path(sys._MEIPASS).resolve()):
        raise ValueError('Einstellungen dürfen nicht im internen Programmverzeichnis gespeichert werden.')
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with edit_lock(path):
        def check():
            current = path.read_bytes() if path.exists() else None
            if current != expected:
                raise SettingsConflict('Die Datei wurde extern geändert. Bitte erneut laden.')
        check()
        descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            check()
            if expected is not None:
                backups = path.parent / 'backups'
                backups.mkdir(exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
                (backups / (path.name + '.' + stamp + '-' + uuid4().hex + '.bak')).write_bytes(expected)
            check()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return payload


class ConfigDocument:
    def __init__(self, game, path, data, original=None):
        self.game, self.path = game, Path(path).resolve()
        self.data, self.original = copy.deepcopy(data), original
        self.validate()

    @classmethod
    def load(cls, game, path):
        data, raw = read_json(path)
        return cls(game, path, data, raw)

    def view(self):
        return game_api(self.game).Settings.from_data(self.game, self.path, self.data)

    def validate(self):
        settings = self.view()
        for key in PATH_KEYS:
            value = self.data.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError('Ein Pfad muss eine Zeichenfolge sein: ' + key)
        folders = self.data.get('save_folders', [])
        if not isinstance(folders, list) or any(not isinstance(v, str) or not v.strip() for v in folders):
            raise ValueError('save_folders muss eine Liste nicht leerer Pfade sein.')
        sources = [settings.expand(self.data[key]) for key in ('game_data', 'account', 'stamps', 'archive')
                   if self.data.get(key)] + settings.saves()
        destinations = [settings.output, settings.report_output, settings.stamp_output, settings.log_output]
        for destination in destinations:
            game_api(self.game).protect_output(destination, sources)
            # Also protect the root desktop code and the other standalone projects.
            for code in [ROOT, *(ROOT / game for game in GAMES), ROOT / 'desktop', ROOT / 'templates']:
                if destination == code or code.is_relative_to(destination):
                    raise ValueError('Ausgabe und Programmordner dürfen sich nicht überschneiden.')
            protected = [ROOT / name for name in ('desktop', 'templates', 'scripts', 'tests',
                                                   '.venv', '.git', '.github', 'site')]
            protected += [ROOT / game / name for game in GAMES
                          for name in ('tools', 'docs', 'tests', '.venv')]
            for code in protected:
                if destination.is_relative_to(code):
                    raise ValueError('Ausgabe und Programmordner dürfen sich nicht überschneiden.')
        return settings

    def copy_to(self, destination):
        """Rebase only known paths, including implicit output, before importing."""
        destination = Path(destination).resolve()
        if destination == self.path or (destination.exists() and self.path.exists()
                                        and destination.samefile(self.path)):
            raise ValueError('Quelle und Importziel sind identisch. Bitte Datei verwenden wählen.')
        settings = self.view()
        data = relocated_data(settings)
        return ConfigDocument(self.game, destination, data)

    def save(self):
        self.validate()
        self.original = atomic_save(self.path, self.data, self.original)


class SettingsStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else local_app_data()
        if getattr(sys, 'frozen', False) and self.directory.resolve().is_relative_to(Path(sys._MEIPASS).resolve()):
            raise ValueError('GUI-Daten müssen ausserhalb des internen Programmverzeichnisses liegen.')
        self.preferences_path = self.directory / 'gui.json'
        self.preferences, self.original = ({}, None)
        if self.preferences_path.exists():
            self.preferences, self.original = read_json(self.preferences_path)
        selections = self.preferences.get('configurations', {})
        if not isinstance(selections, dict) or any(
                game not in GAMES or not isinstance(path, str) or not path.strip()
                for game, path in selections.items()):
            raise ValueError('Ungültige Konfigurationsauswahl in gui.json.')

    def default_path(self, game):
        if game not in GAMES:
            raise ValueError('Unbekanntes Spiel: ' + str(game))
        return self.directory / game / 'settings.json'

    def open_game(self, game):
        path = Path(self.preferences.get('configurations', {}).get(game, self.default_path(game)))
        if path.exists():
            return ConfigDocument.load(game, path)
        # A missing explicitly selected external file must not be silently recreated.
        if game in self.preferences.get('configurations', {}):
            raise FileNotFoundError(path)
        from desktop.first_run import system_settings
        document = ConfigDocument(game, path, system_settings(game))
        document.save()
        return document

    def select(self, document):
        previous = copy.deepcopy(self.preferences)
        self.preferences.setdefault('configurations', {})[document.game] = str(document.path)
        try:
            self.save_preferences()
        except Exception:
            self.preferences = previous
            raise

    def save_preferences(self):
        self.original = atomic_save(self.preferences_path, self.preferences, self.original)
