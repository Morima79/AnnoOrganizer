"""Standalone save-manager translations; user names and paths are never translated."""
import ctypes
import os
import re


def windows_display_language():
    """Use the same Windows display-language preference as the Organizer."""
    if os.name != 'nt':
        return ''
    try:
        kernel = ctypes.windll.kernel32
        count, size = ctypes.c_ulong(), ctypes.c_ulong()
        if kernel.GetUserPreferredUILanguages(8, ctypes.byref(count), None, ctypes.byref(size)):
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel.GetUserPreferredUILanguages(8, ctypes.byref(count), buffer, ctypes.byref(size)):
                return buffer.value
        buffer = ctypes.create_unicode_buffer(85)
        if kernel.LCIDToLocaleName(kernel.GetUserDefaultUILanguage(), buffer, len(buffer), 0):
            return buffer.value
    except (OSError, AttributeError, ValueError):
        pass
    return ''


def choose_language(saved=None, display_language=None):
    if saved in ('de', 'en'):
        return saved
    name = windows_display_language() if display_language is None else display_language
    return 'de' if (name or '').replace('_', '-').split('-')[0].lower() == 'de' else 'en'


MESSAGES = {
    'guide': ('Anleitung', 'Guide'),
    'guide_error': ('Anleitung öffnen', 'Open guide'),
    'guide_open_failed': ('Die Anleitung konnte nicht geöffnet werden: {url}', 'Could not open the guide: {url}'),
    'title': ('Spielstände verwalten', 'Manage saved games'),
    'game': ('Spiel:', 'Game:'),
    'warning': ('Spiel vor Änderungen schliessen. Cloud-Synchronisierung kann alte Profile wiederherstellen.',
                'Close the game before editing. Cloud synchronisation may restore old profiles.'),
    'select_files': ('Einzelne Saves auswählen …', 'Select individual saves …'),
    'select_folder': ('Ganzer Profilordner …', 'Complete profile folder …'),
    'select_names': ('Alle Namen im Ordner …', 'All names in folder …'),
    'no_source': ('Keine Quelle ausgewählt', 'No source selected'),
    'file': ('Datei', 'File'),
    'praetor': ('Prätor', 'Praetor'),
    'player': ('Spielername', 'Player name'),
    'profile': ('Speicherprofil', 'Save profile'),
    'saved_name': ('Gespeicherter Name', 'Stored save name'),
    'target_name': ('Ziel-Profilname', 'Destination profile name'),
    'backup_folder': ('Sicherungsordner', 'Backup folder'),
    'destination': ('Ziel: {path}', 'Destination: {path}'),
    'start_folder': ('Startordner: {path}', 'Starting folder: {path}'),
    'account': ('Spielkonto: {path}', 'Game account: {path}'),
    'ready': ('Saves oder einen Profilordner auswählen.', 'Select saves or a profile folder.'),
    'change_praetor': ('Prätornamen ändern', 'Change praetor name'),
    'change_player': ('Spielernamen ändern', 'Change player name'),
    'only_praetor': ('Nur Prätor ändern', 'Change praetor only'),
    'only_player': ('Nur Spielername ändern', 'Change player name only'),
    'name_hint': ('Optional beim Übertragen oder am bisherigen Ort ändern. Gilt für alle ausgewählten Saves und daraus künftig erzeugte Spielstände.',
                  'Optionally change the name during a transfer or in place. Applies to all selected saves and future saves created from them.'),
    'structure_hint': ('Zielprofile liegen direkt im selben Konto. Unterordner in Profilen sind gesperrt. Das Speicherprofil wird an den Zielordner angeglichen; Originale werden vorab als ZIP gesichert.',
                       'Destination profiles sit directly in the same account. Profile subfolders are blocked. The save profile is aligned with the destination folder; originals are backed up as a ZIP first.'),
    'copy': ('Kopieren', 'Copy'),
    'move': ('Verschieben', 'Move'),
    'rename': ('Profilordner umbenennen …', 'Rename profile folder …'),
    'rename_action': ('Profilordner umbenennen', 'Rename profile folder'),
    'names_action': ('Namen ändern', 'Change names'),
    'files_title': ('{game}-Saves auswählen', 'Select {game} saves'),
    'folder_title': ('Einen Profilordner auswählen (nicht den Kontoordner)', 'Select a profile folder (not the account folder)'),
    'names_title': ('Profilordner für die Namensänderung aller Saves wählen', 'Select a profile folder to rename the player in all saves'),
    'folder_error': ('Profilordner nicht verwendbar', 'Profile folder cannot be used'),
    'all_selected': ('Alle {count} Saves des Ordners ausgewählt. Neuen Namen eingeben und «{action}» ausführen.',
                     'All {count} saves in the folder selected. Enter a new name and choose “{action}”.'),
    'selection': ('{count} Save(s) · {path}', '{count} save(s) · {path}'),
    'loaded': ('Felder gelesen. Zielordner prüfen und Aktion auswählen.', 'Fields read. Check the destination folder and choose an action.'),
    'load_failed': ('Auswahl konnte nicht geladen werden', 'Could not load the selection'),
    'unsupported': ('Spielstand nicht unterstützt', 'Save is not supported'),
    'choose_source': ('Quelle wählen', 'Select source'),
    'source_first': ('Zuerst Saves oder einen Profilordner auswählen.', 'Select saves or a profile folder first.'),
    'target_title': ('Direkten Ziel-Profilordner wählen', 'Select a direct destination profile folder'),
    'invalid_target': ('Ungültiges Ziel', 'Invalid destination'),
    'backup_title': ('Dauerhaften Sicherungsordner ausserhalb des Spielkontos wählen', 'Select a permanent backup folder outside the game account'),
    'choose_profile': ('Profilordner wählen', 'Select profile folder'),
    'profile_first': ('Zuerst «Ganzer Profilordner» auswählen.', 'Select “Complete profile folder” first.'),
    'action_error': ('Aktion nicht möglich', 'Action cannot be performed'),
    'confirmation': ('{count} Save(s) aus {source}\nZiel: {destination}\n{person}: {player}\nSpeicherprofil: {profile}\nSicherung: {backup}\n\nSpiel geschlossen? Aktion jetzt ausführen?',
                     '{count} save(s) from {source}\nDestination: {destination}\n{person}: {player}\nSave profile: {profile}\nBackup: {backup}\n\nIs the game closed? Perform this action now?'),
    'unchanged': ('unverändert', 'unchanged'),
    'working': ('Saves prüfen, sichern und bearbeiten …', 'Checking, backing up and editing saves …'),
    'done_status': ('Fertig. Sicherung: {result}', 'Done. Backup: {result}'),
    'failed_status': ('Abgebrochen: {result}', 'Cancelled: {result}'),
    'completed_selection': ('Aktion abgeschlossen · für weitere Aktionen Quelle erneut auswählen', 'Action completed · select a source again for another action'),
    'completed': ('Abgeschlossen', 'Completed'),
    'completed_message': ('Saves geprüft und übertragen.\nSicherung: {result}', 'Saves verified and processed.\nBackup: {result}'),
    'cancelled': ('Aktion abgebrochen', 'Action cancelled'),
    'busy': ('Bearbeitung läuft', 'Editing in progress'),
    'please_wait': ('Bitte warten, bis die Übertragung abgeschlossen ist.', 'Please wait until the transfer has completed.'),
    'new_suffix': (' - Neu', ' - New'),
    'ambiguous': ('Nicht eindeutig zuordenbar', 'Cannot identify unambiguously'),
}


