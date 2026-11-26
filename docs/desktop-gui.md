# Desktop GUI proposal

[English](desktop-gui.md) · [Deutsch](desktop-gui.de.md) · [Wishlist](wishlist.md)

Status: interface, settings management, output protection and portable Windows x64 package implemented; independent Windows acceptance remains open.

## Goal

Provide a portable Windows application that lets Anno players configure and run the existing tools without installing Python, editing JSON manually or using a command prompt. Preserve the existing CLI, standalone game folders and browser-based galleries. Aim to deliver the first usable GUI before broader community promotion.

## MVP

- Game navigation: Anno 117, Anno 1800 and Anno 1404 (including supported editions).
- Detect game installations and user directories using existing detection logic; allow manual overrides.
- Configure installation, save/account, stamp (117/1800 only) and output paths as applicable.
- Select map analysis/Excel reports or stamp gallery/blueprints according to existing capabilities. Do not advertise unsupported combinations or independent export switches unless implemented.
- Run bundled demos with isolated input/output and without changing personal settings.
- Validate configuration before processing; show clear diagnostics and offer to open logs.
- Show progress, current operation and cancellation; prevent concurrent runs against the same output.
- Open generated galleries in the default browser and open the output folder.
- German/English GUI, version information and manual release check.
- On first launch, use the preferred Windows display language: German for language identifiers whose language component is `de` (e.g. `de-DE`, `de-CH`, `de-AT`), otherwise English. Fall back to English if detection fails. A visible DE/EN control allows manual selection at any time; save it in `gui.json` and prefer it over the system language on subsequent launches. Detect the display language rather than number formatting, region or keyboard layout. This selection applies to the GUI; existing language rules for HTML galleries, logs and exports remain in place.

## Recommended architecture

Use Python with Tkinter/ttk and PyInstaller initially. Keep the GUI thin and reuse the existing root and game-specific launchers, parsers and generators. Extract reusable services from CLI code where required; avoid duplicate processing and interactive console prompts in GUI mode. Execute long-running work outside the UI thread and marshal progress events to the UI thread. Use cooperative cancellation where possible; define safe cancellation boundaries and report partial output. Do not simulate determinate progress when totals are unknown.

Alternative: VB.NET/WPF on .NET 10 LTS with a packaged Python CLI engine. A structured process contract (arguments, progress events, exit codes and cancellation) would be required. Reconsider only if the desktop UI becomes substantially more complex; two runtimes and build stacks are unnecessary for the initial scope.

The following diagram shows the VB.NET/WPF alternative; the initially recommended Python/Tkinter architecture is described above.

[![Architecture sketch of the VB.NET/WPF alternative with a packaged Python engine and HTML, Excel and blueprint outputs](images/desktop-gui-architecture.png)](images/desktop-gui-architecture.png)

[Architecture diagram as SVG](images/desktop-gui-architecture.svg)

## Configuration and data

Reuse the current per-game settings.json schema and semantics, including --config, relative paths, ${DOCUMENTS} and ${HOME}. Preserve unknown keys and existing settings. Validate paths, avoid overwriting user settings on upgrades, and keep personal settings separate from bundled resources. The configuration location and import rules are detailed below; retain existing CLI compatibility. Keep outputs configurable, and never modify original saves or stamps. Resolve bundled resources independently of the working directory and do not write into PyInstaller's internal resource directory.

## Details of the three technical decisions

The following decisions describe the intended initial implementation. They are only partially implemented; current capabilities and remaining interfaces are described below.

### 1. Execution from source and in the Windows package

- The GUI starts a separate worker process for each job. Source installations use a Python worker module; the packaged application starts the same executable with an internal `--worker` mode handled before GUI initialization. The package must not use `sys.executable` as a Python interpreter for a `.py` file. A job specifies the game, action (`demo`, `analyze`, `stamps`), absolute configuration path and optional `rescan`.
- The worker calls non-interactive, game-specific services extracted from existing entry points and shared by GUI and CLI. Replace the current script launches and console prompts deliberately; parsers and generators remain the shared domain logic. Each game folder retains the services required for standalone operation without depending on the repository root.
- GUI and worker exchange versioned UTF-8 JSON lines: stdout carries events with `protocol_version`, `run_id`, `type` and payload; stdin accepts a cancellation request. Event types are `started`, `stage`, `progress`, `diagnostic` and `finished`. Progress includes `completed` and `total` only when totals are known. Existing text output goes to the log and must not pollute the event channel; stderr carries unexpected process errors.
- `finished` includes status `success`, `failed` or `cancelled`, actual generated gallery paths, the log path and partial-output information. Exit codes: `0` success, `1` processing failure, `2` invalid job/configuration, `130` cancellation. A missing or contradictory completion event is a failure. The GUI opens new results only after confirmed success. A background reader queues events for the Tk main thread; only that thread updates widgets.
- The packaged worker uses only bundled modules and resources. After extraction, a smoke test runs all three demos without installed Python, from a different working directory and with the required game resources.

