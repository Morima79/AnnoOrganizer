"""Check profile-only destination UI and the separate in-place praetor action."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_save_editor import account, editor, save

TOOLS = Path(__file__).resolve().parents[1] / 'anno117/tools'
with patch.object(sys, 'path', [str(TOOLS), *sys.path]):
    spec = importlib.util.spec_from_file_location('save_manager_ui_fixture', TOOLS / 'manage_saves.py')
    ui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ui)


class SaveManagerUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=editor.temporary_root())
        self.root = account(Path(self.temp.name))
        self.source = self.root / 'Old/Save.a8s'
        self.source.parent.mkdir()
        self.source.write_bytes(save())
        self.app = ui.SaveManager(preferences_path=Path(self.temp.name) / 'preferences.json')
        self.app.withdraw()
        self.app.backup.set(str(Path(self.temp.name) / 'backups'))

    def tearDown(self):
        self.app.destroy()
        self.temp.cleanup()

    def wait_done(self):
        deadline = time.monotonic() + 5
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(.01)
        self.assertFalse(self.app.busy)

    def test_selection_shows_praetor_and_rejects_nested_target_before_confirmation(self):
        self.app.load([self.source])
        self.assertEqual(self.app.account, self.root)
        self.assertEqual(self.app.new_player.get(), 'Old Praetor')
        self.assertEqual(tuple(self.app.tree.item('0', 'values')), ('Old Praetor', 'Old', 'Manual 8'))
        self.app.target_name.set('Other/Nested')
        with patch.object(ui.messagebox, 'showerror') as error, patch.object(ui.messagebox, 'askokcancel') as confirm:
            self.app.start(True)
        error.assert_called_once()
        self.assertIn('Unterordner', error.call_args.args[1])
        self.assertIn('Ziel-Profilname', error.call_args.args[1])
        confirm.assert_not_called()
        self.assertFalse((self.root / 'Other').exists())

    def test_game_selector_clears_inputs_and_blocks_unimplemented_game_operations(self):
        self.assertEqual(tuple(self.app.game_combo.cget('values')), tuple(ui.GAME_LABELS.values()))
        for game in ('anno1404',):
            with self.subTest(game=game):
                self.app.load([self.source])
                self.app.change_player.set(True)
                self.app.new_player.set('Pending edit')
                self.app.game_choice.set(ui.GAME_LABELS[game])
                self.app.on_game_changed()
                self.assertEqual(self.app.game, game)
                self.assertEqual(self.app.sources, [])
                self.assertEqual(self.app.target_name.get(), '')
                self.assertEqual(self.app.new_player.get(), '')
                self.assertFalse(self.app.change_player.get())
                self.assertIn('noch nicht freigeschaltet', self.app.status.get())
                self.assertEqual(str(self.app.game_combo.cget('state')), 'readonly')
                self.assertTrue(all(str(control.cget('state')) == 'disabled' for control in self.app.controls))
                with patch.object(ui, 'transfer') as transfer, patch.object(ui, 'read_summary') as read, patch.object(ui.filedialog, 'askopenfilenames') as files:
                    self.app.start(True)
                    self.app.load([self.source])
                    self.app.select_files()
                transfer.assert_not_called()
                read.assert_not_called()
                files.assert_not_called()
                self.app.game_choice.set(ui.GAME_LABELS['anno117'])
                self.app.on_game_changed()
                self.assertEqual(self.app.save_root, self.root)
                self.assertEqual(str(self.app.target_entry.cget('state')), 'normal')

    def test_selected_game_is_remembered_and_switching_is_blocked_while_busy(self):
        self.app.game_choice.set(ui.GAME_LABELS['anno1404'])
        self.app.on_game_changed()
        self.app.busy = True
        self.app.refresh_controls()
        self.assertEqual(str(self.app.game_combo.cget('state')), 'disabled')
        self.app.game_choice.set(ui.GAME_LABELS['anno117'])
        self.app.on_game_changed()
        self.assertEqual(self.app.game, 'anno1404')
        self.assertEqual(self.app.game_choice.get(), ui.GAME_LABELS['anno1404'])
        self.app.busy = False
        preferences_path = self.app.preferences_path
        self.app.destroy()
        self.app = ui.SaveManager(preferences_path=preferences_path)
        self.app.withdraw()
        self.assertEqual(self.app.game, 'anno1404')
        self.assertEqual(str(self.app.game_combo.cget('state')), 'readonly')
        self.assertEqual(str(self.app.target_entry.cget('state')), 'disabled')

    def test_organizer_theme_and_icon_are_used(self):
        style = ui.ttk.Style(self.app)
        self.assertEqual(style.theme_use(), 'clam')
        self.assertEqual(self.app.cget('background'), '#20252d')
        self.assertEqual(style.lookup('Title.TLabel', 'foreground'), '#dfb875')
        self.assertEqual(style.lookup('Accent.TButton', 'background'), '#cba56a')
        self.assertEqual(style.lookup('Treeview', 'fieldbackground'), '#181c22')
        self.assertEqual(style.lookup('TEntry', 'insertcolor'), '#ffffff')
        self.assertEqual((TOOLS / 'assets/annoorganizer.ico').read_bytes(),
                         (TOOLS.parents[1] / 'desktop/assets/annoorganizer.ico').read_bytes())

    def test_1800_uses_its_own_account_root_and_file_filter(self):
        self.app.load([self.source])
        documents = Path(self.temp.name) / 'Documents'
        other_root = account(documents / 'Anno 1800', 'anno1800')
        source = other_root / 'Old/Save.a7s'
        source.parent.mkdir()
        source.write_bytes(save('anno1800'))
        with patch.object(ui, 'documents_folder', return_value=documents):
            self.app.game_choice.set(ui.GAME_LABELS['anno1800'])
            self.app.on_game_changed()
        self.assertEqual(self.app.save_root, other_root)
        with patch.object(ui.filedialog, 'askopenfilenames', return_value=()) as chooser:
            self.app.select_files()
        self.assertEqual(chooser.call_args.kwargs['filetypes'], [('Anno 1800', '*.a7s')])
        self.app.load([source])
        self.assertEqual(self.app.player_toggle_text.get(), 'Spielernamen ändern')
        self.app.game_choice.set(ui.GAME_LABELS['anno117'])
        self.app.on_game_changed()
        self.assertEqual(self.app.save_root, self.root)
        self.app.game_choice.set(ui.GAME_LABELS['anno1800'])
        self.app.on_game_changed()
        self.assertEqual(self.app.save_root, other_root)

    def test_bulk_name_action_selects_and_edits_every_direct_save_for_both_games(self):
        for game in ('anno117', 'anno1800'):
            with self.subTest(game=game):
                root = account(Path(self.temp.name) / game, game)
                folder = root / 'Names'
                folder.mkdir()
                extension = editor.game_format(game)['extension']
                for name in ('One', 'Two'):
                    (folder / (name + extension)).write_bytes(save(game))
                self.app.game_choice.set(ui.GAME_LABELS[game])
                self.app.on_game_changed()
                with patch.object(ui.filedialog, 'askdirectory', return_value=str(folder)):
                    self.app.select_name_folder()
                self.assertEqual(len(self.app.sources), 2)
                self.assertTrue(self.app.change_player.get())
                self.app.new_player.set('All Players Renamed')
                with patch.object(ui.messagebox, 'askokcancel', return_value=True), patch.object(ui.messagebox, 'showinfo'), patch.object(ui.messagebox, 'showerror') as error:
                    self.app.start(False, edit_in_place=True)
                    self.wait_done()
                error.assert_not_called()
                for source in folder.glob('*' + extension):
                    self.assertEqual(editor.player_name(source.read_bytes(), game), 'All Players Renamed')

    def test_window_bounds_survive_restart_without_losing_account_preferences(self):
        self.app.deiconify()
        self.app.geometry('1040x800+60+70')
        self.app.update()
        self.app.remember_account(self.root)
        self.app.preferences['unrelated_preference'] = 'keep'
        preferences_path = self.app.preferences_path
        self.app.destroy()
        saved = json.loads(preferences_path.read_text(encoding='utf-8'))
        self.assertEqual(saved['windows']['main']['width'], 1040)
        self.assertEqual(saved['windows']['main']['height'], 800)
        self.assertEqual(saved['account_root'], str(self.root))
        self.app = ui.SaveManager(preferences_path=preferences_path)
        self.app.update()
        self.assertEqual(self.app.winfo_width(), 1040)
        self.assertEqual(self.app.winfo_height(), 800)
        self.assertLessEqual(abs(self.app.winfo_x() - saved['windows']['main']['x']), 10)
        self.assertLessEqual(abs(self.app.winfo_y() - saved['windows']['main']['y']), 10)
        self.app.remember_account(self.root)
        stored = json.loads(preferences_path.read_text(encoding='utf-8'))
        self.assertIn('main', stored['windows'])
        self.assertEqual(stored['unrelated_preference'], 'keep')

    def test_unreachable_saved_window_is_recovered_and_minimised_state_is_not_restored(self):
        from anno_save_ui import visible_bounds
        saved = dict(x=-1800, y=100, width=1040, height=800, state='iconic')
        areas = [(-1920, 0, 0, 1080), (0, 0, 1920, 1080)]
        self.assertEqual(visible_bounds(saved, areas, (980, 760))['x'], -1800)
        recovered = visible_bounds(saved, areas[1:], (980, 760))
        self.assertEqual(recovered['x'], 0)
        self.assertEqual(recovered['state'], 'normal')

    def test_profile_rename_uses_prefilled_target_without_a_second_name_dialog(self):
        self.app.load([self.source], self.source.parent)
        self.assertEqual(self.app.target_name.get(), 'Old - Neu')
        self.app.target_name.set('Chosen Name')
        with patch.object(ui.messagebox, 'askokcancel', return_value=False) as confirm:
            self.app.rename_folder()
        confirm.assert_called_once()
        self.assertIn(str(self.root / 'Chosen Name'), confirm.call_args.args[1])
        self.assertEqual(self.app.target_name.get(), 'Chosen Name')
        self.assertTrue(self.source.exists())

    def test_praetor_only_ignores_transfer_destination_and_retains_save(self):
        self.app.load([self.source])
        self.app.target_name.set('Ignored transfer destination')
        self.app.change_player.set(True)
        self.app.new_player.set('Prätor: Renamed')
        with patch.object(ui.messagebox, 'askokcancel', return_value=True), patch.object(ui.messagebox, 'showinfo'), patch.object(ui.messagebox, 'showerror') as error:
            self.app.start(False, edit_in_place=True)
            self.wait_done()
        error.assert_not_called()
        self.assertEqual(editor.player_name(self.source.read_bytes()), 'Prätor: Renamed')
        self.assertFalse((self.root / 'Ignored transfer destination').exists())
        self.assertEqual(self.app.sources, [])
        self.assertEqual(self.app.new_player.get(), '')
        self.assertFalse(self.app.change_player.get())
        self.assertEqual(str(self.app.player_entry.cget('state')), 'disabled')
        self.assertEqual(self.app.target_name.get(), '')
        self.assertEqual(self.app.save_root, self.root)

    def test_all_dialogs_start_at_account_root_and_remember_it_after_success(self):
        self.app.load([self.source])
        with patch.object(ui.filedialog, 'askopenfilenames', return_value=()) as files:
            self.app.select_files()
        self.assertEqual(files.call_args.kwargs['initialdir'], str(self.root))
        for method in (self.app.select_folder, self.app.choose_destination, self.app.choose_backup):
            with self.subTest(method=method.__name__), patch.object(ui.filedialog, 'askdirectory', return_value='') as folders:
                method()
                self.assertEqual(folders.call_args.kwargs['initialdir'], str(self.root))
        self.app.clear_selection()
        with patch.object(ui.filedialog, 'askopenfilenames', return_value=()) as files:
            self.app.select_files()
        self.assertEqual(files.call_args.kwargs['initialdir'], str(self.root))
        self.assertEqual(ui.initial_save_root(self.app.preferences_path), self.root)

    def test_first_start_discovers_redirected_documents_without_a_hardcoded_user_path(self):
        documents = Path(self.temp.name) / 'Redirected Documents'
        found = account(documents / 'Anno 117 - Pax Romana')
        with patch.object(ui, 'documents_folder', return_value=documents):
            self.assertEqual(ui.initial_save_root(self.app.preferences_path), found)
        self.app.preferences_path.write_text('{"account_root": "nonexistent-account"}', encoding='utf-8')
        with patch.object(ui, 'documents_folder', return_value=documents):
            self.assertEqual(ui.initial_save_root(self.app.preferences_path), found)

    def test_whole_folder_selection_does_not_silently_ignore_nested_saves(self):
        nested = self.source.parent / 'Nested'
        nested.mkdir()
        (nested / 'Hidden.a8s').write_bytes(save())
        with patch.object(ui.messagebox, 'showerror') as error:
            self.app.load([self.source], self.source.parent)
        error.assert_called_once()
        self.assertEqual(self.app.sources, [])
        self.assertIsNone(self.app.account)


if __name__ == '__main__':
    unittest.main()
