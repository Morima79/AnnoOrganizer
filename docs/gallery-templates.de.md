# Gemeinsame Galerie-Vorlagen

[English](gallery-templates.md) · [Deutsch](gallery-templates.de.md) · [README](../README.de.md)

Die fünf Galerien verwenden zwei zentral gepflegte Seitenvorlagen:

| Galerie | HTML | Farben und Layout |
|---|---|---|
| Karten | [map_gallery.html](../templates/map_gallery.html) | [map_gallery.css](../templates/map_gallery.css) |
| Stempel | [stamp_gallery.html](../templates/stamp_gallery.html) | [stamp_gallery.css](../templates/stamp_gallery.css) |
| Demo-Startseite | [demo_index.html](../templates/demo_index.html) | Seitenstil in der Vorlage, gemeinsames Schalter-CSS |

Der gemeinsame Renderer [anno_gallery.py](../templates/anno_gallery.py) setzt den Seitenrahmen, das Logo und das Farbthema zusammen. Anno 117 und 1800 teilen zusätzlich den vollständigen Katalog in `templates/map_catalog.html`, die Laufzeit `map_catalog.js` und den Karten-/Seitenrenderer `anno_map_catalog.py`. Die Exporte liefern spielbezogene Karten und Detailwerte. Anno 1404 behält sein Gelände-Kartenraster und den Editionsfilter und verwendet denselben Rahmen, dieselben Farbressourcen und Kennzahlengruppen. Bilder, CSS und Logo werden wie bisher lokal eingebunden; für die erzeugte Galerie ist kein Webserver erforderlich.

Karten- und Stempelgalerien verwenden einheitlich `system-ui, sans-serif`, einschliesslich Haupt- und Kartentiteln. Haupttitel teilen sich Schriftgrösse, Gewicht und Zeilenhöhe. Die README-Vorschauen stehen in einer gemeinsamen Tabelle mit einheitlich 360 Pixel breiten Bildern; neue Screenshots werden mit 1264 Pixel Bildbreite aufgenommen (1280 Pixel Browserbreite einschliesslich Scrollleiste).

Logo und DE/EN-Schalter stehen in einer gemeinsamen, oben bündigen Zeile. Der Renderer berechnet den sichtbaren Alphabereich des Logos und blendet transparente Ränder nur im Layout aus; die eingebetteten Original-PNGs bleiben unverändert. Auf schmalen Bildschirmen verkleinert sich das Logo, während die Sprachbuttons erreichbar bleiben. [Vorschau des kompakten Kopfbereichs](images/gallery-header.jpg).

Beide Stempel-Header zeigen die ungefilterte Gesamtzahl der exportierten Stempel und die Anzahl Regionen, aus denen diese Stempel stammen. Der gemeinsame Renderer ermittelt die Zahlen aus den Karten; gemeinsame `stamp-totals`-Stile geben jeder Anzeige genau einen Rahmen. Übersetzungsfelder erhalten keine eigenen Rahmen.

## Inselgrafiken

Anno 1800 reduziert die Deckkraft halbtransparenter, rein schwarzer Inselschatten vor dem Skalieren um 75 Prozent. Geländefarben, vollständig deckende Geländepixel, Inselpositionen und Abmessungen bleiben erhalten. Enbesa wird um alle Inselgelände mit 64 Feldern Wasserabstand eingerahmt. Die Arktis entfernt Wasser nur links und unten; ihre oberen und rechten Festlandkanten bleiben erhalten. Der Ausschnitt wird auf die übliche Bildbreite vergrössert und in der Bildfusszeile mit seinen Abmessungen gekennzeichnet. Gespeicherte Weltgrössen bleiben unverändert. Bei nicht aufgelösten Inselgrafiken bleibt die vollständige Karte erhalten.

