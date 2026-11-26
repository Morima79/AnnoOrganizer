# Desktop interface

[English](desktop.md) · [Deutsch](desktop.de.md) · [README](../README.md)

The desktop preview configures and runs the existing Anno 117, 1800 and 1404 tools. It can run as a portable Windows x64 package or from source with Python 3.11 or later including Tkinter. Existing console launchers and separately copied game folders remain functional.

## Portable Windows package

Extract the entire ZIP built by `scripts/build_desktop.py` and open **AnnoOrganizer.exe**. Keep `_internal/` beside it. Python and runtime packages are included; the target machine needs neither Python, pip nor an installer. The package targets Windows 10/11 x64. It is unsigned, so Windows may show a SmartScreen reputation warning. Check the source and SHA-256 checksum; signing is a separate step. No security barriers are bypassed and no automatic updates are installed.

The executable uses the same worker through `--worker --game ...` and stores personal data outside internal resources. `BUILD.json` records the source commit, package version and resource hashes; `THIRD-PARTY-NOTICES.txt` and `licenses/` provide license texts. The [existing release workflow](publishing.md) now includes the Windows build for future publication. A local build is not a published release.

## Source launch and first run

Run from the repository root:

```powershell
.\Launch.cmd --gui
```

The launcher prepares the Python environment and required packages as before. With an existing environment, you can also run:

```powershell
.\.venv\Scripts\python.exe launch.py --gui
```

Opening a game for the first time automatically creates its `settings.json`. Windows supplies the actual Documents folder, including folder redirection; Steam/Ubisoft registrations supply the 117/1800 installation where available. Standard save and stamp folders under Documents are configured. For 1404, existing `Savegames` folders for the base game and Venice are included. New outputs go to `Documents/AnnoOrganizer/Anno 117/`, `Anno 1800/` or `Anno 1404/`, with `reports/`, `stamps/` and `logs/` subdirectories. Input folders are never created or modified.

Choose the desired game on the left, review detected paths and press **Generate**. **Maps and Excel** is selected without a saved choice. Missing installations or input folders must be supplied in the fields; the error identifies the affected path. Existing settings and selected external files remain unchanged.

**Bundled demo** remains a separate action that reads bundled examples only. Starting it shows a notice with the demo output folder and explains that personal galleries will not be updated. Status explicitly says **Generating demo** during the run. Normal exports and **Update all galleries** do not show this notice. Anno 117 and 1800 require their game resources for demos too. The Anno 1404 demo requires no game installation. Demo outputs stay under `<output>/demo/`.

The absolute output destination is displayed before starting. The window stays responsive while processing; inputs, game/language selection, tabs and other action buttons are disabled. **Cancel** and read-only access to existing galleries remain available. Galleries open in the default browser. No private data is uploaded.

**Open galleries** opens all existing map and stamp galleries for this game in the displayed output destinations, including separate demo outputs. The small arrow beside it offers individual selection. Existing pages are available immediately after restarting and after failed or cancelled jobs. Availability is checked periodically; it does not indicate that the current job succeeded.

The gallery button and selection arrow share one outline with a subtle inner divider. The left side opens all available galleries; the right side selects an individual gallery. The arrow area is compact with a centred arrow. If Windows cannot open a gallery in the default browser, the GUI shows its path for opening the file directly.

The expanded gallery selector uses the same dark background and light text as the interface. Its highlighted entry is gold.

The **Open galleries after generation** checkbox opens newly generated galleries in the default browser after a successful run, including demos. For **Update all galleries**, pages open after the entire successful batch finishes. Failure, cancellation or closing the GUI prevents automatic opening. The option is initially disabled and is saved in `gui.json` for the next launch.

## Edit and reuse settings

**Update all galleries** checks Anno 117, 1800 and 1404 with one click and updates their usable galleries: up to three map galleries and two stamp galleries. It uses the normal configured inputs and output destinations, independently of the selected individual action. Loaded unsaved drafts are included; saved configurations are read for games that have not been opened yet. Personal configuration files are not saved by this operation.

Before the first job, the GUI checks every required input, game resource and output destination. Missing installations, missing 1404 save folders or games without input folders are skipped. If only the save or stamp folder is missing for 117/1800, the other gallery can still be updated. A completion notice lists successfully updated galleries and games or individual galleries that are absent or not configured, with reasons. If no game is usable, setup information appears without starting a worker. This supports users who only use one game.

Other configuration errors or overlapping destinations prevent startup and are listed with game identifiers. Planned jobs run sequentially; status shows the job number, game and action. Failure or **Cancel** stops remaining jobs. Already published galleries are retained; the sequence is not one transaction. The summary with individual results and skipped games is stored in `<GUI data directory>/logs/all-games-last-run.json`. Galleries remain accessible through their respective game views.

Actions appear in this order: **Maps and Excel**, **Stamp gallery**, **Bundled demo**. The last selected action is saved immediately per game in `gui.json` and restored when switching games or restarting. Saving the personal configuration is not required. Without a valid saved choice, **Maps and Excel** is selected; Anno 1404 has no stamp gallery.

