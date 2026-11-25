# Desktop interface

[English](desktop.md) · [Deutsch](desktop.de.md) · [README](../README.md)

The desktop preview configures and runs the existing Anno 117, 1800 and 1404 tools. It can run as a portable Windows x64 package or from source with Python 3.11 or later including Tkinter. Existing console launchers and separately copied game folders remain functional.

## Portable Windows package

Extract the entire ZIP built by `scripts/build_desktop.py` and open **AnnoOrganizer.exe**. Keep `_internal/` beside it. Python and runtime packages are included; the target machine needs neither Python, pip nor an installer. The package targets Windows 10/11 x64. It is unsigned, so Windows may show a SmartScreen reputation warning. Check the source and SHA-256 checksum; signing is a separate step. No security barriers are bypassed and no automatic updates are installed.

The executable uses the same worker through `--worker --game ...` and stores personal data outside internal resources. `BUILD.json` records the source commit, package version and resource hashes; `THIRD-PARTY-NOTICES.txt` and `licenses/` provide license texts. The [existing release workflow](publishing.md) now includes the Windows build for future publication. A local build is not a published release.

## Source launch and first demo

Run from the repository root:

```powershell
.\Launch.cmd --gui
```

The launcher prepares the Python environment and required packages as before. With an existing environment, you can also run:

```powershell
.\.venv\Scripts\python.exe launch.py --gui
```

Choose a game on the left, leave **Bundled demo** selected and press **Generate**. Example inputs are already configured. Anno 117 and 1800 require their game resources; an empty installation field uses automatic detection where possible. Otherwise select the game folder or `maindata`. The Anno 1404 demo requires no game installation. Demos read bundled examples only.

The absolute output destination is displayed before starting. The window stays responsive while processing; game selection and configuration changes are disabled. After success, use **Open galleries** and **Output folder**. Galleries open in the default browser. No private data is uploaded.

## Edit and reuse settings

- **Use file**: Select an existing `settings.json` and review resolved destinations. The file stays in place; only **Save** modifies it. Relative paths remain relative to its directory.
- **Import copy**: Select the source and review the import destination and resolved paths. Confirming saves the copy. Known relative paths and implicit output defaults retain their original destinations. Unknown keys are preserved. The source remains unchanged; source and destination must be different files. Replacing an existing destination requires additional confirmation and creates a backup.
- **Default file**: Return to this game's saved GUI configuration or load new defaults into memory. An external file selection is replaced only when the selected default file is saved.
- **Reload**: Read the current file again. Discarding unsaved changes requires confirmation.
- **Save**: Write displayed values to the file shown under **Settings file**. Previous content is backed up under `backups/` beside that file. If another application changed it since loading, reload instead of overwriting.

The **Inputs** and **Outputs and time zone** tabs contain game-specific fields. For Anno 1404, enter one save folder per line. Empty optional output fields use existing default subdirectories. Scrollbars keep fields accessible in small windows. For keys and placeholders, see [settings documentation](settings.de.md) (German).

**Generate uses displayed values without saving the personal configuration.** Each job receives a temporary configuration copy with the same resolved path destinations. That copy is removed after the process exits. Demo runs stay under `<output>/demo/` and ignore separate personal report, stamp and log destinations.

New GUI files live under `%LOCALAPPDATA%/AnnoOrganizer/<game>/settings.json`, with new outputs in its `local-data/` directory. The actual Windows folder is resolved through the operating system. GUI preferences are stored in `gui.json` alongside game directories. Upgrades do not change these files. Console launchers retain their existing defaults. To explicitly choose another GUI data directory:

```powershell
.\Launch.cmd --gui --gui-data-dir "D:/AnnoOrganizer Data"
```

You can also open an external configuration directly:

```powershell
.\Launch.cmd --gui --game anno1404 --config "D:/My Annos/1404/settings.json"
```

## Language, status and cancellation

On first launch, the preferred Windows display language selects the interface: `de`, `de-DE`, `de-CH` or `de-AT` selects German; other languages or detection failures select English. **DE/EN** can be changed at any time; the saved manual choice takes precedence on subsequent launches. Inputs, game, action and selected tab survive language changes. HTML galleries keep their independent language choice; raw data, paths and logs are not translated.

Status names the current processing step. The moving indicator shows activity rather than an estimated percentage. **Cancel** requests cooperative cancellation. An active parser or publication may finish before the next safe boundary. Closing during processing can request cancellation; the window then waits for process completion.

Success is displayed only when the worker completion and process exit code agree. Failure or cancellation reports possible partial output; the gallery button becomes available after successful runs only. **Logs** shows diagnostics and action logs, including during an active job. **About** shows development version, license information and a link to GitHub releases; no automatic update takes place.

## Current limitations

This is a development build. The extracted executable was locally tested with all five demo galleries and installed 117/1800 game resources, from a different working directory with unusable Python search paths. DE/EN, state transitions, configuration import and a 1404 GUI demo were checked separately. Independent acceptance on a fresh Windows system without development tools remains outstanding; altered Python search paths do not fully replace that check. GUI, CLI and direct generator calls now reserve their actual output trees, including nested paths, logs and stamp caches, across processes. OS-owned locks release reservations after a process crash too. Stamp galleries and resource caches are generated in working copies and published only after successful processing. Cancellation before publication preserves existing contents; publication failure triggers rollback. If another application blocks rollback too, backup copies and `RECOVERY.json` are retained at the location reported in the log. Original saves and stamps remain read only. Overlapping stamp/cache destinations and links inside these output trees are rejected. Multiple demo actions do not form one transaction; actions completed before a later failure may remain published.

Unofficial project by Morima79, unaffiliated with Ubisoft. Use at your own risk under the [MIT license](../LICENSE). Further architecture and acceptance details: [GUI proposal](desktop-gui.md).
