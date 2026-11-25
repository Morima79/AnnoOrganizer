# Desktop interface

[English](desktop.md) · [Deutsch](desktop.de.md) · [README](../README.md)

The desktop preview configures and runs the existing Anno 117, 1800 and 1404 tools. It currently runs from source with Python 3.11 or later including Tkinter. No portable executable package is available yet. Existing console launchers and separately copied game folders remain functional.

## Launch and first demo

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

This is a source preview. Checks cover DE/EN, state transitions, configuration import and a complete Anno 1404 demo run. An executable package without Python, clean-Windows acceptance and GUI runs using Anno 117/1800 game resources remain outstanding. Existing `output` locking remains; do not concurrently run configurations with different `output` roots sharing report/stamp/log destinations yet. Some stamp images and caches are written directly; cancellation can leave partial output, and complete rollback is not implemented yet.

Unofficial project by Morima79, unaffiliated with Ubisoft. Use at your own risk under the [MIT license](../LICENSE). Further architecture and acceptance details: [GUI proposal](desktop-gui.md).
