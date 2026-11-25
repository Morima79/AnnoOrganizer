# Desktop GUI proposal

[English](desktop-gui.md) · [Deutsch](desktop-gui.de.md) · [Wishlist](wishlist.md)

Status: Proposed; not implemented.

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

## Recommended architecture

Use Python with Tkinter/ttk and PyInstaller initially. Keep the GUI thin and reuse the existing root and game-specific launchers, parsers and generators. Extract reusable services from CLI code where required; avoid duplicate processing and interactive console prompts in GUI mode. Execute long-running work outside the UI thread and marshal progress events to the UI thread. Use cooperative cancellation where possible; define safe cancellation boundaries and report partial output. Do not simulate determinate progress when totals are unknown.

Alternative: VB.NET/WPF on .NET 10 LTS with a packaged Python CLI engine. A structured process contract (arguments, progress events, exit codes and cancellation) would be required. Reconsider only if the desktop UI becomes substantially more complex; two runtimes and build stacks are unnecessary for the initial scope.

## Configuration and data

Reuse the current per-game settings.json schema and semantics, including --config, relative paths, ${DOCUMENTS} and ${HOME}. Preserve unknown keys and existing settings. Validate paths, avoid overwriting user settings on upgrades, and keep personal settings separate from bundled resources. Define a writable configuration location (e.g. LocalAppData) and migration/explicit import rules before implementing; retain existing CLI compatibility. Keep outputs configurable, and never modify original saves or stamps. Resolve bundled resources independently of the working directory and do not write into PyInstaller's internal resource directory.

## UI concept

A single window with game navigation on the left and game-specific paths/actions on the right. Provide Settings and About, Generate, Cancel and Open galleries actions, a progress/status area and access to logs. Disable irrelevant controls, e.g. stamps for Anno 1404. Use the existing HTML galleries rather than implementing a desktop gallery viewer.

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

## Implementation sequence

1. Inspect launcher/configuration APIs and define reusable non-interactive execution/progress contracts.
2. Implement GUI and settings handling, with tests for path and settings compatibility.
3. Add worker execution, cancellation, logging and output navigation.
4. Package and test frozen Windows build; extend publishing workflow and quick-start documentation.
5. Validate on a clean Windows environment and prepare community announcement with screenshots, demo link and release link.

This is a proposal, not a commitment to a release date or implementation technology.
