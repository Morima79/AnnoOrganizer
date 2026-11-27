"""Exercise display-language choice, worker integrity and Tk state transitions."""
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.language import choose_language, resources
from desktop.worker_client import WorkerClient
from desktop.window_state import visible_bounds, work_areas


class LanguageTests(unittest.TestCase):
    def test_display_language_and_saved_override(self):
        for language in ('de', 'de-DE', 'de-CH', 'de_AT', 'DE-ch'):
            self.assertEqual(choose_language(display_language=language), 'de')
        for language in ('', None, 'fr-CH', 'en-DE', 'it-CH'):
            with patch('desktop.language.windows_display_language', return_value=''):
                self.assertEqual(choose_language(display_language=language), 'en')
        self.assertEqual(choose_language('en', 'de-CH'), 'en')
        self.assertEqual(choose_language('de', 'en-US'), 'de')

    def test_resources_have_matching_keys_and_placeholders(self):
        de, en = resources('de'), resources('en')
        self.assertEqual(de.keys(), en.keys())
        for key in de:
            self.assertEqual(set(re.findall(r'{([^}]+)}', de[key])),
                             set(re.findall(r'{([^}]+)}', en[key])), key)


class WindowBoundsTests(unittest.TestCase):
    def test_removed_monitor_is_recovered_and_negative_monitor_positions_remain_valid(self):
        saved = dict(x=-1800, y=100, width=900, height=740)
        areas = [(-1920, 0, 0, 1080), (0, 0, 1920, 1080)]
        self.assertEqual(visible_bounds(saved, areas, (860, 720))['x'], -1800)
        self.assertEqual(visible_bounds(saved, areas[1:], (860, 720))['x'], 0)
        saved['x'] = 0
        self.assertEqual(visible_bounds(saved, areas, (860, 720))['x'], 0)

    def test_invalid_geometry_is_ignored_and_minimized_state_is_not_restored(self):
        areas = [(0, 0, 1920, 1080)]
        self.assertIsNone(visible_bounds({'width': 'huge'}, areas, (1, 1)))
        result = visible_bounds(dict(x=10, y=10, width=900, height=740, state='iconic'), areas, (860, 720))
        self.assertEqual(result['state'], 'normal')


class WorkerClientTests(unittest.TestCase):
    def events(self, status='success'):
        return [dict(protocol_version=1, run_id='job', type='started', payload={}),
                dict(protocol_version=1, run_id='job', type='finished',
                     payload=dict(status=status, galleries=[], logs=[], partial_output=False))]

    def run_fake(self, events, code):
        client = WorkerClient()
        with patch('desktop.worker_client.subprocess.Popen') as popen:
            process = popen.return_value.__enter__.return_value
            process.stdout = io.StringIO('\n'.join(json.dumps(e) for e in events))
            process.wait.return_value = code
            client._run(['fixture'])
        received = []
        while not client.events.empty():
            received.append(client.events.get_nowait())
        return received[-1]['payload']

    def test_success_requires_consistent_exit_and_complete_protocol(self):
        self.assertEqual(self.run_fake(self.events(), 0)['status'], 'success')
        self.assertEqual(self.run_fake(self.events(), 1)['status'], 'failed')
        self.assertEqual(self.run_fake(self.events()[:1], 0)['status'], 'failed')
        events = self.events()
        events[-1]['run_id'] = 'other'
        self.assertEqual(self.run_fake(events, 0)['status'], 'failed')
        self.assertEqual(self.run_fake([*self.events(), self.events()[0]], 0)['status'], 'failed')
        events = self.events()
        events[-1]['payload']['logs'] = None
        self.assertEqual(self.run_fake(events, 0)['status'], 'failed')

    def test_second_start_is_rejected(self):
        client = WorkerClient()
        client.running = True
        with self.assertRaises(ValueError):
            client.start('anno1404', 'demo', 'unused.json')