### 2. Settings location and reuse of existing configurations

- The GUI manages `%LOCALAPPDATA%/AnnoOrganizer/<game>/settings.json` per game; GUI-only preferences live separately in `%LOCALAPPDATA%/AnnoOrganizer/gui.json`. Resolve the Windows folder through the operating system and check write access. In the MVP, portable means launchable without an installer; settings are not automatically stored beside the executable. CLI defaults and explicit `--config` remain supported.
- During setup, users can **use an existing configuration in place** or explicitly **import a copy**. Show the source path and resolved input/output destinations. Do not automatically search personal saves or silently migrate settings. An external file changes only when the user explicitly saves edited settings.
- When copying, resolve all known path fields (`game_data`, `account`, `stamps`, `archive`, `save_folders`, `output`, `report_output`, `stamp_output`, `log_output`) relative to the source file using the same logic as `Settings`, and store relative entries as absolute destinations in the copy. Preserve implicit default destinations such as `./local-data` too. Empty optional values stay empty; absolute entries and placeholders may remain unchanged if they resolve identically at the destination. Preserve unknown keys and values unchanged; do not interpret unknown relative strings as paths.
- New GUI configurations use `Documents/AnnoOrganizer/Anno <number>/` beneath the actual Windows Documents folder. Show the absolute destination before the first run. Console launchers retain `<game>/local-data/`; imported configurations retain their existing destinations. New demo inputs come from bundled resources; demo outputs stay entirely under `<output>/demo/` and ignore separate personal output destinations.
- Save validated settings through a unique temporary file in the same directory and atomic replacement. Back up an existing configuration before changing it and detect intervening external edits; reload on conflict instead of overwriting. Upgrades replace program resources only. Tests must cover direct external use, import with relative/implicit paths, unknown keys and restart/upgrade persistence.

### 3. Cancellation, partial results and output locking

- The worker checks cooperative cancellation before each stage, between input files and before publishing new results. During non-interruptible parser or library calls, the GUI displays “Cancellation requested” until the next safe boundary. Cancelling a demo also cancels its remaining actions. The MVP offers no forced process termination in the UI; closing an active window requests cancellation and remains responsive until acknowledgement.
- Generate and validate new reports, galleries and related images in a run-specific temporary output directory first. A gallery must only reference fully published resources. Publish individual files through atomic replacement; for multiple files, publish required resources before HTML/Excel entry points and preserve existing referenced resources. Separate output directories do not form an atomic transaction: explicitly report any already published partial output in the completion status and log. Preserve existing valid outputs when cancellation precedes publication; remove only the job's own temporary files.
- The current `.annoorganizer.lock` protects only `settings.output`. GUI and CLI must share a cross-process locking mechanism and reserve every actual destination before writing: `output`, the active report/stamp destination, the log destination and writable cache destinations. Demos use effective demo destinations only. Different configurations sharing `report_output`, `stamp_output` or `log_output` must not bypass locking.
- Compare resolved Windows paths, accounting for case, short names and directory links. Equal or nested write destinations across jobs are conflicts. Check and register all destinations together under a per-user operating-system lock so two processes cannot claim free destinations simultaneously. A second GUI instance and CLI calls must observe the same reservations; remove stale entries only after confirming the owning process has ended. Hold reservations through publication and final logging, and release them in `finally`.
- Regressions: jobs with different `output` values but a shared report/log destination; nested or aliased destinations; cancellation during input and before publication; a locked Excel file; unexpected worker exit; publication failure after a successful demo action. Failure or cancellation must never appear as overall success or modify original data.

## UI concept

A single window with game navigation on the left and game-specific paths/actions on the right. Provide Settings and About, Generate, Cancel and Open galleries actions, a progress/status area and access to logs. Disable irrelevant controls, e.g. stamps for Anno 1404. Use the existing HTML galleries rather than implementing a desktop gallery viewer.

The visual concept shows the proposed game navigation, path selection and output actions with English example text. The displayed paths and individual export checkboxes are illustrative examples; the decisions in this proposal define default paths and available action combinations.

[![Anno 117 GUI concept with game navigation, folder selection and gallery generation actions](images/desktop-gui-concept.png)](images/desktop-gui-concept.png)

[GUI concept as SVG](images/desktop-gui-concept.svg)

## Distribution

