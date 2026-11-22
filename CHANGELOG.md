# Changelog

Notable changes to AnnoTools. Each version includes English and German release notes.
Wichtige Änderungen an AnnoTools. Jede Version enthält englische und deutsche Release-Hinweise.

## [Unreleased]

## [v0.1.6] - 2026-11-22

### English

- Added DE/EN switching to all five galleries, with embedded central language resources, preserved filters and image views, bilingual demo snapshots, documentation and localisation tests.
- Updated Pages, release and test actions to versions using Node.js 24, including the nested Pages artifact upload, to remove Node.js 20 deprecation warnings.

### Deutsch

- DE/EN-Umschaltung für alle fünf Galerien mit eingebetteten zentralen Sprachressourcen, erhaltenen Filtern und Bildansichten, zweisprachigen Demo-Seiten, Dokumentation und Übersetzungstests ergänzt.
- Pages-, Release- und Test-Actions auf Versionen mit Node.js 24 aktualisiert, einschliesslich des indirekten Pages-Artefakt-Uploads, um die Node.js-20-Abkündigungswarnungen zu beheben.

## [v0.1.5] - 2026-11-22

### English

- Unified map and stamp gallery typography, including page and card headings, through the shared templates.
- Refreshed all five screenshots and aligned their preview widths in both READMEs.

### Deutsch

- Schriftbild der Karten- und Stempelgalerien einschliesslich Haupt- und Kartentiteln über die gemeinsamen Vorlagen vereinheitlicht.
- Alle fünf Screenshots erneuert und ihre Vorschaubreiten in beiden Readmes angeglichen.

## [v0.1.4] - 2026-11-21

### English

- Fixed Windows temporary-path comparisons in configuration tests for GitHub runners using short user directory names.
- Added optional separate report, stamp and log output directories for external per-game settings; demo outputs remain isolated.
- Refreshed all five gallery screenshots in the German and English READMEs to show the shared layout, game logos and current colour themes.

### Deutsch

- Windows-Pfadvergleiche in Konfigurationstests für GitHub-Runner mit kurzen Benutzerordnernamen korrigiert.
- Optionale getrennte Ausgabeordner für Auswertungen, Stempel und Protokolle bei externen Spieleinstellungen ergänzt; Demo-Ausgaben bleiben getrennt.
- Alle fünf Galerie-Screenshots in den deutschen und englischen Readmes auf das gemeinsame Layout mit Spiel-Logos und aktuellen Farbthemen aktualisiert.

## [v0.1.3] - 2026-11-21

### English

- Simplified both stamp gallery footers to show only the last update date and time.
- Added shared map and stamp page templates with backgrounds inspired by each game's interface. Each game remains independently usable through synchronised template copies.
- Changed Anno 1404 to a light parchment theme and removed operational file-status messages from gallery pages.
- Removed separate logo panels so logos blend into map backgrounds and stamp gallery headers. Added template maintenance guides and a command to synchronise standalone copies and refresh existing demo frames.

### Deutsch

- Beide Stempelgalerie-Fusszeilen zeigen nur noch den Stand mit Datum und Uhrzeit.
- Gemeinsame Karten- und Stempelvorlagen mit an die Spieloberflächen angelehnten Hintergründen ergänzt. Synchronisierte Vorlagenkopien erhalten die eigenständige Nutzbarkeit jedes Anno-Ordners.
- Anno 1404 auf eine helle Pergamentoptik umgestellt und technische Dateistatusmeldungen aus den Galerien entfernt.
- Separate Logo-Flächen entfernt: Logos fügen sich in Kartenhintergründe und Stempel-Banner ein. Vorlagenpflege dokumentiert und einen Befehl zum Synchronisieren der eigenständigen Kopien sowie Aktualisieren der Demo-Seiten ergänzt.

## [v0.1.2] - 2026-11-21

### English

- Restored the game logos for Anno 117, Anno 1800 and Anno 1404 in the gallery exporters and all five online demo galleries. The logos are now bundled with the tools and included in the release ZIP.
- Added linked test, latest-release and demo badges to all German and English READMEs.
- Moved detailed publishing instructions into separate English and German guides under `docs/`.
- Added this bilingual changelog. Tagged releases now use the matching changelog entry as their release description, with checks for missing or ambiguous entries.

### Deutsch

- Die Spiel-Logos für Anno 117, Anno 1800 und Anno 1404 sind in den Galerie-Werkzeugen und allen fünf Online-Demos wieder enthalten. Die Logos werden mit den Werkzeugen und in der Release-ZIP mitgeliefert.
- Verlinkte Badges für Tests, die aktuelle Release-Version und die Demo-Seite in allen deutschen und englischen Readmes ergänzt.
- Ausführliche Veröffentlichungsanleitungen in separate deutsche und englische Anleitungen unter `docs/` verschoben.
- Dieses zweisprachige Changelog ergänzt. Getaggte Releases verwenden jetzt den passenden Changelog-Eintrag als Beschreibung; fehlende oder mehrdeutige Einträge werden erkannt.

## [v0.1.1] - 2026-11-21

### English

- Added automatic release ZIP creation and SHA-256 checksums after successful Windows tests on Python 3.11 and 3.14.
- Published a GitHub Pages landing page with three map galleries and two stamp galleries from the bundled demos.
- Added validation for public demo image links and local machine paths, plus online demo links in the READMEs.

### Deutsch

- Automatische Release-ZIPs und SHA-256-Prüfsummen nach erfolgreichen Windows-Tests mit Python 3.11 und 3.14 ergänzt.
- GitHub-Pages-Startseite mit drei Karten- und zwei Stempelgalerien aus den mitgelieferten Demos veröffentlicht.
- Prüfungen für Bildverweise und lokale Rechnerpfade sowie Online-Demo-Links in den Readmes ergänzt.

## [v0.1.0] - 2026-11-21

### English

- First public release: independent Windows tools for Anno 117, Anno 1800 and Anno 1404, including Venice and History Edition.
- Map galleries and Excel savegame reports for all three games; stamp galleries and blueprint PNGs for Anno 117 and Anno 1800.
- Bundled demo saves and stamps, configurable paths, automatic installation detection, screenshots, and German/English READMEs.

### Deutsch

- Erste öffentliche Version: eigenständig verwendbare Windows-Werkzeuge für Anno 117, Anno 1800 und Anno 1404 einschliesslich Venedig und History Edition.
- Kartengalerien und Excel-Spielstandauswertungen für alle drei Spiele; Stempelgalerien und Bauplan-PNGs für Anno 117 und Anno 1800.
- Demo-Spielstände und Stempel, einstellbare Pfade, automatische Installationserkennung, Screenshots und deutsche/englische Readmes.