@unittest.skipUnless(os.name == 'nt', 'Windows Tk desktop')
class DesktopUITests(unittest.TestCase):
    def setUp(self):
        from desktop.app import DesktopApp
        from desktop.self_test import seed_demo_settings
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        seed_demo_settings(self.folder / 'gui')
        self.original_configs = {game: (self.folder / 'gui' / game / 'settings.json').read_bytes()
                                 for game in ('anno117', 'anno1800', 'anno1404')}
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        with patch('desktop.app.choose_language', return_value='de'):
            self.app = DesktopApp(self.root, directory=self.folder / 'gui', game='anno1404')
        self.errors = []
        self.app.error = lambda exc: self.errors.append(str(exc))
        notice_patch = patch('desktop.app.messagebox.showinfo')
        self.notice = notice_patch.start()
        self.addCleanup(notice_patch.stop)

    def test_display_name_uses_localized_product_title(self):
        self.assertEqual(self.root.title(), 'ANNO - Organizer')
        self.assertEqual(resources('de')['app_title'], 'ANNO - Organizer')
        self.assertEqual(resources('en')['app_title'], 'ANNO - Organizer')
        self.app.change_language('en')
        self.assertEqual(self.root.title(), 'ANNO - Organizer')

    def test_guide_button_opens_bundled_html_in_the_selected_language(self):
        self.assertEqual(self.app.guide_button.cget('text'), 'Anleitung')
        page = self.folder / 'docs/user-guide.html'
        page.parent.mkdir()
        page.write_text('<html>Guide</html>', encoding='utf-8')
        for language in ('de', 'en'):
            self.app.change_language(language)
            with patch('desktop.app.ROOT', self.folder), patch('desktop.app.webbrowser.open', return_value=True) as browser:
                self.app.open_guide()
                browser.assert_called_once_with(page.resolve().as_uri() + '?lang=' + language)
        self.assertEqual(self.app.guide_button.cget('text'), 'User guide')

    def test_guide_falls_back_to_the_website_and_reports_browser_failure(self):
        url = 'https://morima79.github.io/AnnoOrganizer/guide/?lang=de'
        with patch('desktop.app.ROOT', self.folder), patch('desktop.app.webbrowser.open', return_value=True) as browser:
            self.app.open_guide()
            browser.assert_called_once_with(url)
        with patch('desktop.app.ROOT', self.folder), patch('desktop.app.webbrowser.open', return_value=False):
            self.app.open_guide()
        self.assertIn(url, self.errors[-1])

    def test_language_switch_preserves_draft_and_selected_tab_and_persists(self):
        self.app.fields['output'].set(str(self.folder / 'Äusserer Ordner'))
        self.app.add_save_folder(str(self.folder / 'More Saves'))
        self.app.notebook.select(1)
        self.app.change_language('en')
        self.assertEqual(self.app.fields['output'].get(), str(self.folder / 'Äusserer Ordner'))
        self.assertTrue(any('More Saves' in field.get() for field in self.app.folder_fields))
        self.assertEqual(self.app.notebook.index('current'), 1)
        self.assertEqual(json.loads(self.app.store.preferences_path.read_text(encoding='utf-8'))['language'], 'en')
        self.assertEqual(self.app.document.path.read_bytes(), self.original_configs['anno1404'])
        self.assertEqual(self.errors, [])

    def test_game_switch_preserves_unsaved_fields_and_rejects_1404_stamps(self):
        self.app.fields['output'].set(str(self.folder / 'Changed'))
        self.app.switch_game('anno117')
        self.app.action.set('stamps')
        self.app.switch_game('anno1404')
        self.assertEqual(self.app.action.get(), 'analyze')
        self.assertEqual(self.app.fields['output'].get(), str(self.folder / 'Changed'))

    def test_1404_uses_single_line_fields_and_preserves_multiple_paths(self):
        from tkinter import ttk
        self.assertIsInstance(self.app.folder_entries[0], ttk.Entry)
        long_path = str(self.folder / ('long path ' * 15).strip())
        self.app.folder_fields[0].set(long_path)
        self.app.add_save_folder(str(self.folder / 'Second Save Folder'))
        self.app.collect()
        self.assertEqual(self.app.document.data['save_folders'], [long_path, str(self.folder / 'Second Save Folder')])
        self.app.remove_save_folder(1)
        self.app.collect()
        self.assertEqual(self.app.document.data['save_folders'], [long_path])

    def test_selected_action_is_saved_per_game_and_restored_after_restart(self):
        from desktop.app import DesktopApp
        self.app.action_buttons['analyze'].invoke()
        self.app.switch_game('anno117')
        self.app.action_buttons['stamps'].invoke()
        self.app.switch_game('anno1404')
        self.assertEqual(self.app.action.get(), 'analyze')
        second = tk.Tk()
        second.withdraw()
        self.addCleanup(second.destroy)
        restarted = DesktopApp(second, directory=self.app.store.directory, game='anno1404')
        self.assertEqual(restarted.action.get(), 'analyze')
        restarted.switch_game('anno117')
        self.assertEqual(restarted.action.get(), 'stamps')
        restarted.action_buttons['demo'].invoke()
        saved = json.loads(restarted.store.preferences_path.read_text(encoding='utf-8'))
        self.assertEqual(saved['actions'], {'anno1404': 'analyze', 'anno117': 'demo'})
        self.assertEqual(restarted.document.path.read_bytes(), self.original_configs['anno117'])

    def test_auto_open_choice_is_optional_and_restored_after_restart(self):
        from desktop.app import DesktopApp
        self.assertFalse(self.app.auto_open.get())
        self.app.auto_open_checkbox.invoke()
        self.app.change_language('en')
        self.assertTrue(self.app.auto_open.get())
        second = tk.Tk()
        second.withdraw()
        self.addCleanup(second.destroy)
        restarted = DesktopApp(second, directory=self.app.store.directory, game='anno1404')
        self.assertTrue(restarted.auto_open.get())
        restarted.auto_open_checkbox.invoke()
        self.assertIs(restarted.store.preferences['auto_open_galleries'], False)
        self.assertEqual(restarted.document.path.read_bytes(), self.original_configs['anno1404'])

    def test_auto_open_only_opens_current_successful_results_once(self):
        page = self.folder / 'new gallery.html'
        page.write_text('gallery', encoding='utf-8')
        self.app.auto_open.set(True)
        with patch('desktop.app.webbrowser.open', return_value=True) as browser:
            for status in ('failed', 'cancelled', 'success'):
                self.app.client.events.put(dict(type='completed', payload=dict(
                    status=status, galleries=[str(page), str(page)], logs=[], partial_output=False)))
                self.app.poll()
            browser.assert_called_once_with(page.resolve().as_uri())
            self.app.auto_open.set(False)
            self.app.client.events.put(dict(type='completed', payload=dict(
                status='success', galleries=[str(page)], logs=[], partial_output=False)))
            self.app.poll()
            self.assertEqual(browser.call_count, 1)

    def test_invalid_saved_action_falls_back_to_analyze(self):
        for actions in ([], {'anno1404': 'stamps'}, {'anno1404': 'unknown'}):
            self.app.store.preferences['actions'] = actions
            self.assertEqual(self.app.saved_action('anno1404'), 'analyze')

    def test_selected_language_and_tabs_use_gold_without_padding_changes(self):
        from tkinter import ttk
        style = ttk.Style(self.root)
        self.assertEqual(style.lookup(self.app.language_buttons['de'].cget('style'), 'background'), '#cba56a')
        self.app.change_language('en')
        self.assertEqual(style.lookup(self.app.language_buttons['en'].cget('style'), 'background'), '#cba56a')
        self.assertNotEqual(self.app.language_buttons['de'].cget('style'), 'LanguageSelected.TButton')
        self.assertEqual(style.lookup('TNotebook.Tab', 'background', ('selected',)), '#cba56a')
        self.assertEqual(str(style.lookup('TNotebook.Tab', 'padding', ('selected',))),
                         str(style.lookup('TNotebook.Tab', 'padding', ('!selected',))))

    def test_about_is_owned_by_main_and_survives_language_changes(self):
        self.app.about()
        window = self.app.child_windows['about']
        self.assertEqual(str(window.transient()), str(self.root))
        self.app.about()
        self.assertIs(self.app.child_windows['about'], window)
        self.app.change_language('en')
        self.assertTrue(window.winfo_exists())
        self.assertEqual(window.title(), 'About')

    def test_window_geometry_survives_restart(self):
        from desktop.app import DesktopApp
        self.root.deiconify()
        self.root.geometry('950x780+100+120')
        self.root.update()
        self.app.window_state.remember_all()
        self.app.store.save_preferences()
        saved = self.app.store.preferences['windows']['main']
        expected = visible_bounds(saved, work_areas(self.root), (860, 720))
        second = tk.Tk()
        self.addCleanup(second.destroy)
        second.withdraw()
        DesktopApp(second, directory=self.app.store.directory, game='anno1404')
        second.deiconify()
        second.update()
        self.assertEqual(second.winfo_width(), expected['width'])
        self.assertEqual(second.winfo_height(), expected['height'])
        self.assertAlmostEqual(second.winfo_x(), expected['x'], delta=2)
        self.assertAlmostEqual(second.winfo_y(), expected['y'], delta=2)

    def test_maximizing_keeps_normal_bounds_for_restoration(self):
        self.root.deiconify()
        self.root.geometry('950x780+100+120')
        self.root.update()
        self.app.window_state.remember_all()
        normal = dict(self.app.store.preferences['windows']['main'])
        self.root.state('zoomed')
        self.root.update()
        self.app.window_state.remember_all()
        saved = self.app.store.preferences['windows']['main']
        self.assertEqual(saved, dict(normal, state='zoomed'))

    def test_child_window_bounds_are_saved_and_restored_on_reopen(self):
        self.root.deiconify()
        self.root.update()
        self.app.about()
        window = self.app.child_windows['about']
        window.geometry('500x300+130+150')
        self.root.update()
        self.app.close_child('about')
        saved = self.app.store.preferences['windows']['about']
        expected = visible_bounds(saved, work_areas(self.root), (1, 1))
        self.app.about()
        window = self.app.child_windows['about']
        self.root.update()
        self.assertEqual(window.winfo_width(), expected['width'])
        self.assertEqual(window.winfo_height(), expected['height'])
        self.assertAlmostEqual(window.winfo_x(), expected['x'], delta=2)
        self.assertAlmostEqual(window.winfo_y(), expected['y'], delta=2)

    def test_save_retains_unknown_values(self):
        self.app.document.data['custom'] = {'keep': True}
        self.assertTrue(self.app.save())
        data = json.loads(self.app.document.path.read_text(encoding='utf-8'))
        self.assertEqual(data['custom'], {'keep': True})
        self.assertFalse(self.app.dirty())
        self.assertEqual(self.errors, [])

    def test_entries_use_a_bright_insertion_cursor(self):
        from tkinter import ttk
        style = ttk.Style(self.root)
        self.assertEqual(style.lookup('TEntry', 'insertcolor'), '#ffffff')
        self.assertEqual(str(style.lookup('TEntry', 'insertwidth')), '2')

    def test_failed_browser_launch_reports_the_existing_gallery_path(self):
        page = self.app.document.view().report_output / 'map-gallery.html'
        page.parent.mkdir(parents=True)
        page.write_text('<html>existing gallery</html>', encoding='utf-8')
        with patch('desktop.app.webbrowser.open', return_value=False), \
                patch('desktop.app.messagebox.showerror') as error:
            self.app.open_galleries()
        self.assertIn(str(page), error.call_args.args[1])
        self.assertIn(str(page), self.app.details)

    def test_worker_diagnostics_remain_available_after_temporary_job_cleanup(self):
        self.app.client.events.put(dict(type='completed', payload=dict(
            status='failed', galleries=[], logs=[], partial_output=False,
            message='Permission denied: output folder')))
        self.app.poll()
        log = self.app.store.directory / 'logs/anno1404-last-run.json'
        saved = json.loads(log.read_text(encoding='utf-8'))
        self.assertEqual(saved['result']['message'], 'Permission denied: output folder')
        self.assertEqual(saved['result']['status'], 'failed')
        self.assertIsNone(self.app.snapshot)

    def test_reports_resolve_separate_and_demo_destinations_and_open_with_windows(self):
        self.assertTrue(self.app.report_button.instate(['disabled']))
        for game in ('anno1404', 'anno117', 'anno1800'):
            self.app.switch_game(game)
            self.app.fields['report_output'].set(str(self.folder / game / 'Separate Reports'))
            view = self.app.draft_view()
            paths = [view.report_output / (game + '-map-seeds.xlsx'),
                     view.output / 'demo/reports' / (game + '-map-seeds.xlsx')]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'workbook fixture')
            self.app.refresh_galleries()
            self.assertTrue(self.app.report_button.instate(['!disabled']))
            self.assertEqual([path for _, path in self.app.available_reports()], paths)
            self.app.fill_report_menu()
            with patch('desktop.app.os.startfile') as start:
                self.app.report_menu.invoke(0)
                self.app.report_menu.invoke(1)
            self.assertEqual([call.args[0] for call in start.call_args_list], paths)
            with patch('desktop.app.os.startfile', side_effect=OSError('No file association')):
                self.app.open_report(paths[0])
            self.assertIn('No file association', self.errors)
            self.assertTrue(self.app.save())
            self.app.reload()
            self.assertEqual([path for _, path in self.app.available_reports()], paths)
            paths[0].unlink()
            self.assertEqual([path for _, path in self.app.available_reports()], paths[1:])

    def test_logs_follow_game_selection_in_open_window_and_survive_restart(self):
        from desktop.app import DesktopApp
        log = self.folder / 'demo.log'
        log.write_text('1404 demo log', encoding='utf-8')
        self.app.record_result(result=dict(status='failed', logs=[str(log)], message='1404 diagnostic'))
        self.app.details = 'stale details'
        self.app.show_logs()
        self.assertIn('1404 demo log', self.app.log_text.get('1.0', 'end'))
        self.app.switch_game('anno1800')
        self.assertEqual(self.app.details, '')
        self.assertEqual(self.app.log_text.get('1.0', 'end-1c'), self.app.t('log_empty'))
        self.app.close_child('logs')
        self.app.switch_game('anno1404')
        self.app.show_logs()
        self.assertIn('1404 diagnostic', self.app.log_text.get('1.0', 'end'))
        second = tk.Tk()
        second.withdraw()
        self.addCleanup(second.destroy)
        restarted = DesktopApp(second, directory=self.app.store.directory, game='anno1404')
        restarted.show_logs()
        self.assertIn('1404 demo log', restarted.log_text.get('1.0', 'end'))
        log.unlink()
        self.assertIn('1404 diagnostic', restarted.log_content())
        record = self.app.store.directory / 'logs/anno1404-last-run.json'
        record.write_text('{invalid', encoding='utf-8')
        self.app.refresh_logs()
        self.assertNotIn('1404 demo log', self.app.log_text.get('1.0', 'end'))

    def test_main_window_uses_bundled_application_icon(self):
        from desktop.app import DesktopApp
        second = tk.Tk()
        second.withdraw()
        self.addCleanup(second.destroy)
        with patch.object(second, 'iconbitmap', wraps=second.iconbitmap) as icon:
            DesktopApp(second, directory=self.app.store.directory, game='anno1404')
        icon.assert_called_once_with(default=str(ROOT / 'desktop/assets/annoorganizer.ico'))

    def test_browse_starts_at_resolved_draft_or_nearest_existing_parent(self):
        source = self.app.document.path.parent / 'Saved Games'
        source.mkdir(parents=True)
        self.app.folder_fields[0].set('./Saved Games')
        with patch('desktop.app.filedialog.askdirectory', return_value='') as choose:
            self.app.browse_save_folder(self.app.folder_fields[0])
            self.assertEqual(Path(choose.call_args.kwargs['initialdir']), source.resolve())
        self.app.fields['output'].set('./Saved Games/New Output')
        with patch('desktop.app.filedialog.askdirectory', return_value=str(self.folder)) as choose:
            self.app.browse('output')
            self.assertEqual(Path(choose.call_args.kwargs['initialdir']), source.resolve())
        self.assertEqual(self.app.fields['output'].get(), str(self.folder))

    def test_game_browse_shows_executables_and_resolves_data_from_bin(self):
        self.app.switch_game('anno1800')
        installation = self.folder / 'Anno 1800'
        data = installation / 'maindata'
        data.mkdir(parents=True)
        (data / 'data0.rda').write_bytes(b'fixture')
        binary = installation / 'Bin/Win64/Anno1800.exe'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'fixture, never executed')
        self.app.fields['game_data'].set(str(data))
        with patch('desktop.app.filedialog.askopenfilename', return_value=str(binary)) as choose:
            self.app.browse('game_data')
            self.assertEqual(Path(choose.call_args.kwargs['initialdir']), installation.resolve())
            self.assertEqual(choose.call_args.kwargs['filetypes'][0][1], '*.exe')
        self.assertEqual(Path(self.app.fields['game_data'].get()), data.resolve())
        self.app.switch_game('anno117')
        original = self.app.fields['game_data'].get()
        with patch('desktop.app.filedialog.askopenfilename', return_value=str(binary)), \
                patch('desktop.app.messagebox.showerror') as error:
            self.app.browse('game_data')
        error.assert_called_once()
        self.assertEqual(self.app.fields['game_data'].get(), original)

    def test_existing_galleries_survive_restart_and_offer_individual_selection(self):
        self.app.switch_game('anno1800')
        self.app.fields['output'].set(str(self.folder / 'Output'))
        self.app.fields['report_output'].set(str(self.folder / 'Separate Reports'))
        self.app.fields['stamp_output'].set(str(self.folder / 'Separate Stamps'))
        view = self.app.draft_view()
        pages = [view.report_output / 'map-gallery.html', view.stamp_output / 'stamp-gallery.html',
                 view.output / 'demo/reports/map-gallery.html', view.output / 'demo/stamps/stamp-gallery.html']
        for page in pages:
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text('<html>existing gallery</html>', encoding='utf-8')
        self.app.refresh_galleries()
        self.assertIsNone(self.app.last_result)
        self.assertTrue(self.app.gallery_button.instate(['!disabled']))
        self.assertEqual({path for _, path in self.app.available_galleries()}, set(pages))
        self.app.fill_gallery_menu()
        self.assertEqual(self.app.gallery_menu.index('end'), 3)
        with patch('desktop.app.webbrowser.open') as browser:
            self.app.gallery_menu.invoke(0)
            browser.assert_called_once_with(pages[0].as_uri())
            browser.reset_mock()
            self.app.open_galleries()
            self.assertEqual(browser.call_count, 4)
        self.app.collect()
        self.assertTrue(self.app.save())
        self.app.reload()
        self.assertTrue(self.app.gallery_button.instate(['!disabled']))
        pages[0].unlink()
        self.assertEqual(len(self.app.available_galleries()), 3)

    def test_busy_locks_interface_but_keeps_existing_galleries_readable(self):
        view = self.app.document.view()
        page = view.report_output / 'map-gallery.html'
        page.parent.mkdir(parents=True)
        page.write_text('<html>existing gallery</html>', encoding='utf-8')
        def start(*args):
            self.app.client.running = True
        selected = self.app.notebook.select()
        with patch.object(self.app.client, 'start', side_effect=start):
            self.app.generate()
        self.assertTrue(all(control.instate(['disabled']) for control in self.app.controls))
        self.assertEqual(self.app.notebook.select(), selected)
        self.assertTrue(all(self.app.notebook.tab(tab, 'state') == 'disabled'
                            for tab in self.app.notebook.tabs() if tab != selected))
        self.assertTrue(self.app.cancel_button.instate(['!disabled']))
        self.assertTrue(self.app.gallery_button.instate(['!disabled']))
        self.assertTrue(self.app.gallery_menu_button.instate(['!disabled']))
        self.app.change_language('en')
        self.app.switch_game('anno1800')
        self.assertEqual(self.app.language, 'de')
        self.assertEqual(self.app.game, 'anno1404')
        self.app.client.running = False
        self.app.cleanup_snapshot()
        self.app.apply_busy()
        self.assertEqual(self.app.notebook.select(), selected)
        self.assertTrue(all(control.instate(['!disabled']) for control in self.app.controls))

    def test_close_requests_cancellation_waits_and_keeps_unsaved_changes_reviewable(self):
        self.app.fields['output'].set(str(self.folder / 'Unsaved output'))
        def start(*args):
            self.app.client.running = True
        with patch.object(self.app.client, 'start', side_effect=start):
            self.app.generate()
        with patch('desktop.app.messagebox.askyesno', return_value=False), \
                patch.object(self.app.client, 'cancel') as cancel:
            self.app.close()
            cancel.assert_not_called()
        with patch('desktop.app.messagebox.askyesno', return_value=True), \
                patch.object(self.app.client, 'cancel') as cancel:
            self.app.close()
            cancel.assert_called_once()
        self.assertTrue(self.app.closing)
        self.assertFalse(self.app.closed)
        self.assertIsNotNone(self.app.snapshot)
        self.app.client.running = False
        self.app.client.events.put(dict(type='completed', payload=dict(
            status='cancelled', galleries=[], logs=[], partial_output=False)))
        with patch('desktop.app.messagebox.askyesnocancel', return_value=None):
            self.app.poll()
        self.assertFalse(self.app.closing)
        self.assertFalse(self.app.closed)
        self.assertIsNotNone(self.app._poll_id)
        self.assertTrue(self.app.dirty())
        with patch('desktop.app.messagebox.askyesnocancel', return_value=False), \
                patch.object(self.app, 'finish_close') as finish:
            self.app.close()
            finish.assert_called_once()

    def test_use_then_import_external_config_preserves_source_and_destinations(self):
        source = self.folder / 'external.json'
        data = dict(version=1, game='anno1404', save_folders=['./Saves'],
                    output='./Private Output', custom={'keep': True})
        source.write_text(json.dumps(data), encoding='utf-8')
        before = source.read_bytes()
        with patch('desktop.app.filedialog.askopenfilename', return_value=str(source)), \
                patch('desktop.app.messagebox.askyesno', return_value=True):
            self.app.use_file()
            self.assertEqual(self.app.document.path, source.resolve())
            expected = self.app.document.view().output
            self.app.import_file()
        self.assertEqual(self.app.document.path, self.app.store.default_path('anno1404').resolve())
        self.assertEqual(self.app.document.view().output, expected)
        self.assertEqual(self.app.document.data['custom'], {'keep': True})
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(self.errors, [])

    def test_demo_runs_without_writing_personal_config_and_restores_controls(self):
        self.app.action.set('demo')
        self.app.generate()
        self.notice.assert_called_once()
        self.assertIn(str(self.app.document.view().output / 'demo'), self.notice.call_args.args[1])
        self.assertIn('Demo', self.app.status_text())
        self.assertTrue(self.app.generate_button.instate(['disabled']))
        self.assertEqual(self.app.document.path.read_bytes(), self.original_configs['anno1404'])
        deadline = time.monotonic() + 20
        while self.app.snapshot is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertIsNone(self.app.snapshot)
        self.assertEqual(self.app.status, 'success', self.app.details)
        self.assertTrue(self.app.gallery_button.instate(['!disabled']))
        self.assertTrue(self.app.generate_button.instate(['!disabled']))
        self.assertEqual(self.app.document.path.read_bytes(), self.original_configs['anno1404'])
        self.assertTrue(all(Path(p).is_file() for p in self.app.last_result['galleries']))
        self.assertFalse(list((self.app.store.directory / 'runs').glob('job-*')))
        self.assertEqual(self.errors, [])

    def test_normal_generation_does_not_show_a_demo_notice(self):
        def start(*args):
            self.app.client.running = True
        self.app.action.set('analyze')
        with patch.object(self.app.client, 'start', side_effect=start):
            self.app.generate()
        self.notice.assert_not_called()
        self.assertNotIn('Demo', self.app.status_text())
        self.app.client.running = False
        self.app.cleanup_snapshot()

    def test_cancel_waits_for_completion_before_restoring_controls(self):
        def start(*args):
            self.app.client.running = True
        with patch.object(self.app.client, 'start', side_effect=start):
            self.app.generate()
        self.app.cancel()
        self.assertEqual(self.app.status, 'cancelling')
        self.assertTrue(self.app.generate_button.instate(['disabled']))
        self.app.client.running = False
        self.app.client.events.put(dict(type='completed', payload=dict(
            status='cancelled', galleries=[], logs=[], partial_output=False)))
        self.app.poll()
        self.assertEqual(self.app.status, 'cancelled')
        self.assertTrue(self.app.generate_button.instate(['!disabled']))
        self.assertTrue(self.app.gallery_button.instate(['disabled']))
        self.assertIsNone(self.app.snapshot)

    def test_invalid_configuration_cannot_keep_an_old_success_state(self):
        self.app.last_result = dict(status='success', galleries=['previous.html'], logs=[], partial_output=False)
        self.app.status = 'success'
        self.app.fields['output'].set(str(ROOT / 'desktop'))
        self.app.generate()
        self.assertEqual(self.app.status, 'failed')
        self.assertTrue(self.app.gallery_button.instate(['disabled']))
        self.assertIsNone(self.app.snapshot)
        self.assertFalse(self.app.client.running)
        self.assertTrue(self.errors)

    def test_missing_save_folder_is_reported_before_starting_a_worker(self):
        self.app.folder_fields[0].set(str(self.folder / 'missing-saves'))
        with patch.object(self.app.client, 'start') as start:
            self.app.generate()
        start.assert_not_called()
        self.assertIsNone(self.app.snapshot)
        self.assertEqual(self.app.status, 'failed')
        self.assertTrue(self.errors)

    def test_noninteractive_gui_smoke_covers_first_launch_and_worker(self):
        from desktop.self_test import run
        report = self.folder / 'gui-smoke.json'
        self.assertEqual(run(report, self.folder / 'self-test-state'), 0)
        self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'success')

    def test_single_game_smoke_updates_available_gallery_and_reports_missing_games(self):
        from desktop.self_test import run
        report = self.folder / 'single-game-smoke.json'
        self.assertEqual(run(report, self.folder / 'single-game-state', single_game=True), 0)
        result = json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(len(result['galleries']), 1)
        self.assertEqual({item['game'] for item in result['skipped']}, {'anno117', 'anno1800'})


if __name__ == '__main__':
    unittest.main()