Anno 117 verwendet für alle Inseln die Laufzeit-DDS ohne Rückgriff auf PNG-Vorschauen. Latium, Albion und Aegyptus erhalten regional abgestimmte Helligkeitsbereiche der Mitteltöne und eine leicht verringerte Sättigung. Dunkle römische Inseln werden weniger aufgehellt; Albions Grüntöne und der ägyptische Sand behalten ihren regionalen Charakter. Alphakanal, Küstenlinien und neutrale Felsfarben bleiben erhalten. Aegyptus wird bis zu den Aussenkanten seiner vier Geländeteile beschnitten (1920 × 1920 Felder). Der leere Wasserbereich oben und rechts entfällt, das Gelände erscheint bei gleicher Bildbreite um ein Drittel grösser. Die gespeicherte Kartengrösse bleibt erhalten; die Bildfusszeile kennzeichnet den Ausschnitt. Alle dekodierten und farblich angeglichenen Inselgrafiken werden über mehrere Exporte aus `terrain-cache/` im konfigurierten Berichtsausgabeordner wiederverwendet. Der Cache-Schlüssel berücksichtigt Renderer-Version, Archiveintrag, Archivgrösse und Änderungszeit; beschädigte Einträge werden neu erzeugt. Überlappungen des Aegyptus-Geländes werden nur über vorhandenem Gelände weich überblendet. Küstenlinien bleiben erhalten und schwarze Platzhalterflächen der Quadranten abgedeckt. Unterschiede der Originaltexturen können weiterhin sichtbar bleiben.

## Farben

Die Farben orientieren sich an der jeweiligen Spieloberfläche. Die transparenten Logos fügen sich in diese Flächen ein. `THEMES` im gemeinsamen Renderer legt Hintergrund sowie lesbare Text-, Rahmen- und Linkfarben fest:

- Anno 117: Beige (`#f1e5cc`).
- Anno 1800: Dunkelblau (`#173345`).
- Anno 1404: Helle Pergamentoptik (`#f3ead8`) mit Braun- und Goldtönen.

Bei Kartengalerien gilt dieses Thema für die gesamte Seite. Bei Stempelgalerien gilt es für den Header-Banner; der Bereich mit Suche und Bauplänen bleibt hell. Das Logo selbst bekommt keine separate Hintergrundfläche. Beide Stempel-Fusszeilen enthalten ausschliesslich den Aktualisierungszeitpunkt (`Stand:` / `Updated:`).

## Sprachen DE / EN

Alle fünf Galerien besitzen einen gemeinsamen Sprachschalter im Kopfbereich. In Stempelgalerien gibt es denselben Schalter zusätzlich in der modalen Grossansicht. Beim Umschalten bleiben Suche, Filterwerte, Sortierung, Profilwahl, aufgeklappte Details und die Bildansicht samt Zoom erhalten. `html.lang`, Seitentitel, Platzhalter und zugängliche Bild-/Schaltflächenbeschreibungen wechseln ebenfalls.

Die Demo-Startseite verwendet denselben DE/EN-Schalter und dieselbe gespeicherte Sprachwahl. Ein Wechsel zur Galerie und über den Demo-Rücklink zurück erhält die gewählte Sprache, sofern Browserspeicher verfügbar ist. Titel, Meta-Beschreibung, Einführung, Galerie-Links und Fusszeile stammen aus den zentralen `demo.*`-Ressourcen. Die Vorlage `templates/demo_index.html` wird mit `--refresh-site` nach `site/index.html` geschrieben; `--check` erkennt eine veraltete Startseite. [Englische Startseiten-Vorschau](images/demo-home-en.jpg).

Die fünf Galerielinks öffnen eigene Tabs und kündigen dies in ihren übersetzten zugänglichen Beschreibungen an. Die Startseite bleibt geöffnet. Anno-1404-Kartenbilder verwenden eine einheitliche Wasserfarbe (`#366d7c`) für das offene Meer und das Wasser innerhalb der Inselbereiche, damit keine rechteckigen Flächen entstehen. Vorhandene zwischengespeicherte Bilder werden nach einer Änderung der Renderer-Version oder mit `--rescan` neu erzeugt.

