"""Tk desktop preview backed by isolated game workers and explicit settings."""
import copy
import json
import os
from pathlib import Path
from queue import Empty
import re
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from desktop.language import choose_language, resources
from desktop.settings_store import ConfigDocument, GAMES, ROOT, SettingsConflict, SettingsStore
from desktop.worker_client import WorkerClient


def source_version():
    text = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    match = re.search(r'^## \[(v[^]]+)\]', text, re.MULTILINE)
    return (match.group(1) if match else 'development') + ' + desktop preview'


class DesktopApp:
    def __init__(self, root, *, directory=None, game='anno117', config=None):
        self.root = root
        self.store = SettingsStore(directory)
        self.language = choose_language(self.store.preferences.get('language'))
        self.texts = resources(self.language)
        self.client = WorkerClient()
        self.game = game
        self.documents, self.baselines = {}, {}
        self.document = None
        self.fields = {}
        self.folder_text = None
        self.controls = []
        self.status = 'ready'
        self.stage_action = None
        self.details = ''
        self.last_result = None
        self.active_logs = []
        self.snapshot = None
        self.closing = False
        self._poll_id = None
        self.action = tk.StringVar(root, 'demo')
        self.action.trace_add('write', lambda *_: self.refresh_destination())
        self.root.title('AnnoOrganizer')
        self.root.geometry('1080x820')
        self.root.minsize(860, 720)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Destroy>', self.on_destroy, add='+')
        self._style()
        self._load(game, config)
        self.render()
        self._poll_id = self.root.after(80, self.poll)

    def on_destroy(self, event):
        if event.widget is self.root and self._poll_id is not None:
            try:
                self.root.after_cancel(self._poll_id)
            except tk.TclError:
                pass
            self._poll_id = None

    def t(self, key, **values):
        return self.texts[key].format(**values)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background='#20252d', foreground='#e5e7eb')
        style.configure('TFrame', background='#20252d')
        style.configure('TLabel', background='#20252d', foreground='#e5e7eb')
        style.configure('Title.TLabel', font=('Segoe UI', 21, 'bold'), foreground='#dfb875')
        style.configure('Muted.TLabel', foreground='#b6bdc8')
        style.configure('TButton', padding=(10, 6), background='#3c424c')
        style.map('TButton', background=[('active', '#505966')], foreground=[('disabled', '#89919d')])
        style.configure('Accent.TButton', background='#cba56a', foreground='#171b22', font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#dfb875')])
        style.configure('TEntry', fieldbackground='#181c22', foreground='#e5e7eb', padding=5)
        style.configure('TNotebook', background='#20252d', borderwidth=0)
        style.configure('TNotebook.Tab', background='#3c424c', padding=(14, 7))
        style.map('TNotebook.Tab', background=[('selected', '#505966')])
        style.configure('TRadiobutton', background='#20252d', foreground='#e5e7eb')
        style.map('TRadiobutton', background=[('disabled', '#20252d')],
                  foreground=[('disabled', '#89919d')])
        style.configure('Horizontal.TProgressbar', troughcolor='#181c22', background='#cba56a')
        self.root.configure(background='#20252d')

    def _load(self, game, config=None):
        self.game = game
        try:
            if config is not None:
                self.documents[game] = ConfigDocument.load(game, config)
            if game not in self.documents:
                self.documents[game] = self.store.open_game(game)
            self.document = self.documents[game]
            self.baselines.setdefault(game, copy.deepcopy(self.document.data))
        except Exception as exc:
            self.document = None
            self.details = str(exc)
            self.status = 'load_error'

    def collect(self):
        if self.document is None:
            return
        for key, variable in self.fields.items():
            value = variable.get().strip()
            if value or key in self.document.data:
                self.document.data[key] = value
        if self.folder_text is not None:
            self.document.data['save_folders'] = [line.strip() for line in
                self.folder_text.get('1.0', 'end-1c').splitlines() if line.strip()]

    def render(self):
        selected = self.notebook.index('current') if hasattr(self, 'notebook') else 0
        for child in self.root.winfo_children():
            child.destroy()
        self.fields, self.controls, self.folder_text = {}, [], None
        self.wrap_labels = []
        shell = ttk.Frame(self.root, padding=20)
        shell.pack(fill='both', expand=True)
        header = ttk.Frame(shell)
        header.pack(fill='x', pady=(0, 18))
        ttk.Label(header, text='AnnoOrganizer', style='Title.TLabel').pack(side='left')
        for language in ('en', 'de'):
            ttk.Button(header, text=language.upper(), width=4,
                       command=lambda value=language: self.change_language(value)).pack(side='right', padx=3)
        body = ttk.Frame(shell)
        body.pack(fill='both', expand=True)
        navigation = ttk.Frame(body, width=160)
        navigation.pack(side='left', fill='y', padx=(0, 20))
        for game in GAMES:
            button = ttk.Button(navigation, text=game.replace('anno', 'Anno '), width=15,
                                style='Accent.TButton' if game == self.game else 'TButton',
                                command=lambda value=game: self.switch_game(value))
            button.pack(fill='x', pady=(0, 10))
            self.controls.append(button)
        ttk.Button(navigation, text=self.t('about'), command=self.about).pack(fill='x', pady=(24, 8))
        ttk.Label(navigation, text=self.t('preview_hint'), style='Muted.TLabel', wraplength=145).pack(fill='x')
        panel = ttk.Frame(body)
        panel.pack(side='left', fill='both', expand=True)
        panel.bind('<Configure>', lambda event: [label.configure(wraplength=max(200, event.width - 4))
                                                for label in self.wrap_labels])
        ttk.Label(panel, text=self.game.replace('anno', 'Anno '), font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(panel, text=self.t('config'), style='Muted.TLabel').pack(anchor='w', pady=(12, 2))
        configuration_label = ttk.Label(panel, text=str(self.document.path) if self.document else '—', wraplength=720)
        configuration_label.pack(anchor='w', fill='x')
        self.wrap_labels.append(configuration_label)
        tools = ttk.Frame(panel)
        tools.pack(fill='x', pady=10)
        for key, command in [('use_config', self.use_file), ('import_config', self.import_file),
                             ('reload', self.reload), ('defaults', self.defaults), ('save', self.save)]:
            button = ttk.Button(tools, text=self.t(key), command=command)
            button.pack(side='left', padx=(0, 5))
            self.controls.append(button)
        self.notebook = ttk.Notebook(panel)
        self.notebook.pack(fill='both', expand=True)
        self.canvases = []
        inputs = self.page('paths')
        outputs = self.page('outputs')
        self.notebook.select(min(selected, 1))
        if self.document is not None:
            if self.game == 'anno1404':
                ttk.Label(inputs, text=self.t('save_folders')).grid(row=0, column=0, sticky='w')
                self.folder_text = tk.Text(inputs, height=5, width=45, font=('Segoe UI', 10),
                                           background='#181c22', foreground='#e5e7eb', insertbackground='white')
                self.folder_text.grid(row=1, column=0, sticky='nsew', pady=6)
                self.folder_text.insert('1.0', '\n'.join(self.document.data.get('save_folders', [])))
                button = ttk.Button(inputs, text=self.t('browse'), command=lambda: self.browse('save_folders'))
                button.grid(row=1, column=1, padx=(8, 0))
                self.controls.extend([self.folder_text, button])
            else:
                keys = ['game_data', 'account', 'stamps'] + (['archive'] if self.game == 'anno1800' else [])
                for row, key in enumerate(keys):
                    self.field(inputs, row, key)
            for row, key in enumerate(['output', 'report_output', 'stamp_output', 'log_output', 'timezone']):
                if key != 'stamp_output' or self.game != 'anno1404':
                    self.field(outputs, row, key)
            inputs.columnconfigure(0, weight=1)
        hint = ttk.Label(panel, text=self.t('snapshot_hint'), wraplength=720, style='Muted.TLabel')
        hint.pack(anchor='w', pady=(12, 8))
        self.destination_label = ttk.Label(panel, wraplength=720, style='Muted.TLabel')
        self.destination_label.pack(anchor='w', fill='x', pady=(0, 8))
        self.wrap_labels.extend([hint, self.destination_label])
        actions = ttk.Frame(panel)
        actions.pack(fill='x')
        for value, key in [('demo', 'demo'), ('analyze', 'analyze'), ('stamps', 'stamp_action')]:
            radio = ttk.Radiobutton(actions, text=self.t(key), variable=self.action, value=value)
            radio.pack(side='left', padx=(0, 15))
            if value == 'stamps' and self.game == 'anno1404':
                radio.state(['disabled'])
            else:
                self.controls.append(radio)
        commands = ttk.Frame(panel)
        commands.pack(fill='x', pady=(14, 10))
        self.generate_button = ttk.Button(commands, text=self.t('generate'), style='Accent.TButton', command=self.generate)
        self.generate_button.pack(side='left', padx=(0, 8))
        self.cancel_button = ttk.Button(commands, text=self.t('cancel'), command=self.cancel)
        self.cancel_button.pack(side='left')
        self.gallery_button = ttk.Button(commands, text=self.t('open_galleries'), command=self.open_galleries)
        self.gallery_button.pack(side='right')
        self.controls.append(self.generate_button)
        footer = ttk.Frame(panel)
        footer.pack(fill='x')
        self.progress = ttk.Progressbar(footer, mode='indeterminate')
        self.progress.pack(fill='x', pady=5)
        self.status_label = ttk.Label(footer, text=self.status_text(), wraplength=700)
        self.status_label.pack(anchor='w', pady=4)
        self.wrap_labels.append(self.status_label)
        ttk.Button(footer, text=self.t('logs'), command=self.show_logs).pack(side='left', pady=8)
        ttk.Button(footer, text=self.t('open_output'), command=self.open_output).pack(side='right', pady=8)
        for variable in self.fields.values():
            variable.trace_add('write', lambda *_: self.refresh_destination())
        self.refresh_destination()
        self.apply_busy()

    def page(self, key):
        page = ttk.Frame(self.notebook)
        self.notebook.add(page, text=self.t(key))
        canvas = tk.Canvas(page, background='#20252d', highlightthickness=0, width=400, height=80)
        scroll = ttk.Scrollbar(page, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        content = ttk.Frame(canvas, padding=14)
        item = canvas.create_window((0, 0), window=content, anchor='nw')
        content.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
        self.canvases.append(canvas)
        return content

    def refresh_destination(self):
        if not hasattr(self, 'destination_label') or not self.destination_label.winfo_exists():
            return
        path = '—'
        if self.document is not None:
            try:
                data = copy.deepcopy(self.document.data)
                for key, value in self.fields.items():
                    if value.get().strip() or key in data:
                        data[key] = value.get().strip()
                from desktop.settings_store import game_api
                view = game_api(self.game).Settings.from_data(self.game, self.document.path, data)
                path = (view.output / 'demo' if self.action.get() == 'demo' else
                        view.report_output if self.action.get() == 'analyze' else view.stamp_output)
            except Exception:
                pass
        self.destination_label.configure(text=self.t('destination', path=path))

    def field(self, parent, row, key):
        parent.columnconfigure(0, weight=1)
        ttk.Label(parent, text=self.t(key)).grid(row=row * 2, column=0, sticky='w')
        variable = tk.StringVar(self.root, self.document.data.get(key, ''))
        self.fields[key] = variable
        entry = ttk.Entry(parent, textvariable=variable, width=50)
        entry.grid(row=row * 2 + 1, column=0, sticky='ew', pady=(3, 10))
        self.controls.append(entry)
        if key != 'timezone':
            button = ttk.Button(parent, text=self.t('browse'), command=lambda: self.browse(key))
            button.grid(row=row * 2 + 1, column=1, padx=(8, 0), pady=(3, 10))
            self.controls.append(button)

    def status_text(self):
        text = self.t(self.status)
        if self.status == 'running' and self.stage_action:
            text += ' ' + self.t('stamp_action' if self.stage_action == 'stamps' else 'analyze')
        if self.last_result and self.last_result.get('partial_output'):
            text += ' ' + self.t('partial')
        return text

    def apply_busy(self):
        busy = self.client.running or self.snapshot is not None
        for widget in self.controls:
            widget.configure(state='disabled' if busy else 'normal')
        if self.document is None:
            self.generate_button.state(['disabled'])
        self.cancel_button.configure(state='normal' if busy and self.status != 'cancelling' else 'disabled')
        self.gallery_button.configure(state='normal' if not busy and self.last_result and
            self.last_result.get('status') == 'success' else 'disabled')
        if busy:
            self.progress.configure(mode='indeterminate')
            self.progress.start(15)
        else:
            self.progress.stop()
            self.progress.configure(mode='determinate', value=0)

    def error(self, exc):
        self.details = str(exc)
        messagebox.showerror(self.t('error'), self.t('conflict') if isinstance(exc, SettingsConflict)
                             else self.t('settings_error'), parent=self.root)

    def browse(self, key):
        path = filedialog.askdirectory(parent=self.root, title=self.t(key))
        if path:
            if key == 'save_folders':
                current = self.folder_text.get('1.0', 'end-1c').strip()
                self.folder_text.insert('end', ('\n' if current else '') + path)
            else:
                self.fields[key].set(path)

    def change_language(self, language):
        self.collect()
        self.language, self.texts = language, resources(language)
        self.store.preferences['language'] = language
        try:
            self.store.save_preferences()
        except Exception as exc:
            self.error(exc)
        self.render()

    def switch_game(self, game):
        self.collect()
        self.status, self.last_result, self.stage_action = 'ready', None, None
        self.active_logs = []
        if game == 'anno1404' and self.action.get() == 'stamps':
            self.action.set('demo')
        self._load(game)
        self.render()

    def dirty(self):
        return self.document is not None and self.document.data != self.baselines.get(self.game)

    def discard_ok(self):
        self.collect()
        return not self.dirty() or messagebox.askyesno(self.t('reload'), self.t('discard'), parent=self.root)

    def reload(self):
        if not self.discard_ok():
            return
        try:
            path = self.document.path if self.document else self.store.default_path(self.game)
            if path.exists():
                self.document = ConfigDocument.load(self.game, path)
            else:
                self.documents.pop(self.game, None)
                self._load(self.game)
                if self.document is None:
                    self.render()
                    return
            self.documents[self.game] = self.document
            self.baselines[self.game] = copy.deepcopy(self.document.data)
            self.status = 'ready'
            self.render()
        except Exception as exc:
            self.error(exc)

    def defaults(self):
        if not self.discard_ok():
            return
        try:
            data = self.store.preferences.get('configurations', {})
            # Reading defaults must not change the persisted external selection.
            temporary = SettingsStore(self.store.directory)
            temporary.preferences['configurations'] = {k: v for k, v in data.items() if k != self.game}
            document = temporary.open_game(self.game)
            self.document = self.documents[self.game] = document
            self.baselines[self.game] = copy.deepcopy(document.data)
            self.status = 'ready'
            self.render()
        except Exception as exc:
            self.error(exc)

    def save(self):
        self.collect()
        if self.document is None:
            return False
        try:
            self.document.save()
            self.store.select(self.document)
            self.baselines[self.game] = copy.deepcopy(self.document.data)
            self.status = 'saved'
            self.status_label.configure(text=self.status_text())
            return True
        except Exception as exc:
            self.error(exc)
            return False

    def use_file(self):
        if not self.discard_ok():
            return
        path = filedialog.askopenfilename(parent=self.root, filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            document = ConfigDocument.load(self.game, path)
            view = document.view()
            paths = '\n'.join(str(p) for p in [*view.all_sources(), view.output, view.report_output,
                                               view.stamp_output, view.log_output])
            if not messagebox.askyesno(self.t('use_config'), self.t('use_preview', source=document.path,
                                                                   paths=paths), parent=self.root):
                return
            self.store.select(document)
            self.document = self.documents[self.game] = document
            self.baselines[self.game] = copy.deepcopy(document.data)
            self.status = 'ready'
            self.render()
        except Exception as exc:
            self.error(exc)

    def import_file(self):
        if not self.discard_ok():
            return
        source = filedialog.askopenfilename(parent=self.root, filetypes=[('JSON', '*.json')])
        if not source:
            return
        try:
            document = ConfigDocument.load(self.game, source).copy_to(self.store.default_path(self.game))
            view = document.view()
            paths = '\n'.join(str(p) for p in [*view.all_sources(), view.output, view.report_output,
                                               view.stamp_output, view.log_output])
            if not messagebox.askyesno(self.t('import_config'), self.t('import_preview', paths=paths,
                                                                     target=document.path), parent=self.root):
                return
            if document.path.exists():
                if not messagebox.askyesno(self.t('import_config'), self.t('overwrite'), parent=self.root):
                    return
                document.original = document.path.read_bytes()
            document.save()
            self.store.select(document)
            self.document = self.documents[self.game] = document
            self.baselines[self.game] = copy.deepcopy(document.data)
            self.status = 'saved'
            self.render()
        except Exception as exc:
            self.error(exc)

    def generate(self):
        if self.client.running or self.snapshot is not None:
            return
        self.collect()
        if self.document is None:
            return
        try:
            self.document.validate()
            runtime = self.store.directory / 'runs'
            runtime.mkdir(parents=True, exist_ok=True)
            self.snapshot = tempfile.TemporaryDirectory(prefix='job-', dir=runtime)
            document = self.document.copy_to(Path(self.snapshot.name) / 'settings.json')
            document.save()
            self.last_result, self.details, self.stage_action = None, '', None
            self.active_logs = []
            self.status = 'running'
            self.client.start(self.game, self.action.get(), document.path)
            self.apply_busy()
            self.status_label.configure(text=self.status_text())
        except Exception as exc:
            if self.snapshot is not None:
                self.cleanup_snapshot()
            self.last_result = dict(status='failed', galleries=[], logs=[], partial_output=False)
            self.status = 'failed'
            self.apply_busy()
            self.status_label.configure(text=self.status_text())
            self.error(exc)

    def cleanup_snapshot(self):
        snapshot, self.snapshot = self.snapshot, None
        if snapshot is not None:
            try:
                snapshot.cleanup()
            except OSError as exc:
                self.details += '\n' + str(exc)

    def cancel(self):
        self.client.cancel()
        self.status = 'cancelling'
        self.status_label.configure(text=self.status_text())
        self.cancel_button.state(['disabled'])

    def poll(self):
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None
        try:
            while True:
                event = self.client.events.get_nowait()
                if event['type'] == 'stage':
                    self.stage_action = event['payload'].get('action')
                    logfile = event['payload'].get('log')
                    if isinstance(logfile, str):
                        self.active_logs.append(logfile)
                elif event['type'] == 'completed':
                    self.last_result = event['payload']
                    self.details = '\n'.join(str(self.last_result.get(key, '')) for key in ('message', 'diagnostics'))
                    self.status = self.last_result['status']
                    self.cleanup_snapshot()
                    self.apply_busy()
                    if self.closing:
                        self.root.destroy()
                        return
                self.status_label.configure(text=self.status_text())
        except Empty:
            pass
        self._poll_id = self.root.after(80, self.poll)

    def open_galleries(self):
        if self.last_result and self.last_result['status'] == 'success':
            for path in self.last_result['galleries']:
                if Path(path).is_file():
                    webbrowser.open(Path(path).as_uri())

    def open_output(self):
        try:
            self.collect()
            if self.document is None:
                return
            view = self.document.view()
            if self.last_result and self.last_result.get('galleries'):
                path = Path(self.last_result['galleries'][0]).parent
            else:
                path = (view.output / 'demo' if self.action.get() == 'demo' else
                        view.report_output if self.action.get() == 'analyze' else view.stamp_output)
            if not path.is_dir():
                messagebox.showinfo(self.t('open_output'), self.t('missing_output'), parent=self.root)
                return
            os.startfile(path)
        except Exception as exc:
            self.error(exc)

    def show_logs(self):
        window = tk.Toplevel(self.root)
        window.title(self.t('logs'))
        window.geometry('850x500')
        text = tk.Text(window, wrap='word')
        text.pack(fill='both', expand=True)
        content = self.details
        for path in (self.last_result or {}).get('logs', self.active_logs):
            try:
                if Path(path).is_file():
                    content += '\n\n' + path + '\n' + Path(path).read_text(encoding='utf-8', errors='replace')[-100000:]
            except OSError as exc:
                content += '\n' + str(exc)
        text.insert('1.0', content.strip() or self.t('log_empty'))
        text.configure(state='disabled')

    def about(self):
        window = tk.Toplevel(self.root)
        window.title(self.t('about'))
        ttk.Label(window, text=self.t('about_text', version=source_version()), padding=22).pack()
        ttk.Button(window, text=self.t('check_releases'), command=lambda: webbrowser.open(
            'https://github.com/Morima79/AnnoOrganizer/releases')).pack(pady=(0, 18))

    def close(self):
        if self.client.running or self.snapshot is not None:
            if messagebox.askyesno(self.t('cancel'), self.t('close_running'), parent=self.root):
                self.closing = True
                self.cancel()
            return
        self.collect()
        dirty = [game for game, doc in self.documents.items() if doc.data != self.baselines.get(game)]
        if dirty:
            answer = messagebox.askyesnocancel(self.t('save'), self.t('close_dirty'), parent=self.root)
            if answer is None:
                return
            if answer:
                try:
                    for game in dirty:
                        self.documents[game].save()
                        self.store.select(self.documents[game])
                        self.baselines[game] = copy.deepcopy(self.documents[game].data)
                except Exception as exc:
                    self.error(exc)
                    return
        self.root.destroy()


def main(*, directory=None, game='anno117', config=None):
    root = tk.Tk()
    try:
        DesktopApp(root, directory=directory, game=game, config=config)
        root.mainloop()
    except Exception as exc:
        messagebox.showerror('AnnoOrganizer', str(exc), parent=root)
        root.destroy()
        return 1
    return 0
