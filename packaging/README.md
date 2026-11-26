# ANNO - Organizer for Windows x64

[English](README.md) · [Deutsch](README.de.md)

**Start here: [Step-by-step guide with pictures](_internal/docs/user-guide.html?lang=en).**

Extract the entire ZIP, then open **AnnoOrganizer.exe**. Keep `_internal/` beside the executable. No Python installation, installer, runtime pip or administrator access is required. Anno 117 and 1800 still require their installed game resources; the Anno 1404 demo needs no game installation.

Select a game and check the detected installation and standard input folders. **Maps and Excel** is selected on first launch; press **Generate** to process your own saves, or select **Stamp gallery** for 117/1800 stamps. To try the examples instead, explicitly select **Bundled demo**; the startup notice identifies its separate output folder. Saves and stamps are read only.

New settings are created under `%LOCALAPPDATA%/AnnoOrganizer/<game>/settings.json`. New output goes to `AnnoOrganizer/Anno <number>/` under your Windows Documents folder, including redirection. Existing settings and paths are preserved when replacing the application folder. **Generate** uses displayed values without saving the personal settings file; use **Save** to retain edited paths. Existing configurations can be selected or imported.

**Update all galleries** updates usable games with one click and lists skipped games or input folders at the end. **Open galleries** and its adjacent arrow open existing pages; **Open galleries after generation** optionally opens successful results automatically. This choice is saved.

The interface uses German for a German Windows display language, English otherwise. A saved DE/EN choice takes precedence. Open galleries after a successful run; inspect **Logs** if processing fails. Cancellation waits for the next safe boundary.

This package is unsigned. Windows may show a SmartScreen reputation warning. Check the source and published SHA-256 checksum; signing is evaluated separately. No automatic updates are installed.

[Illustrated beginner guide](_internal/docs/user-guide.html?lang=en) · [MIT license](LICENSE) · [Third-party notices](THIRD-PARTY-NOTICES.txt)

Unofficial project by **Morima79**, unaffiliated with Ubisoft. Use at your own risk without warranty under the MIT license. Preserve author attribution and the [original repository](https://github.com/Morima79/AnnoOrganizer) when redistributing. The build identity and resource hashes are recorded in `BUILD.json`.