Die zentralen Sprachressourcen liegen in [locales/de.json](../templates/locales/de.json) und [locales/en.json](../templates/locales/en.json). Beide Dateien verwenden dieselben stabilen Schlüssel und Platzhalter, beispielsweise `stamp.count` mit `{shown}` und `{total}`. `.one`-Varianten behandeln Einzahlformen. Fehlende Schlüssel oder abweichende Platzhalter führen beim Export zu einer verständlichen Fehlermeldung.

[anno_i18n.py](../templates/anno_i18n.py) bindet bekannte Oberflächentexte und erzeugte Anzeigen an Ressourcenschlüssel. Explizite Markierungen wie `<span data-i18n="filters.allRegions">Alle Regionen</span>` können direkt in Vorlagen stehen. Für dynamische Texte verwenden die Exporter `galleryI18n.t('stamp.count', {shown, total})` und reagieren auf `gallerylanguagechange`. Nur Text und Beschriftungen ändern sich; interne Optionswerte bleiben stabil. Eigene Namen und Pfade werden von der Bindung ausgeschlossen. Zusätzliche unveränderte Inhalte können mit `data-i18n-ignore` markiert werden.

Der Renderer bettet beide JSON-Ressourcen sowie [gallery_i18n.js](../templates/gallery_i18n.js) und das Schalter-CSS in jede erzeugte HTML-Datei ein. Es gibt keine Sprachdatei-Abrufe und keine neue Laufzeitabhängigkeit. Die Umschaltung funktioniert dadurch auch beim direkten Öffnen einer lokalen HTML-Datei. Deutsch ist die Vorgabe; die Auswahl wird unter `annoorganizer.gallery.language` im Browser gespeichert, sofern dessen Speicher verfügbar ist. Gesperrter Speicher verhindert die Umschaltung nicht. Ohne JavaScript bleibt die deutsche Oberfläche lesbar.

Eigene Profil-, Ordner- und Stempelnamen, Dateipfade, technische Rohwerte und aus dem Spiel übernommene Objekt-/DLC-Namen bleiben erhalten. Beschriftungen innerhalb der PNGs, Excel-Auswertungen, Startermenüs und Protokolle sind nicht Teil der HTML-Sprachumschaltung.

Neue oder geänderte Übersetzungen in beiden zentralen JSON-Dateien pflegen, danach die Vorlagen synchronisieren und die Demo-Seiten aktualisieren. Die Tests prüfen Ressourcen-/Platzhaltergleichheit, gültige Bindungen aller fünf Seiten, unveränderte Identitäten, sichere Einbettung, eigenständige Anno-Kopien sowie das JavaScript-Verhalten bei gesperrtem oder ungültigem Browserspeicher. `node --test tests/gallery_i18n_runtime.cjs tests/map_catalog_runtime.cjs` führt die JavaScript-Tests separat aus; die Python-Tests rufen sie bei verfügbarem Node.js ebenfalls auf.

[Englische Galerie-Vorschau mit DE/EN-Schalter](../anno117/docs/images/stamp-gallery-en.jpg). Alle fünf Galerien besitzen passende deutsche (`*-gallery.jpg`) und englische (`*-gallery-en.jpg`) Aufnahmen. Jede README verwendet ihre eigene Sprache, mit anklickbaren 360-Pixel-Vorschauen und 1264 Pixel Bildbreite. Der geprüfte Aufnahmeweg über die Edge-DevTools steht in `AGENTS.md`. Vorhandene Aufnahmen haben dieselbe Bildbreite.

## Vorlagen ändern

