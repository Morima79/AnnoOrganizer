"""Find locally installed Anno game data without scanning entire drives."""
from functools import lru_cache
import os
from pathlib import Path
import re

GAME_NAMES = {'anno117': ('Anno 117 - Pax Romana', 'Anno 117 Pax Romana', 'Anno 117'),
              'anno1800': ('Anno 1800', 'Anno1800')}


def resolve_game_data(path, game):
    marker = 'config.rda' if game == 'anno117' else 'data0.rda'
    path = Path(path).resolve()
    for candidate in (path, path / 'maindata'):
        if (candidate / marker).is_file():
            return candidate
    return path


def steam_libraries(root):
    libraries = [Path(root)]
    filename = Path(root) / 'steamapps/libraryfolders.vdf'
    if filename.is_file():
        text = filename.read_text(encoding='utf-8-sig', errors='replace')
        for value in re.findall(r'"path"\s*"((?:\\.|[^"\\])*)"', text):
            libraries.append(Path(value.replace('\\\\', '\\')))
    return list(dict.fromkeys(libraries))


def registry_locations():
    if os.name != 'nt':
        return [], [], []
    import winreg
    steam = []
    ubisoft = []
    installed = []
    for hive, key, name, result in [
        (winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath', steam),
        (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Valve\Steam', 'InstallPath', steam),
        (winreg.HKEY_LOCAL_MACHINE, r'Software\Ubisoft\Launcher', 'InstallDir', ubisoft),
        (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Ubisoft\Launcher', 'InstallDir', ubisoft),
    ]:
        try:
            with winreg.OpenKey(hive, key) as handle:
                value = winreg.QueryValueEx(handle, name)[0]
                if value:
                    result.append(Path(value))
        except OSError:
            pass
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for prefix in (r'Software\Microsoft\Windows\CurrentVersion\Uninstall',
                       r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'):
            try:
                with winreg.OpenKey(hive, prefix) as parent:
                    count = winreg.QueryInfoKey(parent)[0]
                    for index in range(count):
                        try:
                            with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as entry:
                                label = str(winreg.QueryValueEx(entry, 'DisplayName')[0]).lower()
                                if 'anno 117' in label or 'anno 1800' in label:
                                    location = winreg.QueryValueEx(entry, 'InstallLocation')[0]
                                    if location:
                                        installed.append(Path(location))
                        except OSError:
                            pass
            except OSError:
                pass
    return steam, ubisoft, installed


@lru_cache(maxsize=2)
def find_game_data(game):
    if game not in GAME_NAMES:
        return None
    steam, ubisoft, installed = registry_locations()
    for key in ('ProgramFiles(x86)', 'ProgramFiles'):
        if os.environ.get(key):
            base = Path(os.environ[key])
            steam.append(base / 'Steam')
            ubisoft.append(base / 'Ubisoft/Ubisoft Game Launcher')
    candidates = list(installed)
    for root in dict.fromkeys(steam):
        for library in steam_libraries(root):
            candidates.extend(library / 'steamapps/common' / name for name in GAME_NAMES[game])
    for root in dict.fromkeys(ubisoft):
        candidates.extend(root / 'games' / name for name in GAME_NAMES[game])
    marker = 'config.rda' if game == 'anno117' else 'data0.rda'
    for path in candidates:
        found = resolve_game_data(path, game)
        if (found / marker).is_file():
            return found
    return None
