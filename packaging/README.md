# AnnoOrganizer for Windows x64

[English](README.md) · [Deutsch](README.de.md)

Extract the entire ZIP, then open **AnnoOrganizer.exe**. Keep `_internal/` beside the executable. No Python installation, installer, runtime pip or administrator access is required. Anno 117 and 1800 still require their installed game resources; the Anno 1404 demo needs no game installation.

Select a game, leave **Bundled demo** selected and press **Generate**. Use the existing configuration selector/import to process your own inputs later. Saves and stamps are read only. Settings and output default to your Windows LocalAppData folder and survive replacing the application folder. Generate does not overwrite your personal settings file.

The interface uses German for a German Windows display language, English otherwise. A saved DE/EN choice takes precedence. Open galleries after a successful run; inspect **Logs** if processing fails. Cancellation waits for the next safe boundary.

This development package is unsigned. Windows may show a SmartScreen reputation warning. Check the source and published SHA-256 checksum; signing is evaluated separately. No automatic updates are installed.

[Full guide](_internal/docs/desktop.md) · [MIT license](LICENSE) · [Third-party notices](THIRD-PARTY-NOTICES.txt)

Unofficial project by **Morima79**, unaffiliated with Ubisoft. Use at your own risk without warranty under the MIT license. Preserve author attribution and the [original repository](https://github.com/Morima79/AnnoOrganizer) when redistributing. The build identity and resource hashes are recorded in `BUILD.json`.
