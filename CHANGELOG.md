# Changelog

Notable changes to AnnoOrganizer. Each version includes English and German release notes.
Wichtige Änderungen an AnnoOrganizer. Jede Version enthält englische und deutsche Release-Hinweise.

## [Unreleased]

### English

- Remember desktop window positions, sizes and maximized states with monitor recovery; keep About/Logs above their owner, use single-line Anno 1404 folder fields, and highlight selected tabs/language in gold without shrinking tabs.

- Build a portable Windows x64 GUI/worker package with pinned dependencies, licenses, source/resource manifests, SHA-256 checksums and extracted-EXE smoke tests; integrate it into the existing release workflow and protect internal resources against writes.

- Reserve actual output/log/cache trees across desktop and CLI processes, recover crash-stale reservations, and stage stamp galleries/caches with publication rollback and retained recovery data if rollback is blocked.

- Add a Tkinter desktop preview via `Launch.cmd --gui`, with saved/system DE/EN selection, game-specific settings/imports, temporary job configurations, responsive worker execution, cancellation, logs and output navigation. Verify worker completion against its exit code before enabling successful results.

- Add desktop settings management with LocalAppData defaults, external-file selection, path-preserving imports, unknown-key retention, backups and conflict-aware atomic saves; share CLI path resolution for unsaved settings.

- Add an isolated source-worker entry point with JSON-line events, explicit exit codes and matching-job cancellation requests; check cancellation between actions, saves, map variants and stamps, and before publication.

- Expose explicit settings-based services for all five generators; remove configuration reads on import and script subprocesses from shared execution while retaining direct CLI entry points.

- Prepare shared non-interactive execution for all three game launchers, including validated demo plans, structured stage/completion callbacks and output results. Add `--non-interactive`; retain the transitional Python script backend and document remaining GUI/worker work.

### Deutsch

- Fensterpositionen, Grössen und Maximierung mit Monitorwiederherstellung speichern; Info/Protokolle über ihrem Hauptfenster halten, einzeilige Anno-1404-Pfadfelder verwenden und gewählte Tabs/Sprache goldgelb markieren, ohne Tabs zu verkleinern.

- Portables Windows-x64-Paket für GUI und Worker mit fixierten Abhängigkeiten, Lizenzen, Quell-/Ressourcenmanifest, SHA-256-Prüfsummen und Tests der entpackten EXE ergänzt; in den vorhandenen Release-Workflow integriert und interne Ressourcen gegen Schreibzugriffe geschützt.

- Tatsächliche Ausgabe-/Log-/Cacheziele über Desktop- und CLI-Prozesse reserviert, verwaiste Reservierungen nach Abstürzen freigegeben und Stempelgalerien/-Caches mit Rücknahme fehlgeschlagener Veröffentlichungen sowie erhaltenen Wiederherstellungsdaten abgesichert.

- Tkinter-Desktop-Vorschau über `Launch.cmd --gui` mit gespeicherter/systembasierter DE/EN-Auswahl, spielspezifischen Einstellungen und Importen, temporären Auftragskonfigurationen, bedienbarer Worker-Ausführung, Abbruch, Logs und Ausgabe-Navigation ergänzt. Ergebnisse erst nach übereinstimmendem Worker-Abschluss und Exitcode als erfolgreich freigeben.

- Desktop-Einstellungsverwaltung mit LocalAppData-Standardorten, externer Dateiauswahl, Import mit unveränderten Pfadzielen, Erhalt unbekannter Schlüssel, Sicherungen und konfliktgeprüftem atomarem Speichern ergänzt; CLI-Pfadauflösung auch für ungespeicherte Werte nutzen.

- Isolierten Quellcode-Worker mit JSON-Zeilen-Ereignissen, definierten Exitcodes und auftragsbezogenem Abbruch ergänzt; Abbruch zwischen Aktionen, Saves, Kartenvarianten und Stempeln sowie vor Veröffentlichung prüfen.

- Dienste mit expliziter Konfiguration für alle fünf Generatoren ergänzt; Konfigurationszugriffe beim Import und Skript-Unterprozesse aus der gemeinsamen Ausführung entfernt. Direkte CLI-Einstiege bleiben erhalten.

- Gemeinsame nicht interaktive Ausführung für alle drei Spielstarter vorbereitet: validierte Demo-Pläne, strukturierte Schritt-/Abschlussereignisse und Ausgabeergebnisse. `--non-interactive` ergänzt; vorläufigen Python-Skript-Backend und offene GUI-/Worker-Arbeiten dokumentiert.

## [v0.1.13] - 2026-11-24

### English

- Unify enlarged map images across all three games with a shared zoom/download dialog, DE/EN controls and the same Back/Forward behaviour as stamp viewers. Preserve filters and native PNG links; add viewer regressions.

