# Anno 117 – Save Manager (development version)

Standalone Windows application for Anno 117 save transfers, complete profile-folder renaming and optional praetor-name changes. Anno 1800 saves are not edited. Running the EXE does not require Python or an installed game. Keep the complete application folder, including `_internal/`. Part of [AnnoOrganizer by Morima79](https://github.com/Morima79/AnnoOrganizer), MIT licensed; use at your own risk. The application currently uses German UI text.

## Game selector (prepared)

The top ComboBox offers Anno 117, Anno 1800 and Anno 1404. Only Anno 117 reading and editing are currently enabled. Choosing 1800 or 1404 clears the selection and inputs, disables actions and displays the preparation status. The selection persists across restarts. Switching is disabled during processing. The remembered Anno 117 account root is retained; other games' saves are not opened using the 117 editor.

## Usage

1. Close Anno 117 and let any cloud synchronisation finish.
2. Open `Anno117SaveManager.exe`. Select individual saves from one profile folder or a complete profile folder. Do not select the account folder or `accountdata.a8s`.
3. The account is recognised using `accounts/<account>/accountdata.a8s`. Enter the **Ziel-Profilname** (destination profile name), or choose an existing profile from the same account using **…**. New profiles are created directly under that account. Sources inside profile subfolders, nested destinations and other accounts are rejected. File and folder dialogs always start at the discovered or last-used account root, including after successful actions. Initial discovery uses the actual Windows Documents location; the choice is stored in `%LOCALAPPDATA%/AnnoOrganizer/save-manager.json`. With multiple accounts and no saved choice, browsing starts at the parent `accounts` folder. Choose a durable backup folder outside the game account. Backups default to `%LOCALAPPDATA%/AnnoOrganizer/save-backups/`.
4. **Kopieren** copies and retains the source. **Verschieben** removes source files after verified publication. **Profilordner umbenennen** uses the existing **Ziel-Profilname** field directly, without a second name dialog. Selecting a source prefills and selects `<old name> - Neu` for quick replacement. Select a complete profile folder and an unused sibling name; additional files or subfolders cause rejection. The directory itself is renamed, retaining Windows/OneDrive read-only folder attributes without clearing them. Prepared profile-field updates are then written. On failure, original file contents and the directory name are restored using the verified backup.
5. Optionally enable **Prätornamen ändern** and enter the desired name. Copy, move and profile-rename actions apply it to all selected saves. **Nur Prätor ändern** edits those saves at their existing location, ignoring the transfer destination name. Both profile fields are also aligned with the actual current folder. Unselected older saves retain their previous names. Praetor editing rejects ambiguous or multiple-player mappings. Review source, destination, storage profile and praetor in the confirmation. Normal transfers set both internal profile names to the destination folder name, preserving the internal save name. Transfers never overwrite existing destination files; any collision rejects the entire operation. Only the explicit **Nur Prätor ändern** action replaces selected source files after a verified backup. Success clears the selection, destination name, praetor text and checkbox, while retaining the browsing root. A path entered into the destination-name field receives a plain explanation of the required flat profile structure.
6. A verified ZIP backup of selected originals with a SHA-256 manifest is created before publication or source removal. Modification and Windows creation times are preserved. On failure the application attempts rollback; the backup remains available. To restore manually, extract original saves into the source folder recorded in the manifest.
7. Load a transferred save in the game, save manually and verify the output folder. Cloud synchronisation can restore old profiles; this tool does not delete profiles from the game or cloud.

Disposable editing and build files stay outside configured OneDrive roots. Backups are durable outputs and are never deleted automatically. This development version accepts the known four-member RDA V2.2 layout (`meta.a7s`, `header.a7s`, `gamesetup.a7s`, `data.a7s`) and rejects other layouts. Without a praetor change, `data.a7s` remains byte-identical. With a praetor change, only the uniquely matched `CustomCompanyName` is replaced there; other data fields are preserved. `accountdata.a8s` is used only as an account marker and is never modified. In-place editing writes verified files directly; after a process or power interruption, restore originals from the ZIP backup if necessary.

## Appearance and window position

The window uses the Organizer dark palette, gold accents, Segoe UI, bright insertion cursors and the same application icon. The table, selection colours and scrollbar match the interface.

Closing saves position, size and maximised state in `%LOCALAPPDATA%/AnnoOrganizer/save-manager.json`. Normal bounds are retained when maximising; minimised windows reopen normally. If a previous monitor is disconnected, the window is moved to a reachable work area. Saving window bounds preserves the remembered account root and other preferences. The standalone window-state copy in `anno117/tools/anno_save_ui.py` follows the Organizer implementation in `desktop/window_state.py`.

## Known and unresolved name fields

| Save member | Exact field | Evidence |
| --- | --- | --- |
| `header.a7s` | `CorporationProfile/SavegameProfileDisplayName` | The mismatched H-test header name was replaced by the gamesetup value when saved again. The differing header value did not determine the observed suggestion. |
| `gamesetup.a7s` | `GameSetupManager/SavegameProfileDisplayName` | Determined the output profile folder and the base of the suggested manual save name in the inspected variants. |
| `meta.a7s` | `CorporationSaveGameName` | Stores the saved name; inspected autosaves contained `Autosave ` without a number. The differing M-test value did not determine the next manual save suggestion. |

`SetupSlots/Slot/CompanyName` is a separate player/company name. Optional praetor editing replaces both header/gamesetup values (UTF-8) and the matching `CustomCompanyName` in `data.a7s` (UTF-16 LE). Exactly one consistent player mapping is required; ambiguous or inconsistent names are rejected. Its encoding differs from the three UTF-16 LE fields above. The chat **“Binärdateien analysieren”** records a successful in-game test on 31 October 2026: `OrdnerTest.a8s` was saved in the desired folder after changing both profile fields. Their individual responsibilities for folders and suggested manual save names were not isolated.

On 28 November 2026 the three fields were read again from six current local saves. Shorter and longer profile names and an independent meta name were tested on in-memory copies, keeping `data.a7s` byte-identical. This is structural validation, not a new in-game test.

## In-game results from 28 November 2026

The user loaded four separate copies of the same campaign. Distinct praetor labels were set in both `SetupSlots/Slot/CompanyName` fields (UTF-8) and in `MetaGameManager/MetaGameObjectManager/MetaObjectMap/[]/MetaParticipant/CustomCompanyName/[]` in `data.a7s` (UTF-16 LE). Filenames were `AO117_Datei_K/H/G/M.a8s`, independent of the profile/meta fields under investigation. Resulting saves were subsequently inspected.

| Variant | In-game suggestion | Actual output file | Both profile fields in the new save |
| --- | --- | --- | --- |
| K: both profile fields `AO117_Kontrolle` | `AO117_Kontrolle 1` | `AO117_Kontrolle/AO117_Kontrolle 1.a8s` | `AO117_Kontrolle` |
| H: header `AO117_Headerwert`, gamesetup `AO117_H` | User reported `AO117_H1`; the saved name includes a space | `AO117_H/AO117_H 1.a8s` | `AO117_H` |
| G: header `AO117_G`, gamesetup `AO117_Setupwert`, file in folder `AO117_G` | No readable suggestion; manual saving dialog remained blank/stuck | `AO117_Setupwert/Session Backup.a8s`; no manual result | `AO117_Setupwert` |
| M: both profile fields `AO117_M`, meta `AO117_Metawert` | `AO117_M 1` | `AO117_M/AO117_M 1.a8s` | `AO117_M` |

The user reported filenames `AO117_Datei_K/H/G/M` in the loading menu. Neither the distinct praetor labels nor the differing M meta name determined the observed manual suggestion. Newly written `CorporationSaveGameName` values match the actual saved filenames without their extension; the G backup contains `Session Backup`.

These results support `GameSetupManager/SavegameProfileDisplayName` as the controlling source for output profile and suggested save name in these tests. The H header value was normalised to it on saving. The numbering algorithm was not investigated. The first G session backup alone is not evidence of successful manual saving. Normal transfers continue to set both profile fields to the actual destination folder name.

### G follow-up with a matching folder

A byte-identical copy of the original G save was placed at `AO117_Setupwert/AO117_Datei_G.a8s`. Its header value remained `AO117_G`, gamesetup remained `AO117_Setupwert`, and meta remained `Test2`. The old copy was only renamed to `AO117_Datei_G_AlterOrdner.a8s` in its original folder; both copies have the same SHA-256 digest.

After restarting, the user reported a working manual save dialog suggesting `AO117_Setupwert 1`. The resulting manual save is `AO117_Setupwert/AO117_G_Ergebnis_OrdnerP.a8s`. Both profile fields now contain `AO117_Setupwert`; `CorporationSaveGameName` contains `AO117_G_Ergebnis_OrdnerP`. The praetor remains `AO117 Praetor: G`.

The follow-up therefore succeeds with a differing header profile when the physical folder matches gamesetup. This supports the folder mismatch as the cause of the initial issue, without conclusively proving causation: the destination folder and a session backup already existed during the follow-up, and other conditions were not isolated.

The originally requested result name was too long. The user reported that the manual save dialog only accepted `AO117_G_Ergebnis_OrdnerP`; the saved name has 24 ASCII characters. This establishes an observed 24-character input limit in that dialog, not a general format limit for profile folders or a tested Unicode-name limit. Keep further manual test names short.

## Isolated in-game experiment

The following experiment records the earlier field tests. Normal EXE actions no longer expose mismatched profile values; both are set to match the destination folder. Separate technical test copies can be created through `anno_save_editor.transform(..., overrides=...)`. Use a fresh, uniquely named destination folder for every variant and start each variant from the same original save. Keep the copied filename unchanged.

| Variant | header profile | gamesetup profile | meta save name |
| --- | --- | --- | --- |
| Control | Control folder name | Control folder name | Original save name |
| H | `Test_Header_117` | H test folder name | Original save name |
| G | G test folder name | `Test_Setup_117` | Original save name |
| M | M test folder name | M test folder name | `Test_Meta_117` |

Load the control first. Restart the game for each variant, load that specific copy, open manual saving and **record the suggested name before typing anything**. Save under a unique name and inspect the actual output folder. Read all three names from the new save using this tool. H/G may create folders different from the copied save's folder; that is part of the result. Do not derive variants from newly saved test results.

Record variant, source file, three input names, displayed profile name, suggested manual save name, actual output folder and three names in the newly saved file. Assign individual field responsibilities only after those observations.

## Source and build

Run: `.venv\Scripts\python.exe anno117/tools/manage_saves.py`.

Build a Windows development package: `.venv\Scripts\python.exe scripts/build_save_manager.py`, using the existing `requirements-build.txt`. Output: `dist/save-manager-dev/`. This does not publish, commit or tag anything. Use a new `--output` directory for subsequent builds. The builder checks GUI startup, profile renaming, in-place praetor editing and nested-target rejection on isolated copies of an approved demo save. It includes a ZIP, checksum, source hashes and licence notices. The development executable is unsigned.

## Application tests with small save copies

On 28 November 2026 separate copies of an early manual save (about 0.4 MB) were tested and resulting files inspected:

- V: One save moved to `AO117_V_Ziel`, retaining a control copy in the source profile. The user confirmed loading, suggestion `AO117_V_Ziel 1` and saving as `AO117_V_OK`.
- U: Profile renamed to `AO117_U_Neu`; the old folder is absent and both original saves have matching profile fields in the new folder. The user confirmed both saves were visible, suggestions `AO117_U_Neu 1`, and saving as `AO117_U_OK`.
- P: Praetor renamed in place to `AO117 Praetor Neu`. Both profile fields remain `AO117_P_Test`; all three praetor fields in `P_Test` and `AO117_P_OK` contain the new name. The user confirmed the loading-menu name, suggestion `AO117_P_Test 1` and saving as `AO117_P_OK`. A separate visual confirmation of the in-game praetor name was left blank.
- Nested-folder rejection was confirmed in the UI. Its message now explains that only a profile name is allowed; successful actions also clear the praetor controls.