1. HTML, CSS oder `THEMES` ausschliesslich im zentralen Ordner `templates/` bearbeiten.
2. `python scripts/sync_gallery_templates.py --refresh-site` ausführen. Das synchronisiert die mitgelieferten Kopien und aktualisiert die Demo-Startseite sowie den Seitenrahmen der fünf bestehenden Demo-Snapshots. Die Demo-Daten und Bildverweise bleiben erhalten; dafür sind keine Spieldaten nötig.
3. `python scripts/sync_gallery_templates.py --check`, `python scripts/validate_site.py` und `python -m unittest discover -s tests -v` ausführen.
4. Persönliche Galerien mit dem jeweiligen AnnoOrganizer-Starter aktualisieren. Bei geänderten Demo-Inhalten die Demos zusätzlich regulär neu erzeugen.

Jeder Anno-Ordner enthält den Renderer und seine Vorlagen unter `tools/`. Diese Kopien werden automatisch aus den zentralen Quellen übernommen und von den Tests geprüft. Dadurch bleibt ein einzelner Anno-Ordner ohne den Rest des Repositories nutzbar. Keine Symlinks und keine zusätzlichen Laufzeit-Abhängigkeiten sind erforderlich. Die mitgelieferten Kopien nicht separat bearbeiten.

Reine Betriebs- und Dateistatusmeldungen gehören in die Protokolle, nicht in die Galerien. Karten, Bauplan-Eigenschaften und die für ihre Verwendung nötigen Hinweise bleiben sichtbar.

## Spielstand-Gruppen

Die gemeinsame Darstellung liegt in `templates/anno_save_summary.py`, die konservative Auslesung in `templates/anno_save_statistics.py`. Beide Dateien werden zusammen mit den Vorlagen in die eigenständig nutzbaren Spielordner synchronisiert. Die Exporter liefern getrennte Zusammenfassungen pro Partie; Details werden mit nativen, zunächst geschlossenen `details`/`summary`-Elementen dargestellt. Labels und Bevölkerungsstufen liegen in beiden zentralen Sprachressourcen. [Kennzahlen und Grenzen](save-statistics.de.md).

## Navigation der Bildansichten

Alle fünf Galerien öffnen Bilder in einem Dialog mit Zoom und PNG-Download. Die drei Kartengalerien verwenden gemeinsam `templates/map_viewer.html` und `map_viewer.js`, mit Originalgrösse/Einpassen, Zoom per Bildklick und DE/EN-Schalter im Dialog. Ohne JavaScript und bei modifizierten Klicks bleiben die normalen PNG-Links verfügbar. Bestehende Stempeldialoge und Kartendialoge verwenden dieselbe Verlaufslogik aus `templates/stamp_viewer.js` mit getrennten Verlaufsschlüsseln. Beim Öffnen entsteht ein Eintrag mit unveränderter Galerieadresse. Browser-Zurück schliesst ihn; Vorwärts öffnet dasselbe Bild wieder. Schliessen, Escape und Hintergrundklick führen ebenfalls zum Galerieeintrag zurück. Filter bleiben auf der Seite erhalten; Sprachwechsel erhalten den Zoomzustand. Bei gesperrtem Verlauf bleibt der Dialog bedienbar, die Browsernavigation steht dann jedoch nicht zur Verfügung. `node --test tests/map_viewer_runtime.cjs tests/stamp_viewer_runtime.cjs` prüft Navigation und Bildansichten.

## Bedienung des Kartenkatalogs

Anno 1404 stellt ebenso Suche, Edition, Sortierung und Profilwahl aus dem jeweiligen Verlaufseintrag wieder her.

117/1800 speichern Suche, Spielmodus, Sortierung und die genaue Profilwahl im aktuellen Browser-Verlaufseintrag. Nach dem Öffnen eines Kartenbildes stellt «Zurück» diese Auswahl und die Trefferzahl wieder her, auch wenn der Browser die Seite neu lädt. Getrennte Galerieeinträge bleiben unabhängig. Gesperrter Zugriff auf den Verlauf verhindert das Filtern nicht; die Wiederherstellung ist dann jedoch nicht verfügbar.

