"""Exercise first-launch GUI setup and its real worker without interactive dialogs."""
import json
from pathlib import Path
import tkinter as tk

from desktop.app import DesktopApp


def run(report, directory):
    root = None
    result = dict(status='failed')
    try:
        root = tk.Tk()
        root.withdraw()
        app = DesktopApp(root, directory=directory, game='anno1404')
        if app.document is None:
            raise ValueError(app.details)
        errors = []
        app.error = lambda exc: errors.append(str(exc))
        app.change_language('en')
        app.change_language('de')
        if errors:
            raise ValueError('\n'.join(errors))
        app.generate()
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
        watchdog = root.after(60000, timeout)
        root.mainloop()
        root.after_cancel(watchdog)
        if expired or errors or app.status != 'success':
            raise ValueError('GUI smoke failed: ' + app.details + '\n'.join(errors))
        if app.document.path.exists():
            raise ValueError('GUI demo unexpectedly saved a personal configuration')
        result = dict(status='success', language=app.language, galleries=app.last_result['galleries'])
    except Exception as exc:
        result['message'] = str(exc)
    finally:
        if root is not None:
            root.destroy()
        Path(report).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['status'] == 'success' else 1