- **Use file**: Select an existing `settings.json` and review resolved destinations. The file stays in place; only **Save** modifies it. Relative paths remain relative to its directory.
- **Import copy**: Select the source and review the import destination and resolved paths. Confirming saves the copy. Known relative paths and implicit output defaults retain their original destinations. Unknown keys are preserved. The source remains unchanged; source and destination must be different files. Replacing an existing destination requires additional confirmation and creates a backup.
- **Default file**: Return to this game's saved GUI configuration or create a missing default file with automatically detected values. An external file selection is replaced only when the selected default file is saved.
- **Reload**: Read the current file again. Discarding unsaved changes requires confirmation.
- **Save**: Write displayed values to the file shown under **Settings file**. Previous content is backed up under `backups/` beside that file. If another application changed it since loading, reload instead of overwriting.

The **Inputs** and **Outputs and time zone** tabs contain game-specific fields. For Anno 1404, each save folder has its own single-line path field without wrapping; **Add folder** and **Remove** manage multiple folders. Empty optional output fields use existing default subdirectories. Scrollbars keep fields accessible in small windows. For keys and placeholders, see [settings documentation](settings.de.md) (German).

**Browse** opens the resolved path from that field. Relative paths use the configuration directory; placeholders such as `${DOCUMENTS}` are expanded. For destinations that do not exist yet, the nearest existing parent opens. Game installation browsing displays EXE files: select the game's executable, including one inside a `Bin` subdirectory. The GUI locates and checks its matching `maindata` folder and enters that path. Game or `maindata` folders can still be entered directly.

**Time zone** controls report timestamps and normally needs no changes. `Europe/Zurich` suits Switzerland, including daylight saving time. Other IANA time zones remain configurable for other regions or existing configurations. Anno 1404 map galleries use local Windows time for file timestamps; statistics use the configured time zone.

**Generate uses displayed values without saving the personal configuration.** Each job receives a temporary configuration copy with the same resolved path destinations. That copy is removed after the process exits. Demo runs stay under `<output>/demo/` and ignore separate personal report, stamp and log destinations.

New GUI files are created under `%LOCALAPPDATA%/AnnoOrganizer/<game>/settings.json`, with new outputs in `AnnoOrganizer/Anno <number>/` under the detected Documents folder. GUI preferences are stored in `gui.json` alongside game directories. Upgrades never overwrite existing settings or personal paths. Console launchers retain their existing defaults. To explicitly choose another GUI data directory:

```powershell
.\Launch.cmd --gui --gui-data-dir "D:/AnnoOrganizer Data"
```

Only one interface runs per GUI data directory. A second launch shows a notice instead of writing competing preferences. The OS-owned lock is released after a process crash too. Separate GUI data directories remain possible; existing output locks still protect shared destinations.

You can also open an external configuration directly:

```powershell
.\Launch.cmd --gui --game anno1404 --config "D:/My Annos/1404/settings.json"
```

## Language, status and cancellation

Main, About and Logs window positions, sizes and maximized states are saved in `gui.json` and restored when reopened. Minimized states are not restored; windows are moved into a reachable screen area after monitor changes. About and Logs belong to the main window and stay above it. The selected tab and active language are highlighted in gold; tab sizes remain unchanged when switching.

On first launch, the preferred Windows display language selects the interface: `de`, `de-DE`, `de-CH` or `de-AT` selects German; other languages or detection failures select English. **DE/EN** can be changed when no job is running; the saved manual choice takes precedence on subsequent launches. Inputs, game, action and selected tab survive language changes. HTML galleries keep their independent language choice; raw data, paths and logs are not translated.

Status names the current processing step. The moving indicator shows activity rather than an estimated percentage. **Cancel** requests cooperative cancellation. An active parser or publication may finish before the next safe boundary. Closing during processing asks whether to cancel. **No** lets the job continue; **Yes** requests cancellation and waits for process completion before closing. Unsaved settings are then offered for saving as during normal closing. Force quitting through Task Manager is not an orderly cancellation.

Success is displayed only when the worker completion and process exit code agree. Failure or cancellation reports possible partial output. **Logs** shows diagnostics and action logs. **About** shows development version, license information and a link to GitHub releases; no automatic update takes place.

Each game's latest job and error details are saved to `<GUI data directory>/logs/<game>-last-run.json`. Errors that occur before generator logs start remain readable after closing the GUI. These files may contain personal paths and stay local.

## Current limitations

This is a development build. The extracted executable was locally tested with all five demo galleries and installed 117/1800 game resources, from a different working directory with unusable Python search paths. DE/EN, state transitions, configuration import and a 1404 GUI demo were checked separately. Independent acceptance on a fresh Windows system without development tools remains outstanding; altered Python search paths do not fully replace that check. GUI, CLI and direct generator calls now reserve their actual output trees, including nested paths, logs and stamp caches, across processes. OS-owned locks release reservations after a process crash too. Stamp galleries and resource caches are generated in working copies and published only after successful processing. Cancellation before publication preserves existing contents; publication failure triggers rollback. If another application blocks rollback too, backup copies and `RECOVERY.json` are retained at the location reported in the log. Original saves and stamps remain read only. Overlapping stamp/cache destinations and links inside these output trees are rejected. Multiple demo actions do not form one transaction; actions completed before a later failure may remain published.

Unofficial project by Morima79, unaffiliated with Ubisoft. Use at your own risk under the [MIT license](../LICENSE). Further architecture and acceptance details: [GUI proposal](desktop-gui.md).