### Deutsch

- Karten-Grossansichten aller drei Spiele durch einen gemeinsamen Zoom-/Download-Dialog mit DE/EN und derselben Zurück-/Vorwärts-Navigation wie bei Stempeln vereinheitlicht. Filter und normale PNG-Links erhalten; Laufzeittests ergänzt.

## [v0.1.12] - 2026-11-24

### English

- Display Excel statistics as grouped integers and seeds without grouping. Add three downloadable demo workbooks and offline ZIPs with linked map images, bilingual demo links and README documentation.

- Make both stamp image dialogs participate in browser Back/Forward navigation without changing gallery URLs or filters.

- Preserve map search, filters, sorting and profile selection when returning from a map image in all three games. Document the unverified gameplay meaning of Anno 1800's stored Dockworkers setting.

### Deutsch

- Excel-Kennzahlen als Ganzzahlen mit Tausendertrennzeichen und Seeds ohne Trennzeichen formatiert. Drei Demo-Arbeitsmappen und Offline-ZIPs mit verknüpften Kartenbildern, zweisprachigen Demo-Links und README-Hinweisen ergänzt.

- Bilddialoge beider Stempelgalerien mit Browser-Zurück/Vorwärts bedienbar gemacht; Galerieadresse und Filter bleiben erhalten.

- Suche, Filter, Sortierung und Profilwahl beim Zurückkehren vom Kartenbild in allen drei Spielen erhalten. Nicht bestätigte Spielwirkung der gespeicherten Anno-1800-Einstellung Hafenarbeiter dokumentiert.

## [v0.1.11] - 2026-11-24

### English

- Capture all five demo galleries in German and English in the background; use matching screenshot languages and uniform 360-pixel previews throughout the eight READMEs.

- Unify stamp-header totals for Anno 117 and 1800, counting exported stamps and represented regions with one border per badge in both languages.

- Select demo saves with settled campaigns containing population and residences for all three games; refresh all five README screenshots and document the verified capture workflow. Read Anno 1800 residence population independently of missing or differing profile totals, with explicit source labels and discrepancy notes.

- Use verified game-specific DE/EN setting headings and enum labels for all three games, preserving contextual meanings and unknown raw values. Correct Anno 117 setup island-size IDs separately from generated geometry and Anno 1800 mainly-small/medium/large island labels. Document text IDs, datasets and limitations.

- Scope save counts, dates, playtime records and older-save warnings to individual campaigns in all three games. Variant summaries and Excel map sheets show campaign/file totals and summed campaign playtime, avoiding cross-campaign comparisons.

- Keep 117/1800 campaign histories in one map variant based on readable map options, eliminating repeated current dates/statistics across patch-driven variants. Default to newest save first and add an unconditional back-to-top link to every map card.

- Unified the 117/1800 map catalogue, cards, seed lists and controls. Fixed statistics-card search, mode filters, counts and profile return navigation; aligned controls and placed finances before population/residences in all three games. Documented map-variant grouping and added catalogue runtime regressions.
- Added latest-save population, wealth, supported balance, residence, ship and settled-island statistics for all three games. Compact, initially collapsed bilingual groups keep details and save history out of the summary; uncertain values show “not available”. Excel includes a current-campaign worksheet. Added source/limitation documentation and regression coverage.

### Deutsch

- Alle fünf Demo-Galerien im Hintergrund auf Deutsch und Englisch aufgenommen; passende Bildsprachen und einheitliche 360-Pixel-Vorschauen in allen acht READMEs eingebunden.

- Stempel-Header für Anno 117 und 1800 vereinheitlicht: Gesamtzahl der Stempel und vertretenen Regionen mit genau einem Rahmen pro Anzeige in beiden Sprachen.

- Für alle drei Spiele Demo-Saves mit besiedelten Partien, Bevölkerung und Wohnhäusern ausgewählt, alle fünf README-Screenshots erneuert und den geprüften Aufnahmeweg dokumentiert. Anno-1800-Wohnhausbevölkerung unabhängig von fehlenden oder abweichenden Profil-Gesamtzählern ausgelesen, mit klarer Quellenbezeichnung und Abweichungshinweis.

- Geprüfte spielbezogene DE/EN-Einstellungsnamen und Enum-Texte für alle drei Spiele eingebunden; kontextabhängige Bedeutungen und unbekannte Rohwerte bleiben getrennt. Anno-117-Setup-Inselgrössen separat von erzeugter Geometrie und Anno-1800-Inselgrössen mit «Mehrheitlich …» korrigiert. Text-IDs, Datasets und Grenzen dokumentiert.