Initially use PyInstaller onedir and --windowed, distributed as a portable Windows ZIP via GitHub Releases. Build on Windows in the existing release workflow (or a dedicated workflow), package required templates, demo files and runtime dependencies, preserve license notices and include third-party notices. No game resource archives or personal data. No runtime pip installation. Keep the existing source distribution available. Verify resource resolution and dependency inclusion in the frozen build; consider onefile only later. Publish SHA-256 checksums; explain possible SmartScreen warnings for unsigned binaries, and evaluate signing separately. Do not advise bypassing security controls. No installer, automatic updates or embedded browser in MVP.

## Acceptance checklist

- [ ] Fresh supported Windows machine without Python: extract and launch successfully.
- [ ] All three game paths can be detected or configured manually; settings survive restart and upgrade.
- [ ] Existing CLI and standalone game folders remain functional; existing regression tests pass.
- [ ] All five supported demo galleries work subject to existing game-resource prerequisites; demo does not scan personal files.
- [ ] Personal map/Excel and supported stamp outputs match CLI behavior on equivalent inputs.
- [ ] Paths containing spaces, Unicode and redirected Documents work; invalid paths and locked Excel workbooks produce actionable messages.
- [ ] UI remains responsive; cancellation and failures are reported without falsely claiming success or damaging source files.
- [ ] Logs and generated outputs can be opened; German and English UI work.
- [ ] Release ZIP is reproducible through CI, includes required resources and licenses, and is smoke-tested after extraction.

## Implementation status: preparing shared execution

The first implementation step now provides `anno_execution.py`. Its canonical source lives under `templates/`; `scripts/sync_gallery_templates.py` distributes identical copies to `<game>/tools/` so each game folder remains independent. All three launchers use this service.

- `prepare_execution(settings, project, action, rescan=False)` accepts an already loaded `Settings` object, selects supported actions, isolates demos and validates every stage without writes, prompts or browser launches. Relative paths and external configurations retain existing `Settings` semantics; personal configuration files are not modified.
- `execute_plan(plan, on_event=None, on_output=None, *, cancel_requested=None, run_id=None)` executes the plan and returns `ExecutionResult(galleries, logs)` containing `Path` objects. Exceptions propagate. `on_output` receives raw log lines; `on_event` receives dictionaries with `protocol_version: 1`, `run_id`, `type` and `payload`. Currently implemented: `started`, `stage` and `finished`. Callbacks run synchronously on the calling thread and must not raise; a future GUI adapter must marshal events to the UI thread.
- `finished.payload` contains `status`, `galleries`, `logs` and `partial_output`, plus `message` on failure. `galleries` lists successfully completed actions only; `logs` lists intended log paths of actions already started. On failure, `partial_output: true` means outputs may exist even if the failed action did not produce a complete gallery. A missing gallery entry point despite exit code 0 is a failure. `KeyboardInterrupt` or `ExecutionCancelled` is reported as `cancelled` and re-raised. An optional `cancel_requested` callback is checked at safe boundaries.
- Root and game launchers offer `--non-interactive`. An explicit action is required, plus a game for the root launcher. This mode does not create missing settings, prompt for installation paths or allow `--init-settings`. `--check` retains its read-only fallback to the example configuration at the default location. Continue to use `--no-open` to suppress browser launches.

Example using an existing external configuration:

```powershell
.\.venv\Scripts\python.exe launch.py --game anno1404 --action demo --config "D:/Anno/settings.json" --non-interactive --no-open
```

The five generators no longer load configuration at import time. Their `run(settings, rescan=False)` service receives settings explicitly; existing direct script calls remain available through `main`. The shared service loads a fresh generator module per action and calls that service without another Python subprocess. Log output is captured separately from events. No temporary demo configuration file is needed; `settings.filename` is preserved. The existing `output` lock still covers the entire demo job. Module-global processing contexts remain limited to one game process for now; the 1800 game-resource index is reset when configuration changes. The frozen build has since been created and checked separately.

Reservations across separate destinations and stamp publication are implemented as described below. Further detailed progress events remain optional; the packaged worker is described below. LocalAppData settings management, GUI and automatic language detection are implemented as a source preview. Because game modules share names, the source service must be used within a single game process; switching games will use a new worker.

## Implementation status: source worker

Each game launcher internally accepts `--worker --action <action> --config <path>` and optional `--rescan`. This entry point is handled before the normal CLI menu, opens no browser and creates no configuration. It uses `anno_worker.py`, also centrally maintained and synchronized into every game folder. Each worker processes exactly one job.

```powershell
.\.venv\Scripts\python.exe anno1404/launch.py --worker --action demo --config "D:/Anno/settings.json"
```

stdout contains only UTF-8 JSON lines in the event format described above. Generator text goes to action logs. The `run_id` returned by `started` applies to every subsequent event. Exit codes are `0` for success, `1` for processing failure, `2` for an invalid job/configuration and `130` for cancellation. Invalid jobs also produce `started` and `finished` events; their `finished.payload.error_code` is `invalid_job`.

