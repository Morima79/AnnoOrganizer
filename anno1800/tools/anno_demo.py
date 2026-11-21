"""Build a demo-only configuration without changing personal settings."""
import copy
from pathlib import Path
from anno_settings import protect_output


def demo_settings(settings, project):
    project = Path(project).resolve()
    demo = project / 'demo'
    if not (demo / 'manifest.json').is_file():
        raise ValueError('Die mitgelieferten Demodateien fehlen: ' + str(demo))
    configured = copy.copy(settings)
    data = dict(settings.data)
    data['output'] = str(settings.output / 'demo')
    for key in ('report_output', 'stamp_output', 'log_output'):
        data.pop(key, None)
    if settings.game == 'anno1404':
        data['save_folders'] = [str(demo / 'saves')]
    else:
        game_data = settings.path('game_data')
        data['game_data'] = str(game_data) if game_data else ''
        data['account'] = str(demo / 'saves')
        data['stamps'] = str(demo / 'stamps')
        data['archive'] = ''
    configured.data = configured.values = data
    configured.output = Path(data['output'])
    protect_output(configured.output, settings.all_sources())
    return configured