- Save-Anzahl, Zeitpunkte, Spielzeitrekorde und Hinweise auf ältere längere Saves in allen drei Spielen pro Partie zugeordnet. Varianten und Excel-Kartenblätter zeigen Gesamtsummen statt irreführender Vergleiche unterschiedlicher Partien.

- Partiehistorien in 117/1800 anhand verständlicher Kartenoptionen zusammengefasst; dadurch keine mehrfach kopierten aktuellen Daten/Kennzahlen in technischen Patch-Varianten. Neueste Saves standardmässig zuerst und sichtbaren Nach-oben-Link in jeder Kartenkachel ergänzt.

- Kartenkatalog, Kartenaufbau, Seed-Listen und Bedienung von 117/1800 vereinheitlicht. Suche, Modusfilter, Trefferzahlen und Profilrücksprung bei Kennzahlenkarten repariert; Bedienelemente bündig ausgerichtet und Geld in allen drei Spielen vor Bevölkerung/Wohnhäusern angeordnet. Variantenbildung dokumentiert und Laufzeittests für den Katalog ergänzt.
- Spielstandauswertung aller drei Spiele um Bevölkerung, Vermögen, unterstützte Bilanzwerte sowie Wohnhaus-, Schiffs- und Inselzahlen des neuesten Saves erweitert. Kompakte, zunächst geschlossene zweisprachige Gruppen bündeln Details und Save-Historie; unsichere Werte erscheinen als «nicht verfügbar». Excel enthält ein Blatt mit aktuellen Partieständen. Datenquellen, Grenzen und Regressionstests ergänzt.

## [v0.1.10] - 2026-11-23

### English

- Renamed the project to AnnoOrganizer and updated repository, release and GitHub Pages links, launcher labels and all five demo galleries. Future release archives use `AnnoOrganizer-<version>.zip`; existing settings, output markers and stored language preferences remain compatible.

### Deutsch

- Projekt in AnnoOrganizer umbenannt und Repository-, Release- und GitHub-Pages-Links, Startertexte sowie alle fünf Demo-Galerien angepasst. Künftige Release-Archive heissen `AnnoOrganizer-<Version>.zip`; bestehende Einstellungen, Ausgabekennungen und gespeicherte Sprachwahl bleiben kompatibel.

## [v0.1.9] - 2026-11-22

### English

- Anno 117 stamp CDLC detection now preserves cosmetic asset-group provenance. Ambrosian and Celtic forest floors are correctly identified as CDLC02, even with base-game graphics paths; regression tests cover both floors, selected skins and base-game replacements.

### Deutsch

- CDLC-Erkennung der Anno-117-Stempel um die Herkunft aus kosmetischen Assetgruppen ergänzt. Ambrosianischer und Keltischer Wald werden trotz Grundspiel-Grafikpfaden korrekt als Blütezeit (CDLC02) erkannt; Regressionstests decken beide Waldflächen, gewählte Skins und Grundspiel-Ersatzflächen ab.

## [v0.1.8] - 2026-11-22

### English

- Removed the separate rectangular background from the collapsible profile playtime section in map galleries and refreshed the Anno 117 and Anno 1800 preview screenshots at a consistent width.

### Deutsch

- Separate rechteckige Hintergrundfläche des einklappbaren Bereichs «Spielzeit pro Profil» in den Kartengalerien entfernt und die Vorschau-Screenshots für Anno 117 und Anno 1800 mit einheitlicher Breite aktualisiert.

## [v0.1.7] - 2026-11-22

### English

- Aligned visible logo tops with DE/EN buttons in a compact shared header row across all five galleries, including narrow screens; original logo assets are preserved.
- Localised the demo landing page using the shared DE/EN resources and stored language choice, including navigation links, footer and metadata.
- Added a step-local Pages runtime adapter that replaces the deprecated built-in `punycode` import with the unchanged MIT-licensed userland implementation; checksums and regression tests keep other warnings visible.

### Deutsch

- Sichtbare Logo-Oberkanten und DE/EN-Buttons in allen fünf Galerien in einer kompakten gemeinsamen Kopfzeile bündig ausgerichtet, auch auf schmalen Bildschirmen; Original-Logos bleiben erhalten.
- Demo-Startseite einschliesslich Navigationslinks, Fusszeile und Metadaten an die gemeinsamen DE/EN-Ressourcen und gespeicherte Sprachwahl angebunden.
- Auf den Pages-Deploy-Schritt begrenzten Laufzeitadapter ergänzt: Die veralteten `punycode`-Imports verwenden die unveränderte Userland-Implementierung mit MIT-Lizenz; Prüfsummen und Regressionstests sichern die Korrektur ab, andere Warnungen bleiben sichtbar.

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
