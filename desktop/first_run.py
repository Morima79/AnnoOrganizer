"""Resolve GUI defaults from Windows Documents and registered installations."""
from desktop.settings_store import game_api


def system_settings(game):
    api = game_api(game)
    documents = api.documents_folder()
    names = {
        'anno117': ('Anno 117 - Pax Romana', 'Anno 117 Pax Romana', 'Anno 117'),
        'anno1800': ('Anno 1800', 'Anno1800'),
        'anno1404': ('Anno 1404', 'ANNO 1404 Venedig'),
    }
    data = dict(version=1, game=game, timezone='Europe/Zurich',
                output=str(documents / 'AnnoOrganizer' / game.replace('anno', 'Anno ')))
    if game == 'anno1404':
        candidates = [documents / name / 'Savegames' for name in names[game]]
        data['save_folders'] = [str(path) for path in candidates if path.is_dir()] or [str(candidates[0])]
    else:
        home = next((documents / name for name in names[game] if (documents / name).is_dir()),
                    documents / names[game][0])
        installation = api.find_game_data(game)
        data.update(game_data=str(installation) if installation else '',
                    account=str(home / 'accounts'), stamps=str(home / 'stamps'))
        if game == 'anno1800':
            data['archive'] = ''
    return data
