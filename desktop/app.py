"""Tk desktop preview backed by isolated game workers and explicit settings."""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from queue import Empty
import re
import sys
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from desktop.language import choose_language, resources
from desktop.batch import BatchError, prepare_all
from desktop.settings_store import ConfigDocument, GAMES, ROOT, SettingsConflict, SettingsStore, gui_session, local_app_data
from desktop.worker_client import WorkerClient
from desktop.window_state import WindowState


def source_version():
    if getattr(sys, 'frozen', False):
        return json.loads((Path(sys.executable).parent / 'BUILD.json').read_text(encoding='utf-8'))['version']
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
        self.folder_fields = []
        self.child_windows = {}
        self.controls = []
        self.status = 'ready'
        self.stage_action = None
        self.details = ''
        self.last_result = None
        self.active_logs = []
        self.snapshot = None
        self.batch = None
        self.batch_cancelled = False
        self.closing = False
        self.closed = False
        self._poll_id = None
        self._gallery_refresh = 0
        self.auto_open = tk.BooleanVar(root, self.store.preferences.get('auto_open_galleries') is True)
        self.action = tk.StringVar(root, self.saved_action(game))
        self.action.trace_add('write', lambda *_: self.refresh_destination())
        self.root.title(self.t('app_title'))
        self.root.iconbitmap(default=str(ROOT / 'desktop/assets/annoorganizer.ico'))
        self.root.geometry('1080x820')
        self.root.minsize(860, 720)
        self.window_state = WindowState(self.root, self.store)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Destroy>', self.on_destroy, add='+')
        self._style()
        self._load(game, config)
        self.render()
        self.window_state.watch(self.root, 'main')
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
        style.configure('TMenubutton', padding=(5, 6), background='#3c424c', foreground='#e5e7eb', arrowcolor='#e5e7eb')
        style.map('TMenubutton', background=[('active', '#505966')], foreground=[('disabled', '#89919d')],
                  arrowcolor=[('disabled', '#89919d')])
        for name in ('Gallery.TButton', 'Gallery.TMenubutton'):
            style.configure(name, borderwidth=0, relief='flat', background='#3c424c',
                            lightcolor='#3c424c', darkcolor='#3c424c', bordercolor='#3c424c')
            style.map(name, lightcolor=[('active', '#505966')], darkcolor=[('active', '#505966')],
                      bordercolor=[('active', '#505966')])
        style.layout('Gallery.TMenubutton', [('Menubutton.border', dict(sticky='nswe', children=[
            ('Menubutton.padding', dict(sticky='nswe', children=[('Menubutton.indicator', dict(sticky=''))]))]))])
        style.configure('Gallery.TMenubutton', padding=0)
        style.configure('Accent.TButton', background='#cba56a', foreground='#171b22', font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#dfb875')])
        style.configure('LanguageSelected.TButton', background='#cba56a', foreground='#171b22')
        style.map('LanguageSelected.TButton', background=[('active', '#dfb875')])
        style.configure('TEntry', fieldbackground='#181c22', foreground='#e5e7eb',
                        insertcolor='#ffffff', insertwidth=2, padding=5)
        style.configure('TNotebook', background='#20252d', borderwidth=0)
        style.configure('TNotebook.Tab', background='#3c424c', padding=(14, 7))
        style.map('TNotebook.Tab', background=[('selected', '#cba56a'), ('!selected', '#3c424c')],
                  foreground=[('selected', '#171b22'), ('!selected', '#e5e7eb')],
                  padding=[('selected', (14, 7)), ('!selected', (14, 7))],
                  lightcolor=[('selected', '#cba56a'), ('!selected', '#3c424c')])
        style.configure('TRadiobutton', background='#20252d', foreground='#e5e7eb')
        style.map('TRadiobutton', background=[('disabled', '#20252d')],
                  foreground=[('disabled', '#89919d')])
        style.configure('TCheckbutton', background='#20252d', foreground='#e5e7eb')
        style.map('TCheckbutton', background=[('active', '#20252d'), ('disabled', '#20252d')],
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
        if self.game == 'anno1404':
            self.document.data['save_folders'] = [field.get().strip() for field in self.folder_fields
                                                 if field.get().strip()]

    def render(self):
        selected = self.notebook.index('current') if hasattr(self, 'notebook') else 0
        if hasattr(self, 'shell'):
            self.shell.destroy()
        self.fields, self.controls, self.folder_fields = {}, [], []
        self.wrap_labels = []
        shell = ttk.Frame(self.root, padding=20)
        self.shell = shell
        shell.pack(fill='both', expand=True)
        header = ttk.Frame(shell)
        header.pack(fill='x', pady=(0, 18))
        ttk.Label(header, text=self.t('app_title'), style='Title.TLabel').pack(side='left')
        self.language_buttons = {}
        for language in ('en', 'de'):
            button = ttk.Button(header, text=language.upper(), width=4,
                                style='LanguageSelected.TButton' if language == self.language else 'TButton',
                                command=lambda value=language: self.change_language(value))
            button.pack(side='right', padx=3)
            self.language_buttons[language] = button
            self.controls.append(button)
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
        self.guide_button = ttk.Button(navigation, text=self.t('user_guide'), command=self.open_guide)
        self.guide_button.pack(fill='x', pady=(24, 8))
        about = ttk.Button(navigation, text=self.t('about'), command=self.about)
        about.pack(fill='x', pady=(0, 8))
        self.controls.append(about)
        ttk.Label(navigation, text=self.t('portable_hint' if getattr(sys, 'frozen', False) else 'preview_hint'),
                  style='Muted.TLabel', wraplength=145).pack(fill='x')
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
                self.folder_fields = [tk.StringVar(self.root, value) for value in
                                      (self.document.data.get('save_folders') or [''])]
                self.folder_rows = ttk.Frame(inputs)
                self.folder_rows.grid(row=1, column=0, sticky='ew', pady=(3, 10))
                self.draw_folder_rows()
                button = ttk.Button(inputs, text=self.t('add_folder'), command=self.add_save_folder)
                button.grid(row=2, column=0, sticky='w')
                self.controls.append(button)
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
        self.action_buttons = {}
        for value, key in [('analyze', 'analyze'), ('stamps', 'stamp_action'), ('demo', 'demo')]:
            radio = ttk.Radiobutton(actions, text=self.t(key), variable=self.action, value=value,
                                    command=self.choose_action)
            radio.pack(side='left', padx=(0, 15))
            self.action_buttons[value] = radio
            if value == 'stamps' and self.game == 'anno1404':
                radio.state(['disabled'])
            else:
                self.controls.append(radio)
        self.auto_open_checkbox = ttk.Checkbutton(panel, text=self.t('auto_open_galleries'),
                                                 variable=self.auto_open, command=self.choose_auto_open)
        self.auto_open_checkbox.pack(anchor='w', pady=(8, 0))
        self.controls.append(self.auto_open_checkbox)
        commands = ttk.Frame(panel)
        commands.pack(fill='x', pady=(14, 10))
        self.generate_button = ttk.Button(commands, text=self.t('generate'), style='Accent.TButton', command=self.generate)
        self.generate_button.pack(side='left', padx=(0, 8))
        self.cancel_button = ttk.Button(commands, text=self.t('cancel'), command=self.cancel)
        self.cancel_button.pack(side='left')
        self.update_all_button = ttk.Button(commands, text=self.t('update_all'), command=self.generate_all)
        self.update_all_button.pack(side='left', padx=(12, 0))
        self.controls.append(self.update_all_button)
        gallery_group = tk.Frame(commands, background='#89919d', padx=1, pady=1)
        gallery_group.pack(side='right')
        self.gallery_menu_button = ttk.Menubutton(gallery_group, width=0, style='Gallery.TMenubutton')
        self.gallery_menu_button.grid(row=0, column=2, sticky='nsew')
        self.gallery_menu_button.bind('<Map>', lambda _: self.size_gallery_arrow())
        self.gallery_menu_button.bind('<Configure>', lambda _: self.size_gallery_arrow())
        self.gallery_menu = tk.Menu(self.gallery_menu_button, tearoff=False, postcommand=self.fill_gallery_menu,
                                    background='#20252d', foreground='#e5e7eb',
                                    activebackground='#cba56a', activeforeground='#171b22',
                                    disabledforeground='#89919d', font=('Segoe UI', 10),
                                    borderwidth=1, relief='solid')
        self.gallery_menu_button.configure(menu=self.gallery_menu)
        self.gallery_button = ttk.Button(gallery_group, text=self.t('open_galleries'),
                                         style='Gallery.TButton', command=self.open_galleries)
        self.gallery_button.grid(row=0, column=0, sticky='nsew')
        tk.Frame(gallery_group, background='#89919d', width=1).grid(row=0, column=1, sticky='ns', pady=6)
        self.controls.append(self.generate_button)
        footer = ttk.Frame(panel)
        footer.pack(fill='x')
        self.progress = ttk.Progressbar(footer, mode='indeterminate')
        self.progress.pack(fill='x', pady=5)
        self.status_label = ttk.Label(footer, text=self.status_text(), wraplength=700)
        self.status_label.pack(anchor='w', pady=4)
        self.wrap_labels.append(self.status_label)
        logs = ttk.Button(footer, text=self.t('logs'), command=self.show_logs)
        logs.pack(side='left', pady=8)
        report_group = ttk.Frame(footer)
        report_group.pack(side='left', padx=8, pady=8)
        self.report_button = ttk.Button(report_group, text=self.t('open_report'), command=self.open_single_report)
        self.report_choice = ttk.Menubutton(report_group, text=self.t('open_report'))
        self.report_menu = tk.Menu(self.report_choice, tearoff=False, postcommand=self.fill_report_menu,
                                   background='#20252d', foreground='#e5e7eb',
                                   activebackground='#cba56a', activeforeground='#171b22',
                                   disabledforeground='#89919d', font=('Segoe UI', 10))
        self.report_choice.configure(menu=self.report_menu)
        output = ttk.Button(footer, text=self.t('open_output'), command=self.open_output)
        output.pack(side='right', pady=8)
        self.controls.extend([logs, output])
        for variable in self.fields.values():
            variable.trace_add('write', lambda *_: self.refresh_destination())
        self.refresh_destination()
        self.apply_busy()
        self.refresh_child_language()

    def size_gallery_arrow(self):
        """Keep a compact, centred arrow area half as wide as the button is tall."""
        group = self.gallery_menu_button.master
        group.columnconfigure(2, minsize=max(16, (self.gallery_button.winfo_height() + 1) // 2))

    def draw_folder_rows(self):
        for widget in self.folder_rows.winfo_children():
            widget.destroy()
        self.controls = [widget for widget in self.controls if widget.winfo_exists()]
        self.folder_entries = []
        self.folder_rows.columnconfigure(0, weight=1)
        for row, variable in enumerate(self.folder_fields):
            entry = ttk.Entry(self.folder_rows, textvariable=variable, width=50)
            entry.grid(row=row, column=0, sticky='ew', pady=(0, 6))
            browse = ttk.Button(self.folder_rows, text=self.t('browse'),
                                command=lambda field=variable: self.browse_save_folder(field))
            browse.grid(row=row, column=1, padx=(8, 0), pady=(0, 6))
            remove = ttk.Button(self.folder_rows, text=self.t('remove_folder'),
                                command=lambda index=row: self.remove_save_folder(index))
            remove.grid(row=row, column=2, padx=(5, 0), pady=(0, 6))
            self.folder_entries.append(entry)
            self.controls.extend([entry, browse, remove])

    def add_save_folder(self, value=''):
        self.folder_fields.append(tk.StringVar(self.root, value))
        self.draw_folder_rows()
        self.folder_entries[-1].focus_set()

    def remove_save_folder(self, index):
        if len(self.folder_fields) == 1:
            self.folder_fields[0].set('')
        else:
            self.folder_fields.pop(index)
            self.draw_folder_rows()

    def browse_save_folder(self, variable):
        path = filedialog.askdirectory(parent=self.root, title=self.t('save_folders'),
                                       initialdir=str(self.browse_start(variable.get())))
        if path:
            variable.set(path)

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
                view = self.draft_view()
                path = (view.output / 'demo' if self.action.get() == 'demo' else
                        view.report_output if self.action.get() == 'analyze' else view.stamp_output)
            except Exception:
                pass
        self.destination_label.configure(text=self.t('destination', path=path))
        if hasattr(self, 'gallery_button') and self.gallery_button.winfo_exists():
            self.refresh_galleries()

    def draft_view(self):
        from desktop.settings_store import game_api
        data = copy.deepcopy(self.document.data)
        for key, value in self.fields.items():
            if value.get().strip() or key in data:
                data[key] = value.get().strip()
        return game_api(self.game).Settings.from_data(self.game, self.document.path, data)

    def browse_start(self, value, *, game=False):
        """Resolve drafts against the configuration and open the nearest existing folder."""
        view = self.document.view()
        path = view.expand(value.strip()) if value.strip() else (view.path('game_data') if game else None)
        path = path or self.document.path.parent
        if path.is_file():
            path = path.parent
        if game and path.name.lower() == 'maindata':
            path = path.parent
        while not path.is_dir() and path.parent != path:
            path = path.parent
        return path

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
        else:
            ttk.Label(parent, text=self.t('timezone_hint'), wraplength=600,
                      style='Muted.TLabel').grid(row=row * 2 + 2, column=0, sticky='w')

    def status_text(self):
        if self.batch is not None and self.status == 'running':
            job = self.batch['jobs'][self.batch['index']]
            return self.t('batch_running', current=self.batch['index'] + 1, total=len(self.batch['jobs']),
                          game=job.game.replace('anno', 'Anno '),
                          action=self.t('analyze' if job.action == 'analyze' else 'stamp_action'))
        text = self.t('demo_running' if self.status == 'running' and self.action.get() == 'demo' else self.status)
        if self.status == 'running' and self.stage_action:
            text += ' ' + self.t('stamp_action' if self.stage_action == 'stamps' else 'analyze')
        if self.last_result and self.last_result.get('partial_output'):
            text += ' ' + self.t('partial')
        return text

    def apply_busy(self):
        busy = self.client.running or self.snapshot is not None
        for widget in self.controls:
            widget.configure(state='disabled' if busy else 'normal')
        selected = self.notebook.select()
        for tab in self.notebook.tabs():
            self.notebook.tab(tab, state='disabled' if busy and tab != selected else 'normal')
        if hasattr(self, 'release_button') and self.release_button.winfo_exists():
            self.release_button.configure(state='disabled' if busy else 'normal')
        if self.document is None:
            self.generate_button.state(['disabled'])
        self.cancel_button.configure(state='normal' if busy and self.status != 'cancelling' else 'disabled')
        self.refresh_galleries()
        if busy:
            self.progress.configure(mode='indeterminate')
            self.progress.start(15)
        else:
            self.progress.stop()
            self.progress.configure(mode='determinate', value=0)

    def error(self, exc):
        self.details = str(exc)
        messagebox.showerror(self.t('error'), self.t('conflict') if isinstance(exc, SettingsConflict)
                             else self.t('batch_invalid', details=exc) if isinstance(exc, BatchError)
                             else self.t('settings_error', details=exc), parent=self.root)

    def browse(self, key):
        initial = self.browse_start(self.fields[key].get(), game=key == 'game_data')
        if key == 'game_data':
            path = filedialog.askopenfilename(parent=self.root, title=self.t('choose_game_exe'),
                initialdir=str(initial), filetypes=[(self.t('executables'), '*.exe')])
            if not path:
                return
            from desktop.settings_store import game_api
            marker = 'config.rda' if self.game == 'anno117' else 'data0.rda'
            for folder in Path(path).resolve().parents:
                data = game_api(self.game).resolve_game_data(folder, self.game)
                if (data / marker).is_file():
                    path = str(data)
                    break
            else:
                self.details = self.t('invalid_game_exe')
                messagebox.showerror(self.t('error'), self.details, parent=self.root)
                return
        else:
            path = filedialog.askdirectory(parent=self.root, title=self.t(key), initialdir=str(initial))
        if path:
            self.fields[key].set(path)

    def change_language(self, language):
        if self.client.running or self.snapshot is not None:
            return
        self.collect()
        self.language, self.texts = language, resources(language)
        self.store.preferences['language'] = language
        try:
            self.window_state.remember_all()
            self.store.save_preferences()
        except Exception as exc:
            self.error(exc)
        self.render()

    def choose_auto_open(self):
        self.store.preferences['auto_open_galleries'] = self.auto_open.get()
        try:
            self.store.save_preferences()
        except Exception as exc:
            self.error(exc)

    def saved_action(self, game):
        actions = self.store.preferences.get('actions', {})
        selected = actions.get(game) if isinstance(actions, dict) else None
        allowed = ('analyze', 'demo') if game == 'anno1404' else ('analyze', 'stamps', 'demo')
        return selected if selected in allowed else 'analyze'

    def remember_action(self):
        if not isinstance(self.store.preferences.get('actions'), dict):
            self.store.preferences['actions'] = {}
        self.store.preferences['actions'][self.game] = self.action.get()

    def choose_action(self):
        if self.client.running or self.snapshot is not None:
            return
        self.remember_action()
        try:
            self.store.save_preferences()
        except Exception as exc:
            self.error(exc)

    def switch_game(self, game):
        if self.client.running or self.snapshot is not None:
            return
        self.collect()
        self.remember_action()
        self.status, self.last_result, self.stage_action = 'ready', None, None
        self.details = ''
        self.active_logs = []
        self._load(game)
        self.action.set(self.saved_action(game))
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

    def generate_all(self):
        if self.client.running or self.snapshot is not None:
            return
        self.collect()
        try:
            if self.document is None:
                raise ValueError(self.details or self.t('load_error'))
            plan = prepare_all(self.store, self.documents)
            jobs = plan.jobs
            if not jobs:
                self.last_result = dict(status='unavailable', galleries=[], logs=[], jobs=[],
                                        skipped=list(plan.skipped), partial_output=False)
                self.status, self.details = 'no_games', ''
                self.record_result(game='all-games', action='all')
                self.apply_busy()
                self.status_label.configure(text=self.status_text())
                self.notify_missing_games(self.last_result)
                return
            runtime = self.store.directory / 'runs'
            runtime.mkdir(parents=True, exist_ok=True)
            self.snapshot = tempfile.TemporaryDirectory(prefix='all-', dir=runtime)
            configs = {}
            for job in jobs:
                if job.game not in configs:
                    document = job.document.copy_to(Path(self.snapshot.name) / job.game / 'settings.json')
                    document.save()
                    configs[job.game] = document.path
            self.batch = dict(jobs=jobs, configs=configs, index=0, results=[], skipped=list(plan.skipped))
            self.batch_cancelled = False
            self.last_result, self.details, self.stage_action = None, '', None
            self.active_logs = []
            self.status = 'running'
            self.start_batch_job()
            self.apply_busy()
            self.status_label.configure(text=self.status_text())
        except Exception as exc:
            self.batch = None
            self.cleanup_snapshot()
            self.last_result = dict(status='failed', galleries=[], logs=[], partial_output=False, message=str(exc))
            self.status, self.details = 'failed', str(exc)
            self.record_result(game='all-games', action='all')
            self.apply_busy()
            self.status_label.configure(text=self.status_text())
            self.error(BatchError(str(exc)))

    def start_batch_job(self):
        job = self.batch['jobs'][self.batch['index']]
        self.stage_action = None
        self.active_logs = []
        self.client.start(job.game, job.action, self.batch['configs'][job.game])

    def complete_job(self, result):
        """Continue a successful queue or summarize its completed and partial outputs."""
        if self.batch is None:
            self.last_result = result
            self.record_result()
            return True
        while True:
            job = self.batch['jobs'][self.batch['index']]
            self.batch['results'].append(dict(game=job.game, action=job.action, result=result))
            game_results = [item for item in self.batch['results'] if item['game'] == job.game]
            game_result = dict(result, diagnostics='', logs=list(dict.fromkeys(
                path for item in game_results for path in item['result'].get('logs', []))),
                message='\n'.join(item['action'] + ': ' + str(item['result'][key])
                    for item in game_results for key in ('message', 'diagnostics') if item['result'].get(key)))
            self.record_result(game=job.game, action=job.action, result=game_result)
            if result['status'] != 'success' or self.batch_cancelled or self.batch['index'] + 1 == len(self.batch['jobs']):
                break
            self.batch['index'] += 1
            try:
                self.start_batch_job()
                self.status_label.configure(text=self.status_text())
                return False
            except Exception as exc:
                result = dict(status='failed', galleries=[], logs=[], partial_output=False, message=str(exc))
        status = result['status']
        if self.batch_cancelled and status == 'success':
            status = 'cancelled'
        results = self.batch['results']
        galleries = list(dict.fromkeys(path for item in results for path in item['result'].get('galleries', [])))
        logs = list(dict.fromkeys(path for item in results for path in item['result'].get('logs', [])))
        messages = [item['game'] + ' / ' + item['action'] + ': ' + str(item['result'][key])
                    for item in results for key in ('message', 'diagnostics') if item['result'].get(key)]
        self.last_result = dict(status=status, galleries=galleries, logs=logs, jobs=results, skipped=self.batch['skipped'],
            partial_output=status != 'success' and (bool(galleries) or any(
                item['result'].get('partial_output') for item in results)), message='\n'.join(messages))
        self.batch = None
        self.record_result(game='all-games', action='all')
        return True

    def notify_missing_games(self, result):
        missing = '\n'.join('• ' + item['game'].replace('anno', 'Anno ') +
                            (' – ' + self.t('analyze' if item['action'] == 'analyze' else 'stamp_action')
                             if item.get('action') else '') + ': ' + self.t(item['reason'])
                            for item in result['skipped'])
        outcome = self.t('no_games' if result['status'] == 'unavailable' else result['status'])
        completed = sum(item['result']['status'] == 'success' for item in result['jobs'])
        messagebox.showinfo(self.t('update_all'), self.t('missing_games_summary', outcome=outcome,
                            completed=completed, missing=missing), parent=self.root)

    def notify_demo(self, destination):
        messagebox.showinfo(self.t('demo_notice_title'), self.t('demo_notice', path=destination), parent=self.root)

    def generate(self):
        if self.client.running or self.snapshot is not None:
            return
        self.collect()
        if self.document is None:
            return
        try:
            view = self.document.validate()
            if self.action.get() != 'demo':
                view.validate(self.action.get())
            runtime = self.store.directory / 'runs'
            runtime.mkdir(parents=True, exist_ok=True)
            self.snapshot = tempfile.TemporaryDirectory(prefix='job-', dir=runtime)
            document = self.document.copy_to(Path(self.snapshot.name) / 'settings.json')
            document.save()
            self.last_result, self.details, self.stage_action = None, '', None
            self.active_logs = []
            self.status = 'running'
            if self.action.get() == 'demo':
                self.apply_busy()
                self.status_label.configure(text=self.status_text())
                self.notify_demo(view.output / 'demo')
            self.client.start(self.game, self.action.get(), document.path)
            self.apply_busy()
            self.status_label.configure(text=self.status_text())
        except Exception as exc:
            if self.snapshot is not None:
                self.cleanup_snapshot()
            self.last_result = dict(status='failed', galleries=[], logs=[], partial_output=False)
            self.last_result['message'] = str(exc)
            self.status = 'failed'
            self.apply_busy()
            self.status_label.configure(text=self.status_text())
            self.record_result()
            self.error(exc)

    def record_result(self, *, game=None, action=None, result=None):
        """Retain the last job's diagnostics even after the GUI closes."""
        try:
            folder = self.store.directory / 'logs'
            folder.mkdir(parents=True, exist_ok=True)
            (folder / ((game or self.game) + '-last-run.json')).write_text(json.dumps(dict(
                updated_at=datetime.now(timezone.utc).isoformat(), action=action or self.action.get(),
                result=result if result is not None else self.last_result), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        except OSError as exc:
            self.details += '\n' + str(exc)

    def cleanup_snapshot(self):
        snapshot, self.snapshot = self.snapshot, None
        if snapshot is not None:
            try:
                snapshot.cleanup()
            except OSError as exc:
                self.details += '\n' + str(exc)

    def cancel(self):
        if self.batch is not None:
            self.batch_cancelled = True
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
                    if not self.complete_job(event['payload']):
                        continue
                    self.details = '\n'.join(str(self.last_result.get(key, '')) for key in ('message', 'diagnostics'))
                    self.status = self.last_result['status']
                    self.cleanup_snapshot()
                    self.apply_busy()
                    if self.last_result.get('skipped') and not self.closing:
                        self.status_label.configure(text=self.status_text())
                        self.notify_missing_games(self.last_result)
                    if self.auto_open.get() and self.status == 'success' and not self.closing:
                        self.open_gallery_paths(self.last_result.get('galleries', []))
                    if self.closing:
                        self.closing = False
                        self.close()
                        if self.closed:
                            return
                self.status_label.configure(text=self.status_text())
        except Empty:
            pass
        if time.monotonic() >= self._gallery_refresh:
            self.refresh_galleries()
            self.refresh_logs()
            self._gallery_refresh = time.monotonic() + 1
        self._poll_id = self.root.after(80, self.poll)

    def available_galleries(self):
        """Discover existing published pages in this configuration, including demos."""
        if self.document is None:
            return []
        try:
            view = self.draft_view()
            candidates = [(self.t('map_gallery'), view.report_output / 'map-gallery.html'),
                          (self.t('demo_map_gallery'), view.output / 'demo/reports/map-gallery.html')]
            if self.game != 'anno1404':
                candidates += [(self.t('stamp_gallery'), view.stamp_output / 'stamp-gallery.html'),
                               (self.t('demo_stamp_gallery'), view.output / 'demo/stamps/stamp-gallery.html')]
            result, seen = [], set()
            for label, path in candidates:
                if path.is_file() and path not in seen:
                    result.append((label, path))
                    seen.add(path)
            return result
        except (ValueError, OSError, KeyError):
            return []

    def refresh_galleries(self):
        state = 'normal' if self.available_galleries() else 'disabled'
        self.gallery_button.configure(state=state)
        self.gallery_menu_button.configure(state=state)
        reports = self.available_reports()
        self.report_button.configure(state='normal' if reports else 'disabled')
        if len(reports) > 1:
            self.report_button.grid_remove()
            self.report_choice.grid(row=0, column=0)
        else:
            self.report_choice.grid_remove()
            self.report_button.grid(row=0, column=0)

    def open_single_report(self):
        reports = self.available_reports()
        if len(reports) == 1:
            self.open_report(reports[0][1])
        else:
            self.refresh_galleries()

    def available_reports(self):
        """Resolve regular and demo workbooks against the displayed configuration."""
        if self.document is None:
            return []
        try:
            view = self.draft_view()
            filename = self.game + '-map-seeds.xlsx'
            candidates = [(self.t('report'), view.report_output / filename),
                          (self.t('demo_report'), view.output / 'demo/reports' / filename)]
            reports, seen = [], set()
            for label, path in candidates:
                if path.is_file() and path not in seen:
                    reports.append((label, path))
                    seen.add(path)
            return reports
        except (ValueError, OSError, KeyError):
            return []

    def fill_report_menu(self):
        self.report_menu.delete(0, 'end')
        for label, path in self.available_reports():
            self.report_menu.add_command(label=label, command=lambda target=path: self.open_report(target))

    def open_report(self, path):
        try:
            if path not in [target for _, target in self.available_reports()]:
                raise OSError(self.t('missing_output'))
            os.startfile(path)
        except OSError as exc:
            self.error(exc)

    def fill_gallery_menu(self):
        self.gallery_menu.delete(0, 'end')
        for label, path in self.available_galleries():
            self.gallery_menu.add_command(label=label, command=lambda target=path: self.open_galleries(target))

    def open_galleries(self, selected=None):
        self.open_gallery_paths([path for _, path in self.available_galleries()
                                 if selected is None or path == selected])

    def open_gallery_paths(self, paths):
        for path in dict.fromkeys(Path(value).resolve() for value in paths):
            if not path.is_file():
                continue
            try:
                if not webbrowser.open(path.as_uri()):
                    raise OSError(self.t('browser_failed', path=path))
            except OSError as exc:
                self.details = str(exc)
                messagebox.showerror(self.t('error'), self.t('browser_failed', path=path), parent=self.root)
                break

    def open_output(self):
        try:
            self.collect()
            if self.document is None:
                return
            view = self.document.view()
            if self.last_result and self.last_result.get('jobs'):
                path = view.stamp_output if self.action.get() == 'stamps' else view.report_output
            elif self.last_result and self.last_result.get('galleries'):
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
        window = self.new_child('logs')
        if window is None:
            return
        window.geometry('850x500')
        self.log_text = tk.Text(window, wrap='word')
        self.log_text.pack(fill='both', expand=True)
        self.refresh_logs()
        self.show_child(window, 'logs')

    def log_content(self):
        """Read only the selected game's saved run or its current live log."""
        content, result = '', {}
        record = self.store.directory / 'logs' / (self.game + '-last-run.json')
        try:
            if record.is_file():
                saved = json.loads(record.read_text(encoding='utf-8'))
                result = saved['result']
                if not isinstance(result, dict) or not isinstance(result.get('logs', []), list):
                    raise ValueError('Invalid saved run')
                content = str(saved.get('updated_at', ''))
                content += '\n' + '\n'.join(str(result.get(key, '')) for key in ('message', 'diagnostics'))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            content = str(exc)
            result = {}
        running_game = self.batch['jobs'][self.batch['index']].game if self.batch else self.game
        paths = result.get('logs', [])
        if (self.client.running or self.snapshot is not None) and running_game == self.game:
            content, paths = '', self.active_logs
        for path in paths:
            if not isinstance(path, str):
                continue
            try:
                if Path(path).is_file():
                    content += '\n\n' + path + '\n' + Path(path).read_text(encoding='utf-8', errors='replace')[-100000:]
            except OSError as exc:
                content += '\n' + str(exc)
        return content.strip() or self.t('log_empty')

    def refresh_logs(self):
        window = self.child_windows.get('logs')
        if window is None or not window.winfo_exists():
            return
        content = self.log_content()
        if self.log_text.get('1.0', 'end-1c') != content:
            self.log_text.configure(state='normal')
            self.log_text.delete('1.0', 'end')
            self.log_text.insert('1.0', content)
            self.log_text.configure(state='disabled')

    def open_guide(self):
        page = ROOT / 'docs/user-guide.html'
        url = page.resolve().as_uri() if page.is_file() else 'https://morima79.github.io/AnnoOrganizer/guide/'
        url += '?lang=' + self.language
        try:
            if not webbrowser.open(url):
                raise OSError(self.t('guide_open_failed', url=url))
        except Exception as exc:
            self.error(exc)

    def about(self):
        window = self.new_child('about')
        if window is None:
            return
        key = 'about_portable_text' if getattr(sys, 'frozen', False) else 'about_text'
        self.about_label = ttk.Label(window, text=self.t(key, version=source_version()), padding=22)
        self.about_label.pack()
        self.release_button = ttk.Button(window, text=self.t('check_releases'), command=lambda: webbrowser.open(
            'https://github.com/Morima79/AnnoOrganizer/releases'))
        self.release_button.pack(pady=(0, 18))
        self.show_child(window, 'about')

    def new_child(self, key):
        existing = self.child_windows.get(key)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift(self.root)
            existing.focus_set()
            return None
        window = tk.Toplevel(self.root)
        window.withdraw()
        window.transient(self.root)
        window.title(self.t(key))
        window.protocol('WM_DELETE_WINDOW', lambda: self.close_child(key))
        self.child_windows[key] = window
        return window

    def show_child(self, window, key):
        self.window_state.watch(window, key, owner=self.root)
        window.deiconify()
        window.lift(self.root)
        window.focus_set()

    def close_child(self, key):
        try:
            self.window_state.close_child(key)
        except Exception as exc:
            self.error(exc)

    def refresh_child_language(self):
        self.refresh_logs()
        for key, window in self.child_windows.items():
            if window.winfo_exists():
                window.title(self.t(key))
                if key == 'about':
                    text = 'about_portable_text' if getattr(sys, 'frozen', False) else 'about_text'
                    self.about_label.configure(text=self.t(text, version=source_version()))
                    self.release_button.configure(text=self.t('check_releases'))

    def finish_close(self):
        try:
            self.remember_action()
            self.window_state.remember_all()
            self.store.save_preferences()
        except Exception as exc:
            self.error(exc)
        self.closed = True
        self.root.destroy()

    def close(self):
        if self.closing:
            return
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
        self.finish_close()


def main(*, directory=None, game='anno117', config=None):
    root = tk.Tk()
    root.withdraw()
    try:
        directory = Path(directory).resolve() if directory is not None else local_app_data()
        try:
            with gui_session(directory):
                DesktopApp(root, directory=directory, game=game, config=config)
                root.deiconify()
                root.mainloop()
        except SettingsConflict:
            language = choose_language()
            messagebox.showinfo('ANNO - Organizer', resources(language)['already_running'], parent=root)
            root.destroy()
            return 1
    except Exception as exc:
        messagebox.showerror('ANNO - Organizer', str(exc), parent=root)
        root.destroy()
        return 1
    return 0