A cancellation command on stdin is `{"protocol_version":1,"run_id":"<run_id>","type":"cancel"}` followed by a newline. Only matching versions and job identifiers are accepted; EOF does not cancel. A background reader sets the cancellation request. Checks occur before execution, between actions, between parsed saves or map variants, between stamps and before publication. Active parsers, thread-pool tasks and individual write/publication operations are allowed to finish. Completed demo actions remain listed if cancellation happens later. Stamp generators now use the working-copy and rollback mechanism described below. Demo actions already published remain in place if cancellation occurs later. The GUI must remain responsive until the completion event and wait for these safe boundaries.

Automated checks cover a real 1404 source-worker demo, protocol errors and cancellation through stdin. Subsequent package testing also covers the executable worker and all five demo galleries using available game resources.

## Implementation status: settings management

`desktop/settings_store.py` manages one configuration per game beneath the actual LocalAppData directory reported by Windows. New files are created automatically on first opening through `desktop/first_run.py`: detected installations, standard inputs and Documents outputs; the initial action is Maps and Excel. Demos remain explicitly selectable. External files can be used in place or explicitly copied. Copying resolves known relative paths and implicit output destinations against the source directory, preserving unknown values. A missing external file is never silently recreated.

`Settings.from_data` provides the same path resolution for unsaved values. `anno_settings.py` is now also synchronized from `templates/`. Saving checks schema, path types and overlaps with inputs/code; missing installations may still be configured, with complete action-specific checks before processing. Changes use an edit lock, a backup of previous content and atomic replacement. Detected external edits since loading cause a conflict instead of an overwrite; editors that do not share the lock cannot be covered by a complete transaction guarantee. GUI preferences and external file selections persist in `gui.json`.

## Implementation status: interface

`launch.py --gui` opens the Tkinter/ttk interface in `desktop/app.py`; the regular CLI remains available. It includes game navigation, scrollable path fields, configuration selection/import/saving, demo/analysis/stamp actions, output destinations, logs and About. Windows display language and saved DE/EN choice use matching resources under `desktop/locales/`. GUI language does not change gallery or log language.

`desktop/worker_client.py` reads worker events on a background thread and queues them for Tk. Success is enabled only after a consistent completion event and exit code. Cancellation requested before worker startup is forwarded after the job identifier arrives. Every job uses a private temporary configuration copy so Generate does not save a personal configuration. Inputs and selected tab survive language changes. Source startup, DE/EN and a 1404 demo were also inspected visibly; scrollable fields keep 860 × 720 pixels usable.

Usage and remaining limitations: [desktop guide](desktop.md). Packaging is described below; independent overall acceptance on a fresh Windows system remains open.

## Implementation status: output protection

`anno_output_lock.py` reserves complete write destinations through a per-user Windows registry lock. Equal and nested targets conflict across different configurations. Short paths and directory links are resolved before comparison. Reservation files carry a held OS lock; unlocked stale entries are removed under the registry guard. `anno_output_transaction.py` generates stamp galleries and resource caches in separate working copies, checks for external edits and publishes resources before HTML. Failed publication rolls back; blocked rollback retains backups and a local recovery index. Both modules are synchronized into every standalone game folder.

## Implementation status: portable package

`desktop_entry.py` starts the interface or the same executable in worker mode. The windowed worker opens inherited Windows pipe handles as UTF-8 streams. Game-specific Python modules remain verified resources to prevent collisions between identical module names in the frozen importer. `requirements-build.txt` pins build and runtime versions; `scripts/build_desktop.py` collects tracked, approved contents only and checks demo filenames against their manifests. Normal builds require a clean commit; explicit development builds carry `-dev` and are marked in `BUILD.json`.

The onedir/windowed build includes runtime, resources, license texts, source commit and input hashes. Internal resources are protected against writes. `scripts/smoke_desktop.py` verifies ZIP, SHA-256, extracted resources and the executable from a different directory without usable Python search paths. Program files must remain unchanged after execution too. All five demo galleries were generated locally with the executable; CI checks 1404 without a game installation. The release workflow waits for Windows build and smoke testing and attaches both packages only when publishing an authorized tag. Local implementation did not publish anything.

## Implementation sequence

1. Inspect launcher/configuration APIs and define reusable non-interactive execution/progress contracts.
2. Implement GUI and settings handling, with tests for path and settings compatibility.
3. Add worker execution, cancellation, logging and output navigation.
4. Package and test frozen Windows build; extend publishing workflow and quick-start documentation.
5. Validate on a clean Windows environment and prepare community announcement with screenshots, demo link and release link.

This is a proposal, not a commitment to a release date or implementation technology.
