"""Standalone save manager for Anno 117 and Anno 1800."""
import argparse
import json
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from anno_save_editor import (GAME_FORMATS, ensure_game_closed, game_format, profile_saves, read_summary, account_directory, inspect_save, player_name, transfer,
                              temporary_root, validate_destination, validate_profile_name, validate_player_name)
from anno_settings import documents_folder
from anno_save_ui import WindowState, apply_theme
from anno_save_language import choose_language, error_text, text

GAME_LABELS = {
    'anno117': 'Anno 117: Pax Romana',
    'anno1800': 'Anno 1800',
}


def guide_path():
    """Locate the offline manual beside the EXE or in the standalone game's docs."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent / 'save-manager-guide.html'
    return Path(__file__).resolve().parents[1] / 'docs/save-manager-guide.html'


def read_preferences(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def is_account_root(path, game='anno117'):
    return game in GAME_FORMATS and path.is_dir() and path.parent.name.casefold() == 'accounts' and (path / game_format(game)['marker']).is_file()


def initial_save_root(preferences_path, game='anno117'):
    """Prefer the remembered account, then discover accounts under redirected Documents."""
    documents = documents_folder()
    if game not in GAME_FORMATS:
        return documents
    data = read_preferences(preferences_path)
    roots_by_game = data.get('account_roots', {})
    remembered_value = roots_by_game.get(game) if isinstance(roots_by_game, dict) else None
    if remembered_value is None and game == 'anno117':
        remembered_value = data.get('account_root')
    if isinstance(remembered_value, str) and remembered_value:
        try:
            remembered = Path(remembered_value).resolve()
            if is_account_root(remembered, game):
                return remembered
        except (OSError, ValueError):
            pass
    roots = [documents / name / 'accounts' for name in game_format(game)['documents']]
    accounts = set()
    for root in roots:
        try:
            accounts.update(path.resolve() for path in root.iterdir() if is_account_root(path, game))
        except OSError:
            continue
    if len(accounts) == 1:
        return next(iter(accounts))
    return next((root for root in roots if root.is_dir()), documents)


def portable_smoke(sample, game='anno117'):
    """Exercise the frozen core on isolated copies, without touching live accounts."""
    original = Path(sample).read_bytes()
    with tempfile.TemporaryDirectory(prefix='anno-portable-smoke-', dir=temporary_root()) as directory:
        root = Path(directory)
        account = root / 'accounts/smoke'
        account.mkdir(parents=True)
        (account / game_format(game)['marker']).write_bytes(b'smoke marker')
        profile = account / 'Old'
        profile.mkdir()
        source = profile / ('Save' + game_format(game)['extension'])
        source.write_bytes(original)
        transfer([source], account / 'New', root / 'backups', move=True,
                 rename_folder=True, player='Portable Player', game=game)
        moved = account / 'New' / ('Save' + game_format(game)['extension'])
        if source.exists() or player_name(moved.read_bytes(), game) != 'Portable Player':
            raise RuntimeError('Portable profile rename failed.')
        transfer([moved], moved.parent, root / 'backups', edit_in_place=True,
                 player='Portable Final', game=game)
        if player_name(moved.read_bytes(), game) != 'Portable Final':
            raise RuntimeError('Portable player edit failed.')
        try:
            transfer([moved], moved.parent / 'Nested', root / 'backups', game=game)
        except ValueError:
            pass
        else:
            raise RuntimeError('Nested output was accepted.')
    if Path(sample).read_bytes() != original:
        raise RuntimeError('Portable smoke input changed.')


class SaveManager(tk.Tk):
    def __init__(self, preferences_path=None, initial_game=None):
        super().__init__()
        self.title('Anno 117 – Spielstände verwalten')
        self.geometry('1080x820')
        self.minsize(980, 760)
        apply_theme(self)
        icon = Path(__file__).parent / 'assets/annoorganizer.ico'
        if os.name == 'nt' and icon.is_file():
            self.iconbitmap(default=str(icon))
        self.sources = []
        self.ambiguous_rows = set()
        self.folder = None
        self.account = None
        local = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'AnnoOrganizer'
        self.preferences_path = Path(preferences_path) if preferences_path is not None else local / 'save-manager.json'
        self.preferences = read_preferences(self.preferences_path)
        self.language = choose_language(self.preferences.get('language'))
        self.text_controls = []
        self.variable_messages = {}
        saved_game = self.preferences.get('selected_game')
        owner = Path(__file__).resolve().parents[1].name
        default_game = owner if owner in GAME_FORMATS else 'anno117'
        self.game = initial_game if initial_game in GAME_LABELS else (saved_game if isinstance(saved_game, str) and saved_game in GAME_LABELS else default_game)
        self.preferences['selected_game'] = self.game
        self.game_choice = tk.StringVar(value=GAME_LABELS[self.game])
        self.save_root = initial_save_root(self.preferences_path, self.game)
        self.events = queue.Queue()
        self.busy = False
        self.destination = tk.StringVar()
        self.target_name = tk.StringVar()
        self.account_label = tk.StringVar()
        self.change_player = tk.BooleanVar(value=False)
        self.new_player = tk.StringVar()
        self.backup = tk.StringVar(value=str(Path(os.environ.get('LOCALAPPDATA', Path.home()))
                                           / 'AnnoOrganizer' / 'save-backups'))
        self.status = tk.StringVar()
        self.set_message(self.status, 'ready')
        body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        header = ttk.Frame(body)
        header.pack(fill='x')
        self.label(header, 'title', style='Title.TLabel').pack(side='left')
        self.guide_button = ttk.Button(header, text=self.t('guide'), command=self.open_guide)
        self.guide_button.pack(side='left', padx=16)
        self.text_controls.append((self.guide_button, 'guide'))
        chooser = ttk.Frame(header)
        chooser.pack(side='right')
        self.language_buttons = {}
        for language in ('en', 'de'):
            button = ttk.Button(chooser, text=language.upper(), width=4,
                                command=lambda value=language: self.change_language(value))
            button.pack(side='right', padx=(6, 0))
            self.language_buttons[language] = button
        self.label(chooser, 'game').pack(side='left', padx=(12, 6))
        self.game_combo = ttk.Combobox(chooser, textvariable=self.game_choice,
                                       values=tuple(GAME_LABELS.values()), state='readonly', width=27)
        self.game_combo.pack(side='left')
        self.game_combo.bind('<<ComboboxSelected>>', self.on_game_changed)
        self.label(body, 'warning',
                  wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=(6, 12))
        buttons = ttk.Frame(body)
        buttons.pack(fill='x')
        self.controls = []
        self.button(buttons, 'select_files', self.select_files).pack(side='left')
        self.button(buttons, 'select_folder', self.select_folder).pack(side='left', padx=8)
        self.button(buttons, 'select_names', self.select_name_folder).pack(side='right')
        self.selection = tk.StringVar()
        self.set_message(self.selection, 'no_source')
        self.selection_label = ttk.Label(body, textvariable=self.selection, wraplength=920)
        self.selection_label.pack(anchor='w', pady=8)
        table = ttk.Frame(body)
        table.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(table, columns=('player', 'profile', 'save'), height=7)
        self.tree.heading('#0', text=self.t('file'))
        for key, label in [('player', 'Prätor'), ('profile', 'Speicherprofil'), ('save', 'Gespeicherter Name')]:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=170)
        self.tree.column('#0', width=240)
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        ttk.Label(body, textvariable=self.account_label, wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=(10, 2))
        for label, variable, callback in [('target_name', self.target_name, self.choose_destination),
                                           ('backup_folder', self.backup, self.choose_backup)]:
            row = ttk.Frame(body)
            row.pack(fill='x', pady=(10, 0))
            self.label(row, label, width=23).pack(side='left')
            entry = ttk.Entry(row, textvariable=variable)
            if variable is self.target_name:
                self.target_entry = entry
            entry.pack(side='left', fill='x', expand=True)
            self.controls.append(entry)
            self.button(row, '…', callback).pack(side='left', padx=(6, 0))
        ttk.Label(body, textvariable=self.destination, wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=4)
        self.target_name.trace_add('write', self.update_destination)
        row = ttk.Frame(body)
        row.pack(fill='x', pady=8)
        self.player_toggle_text = tk.StringVar()
        toggle = ttk.Checkbutton(row, textvariable=self.player_toggle_text, variable=self.change_player,
                                 command=self.update_player_state)
        toggle.pack(side='left')
        self.controls.append(toggle)
        self.player_entry = ttk.Entry(row, textvariable=self.new_player)
        self.player_entry.pack(side='left', fill='x', expand=True, padx=(12, 0))
        self.controls.append(self.player_entry)
        self.update_player_state()
        self.name_hint = tk.StringVar()
        ttk.Label(body, textvariable=self.name_hint, wraplength=920, style='Muted.TLabel').pack(anchor='w')
        self.label(body, 'structure_hint',
                  wraplength=920).pack(anchor='w', pady=8)
        actions = ttk.Frame(body)
        actions.pack(fill='x', pady=8)
        self.button(actions, 'copy', lambda: self.start(False)).pack(side='left')
        self.button(actions, 'move', lambda: self.start(True), style='Accent.TButton').pack(side='left', padx=8)
        self.button(actions, 'rename', self.rename_folder).pack(side='left')
        self.player_button = self.button(actions, 'names_action', lambda: self.start(False, edit_in_place=True))
        self.player_button.pack(side='right')
        ttk.Label(body, textvariable=self.status, wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=8)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.window_state = WindowState(self, self)
        self.window_state.watch(self, 'main')
        self.refresh_controls()
        self.update_game_view()
        self.poll_after = self.after(150, self.poll)

    def button(self, parent, text, command, **options):
        button = ttk.Button(parent, text=self.t(text) if text != '…' else text, command=command, **options)
        if text != '…':
            self.text_controls.append((button, text))
        self.controls.append(button)
        return button

    def t(self, key, **values):
        return text(self.language, key, **values)

    def open_guide(self):
        page = guide_path()
        url = page.resolve().as_uri() if page.is_file() else 'https://morima79.github.io/AnnoOrganizer/save-manager-guide/'
        url += '?lang=' + self.language
        try:
            if not webbrowser.open(url):
                raise OSError(self.t('guide_open_failed', url=url))
        except Exception as exc:
            messagebox.showerror(self.t('guide_error'), str(exc), parent=self)

    def label(self, parent, key, **options):
        label = ttk.Label(parent, text=self.t(key), **options)
        self.text_controls.append((label, key))
        return label

    def set_message(self, variable, key, **values):
        self.variable_messages[str(variable)] = (variable, key, values)
        self.render_message(variable, key, values)

    def render_message(self, variable, key, values):
        if key == 'failed_status':
            values = dict(values, result=error_text(self.language, values['result']))
        if key == 'all_selected':
            values = dict(values, action=self.t('only_praetor' if self.game == 'anno117' else 'only_player'))
        variable.set(self.t(key, **values))

    def change_language(self, language):
        if language not in ('de', 'en') or self.busy:
            return
        self.language = language
        self.preferences['language'] = language
        self.refresh_text()
        self.save_preferences()

    def refresh_text(self):
        for control, key in self.text_controls:
            control.configure(text=self.t(key))
        for variable, key, values in self.variable_messages.values():
            self.render_message(variable, key, values)
        for language, button in self.language_buttons.items():
            button.configure(style='LanguageSelected.TButton' if language == self.language else 'TButton')
        self.title(GAME_LABELS[self.game] + ' – ' + self.t('title'))
        for column, key in (('#0', 'file'), ('player', 'praetor' if self.game == 'anno117' else 'player'),
                            ('profile', 'profile'), ('save', 'saved_name')):
            self.tree.heading(column, text=self.t(key))
        self.player_toggle_text.set(self.t('change_praetor' if self.game == 'anno117' else 'change_player'))
        self.player_button.configure(text=self.t('only_praetor' if self.game == 'anno117' else 'only_player'))
        self.name_hint.set(self.t('name_hint'))
        self.account_label.set(self.t('account' if self.account else 'start_folder', path=self.account or self.save_root))
        self.update_destination()
        for row in self.tree.get_children():
            values = list(self.tree.item(row, 'values'))
            if row in self.ambiguous_rows:
                values[0] = self.t('ambiguous')
                self.tree.item(row, values=values)

    def update_destination(self, *_):
        self.destination.set(self.t('destination', path=self.account / self.target_name.get()) if self.account else '')

    def update_player_state(self):
        self.player_entry.configure(state='normal' if self.change_player.get() and not self.busy
                                     and self.game in GAME_FORMATS else 'disabled')

    def refresh_controls(self):
        state = 'normal' if self.game in GAME_FORMATS and not self.busy else 'disabled'
        for control in self.controls:
            control.configure(state=state)
        self.game_combo.configure(state='disabled' if self.busy else 'readonly')
        for button in self.language_buttons.values():
            button.configure(state='disabled' if self.busy else 'normal')
        self.update_player_state()

    def update_game_view(self):
        self.set_message(self.status, 'ready')
        self.refresh_text()

    def on_game_changed(self, _event=None):
        selected = next((key for key, label in GAME_LABELS.items() if label == self.game_choice.get()), self.game)
        if self.busy:
            self.game_choice.set(GAME_LABELS[self.game])
            return
        if selected == self.game:
            return
        self.game = selected
        self.save_root = initial_save_root(self.preferences_path, selected)
        self.preferences['selected_game'] = selected
        self.clear_selection()
        self.refresh_controls()
        self.update_game_view()
        self.save_preferences()

    def dialog_root(self):
        if not self.save_root.is_dir():
            self.save_root = initial_save_root(self.preferences_path, self.game)
        return str(self.save_root)

    def remember_account(self, account):
        self.save_root = account
        roots = self.preferences.setdefault('account_roots', {})
        if not isinstance(roots, dict):
            roots = self.preferences['account_roots'] = {}
        roots[self.game] = str(account)
        if self.game == 'anno117':
            self.preferences['account_root'] = str(account)
        self.save_preferences()

    def save_preferences(self):
        if hasattr(self, 'window_state'):
            self.window_state.remember_all()
        self.preferences['version'] = 1
        try:
            self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
            self.preferences_path.write_text(json.dumps(self.preferences, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        except OSError:
            # Retain the root for this session even if preferences cannot be saved.
            pass

    def clear_selection(self):
        self.sources, self.folder, self.account = [], None, None
        self.ambiguous_rows.clear()
        self.tree.delete(*self.tree.get_children())
        self.account_label.set(self.t('start_folder', path=self.save_root))
        self.set_message(self.selection, 'no_source')
        self.target_name.set('')
        self.change_player.set(False)
        self.new_player.set('')
        self.update_player_state()

    def select_files(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        selected = filedialog.askopenfilenames(title=self.t('files_title', game=game_format(self.game)['label']), initialdir=self.dialog_root(),
                                             filetypes=[(game_format(self.game)['label'], '*' + game_format(self.game)['extension'])])
        if selected:
            self.load([Path(p) for p in selected])

    def select_folder(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        folder = filedialog.askdirectory(title=self.t('folder_title'),
                                         initialdir=self.dialog_root())
        if folder:
            path = Path(folder)
            self.load(sorted(p for p in path.iterdir() if p.suffix.casefold() == game_format(self.game)['extension']), path)

    def select_name_folder(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        selected = filedialog.askdirectory(title=self.t('names_title'),
                                            initialdir=self.dialog_root())
        if not selected:
            return
        try:
            sources = profile_saves(selected, self.game)
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.t('folder_error'), error_text(self.language, str(exc)), parent=self)
            return
        self.load(sources)
        if self.sources:
            self.change_player.set(True)
            self.update_player_state()
            self.player_entry.focus_set()
            self.player_entry.selection_range(0, tk.END)
            self.set_message(self.status, 'all_selected', count=len(self.sources))

    def load(self, sources, folder=None):
        if self.game not in GAME_FORMATS or self.busy:
            return
        self.clear_selection()
        try:
            if not sources:
                raise ValueError('Keine ' + game_format(self.game)['extension'] + '-Saves gefunden.')
            sources = [Path(p).resolve(strict=True) for p in sources]
            account = account_directory(sources[0].parent, self.game)
            validate_destination(sources, account / (sources[0].parent.name + ' - Neu'), game=self.game)
            if folder is not None and set(sources[0].parent.iterdir()) != set(sources):
                raise ValueError('Der Profilordner enthält weitere Dateien oder Unterordner. '
                                 'Unterordner werden nicht übernommen; bitte einzelne Saves direkt im Profil wählen.')
            labels = set()
            for i, source in enumerate(sources):
                names, label = read_summary(source, self.game)
                labels.add(label)
                if label == 'Nicht eindeutig zuordenbar':
                    self.ambiguous_rows.add(str(i))
                self.tree.insert('', 'end', iid=str(i), text=source.name,
                                 values=(self.t('ambiguous') if str(i) in self.ambiguous_rows else label,
                                         names['gamesetup.a7s'], names['meta.a7s']))
            self.sources, self.folder, self.account = sources, folder, account
            self.remember_account(account)
            self.account_label.set(self.t('account', path=account))
            self.set_message(self.selection, 'selection', count=len(sources), path=sources[0].parent)
            self.target_name.set(sources[0].parent.name + self.t('new_suffix'))
            self.target_entry.focus_set()
            self.target_entry.selection_range(0, tk.END)
            if len(labels) == 1 and 'Nicht eindeutig zuordenbar' not in labels:
                self.new_player.set(next(iter(labels)))
            self.set_message(self.status, 'loaded')
        except Exception as exc:
            self.set_message(self.selection, 'load_failed')
            self.tree.delete(*self.tree.get_children())
            messagebox.showerror(self.t('unsupported'), error_text(self.language, str(exc)), parent=self)

    def choose_destination(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        if not self.account:
            messagebox.showinfo(self.t('choose_source'), self.t('source_first'), parent=self)
            return
        selected = filedialog.askdirectory(title=self.t('target_title'), initialdir=self.dialog_root())
        if selected:
            try:
                destination = Path(selected).resolve(strict=True)
                validate_destination(self.sources, destination, game=self.game)
                self.target_name.set(destination.name)
            except (ValueError, OSError) as exc:
                messagebox.showerror(self.t('invalid_target'), error_text(self.language, str(exc)), parent=self)

    def choose_backup(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        selected = filedialog.askdirectory(title=self.t('backup_title'),
                                          initialdir=self.dialog_root())
        if selected:
            self.backup.set(selected)

    def rename_folder(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        if not self.folder:
            messagebox.showinfo(self.t('choose_profile'), self.t('profile_first'), parent=self)
            return
        self.start(True, rename=True)

    def start(self, move, rename=False, edit_in_place=False):
        if self.busy or not self.sources or self.game not in GAME_FORMATS:
            return
        try:
            ensure_game_closed(self.game)
            player = validate_player_name(self.new_player.get()) if self.change_player.get() else None
            if edit_in_place and player is None:
                raise ValueError('«Namen ändern» aktivieren und einen Namen eingeben.')
            destination = self.sources[0].parent if edit_in_place else self.account / validate_profile_name(self.target_name.get())
            validate_destination(self.sources, destination, edit_in_place=edit_in_place, game=self.game)
            if not self.backup.get().strip():
                raise ValueError('Bitte einen Sicherungsordner angeben.')
            backup = Path(self.backup.get()).resolve()
            if backup == self.account or self.account in backup.parents:
                raise ValueError('Sicherung ausserhalb des Spielkontos wählen.')
            if rename and destination.exists():
                raise ValueError('Für die Ordnerumbenennung einen neuen Profilnamen angeben.')
            if not edit_in_place and any((destination / p.name).exists() for p in self.sources):
                raise ValueError('Eine Zieldatei existiert bereits. Bitte ein anderes Profil wählen.')
        except (ValueError, OSError) as exc:
            messagebox.showerror(self.t('action_error'), error_text(self.language, str(exc)), parent=self)
            return
        action = self.t('names_action' if edit_in_place else ('rename_action' if rename else ('move' if move else 'copy')))
        details = self.t('confirmation', count=len(self.sources), source=self.sources[0].parent, destination=destination,
                         person=self.t('praetor' if self.game == 'anno117' else 'player'),
                         player=player if player is not None else self.t('unchanged'),
                         profile=destination.name, backup=backup)
        if not messagebox.askokcancel(action, details, parent=self):
            return
        self.busy = True
        self.refresh_controls()
        self.set_message(self.status, 'working')
        sources = self.sources.copy()
        def work():
            try:
                result = transfer(sources, destination, backup, move=move, rename_folder=rename,
                                  player=player, edit_in_place=edit_in_place, game=self.game)
                self.events.put((True, str(result)))
            except Exception as exc:
                self.events.put((False, str(exc)))
        threading.Thread(target=work, daemon=False).start()

    def poll(self):
        try:
            success, result = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.refresh_controls()
            self.set_message(self.status, 'done_status' if success else 'failed_status', result=result)
            if success:
                self.clear_selection()
                self.set_message(self.selection, 'completed_selection')
                messagebox.showinfo(self.t('completed'), self.t('completed_message', result=result), parent=self)
            else:
                messagebox.showerror(self.t('cancelled'), error_text(self.language, result), parent=self)
        self.poll_after = self.after(150, self.poll)

    def destroy(self):
        self.save_preferences()
        pending = getattr(self, 'poll_after', None)
        if pending is not None:
            self.after_cancel(pending)
            self.poll_after = None
        super().destroy()

    def close(self):
        if self.busy:
            messagebox.showinfo(self.t('busy'), self.t('please_wait'), parent=self)
        else:
            self.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--sample-save', type=Path)
    parser.add_argument('--game', choices=tuple(GAME_FORMATS))
    options = parser.parse_args()
    if options.self_test:
        with tempfile.TemporaryDirectory(prefix='anno117-gui-smoke-', dir=temporary_root()) as directory:
            app = SaveManager(preferences_path=Path(directory) / 'save-manager.json', initial_game=options.game)
            app.withdraw()
            app.update()
            app.destroy()
        if options.sample_save is not None:
            portable_smoke(options.sample_save, options.game or 'anno117')
    else:
        app = SaveManager(initial_game=options.game)
        app.mainloop()
