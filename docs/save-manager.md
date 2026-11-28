# Anno – Save Manager (development version)

**[Illustrated beginner guide](save-manager-guide.html?lang=en)** · [Open online](https://morima79.github.io/AnnoOrganizer/save-manager-guide/?lang=en)

Standalone Windows application for Anno 117 and Anno 1800 save transfers, complete profile-folder renaming and optional praetor/player-name changes. Anno 117 uses `.a8s`; Anno 1800 uses `.a7s`. Running the EXE does not require Python or an installed game. Keep the complete application folder, including `_internal/`. Part of [AnnoOrganizer by Morima79](https://github.com/Morima79/AnnoOrganizer), MIT licensed; use at your own risk. The interface offers a saved DE/EN language choice.

## Language

Versions from v0.1.22 provide **DE / EN** at the top right, matching the Organizer. On first launch, the Windows display language selects German for German Windows and English otherwise. A saved choice takes precedence afterwards. Labels, selection-dialog titles, confirmations and application messages switch together; personal names, paths and values read from saves remain unchanged. Switching preserves the selection and inputs and is blocked during editing. Native Windows file-dialog buttons and operating-system errors continue to follow the Windows language. Published packages through v0.1.21 still have the German interface.

## Game selector

Download the complete Windows package and its SHA-256 checksum from the [latest release](https://github.com/Morima79/AnnoOrganizer/releases/latest). New packages use the name `AnnoSaveManager-<version>-windows-x64.zip`. Extract the ZIP before opening `AnnoSaveManager.exe`.

The top ComboBox switches between Anno 117 and Anno 1800. Labels use “Prätor” or “Spielername” accordingly. Account roots are remembered separately per game. Switching clears pending save selections and inputs and is disabled while processing.

## Usage

1. Close the selected game and let any cloud synchronisation finish.
2. Open `AnnoSaveManager.exe`. Select individual saves from one profile folder or a complete profile folder. Do not select the account folder or any `accountdata` files.
3. The account is recognised using `accounts/<account>/accountdata.a8s` (117) or `accountdata.a7s` (1800). Enter the **Ziel-Profilname** (destination profile name), or choose an existing profile from the same account using **…**. New profiles are created directly under that account. Sources inside profile subfolders, nested destinations and other accounts are rejected. File and folder dialogs always start at the discovered or last-used account root, including after successful actions. Initial discovery uses the actual Windows Documents location; the choice is stored in `%LOCALAPPDATA%/AnnoOrganizer/save-manager.json`. With multiple accounts and no saved choice, browsing starts at the parent `accounts` folder. Choose a durable backup folder outside the game account. Backups default to `%LOCALAPPDATA%/AnnoOrganizer/save-backups/`.
4. **Kopieren** copies and retains the source. **Verschieben** removes source files after verified publication. **Profilordner umbenennen** uses the existing **Ziel-Profilname** field directly, without a second name dialog. Selecting a source prefills and selects `<old name> - Neu` for quick replacement. Select a complete profile folder and an unused sibling name; additional files or subfolders cause rejection. The directory itself is renamed, retaining Windows/OneDrive read-only folder attributes without clearing them. Prepared profile-field updates are then written. On failure, original file contents and the directory name are restored using the verified backup.
5. Optionally enable **Prätornamen ändern** (117) or **Spielernamen ändern** (1800) and enter the desired name. Copy, move and profile-rename actions apply it to all selected saves. **Nur Prätor ändern** / **Nur Spielername ändern** edits those saves at their existing location, ignoring the transfer destination name. Both profile fields are also aligned with the actual current folder. Unselected older saves retain their previous names. Praetor editing rejects ambiguous or multiple-player mappings. Review source, destination, storage profile and praetor in the confirmation. Normal transfers set both internal profile names to the destination folder name, preserving the internal save name. Transfers never overwrite existing destination files; any collision rejects the entire operation. Only the explicit **Nur Prätor ändern** / **Nur Spielername ändern** action replaces selected source files after a verified backup. Success clears the selection, destination name, praetor text and checkbox, while retaining the browsing root. A path entered into the destination-name field receives a plain explanation of the required flat profile structure.
6. A verified ZIP backup of selected originals with a SHA-256 manifest is created before publication or source removal. Modification and Windows creation times are preserved. On failure the application attempts rollback; the backup remains available. To restore manually, extract original saves into the source folder recorded in the manifest.
7. Load a transferred save in the game, save manually and verify the output folder. Cloud synchronisation can restore old profiles; this tool does not delete profiles from the game or cloud.

Disposable editing and build files stay outside configured OneDrive roots. Backups are durable outputs and are never deleted automatically. This development version accepts FileDB V1 and V2 inside the known four-member RDA V2.2 layout (`meta.a7s`, `header.a7s`, `gamesetup.a7s`, `data.a7s`) and rejects other layouts. Without a praetor change, `data.a7s` remains byte-identical. With a praetor change, only the uniquely matched `CustomCompanyName` is replaced there; other data fields are preserved. `accountdata.a8s` or `accountdata.a7s` is used only as an account marker and is never modified. In-place editing writes verified files directly; after a process or power interruption, restore originals from the ZIP backup if necessary.

## Running-game check

Before copying, moving, profile renaming or name edits, the tool checks whether the selected game is still running. If so, it stops the action with an explanatory message, retaining the selection and inputs. Close the game, let cloud synchronisation finish, then retry the same action. It checks again immediately before writing. Editing is also blocked if Windows cannot provide the process list. This check does not prevent starting the game during editing and does not detect active cloud synchronisation.

## Change names in every save of a profile folder

1. Select the game and click **Alle Namen im Ordner …**.
2. Choose a direct profile folder. All matching saves are listed; unrelated files are retained. Subfolders cause rejection so nested saves are not silently skipped.
3. Enter the new praetor/player name and execute **Nur Prätor ändern** / **Nur Spielername ändern**. The name checkbox is already enabled for this selection.
4. All selected originals are backed up together before writing. Each save receives the name in all three confirmed fields; filenames, internal save names and other game-state fields are preserved. Both profile fields are aligned with the current folder. Errors roll back the whole operation; the ZIP backup permits recovery after a process or power interruption.

Selecting **Ganzer Profilordner** and then the name-only action also edits every listed save. Unselected older saves retain their names. Multiple human players or ambiguous mappings are rejected rather than guessed.

## Anno 1800 fields and validation

| Save member | Exact field | Encoding |
| --- | --- | --- |
| `header.a7s` | `CorporationProfile/GameSetup/SavegameFolderW` | UTF-16 LE |
| `gamesetup.a7s` | `GameSetupManager/SavegameFolderW` | UTF-16 LE |
| `header.a7s` | `CorporationProfile/GameSetup/Peers/Peer/Values/Available/ParticipantType/Values/Human/CompanyName` | UTF-8 |
| `gamesetup.a7s` | `GameSetupManager/Peers/Peer/Values/Available/ParticipantType/Values/Human/CompanyName` | UTF-8 |
| `data.a7s` | `MetaGameManager/MetaGameObjectManager/MetaObjectMap/[]/MetaProfile/CustomCompanyName/[]` | UTF-16 LE |

`meta.a7s/CorporationSaveGameName` contains the saved name including `.a7s` in inspected 1800 saves and is preserved during transfers/name edits. Older saves use FileDB V1 with variable field lengths and one dictionary footer offset; newer saves use V2. Both are rebuilt with full field-level validation and byte-preservation checks outside replaced values. Some local saves still contain earlier profile names despite already residing in renamed folders.

Validation covers synthetic V1/V2 fixtures, shorter/longer Unicode names, backups/rollback and real local save copies. The four application cases below were also verified through the EXE and inside Anno 1800.

## Appearance and window position

The window uses the Organizer dark palette, gold accents, Segoe UI, bright insertion cursors and the same application icon. The table, selection colours and scrollbar match the interface.

Closing saves position, size and maximised state in `%LOCALAPPDATA%/AnnoOrganizer/save-manager.json`. Normal bounds are retained when maximising; minimised windows reopen normally. If a previous monitor is disconnected, the window is moved to a reachable work area. Saving window bounds preserves the remembered account root and other preferences. The standalone window-state copy in `anno117/tools/anno_save_ui.py` follows the Organizer implementation in `desktop/window_state.py`.

## Known and unresolved Anno 117 name fields

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

## Shared sources

Canonical modules live in `templates/save_manager/`. `python scripts/sync_save_manager.py` updates code, icon and guides in the independently usable `anno117/` and `anno1800/` directories; `--check` verifies the copies. Edit canonical modules only.

## Additional local Anno 1800 validation

A real small FileDB V1 save copy was moved individually, renamed as a complete profile folder, then edited in place alongside a second copy to change both player names. The source control copy and original remained unchanged. A 12.3 MB save with approximately 295 MB of uncompressed world state was also verified with a changed profile and Unicode player name. Field comparisons stream through the data without retaining a catalogue of all world-state fields. Both checks concern files and do not replace an in-game test.

## Anno 1800 in-game test on 28 November 2026

The four actions were performed through the Windows EXE and then checked with Computer Use in Anno 1800 (18.4.1412158). Seven clearly labelled copies of an early free game, about 0.53 MB each, were used as inputs, including an unchanged control copy.

| Test | Result after EXE action | In-game check | Manual save suggestion |
| --- | --- | --- | --- |
| V: single save | `V_Verschieben.a7s` in `AO18_V_Ziel`; `V_Bleibt.a7s` retained in source profile | Loaded and saved again | `AO18 TEST V` |
| U: entire profile folder | `AO18_U_Alt` renamed to `AO18_U_Neu`; both saves retained | Both visible and loaded, one new result saved | `AO18 TEST U` |
| P: individual player name | `P_Einzeln.a7s` in `AO18_P_Test`, player `AO18 P Neu` | New name in loading menu, loaded and saved again | `AO18 P Neu` |
| A: all player names in folder | `A_Alle1.a7s` and `A_Alle2.a7s` in `AO18_A_Alle`, player `AO18 A Alle Neu` | Both visible and loaded, one new result saved | `AO18 A Alle Neu` |

In these four variants the manual dialog suggested the player name. All four newly written saves appeared in their intended profile folders, with both internal profile fields still matching the folder. For P and A the changed player name also persisted in the newly saved world state. A separate visual name display within the game world was not checked. Individual name fields were not isolated against one another in this test.

The older source save triggered the normal DLC activation and skyscraper maintenance dialogs; their existing defaults were confirmed only on test copies. The game also created a `Reich der Lüfte.a7s` backup. SHA-256 checks confirmed that the original and V control copy remained unchanged.
