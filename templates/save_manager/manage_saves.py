"""Standalone save manager for Anno 117 and Anno 1800."""
import argparse
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from anno_save_editor import (GAME_FORMATS, ensure_game_closed, game_format, profile_saves, read_summary, account_directory, inspect_save, player_name, transfer,
                              temporary_root, validate_destination, validate_profile_name, validate_player_name)
from anno_settings import documents_folder
from anno_save_ui import WindowState, apply_theme

GAME_LABELS = {
    'anno117': 'Anno 117: Pax Romana',
    'anno1800': 'Anno 1800',
    'anno1404': 'Anno 1404',
}


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
        self.folder = None
        self.account = None
        local = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'AnnoOrganizer'
        self.preferences_path = Path(preferences_path) if preferences_path is not None else local / 'save-manager.json'
        self.preferences = read_preferences(self.preferences_path)
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
        self.account_label = tk.StringVar(value='Startordner: ' + str(self.save_root))
        self.change_player = tk.BooleanVar(value=False)
        self.new_player = tk.StringVar()
        self.backup = tk.StringVar(value=str(Path(os.environ.get('LOCALAPPDATA', Path.home()))
                                           / 'AnnoOrganizer' / 'save-backups'))
        self.status = tk.StringVar(value='Saves oder einen Profilordner auswählen.')
        body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        header = ttk.Frame(body)
        header.pack(fill='x')
        ttk.Label(header, text='Spielstände verwalten', style='Title.TLabel').pack(side='left')
        chooser = ttk.Frame(header)
        chooser.pack(side='right')
        ttk.Label(chooser, text='Spiel:').pack(side='left', padx=(12, 6))
        self.game_combo = ttk.Combobox(chooser, textvariable=self.game_choice,
                                       values=tuple(GAME_LABELS.values()), state='readonly', width=27)
        self.game_combo.pack(side='left')
        self.game_combo.bind('<<ComboboxSelected>>', self.on_game_changed)
        ttk.Label(body, text='Spiel vor Änderungen schliessen. Cloud-Synchronisierung kann alte Profile wiederherstellen.',
                  wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=(6, 12))
        buttons = ttk.Frame(body)
        buttons.pack(fill='x')
        self.controls = []
        self.button(buttons, 'Einzelne Saves auswählen …', self.select_files).pack(side='left')
        self.button(buttons, 'Ganzer Profilordner …', self.select_folder).pack(side='left', padx=8)
        self.button(buttons, 'Alle Namen im Ordner …', self.select_name_folder).pack(side='right')
        self.selection_label = ttk.Label(body, text='Keine Quelle ausgewählt', wraplength=830)
        self.selection_label.pack(anchor='w', pady=8)
        table = ttk.Frame(body)
        table.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(table, columns=('player', 'profile', 'save'), height=7)
        self.tree.heading('#0', text='Datei')
        for key, label in [('player', 'Prätor'), ('profile', 'Speicherprofil'), ('save', 'Gespeicherter Name')]:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=170)
        self.tree.column('#0', width=240)
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        ttk.Label(body, textvariable=self.account_label, wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=(10, 2))
        for label, variable, callback in [('Ziel-Profilname', self.target_name, self.choose_destination),
                                           ('Sicherungsordner', self.backup, self.choose_backup)]:
            row = ttk.Frame(body)
            row.pack(fill='x', pady=(10, 0))
            ttk.Label(row, text=label, width=19).pack(side='left')
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
        ttk.Label(body, text='Zielprofile liegen direkt im selben Konto. Unterordner in Profilen sind gesperrt. '
                  'Das Speicherprofil wird an den Zielordner angeglichen; Originale werden vorab als ZIP gesichert.',
                  wraplength=920).pack(anchor='w', pady=8)
        actions = ttk.Frame(body)
        actions.pack(fill='x', pady=8)
        self.button(actions, 'Kopieren', lambda: self.start(False)).pack(side='left')
        self.button(actions, 'Verschieben', lambda: self.start(True), style='Accent.TButton').pack(side='left', padx=8)
        self.button(actions, 'Profilordner umbenennen …', self.rename_folder).pack(side='left')
        self.player_button = self.button(actions, 'Nur Namen ändern', lambda: self.start(False, edit_in_place=True))
        self.player_button.pack(side='right')
        ttk.Label(body, textvariable=self.status, wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=8)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.window_state = WindowState(self, self)
        self.window_state.watch(self, 'main')
        self.refresh_controls()
        self.update_game_view()
        self.poll_after = self.after(150, self.poll)

    def button(self, parent, text, command, **options):
        button = ttk.Button(parent, text=text, command=command, **options)
        self.controls.append(button)
        return button

    def update_destination(self, *_):
        self.destination.set('Ziel: ' + str(self.account / self.target_name.get()) if self.account else '')

    def update_player_state(self):
        self.player_entry.configure(state='normal' if self.change_player.get() and not self.busy
                                     and self.game in GAME_FORMATS else 'disabled')

    def refresh_controls(self):
        state = 'normal' if self.game in GAME_FORMATS and not self.busy else 'disabled'
        for control in self.controls:
            control.configure(state=state)
        self.game_combo.configure(state='disabled' if self.busy else 'readonly')
        self.update_player_state()

    def update_game_view(self):
        self.title(GAME_LABELS[self.game] + ' – Spielstände verwalten')
        person = 'Prätor' if self.game == 'anno117' else 'Spielername'
        self.tree.heading('player', text=person)
        self.player_toggle_text.set('Prätornamen ändern' if self.game == 'anno117' else 'Spielernamen ändern')
        self.player_button.configure(text='Nur Prätor ändern' if self.game == 'anno117' else 'Nur Spielername ändern')
        self.name_hint.set('Optional beim Übertragen oder am bisherigen Ort ändern. Gilt für alle ausgewählten Saves und daraus künftig erzeugte Spielstände.')
        if self.game in GAME_FORMATS:
            self.account_label.set('Startordner: ' + str(self.save_root))
            self.status.set('Saves oder einen Profilordner auswählen.')
        else:
            self.account_label.set('Spielauswahl vorbereitet: ' + GAME_LABELS[self.game])
            self.status.set('Für ' + GAME_LABELS[self.game] + ' sind Lesen und Bearbeiten von Spielständen noch nicht freigeschaltet.')

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
        self.tree.delete(*self.tree.get_children())
        self.account_label.set('Startordner: ' + str(self.save_root))
        self.target_name.set('')
        self.change_player.set(False)
        self.new_player.set('')
        self.update_player_state()

    def select_files(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        selected = filedialog.askopenfilenames(title=game_format(self.game)['label'] + '-Saves auswählen', initialdir=self.dialog_root(),
                                             filetypes=[(game_format(self.game)['label'], '*' + game_format(self.game)['extension'])])
        if selected:
            self.load([Path(p) for p in selected])

    def select_folder(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        folder = filedialog.askdirectory(title='Einen Profilordner auswählen (nicht den Kontoordner)',
                                         initialdir=self.dialog_root())
        if folder:
            path = Path(folder)
            self.load(sorted(p for p in path.iterdir() if p.suffix.casefold() == game_format(self.game)['extension']), path)

    def select_name_folder(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        selected = filedialog.askdirectory(title='Profilordner für die Namensänderung aller Saves wählen',
                                            initialdir=self.dialog_root())
        if not selected:
            return
        try:
            sources = profile_saves(selected, self.game)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Profilordner nicht verwendbar', str(exc), parent=self)
            return
        self.load(sources)
        if self.sources:
            self.change_player.set(True)
            self.update_player_state()
            self.player_entry.focus_set()
            self.player_entry.selection_range(0, tk.END)
            action = self.player_button.cget('text')
            self.status.set(f'Alle {len(self.sources)} Saves des Ordners ausgewählt. Neuen Namen eingeben und «{action}» ausführen.')

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
                self.tree.insert('', 'end', iid=str(i), text=source.name,
                                 values=(label, names['gamesetup.a7s'], names['meta.a7s']))
            self.sources, self.folder, self.account = sources, folder, account
            self.remember_account(account)
            self.account_label.set('Spielkonto: ' + str(account))
            self.selection_label.config(text=f'{len(sources)} Save(s) · {sources[0].parent}')
            self.target_name.set(sources[0].parent.name + ' - Neu')
            self.target_entry.focus_set()
            self.target_entry.selection_range(0, tk.END)
            if len(labels) == 1 and 'Nicht eindeutig zuordenbar' not in labels:
                self.new_player.set(next(iter(labels)))
            self.status.set('Felder gelesen. Zielordner prüfen und Aktion auswählen.')
        except Exception as exc:
            self.selection_label.config(text='Auswahl konnte nicht geladen werden')
            self.tree.delete(*self.tree.get_children())
            messagebox.showerror('Spielstand nicht unterstützt', str(exc), parent=self)

    def choose_destination(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        if not self.account:
            messagebox.showinfo('Quelle wählen', 'Zuerst Saves oder einen Profilordner auswählen.', parent=self)
            return
        selected = filedialog.askdirectory(title='Direkten Ziel-Profilordner wählen', initialdir=self.dialog_root())
        if selected:
            try:
                destination = Path(selected).resolve(strict=True)
                validate_destination(self.sources, destination, game=self.game)
                self.target_name.set(destination.name)
            except (ValueError, OSError) as exc:
                messagebox.showerror('Ungültiges Ziel', str(exc), parent=self)

    def choose_backup(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        selected = filedialog.askdirectory(title='Dauerhaften Sicherungsordner ausserhalb des Spielkontos wählen',
                                          initialdir=self.dialog_root())
        if selected:
            self.backup.set(selected)

    def rename_folder(self):
        if self.game not in GAME_FORMATS or self.busy:
            return
        if not self.folder:
            messagebox.showinfo('Profilordner wählen', 'Zuerst «Ganzer Profilordner» auswählen.', parent=self)
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
            messagebox.showerror('Aktion nicht möglich', str(exc), parent=self)
            return
        action = 'Namen ändern' if edit_in_place else ('Profilordner umbenennen' if rename else ('Verschieben' if move else 'Kopieren'))
        details = f'{len(self.sources)} Save(s) aus {self.sources[0].parent}\nZiel: {destination}'
        details += '\n' + ('Prätor' if self.game == 'anno117' else 'Spielername') + ': ' + (player if player is not None else 'unverändert')
        details += '\nSpeicherprofil: ' + destination.name
        details += f'\nSicherung: {backup}\n\nSpiel geschlossen? Aktion jetzt ausführen?'
        if not messagebox.askokcancel(action, details, parent=self):
            return
        self.busy = True
        self.refresh_controls()
        self.status.set('Saves prüfen, sichern und bearbeiten …')
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
            self.status.set(('Fertig. Sicherung: ' if success else 'Abgebrochen: ') + result)
            if success:
                self.clear_selection()
                self.selection_label.config(text='Aktion abgeschlossen · für weitere Aktionen Quelle erneut auswählen')
                messagebox.showinfo('Abgeschlossen', 'Saves geprüft und übertragen.\nSicherung: ' + result, parent=self)
            else:
                messagebox.showerror('Aktion abgebrochen', result, parent=self)
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
            messagebox.showinfo('Bearbeitung läuft', 'Bitte warten, bis die Übertragung abgeschlossen ist.', parent=self)
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
