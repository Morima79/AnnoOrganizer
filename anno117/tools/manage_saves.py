"""Standalone window for Anno 117 profile transfers and optional praetor edits."""
import argparse
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from anno_save_editor import (account_directory, inspect_save, praetor_name, transfer,
                              temporary_root, validate_destination, validate_profile_name, validate_praetor)
from anno_settings import documents_folder
from anno_save_ui import WindowState, apply_theme


def read_preferences(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def is_account_root(path):
    return path.is_dir() and path.parent.name.casefold() == 'accounts' and (path / 'accountdata.a8s').is_file()


def initial_save_root(preferences_path):
    """Prefer the remembered account, then discover accounts under redirected Documents."""
    try:
        data = json.loads(preferences_path.read_text(encoding='utf-8'))
        remembered = Path(data['account_root']).resolve()
        if is_account_root(remembered):
            return remembered
    except (OSError, ValueError, TypeError, KeyError):
        pass
    documents = documents_folder()
    roots = [documents / name / 'accounts' for name in
             ('Anno 117 - Pax Romana', 'Anno 117 Pax Romana', 'Anno 117')]
    accounts = set()
    for root in roots:
        try:
            accounts.update(path.resolve() for path in root.iterdir() if is_account_root(path))
        except OSError:
            continue
    if len(accounts) == 1:
        return next(iter(accounts))
    return next((root for root in roots if root.is_dir()), documents)


def portable_smoke(sample):
    """Exercise the frozen core on isolated copies, without touching live accounts."""
    original = Path(sample).read_bytes()
    with tempfile.TemporaryDirectory(prefix='anno117-portable-smoke-', dir=temporary_root()) as directory:
        root = Path(directory)
        account = root / 'accounts/smoke'
        account.mkdir(parents=True)
        (account / 'accountdata.a8s').write_bytes(b'smoke marker')
        profile = account / 'Old'
        profile.mkdir()
        source = profile / 'Save.a8s'
        source.write_bytes(original)
        transfer([source], account / 'New', root / 'backups', move=True,
                 rename_folder=True, praetor='Portable Praetor')
        moved = account / 'New/Save.a8s'
        if source.exists() or praetor_name(moved.read_bytes()) != 'Portable Praetor':
            raise RuntimeError('Portable profile rename failed.')
        transfer([moved], moved.parent, root / 'backups', edit_in_place=True,
                 praetor='Portable Final')
        if praetor_name(moved.read_bytes()) != 'Portable Final':
            raise RuntimeError('Portable praetor edit failed.')
        try:
            transfer([moved], moved.parent / 'Nested', root / 'backups')
        except ValueError:
            pass
        else:
            raise RuntimeError('Nested output was accepted.')
    if Path(sample).read_bytes() != original:
        raise RuntimeError('Portable smoke input changed.')


class SaveManager(tk.Tk):
    def __init__(self, preferences_path=None):
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
        self.save_root = initial_save_root(self.preferences_path)
        self.events = queue.Queue()
        self.busy = False
        self.destination = tk.StringVar()
        self.target_name = tk.StringVar()
        self.account_label = tk.StringVar(value='Startordner: ' + str(self.save_root))
        self.change_praetor = tk.BooleanVar(value=False)
        self.new_praetor = tk.StringVar()
        self.backup = tk.StringVar(value=str(Path(os.environ.get('LOCALAPPDATA', Path.home()))
                                           / 'AnnoOrganizer' / 'save-backups'))
        self.status = tk.StringVar(value='Saves oder einen Profilordner auswählen.')
        body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Anno 117 · Spielstände verwalten', style='Title.TLabel').pack(anchor='w')
        ttk.Label(body, text='Spiel vor Änderungen schliessen. Cloud-Synchronisierung kann alte Profile wiederherstellen.',
                  wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=(6, 12))
        buttons = ttk.Frame(body)
        buttons.pack(fill='x')
        self.controls = []
        self.button(buttons, 'Einzelne Saves auswählen …', self.select_files).pack(side='left')
        self.button(buttons, 'Ganzer Profilordner …', self.select_folder).pack(side='left', padx=8)
        self.selection_label = ttk.Label(body, text='Keine Quelle ausgewählt', wraplength=830)
        self.selection_label.pack(anchor='w', pady=8)
        table = ttk.Frame(body)
        table.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(table, columns=('praetor', 'profile', 'save'), height=7)
        self.tree.heading('#0', text='Datei')
        for key, label in [('praetor', 'Prätor'), ('profile', 'Speicherprofil'), ('save', 'Gespeicherter Name')]:
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
        toggle = ttk.Checkbutton(row, text='Prätornamen ändern', variable=self.change_praetor,
                                 command=self.update_praetor_state)
        toggle.pack(side='left')
        self.controls.append(toggle)
        self.praetor_entry = ttk.Entry(row, textvariable=self.new_praetor)
        self.praetor_entry.pack(side='left', fill='x', expand=True, padx=(12, 0))
        self.controls.append(self.praetor_entry)
        self.update_praetor_state()
        ttk.Label(body, text='Optional beim Übertragen oder mit «Nur Prätor ändern» am bisherigen Ort. '
                  'Gilt für die ausgewählten Saves und daraus künftig erzeugte Spielstände.',
                  wraplength=920, style='Muted.TLabel').pack(anchor='w')
        ttk.Label(body, text='Zielprofile liegen direkt im selben Konto. Unterordner in Profilen sind gesperrt. '
                  'Das Speicherprofil wird an den Zielordner angeglichen; Originale werden vorab als ZIP gesichert.',
                  wraplength=920).pack(anchor='w', pady=8)
        actions = ttk.Frame(body)
        actions.pack(fill='x', pady=8)
        self.button(actions, 'Kopieren', lambda: self.start(False)).pack(side='left')
        self.button(actions, 'Verschieben', lambda: self.start(True), style='Accent.TButton').pack(side='left', padx=8)
        self.button(actions, 'Profilordner umbenennen …', self.rename_folder).pack(side='left')
        self.button(actions, 'Nur Prätor ändern', lambda: self.start(False, edit_in_place=True)).pack(side='right')
        ttk.Label(body, textvariable=self.status, wraplength=920, style='Muted.TLabel').pack(anchor='w', pady=8)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.window_state = WindowState(self, self)
        self.window_state.watch(self, 'main')
        self.poll_after = self.after(150, self.poll)

    def button(self, parent, text, command, **options):
        button = ttk.Button(parent, text=text, command=command, **options)
        self.controls.append(button)
        return button

    def update_destination(self, *_):
        self.destination.set('Ziel: ' + str(self.account / self.target_name.get()) if self.account else '')

    def update_praetor_state(self):
        self.praetor_entry.configure(state='normal' if self.change_praetor.get() and not self.busy else 'disabled')

    def dialog_root(self):
        if not self.save_root.is_dir():
            self.save_root = initial_save_root(self.preferences_path)
        return str(self.save_root)

    def remember_account(self, account):
        self.save_root = account
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
        self.change_praetor.set(False)
        self.new_praetor.set('')
        self.update_praetor_state()

    def select_files(self):
        selected = filedialog.askopenfilenames(title='Anno-117-Saves auswählen', initialdir=self.dialog_root(),
                                             filetypes=[('Anno 117', '*.a8s')])
        if selected:
            self.load([Path(p) for p in selected])

    def select_folder(self):
        folder = filedialog.askdirectory(title='Einen Profilordner auswählen (nicht den Kontoordner)',
                                         initialdir=self.dialog_root())
        if folder:
            path = Path(folder)
            self.load(sorted(p for p in path.iterdir() if p.suffix.casefold() == '.a8s'), path)

    def load(self, sources, folder=None):
        self.clear_selection()
        try:
            if not sources:
                raise ValueError('Keine .a8s-Saves gefunden.')
            sources = [Path(p).resolve(strict=True) for p in sources]
            account = account_directory(sources[0].parent)
            validate_destination(sources, account / (sources[0].parent.name + ' - Neu'))
            if folder is not None and set(sources[0].parent.iterdir()) != set(sources):
                raise ValueError('Der Profilordner enthält weitere Dateien oder Unterordner. '
                                 'Unterordner werden nicht übernommen; bitte einzelne Saves direkt im Profil wählen.')
            labels = set()
            for i, source in enumerate(sources):
                blob = source.read_bytes()
                names = inspect_save(blob)
                try:
                    label = praetor_name(blob)
                except ValueError:
                    label = 'Nicht eindeutig zuordenbar'
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
                self.new_praetor.set(next(iter(labels)))
            self.status.set('Felder gelesen. Zielordner prüfen und Aktion auswählen.')
        except Exception as exc:
            self.selection_label.config(text='Auswahl konnte nicht geladen werden')
            self.tree.delete(*self.tree.get_children())
            messagebox.showerror('Spielstand nicht unterstützt', str(exc), parent=self)

    def choose_destination(self):
        if not self.account:
            messagebox.showinfo('Quelle wählen', 'Zuerst Saves oder einen Profilordner auswählen.', parent=self)
            return
        selected = filedialog.askdirectory(title='Direkten Ziel-Profilordner wählen', initialdir=self.dialog_root())
        if selected:
            try:
                destination = Path(selected).resolve(strict=True)
                validate_destination(self.sources, destination)
                self.target_name.set(destination.name)
            except (ValueError, OSError) as exc:
                messagebox.showerror('Ungültiges Ziel', str(exc), parent=self)

    def choose_backup(self):
        selected = filedialog.askdirectory(title='Dauerhaften Sicherungsordner ausserhalb des Spielkontos wählen',
                                          initialdir=self.dialog_root())
        if selected:
            self.backup.set(selected)

    def rename_folder(self):
        if not self.folder:
            messagebox.showinfo('Profilordner wählen', 'Zuerst «Ganzer Profilordner» auswählen.', parent=self)
            return
        self.start(True, rename=True)

    def start(self, move, rename=False, edit_in_place=False):
        if self.busy or not self.sources:
            return
        try:
            praetor = validate_praetor(self.new_praetor.get()) if self.change_praetor.get() else None
            if edit_in_place and praetor is None:
                raise ValueError('«Prätornamen ändern» aktivieren und einen Namen eingeben.')
            destination = self.sources[0].parent if edit_in_place else self.account / validate_profile_name(self.target_name.get())
            validate_destination(self.sources, destination, edit_in_place=edit_in_place)
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
        action = 'Prätor ändern' if edit_in_place else ('Profilordner umbenennen' if rename else ('Verschieben' if move else 'Kopieren'))
        details = f'{len(self.sources)} Save(s) aus {self.sources[0].parent}\nZiel: {destination}'
        details += '\nPrätor: ' + (praetor if praetor is not None else 'unverändert')
        details += '\nSpeicherprofil: ' + destination.name
        details += f'\nSicherung: {backup}\n\nSpiel geschlossen? Aktion jetzt ausführen?'
        if not messagebox.askokcancel(action, details, parent=self):
            return
        self.busy = True
        for control in self.controls:
            control.configure(state='disabled')
        self.status.set('Saves prüfen, sichern und bearbeiten …')
        sources = self.sources.copy()
        def work():
            try:
                result = transfer(sources, destination, backup, move=move, rename_folder=rename,
                                  praetor=praetor, edit_in_place=edit_in_place)
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
            for control in self.controls:
                control.configure(state='normal')
            self.update_praetor_state()
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
    options = parser.parse_args()
    if options.self_test:
        with tempfile.TemporaryDirectory(prefix='anno117-gui-smoke-', dir=temporary_root()) as directory:
            app = SaveManager(preferences_path=Path(directory) / 'save-manager.json')
            app.withdraw()
            app.update()
            app.destroy()
        if options.sample_save is not None:
            portable_smoke(options.sample_save)
    else:
        app = SaveManager()
        app.mainloop()
