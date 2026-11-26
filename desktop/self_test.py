"""Exercise first-launch GUI setup and its real worker without interactive dialogs."""
import json
from pathlib import Path
import tkinter as tk

from desktop.app import DesktopApp
from desktop.settings_store import ConfigDocument, GAMES, ROOT, SettingsStore, read_json


def seed_demo_settings(directory, games=GAMES):
    """Prepare explicit isolated fixtures; never use detected personal inputs in smoke tests."""
    store = SettingsStore(directory)
    for game in games:
        path = store.default_path(game)
        if path.exists():
            raise FileExistsError('Smoke tests require fresh configuration files: ' + str(path))
        source = ROOT / game / 'settings.example.json'
        data, _ = read_json(source)
        document = ConfigDocument(game, source, data).copy_to(path)
        document.data['output'] = str((store.directory / game / 'local-data').resolve())
        for key in ('report_output', 'stamp_output', 'log_output'):
            document.data.pop(key, None)
        document.save()


def run(report, directory, *, all_games=False, system_inputs=False):
    root = None
    result = dict(status='failed')
    try:
        if system_inputs:
            if Path(directory).exists() and any(Path(directory).iterdir()):
                raise ValueError('System first-run tests require a fresh GUI data directory')
            all_games = True
        else:
            seed_demo_settings(directory)
        root = tk.Tk()
        root.withdraw()
        app = DesktopApp(root, directory=directory, game='anno117' if system_inputs else 'anno1404')
        if system_inputs:
            for game in GAMES:
                app.store.open_game(game)
        originals = {game: app.store.default_path(game).read_bytes() for game in GAMES}
        if app.document is None:
            raise ValueError(app.details)
        errors = []
        app.error = lambda exc: errors.append(str(exc))
        app.change_language('en')
        app.change_language('de')
        if errors:
            raise ValueError('\n'.join(errors))
        starts = [app.generate, app.generate_all] if system_inputs else [app.generate_all if all_games else app.generate]
        if not all_games:
            app.action.set('demo')
        steps = []
        for start in starts:
            start()
            expired = []
            def observe():
                if app.snapshot is None:
                    root.quit()
                else:
                    root.after(40, observe)
            def timeout():
                expired.append(True)
                app.client.cancel()
                root.quit()
            root.after(40, observe)
            watchdog = root.after(1200000 if system_inputs else 240000 if all_games else 60000, timeout)
            root.mainloop()
            root.after_cancel(watchdog)
            if expired or errors or app.status != 'success':
                raise ValueError('GUI smoke failed: ' + app.details + '\n'.join(errors))
            steps.append(dict(status=app.status, galleries=len(app.last_result['galleries'])))
        if any(app.store.default_path(game).read_bytes() != original for game, original in originals.items()):
            raise ValueError('GUI smoke unexpectedly changed an input configuration')
        if all_games and (len(app.last_result.get('jobs', [])) != 5 or len(app.last_result['galleries']) != 5):
            raise ValueError('GUI batch did not complete all five galleries')
        result = dict(status='success', language=app.language, galleries=app.last_result['galleries'],
                      inputs='system' if system_inputs else 'bundled', steps=steps)
    except Exception as exc:
        result['message'] = str(exc)
    finally:
        if root is not None:
            root.destroy()
        Path(report).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['status'] == 'success' else 1