117 und 1800 verwenden dieselbe Profilrangliste, aufklappbare Seed-Liste, Suche, Modusfilter, Sortierung, Trefferzahl und zwei Rücksprung-Schaltflächen. Die Seed-Liste zählt die unterschiedlichen Seeds des Exports. Profillinks wählen ein exaktes Profil und springen zu den Filtern; der Rücksprung setzt Profil-, Such- und Modusfilter zurück und stellt den Fokus auf den gewählten Ranglistenlink. Die Suche verwendet `data-profiles` unabhängig von sichtbaren Kennzahlengruppen; rein numerische Eingaben treffen einen exakten Seed. Die Bedienelemente stehen unten bündig und umbrechen bei wenig Platz. Sortieren und DE/EN-Wechsel verschieben bestehende Karten und erhalten geöffnete Gruppen. In allen drei Spielen steht Geld vor Bevölkerung, Wohnhäusern und Schiffen; dadurch bleiben Bevölkerung und Wohnhäuser benachbart. Regressionstests führen die gemeinsame Laufzeit auch mit Karten ohne optionalen `.profiles`-Absatz aus.

Das gemeinsame `anno_map_variants.py` gruppiert vollständige Partiehistorien nach verständlichen Kartenoptionen und vermeidet Aufteilungen durch Patch-Änderungen. Jede Partie erscheint in genau einer Variante. Export und vorausgewählte Sortierung zeigen den neuesten Save zuerst. Jede Kartenkachel, auch bei 1404, enthält ausserhalb geschlossener Gruppen einen normalen Link zum gemeinsamen Anker `gallery-top`.

Spielbezogene Einstellungsbezeichnungen werden über `anno_game_settings.py`, `game_settings.json` und ausdrückliche `gameSetting.*`-Sprachbindungen erzeugt. Sie nehmen nicht an der allgemeinen Worterkennung teil, damit Normal/Regular/Medium nicht vermischt werden. [Quellen und Enum-Zuordnungen](game-settings.de.md).

## Temporäre Arbeitsdateien

Karten- und Stempelexporte erzeugen Zwischenstände ausserhalb von OneDrive. Standard ist der Benutzer-Tempordner. Über die optionale Umgebungsvariable `ANNOORGANIZER_TEMP_DIR` lässt sich lokal ein vorhandener beschreibbarer absoluter Ordner vorgeben. Fehlende, unbenutzbare oder in OneDrive liegende Vorgaben fallen auf Benutzer-Temp zurück. Das Programm enthält keine rechnerspezifischen Vorgabepfade. Nach einer Änderung der Umgebung die Anwendung neu starten. Konfigurierte oder erkennbare OneDrive-Pfade werden abgewiesen. Fertige Galerien, Caches und Protokolle behalten ihre konfigurierten Ziele. Veröffentlichung und Rücksicherung unterstützen unterschiedliche Laufwerke für temporäre Dateien und Ausgaben. Scheitert die Wiederherstellung, bleiben Arbeitsordner und Rücksicherungen erhalten; die Fehlermeldung nennt ihren Ort und `RECOVERY.json` verzeichnet offene Dateien, sofern sie geschrieben werden kann. Diese Rücksicherungen erst nach erfolgreicher Wiederherstellung entfernen.

## Bebilderte Benutzeranleitung

Die Demo-Startseite verlinkt `site/guide/index.html`. Der Desktop-Button **Anleitung** öffnet `docs/user-guide.html` offline in der gewählten Sprache; das Windows-Paket enthält diese Seite und ihre Bilder. Beide HTML-Fassungen entstehen aus `docs/desktop.md` und `docs/desktop.de.md` mit `templates/user_guide.html`, `templates/user_guide.js` und den gemeinsamen Sprachressourcen. Die Markdown-Quellen bearbeiten und danach `scripts/sync_gallery_templates.py --refresh-site` ausführen; `--check` prüft auch beide erzeugten Seiten und die acht kopierten Anleitungsbilder. `scripts/validate_site.py` prüft alle sieben öffentlichen Seiten. Befehlszeilen- und erweiterte Konfigurationshinweise bleiben in den separaten `desktop-reference`-Anleitungen.