def text(language, key, **values):
    return MESSAGES[key][0 if language == 'de' else 1].format(**values)


# Match complete application errors, preserving path/name captures verbatim.
# Operating-system diagnostics retain their original system language.
ERRORS = {
    'Die Spielprüfung ist nur unter Windows verfügbar.': 'Game process detection is only available on Windows.',
    'Es konnte nicht geprüft werden, ob das Spiel läuft. Bitte die Aktion erneut versuchen. Es wurden keine Saves bearbeitet.':
        'Could not check whether the game is running. Please retry. No saves were edited.',
    '{game} läuft noch. Bitte das Spiel vollständig schliessen und die Cloud-Synchronisierung abwarten. Danach die Aktion erneut ausführen. Es wurden keine Saves bearbeitet.':
        '{game} is still running. Close the game completely and wait for cloud synchronisation, then retry. No saves were edited.',
    'Dieses Spiel wird noch nicht unterstützt.': 'This game is not supported yet.',
    'Kein temporärer Ordner ausserhalb OneDrive verfügbar.': 'No temporary folder outside OneDrive is available.',
    'Ungültiger Windows-Name: {name}': 'Invalid Windows name: {name}',
    'Bitte einen Spielernamen ohne Rand-Leerzeichen oder Steuerzeichen angeben (höchstens 120 UTF-16-Zeichen).':
        'Enter a player name without leading/trailing spaces or control characters (at most 120 UTF-16 code units).',
    'Bitte im Feld «Ziel-Profilname» nur einen Profilnamen eingeben, zum Beispiel «Mein Profil». Pfade und Unterordner sind hier nicht erlaubt. Das Zielprofil wird direkt im Kontoordner angelegt.':
        'Enter only a profile name in “Destination profile name”, for example “My Profile”. Paths and subfolders are not allowed. The destination profile is created directly in the account folder.',
    '{game}-Konto nicht erkannt: Profil direkt unter accounts/<Konto> mit {marker} auswählen.':
        '{game} account not recognised: select a profile directly inside accounts/<account> containing {marker}.',
    'Saves müssen direkt im Profilordner liegen. Unterordner innerhalb eines Profils sind nicht erlaubt.':
        'Saves must be directly inside the profile folder. Subfolders within a profile are not allowed.',
    'Der Profilordner enthält Unterordner. Bitte diese zuerst prüfen; Namen werden nur direkt im Profil geändert.':
        'The profile folder contains subfolders. Check them first; names are only changed in saves directly inside the profile.',
    'Keine passenden Spielstände direkt im Profilordner gefunden.': 'No matching saves found directly inside the profile folder.',
    'Bitte unterschiedliche Saves auswählen.': 'Select distinct saves.',
    'Nur {extension}-Saves direkt aus einem Profilordner auswählen.': 'Select only {extension} saves directly inside one profile folder.',
    'Nur {extension}-Saves aus einem Profilordner auswählen.': 'Select only {extension} saves from one profile folder.',
    'Ziel muss ein direkter Profilordner desselben Kontos sein. Keine Unterordner in Profilen anlegen.':
        'The destination must be a direct profile folder in the same account. Do not create subfolders within profiles.',
    'Spielername ohne Verschieben nur im ursprünglichen Profilordner ändern.': 'An in-place player name change must use the original profile folder.',
    'Für eine Übertragung einen anderen Profilordner wählen.': 'Choose a different profile folder for a transfer.',
    'Der Zielpfad ist kein Ordner.': 'The destination path is not a folder.',
    'Kein unterstützter Spielstand (RDA V2.2).': 'Unsupported save (RDA V2.2 required).',
    'Ungültige RDA-Blockposition.': 'Invalid RDA block position.',
    'Unbekannte RDA-Blockstruktur; keine Bearbeitung.': 'Unknown RDA block structure; editing is blocked.',
    'Ungültige RDA-Dateigrenzen.': 'Invalid RDA file boundaries.',
    'Ungültige RDA-Verkettung.': 'Invalid RDA block chain.',
    'Unerwartete Save-Mitglieder oder zusätzliche Daten.': 'Unexpected save members or extra data.',
    'Namensfeld fehlt oder ist mehrdeutig: {field}': 'Missing or ambiguous name field: {field}',
    'Spielername nicht eindeutig erkennbar; mehrere Spieler oder unbekanntes Save-Format.':
        'Cannot identify the player name unambiguously; multiple players or unknown save format.',
    'Spielernamen in header und gamesetup stimmen nicht überein.': 'Player names in header and gamesetup do not match.',
    'Andere FileDB-Felder wurden verändert.': 'Other FileDB fields were changed.',
    'Unvollständige FileDB-V1-Daten.': 'Incomplete FileDB V1 data.',
    'Ungültiges FileDB-V1-Verzeichnis.': 'Invalid FileDB V1 directory.',
    'Unvollständige FileDB-V1-Länge.': 'Incomplete FileDB V1 length.',
    'Ungültige FileDB-V1-Länge.': 'Invalid FileDB V1 length.',
    'Unvollständiges FileDB-V1-Feld.': 'Incomplete FileDB V1 field.',
    'FileDB-V1-Feldposition nicht gefunden.': 'FileDB V1 field position not found.',
    'FileDB-V1-Feldprüfung fehlgeschlagen.': 'FileDB V1 field verification failed.',
    'Unerwartete Änderung ausserhalb des FileDB-V1-Namensfeldes.': 'Unexpected change outside the FileDB V1 name field.',
    'Ungültige FileDB-Wörterbücher.': 'Invalid FileDB dictionaries.',
    'Feldposition nicht gefunden.': 'Field position not found.',
    'FileDB-Feldprüfung fehlgeschlagen.': 'FileDB field verification failed.',
    'Unerwartete Änderung ausserhalb des Namensfeldes.': 'Unexpected change outside the name field.',
    'Unbekanntes Namensfeld.': 'Unknown name field.',
    'Spielername im Spielzustand nicht eindeutig zuordenbar; keine Änderung ausgeführt.': 'Cannot identify the player name unambiguously in the game state; no change was made.',
    'RDA-Metadaten wurden verändert.': 'RDA metadata was changed.',
    'Unbeteiligtes Save-Mitglied wurde verändert.': 'An unrelated save member was changed.',
    'Namensprüfung fehlgeschlagen.': 'Name verification failed.',
    'Prüfung des Spielernamens fehlgeschlagen.': 'Player name verification failed.',
    'Der Quellordner wurde zwischenzeitlich verändert.': 'The source folder has changed in the meantime.',
    'Ein Save wurde vor der Ordnerumbenennung verändert.': 'A save changed before the folder rename.',
    'Der neue Profilordner existiert bereits.': 'The new profile folder already exists.',
    'Ein Save wurde während der Ordnerumbenennung verändert.': 'A save changed during the folder rename.',
    'Umbenannter Spielstand konnte nicht bestätigt werden.': 'Could not verify the renamed save.',
    'Wiederherstellung unvollständig. Sicherung: {backup}. {error}': 'Restoration incomplete. Backup: {backup}. {error}',
    'Abgebrochen; Originale erhalten. Sicherung: {backup}. {error}': 'Cancelled; originals preserved. Backup: {backup}. {error}',
    'Verknüpfte Quelldateien werden nicht bearbeitet.': 'Linked source files cannot be edited.',
    'Namensänderung ohne Verschieben benötigt einen neuen Spielernamen.': 'An in-place name change requires a new player name.',
    'Ein neuer benachbarter Profilordner ist erforderlich.': 'A new sibling profile folder is required.',
    'Der Profilordner enthält weitere Dateien oder Unterordner.': 'The profile folder contains extra files or subfolders.',
    'Der Profilordner enthält weitere Dateien oder Unterordner. Unterordner werden nicht übernommen; bitte einzelne Saves direkt im Profil wählen.':
        'The profile folder contains extra files or subfolders. Subfolders are not transferred; select individual saves directly inside the profile instead.',
    'Mehrdeutige Dateinamen.': 'Ambiguous filenames.',
    'Zieldatei existiert bereits; nichts wurde überschrieben.': 'A destination file already exists; nothing was overwritten.',
    'Die Sicherung muss ausserhalb des Spielkontos liegen.': 'The backup must be outside the game account.',
    'Quelldatei wurde während der Vorbereitung geändert.': 'A source file changed during preparation.',
    'Sicherungsprüfung fehlgeschlagen.': 'Backup verification failed.',
    'Quelldatei wurde zwischenzeitlich geändert.': 'A source file has changed in the meantime.',
    'Quelle wurde vor der Namensänderung verändert.': 'A source changed before the name edit.',
    'Ausgabedatei konnte nicht bestätigt werden.': 'Could not verify the output file.',
    'Quelle wurde vor dem Verschieben geändert.': 'A source changed before the move.',
    'Keine {extension}-Saves gefunden.': 'No {extension} saves found.',
    '«Namen ändern» aktivieren und einen Namen eingeben.': 'Enable the name-change option and enter a name.',
    'Bitte einen Sicherungsordner angeben.': 'Choose a backup folder.',
    'Sicherung ausserhalb des Spielkontos wählen.': 'Choose a backup folder outside the game account.',
    'Für die Ordnerumbenennung einen neuen Profilnamen angeben.': 'Enter a new profile name to rename the folder.',
    'Eine Zieldatei existiert bereits. Bitte ein anderes Profil wählen.': 'A destination file already exists. Choose a different profile.',
}


def error_text(language, message):
    """Translate whole known diagnostics, leaving unknown/system messages intact."""
    if language == 'de':
        return message
    if message in ERRORS:
        return ERRORS[message]
    for source, target in ERRORS.items():
        if '{' not in source:
            continue
        pattern = re.escape(source)
        for name in re.findall(r'\{(\w+)\}', source):
            pattern = pattern.replace(re.escape('{' + name + '}'), '(?P<' + name + '>.+?)')
        matched = re.fullmatch(pattern, message, re.S)
        if matched:
            values = matched.groupdict()
            if 'error' in values:
                values['error'] = error_text(language, values['error'])
            return target.format(**values)
    return message
