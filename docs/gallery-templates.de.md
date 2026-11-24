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

## Farben

Die Farben orientieren sich an der jeweiligen Spieloberfläche. Die transparenten Logos fügen sich in diese Flächen ein. `THEMES` im gemeinsamen Renderer legt Hintergrund sowie lesbare Text-, Rahmen- und Linkfarben fest:

- Anno 117: Beige (`#f1e5cc`).
- Anno 1800: Dunkelblau (`#173345`).
- Anno 1404: Helle Pergamentoptik (`#f3ead8`) mit Braun- und Goldtönen.

Bei Kartengalerien gilt dieses Thema für die gesamte Seite. Bei Stempelgalerien gilt es für den Header-Banner; der Bereich mit Suche und Bauplänen bleibt hell. Das Logo selbst bekommt keine separate Hintergrundfläche. Beide Stempel-Fusszeilen enthalten ausschliesslich den Aktualisierungszeitpunkt (`Stand:` / `Updated:`).

## Sprachen DE / EN

Alle fünf Galerien besitzen einen gemeinsamen Sprachschalter im Kopfbereich. In Stempelgalerien gibt es denselben Schalter zusätzlich in der modalen Grossansicht. Beim Umschalten bleiben Suche, Filterwerte, Sortierung, Profilwahl, aufgeklappte Details und die Bildansicht samt Zoom erhalten. `html.lang`, Seitentitel, Platzhalter und zugängliche Bild-/Schaltflächenbeschreibungen wechseln ebenfalls.

Die Demo-Startseite verwendet denselben DE/EN-Schalter und dieselbe gespeicherte Sprachwahl. Ein Wechsel zur Galerie und über den Demo-Rücklink zurück erhält die gewählte Sprache, sofern Browserspeicher verfügbar ist. Titel, Meta-Beschreibung, Einführung, Galerie-Links und Fusszeile stammen aus den zentralen `demo.*`-Ressourcen. Die Vorlage `templates/demo_index.html` wird mit `--refresh-site` nach `site/index.html` geschrieben; `--check` erkennt eine veraltete Startseite. [Englische Startseiten-Vorschau](images/demo-home-en.jpg).

Die zentralen Sprachressourcen liegen in [locales/de.json](../templates/locales/de.json) und [locales/en.json](../templates/locales/en.json). Beide Dateien verwenden dieselben stabilen Schlüssel und Platzhalter, beispielsweise `stamp.count` mit `{shown}` und `{total}`. `.one`-Varianten behandeln Einzahlformen. Fehlende Schlüssel oder abweichende Platzhalter führen beim Export zu einer verständlichen Fehlermeldung.

[anno_i18n.py](../templates/anno_i18n.py) bindet bekannte Oberflächentexte und erzeugte Anzeigen an Ressourcenschlüssel. Explizite Markierungen wie `<span data-i18n="filters.allRegions">Alle Regionen</span>` können direkt in Vorlagen stehen. Für dynamische Texte verwenden die Exporter `galleryI18n.t('stamp.count', {shown, total})` und reagieren auf `gallerylanguagechange`. Nur Text und Beschriftungen ändern sich; interne Optionswerte bleiben stabil. Eigene Namen und Pfade werden von der Bindung ausgeschlossen. Zusätzliche unveränderte Inhalte können mit `data-i18n-ignore` markiert werden.

Der Renderer bettet beide JSON-Ressourcen sowie [gallery_i18n.js](../templates/gallery_i18n.js) und das Schalter-CSS in jede erzeugte HTML-Datei ein. Es gibt keine Sprachdatei-Abrufe und keine neue Laufzeitabhängigkeit. Die Umschaltung funktioniert dadurch auch beim direkten Öffnen einer lokalen HTML-Datei. Deutsch ist die Vorgabe; die Auswahl wird unter `annotools.gallery.language` im Browser gespeichert, sofern dessen Speicher verfügbar ist. Gesperrter Speicher verhindert die Umschaltung nicht. Ohne JavaScript bleibt die deutsche Oberfläche lesbar.

Eigene Profil-, Ordner- und Stempelnamen, Dateipfade, technische Rohwerte und aus dem Spiel übernommene Objekt-/DLC-Namen bleiben erhalten. Beschriftungen innerhalb der PNGs, Excel-Auswertungen, Startermenüs und Protokolle sind nicht Teil der HTML-Sprachumschaltung.

Neue oder geänderte Übersetzungen in beiden zentralen JSON-Dateien pflegen, danach die Vorlagen synchronisieren und die Demo-Seiten aktualisieren. Die Tests prüfen Ressourcen-/Platzhaltergleichheit, gültige Bindungen aller fünf Seiten, unveränderte Identitäten, sichere Einbettung, eigenständige Anno-Kopien sowie das JavaScript-Verhalten bei gesperrtem oder ungültigem Browserspeicher. `node --test tests/gallery_i18n_runtime.cjs tests/map_catalog_runtime.cjs` führt die JavaScript-Tests separat aus; die Python-Tests rufen sie bei verfügbarem Node.js ebenfalls auf.

[Englische Galerie-Vorschau mit DE/EN-Schalter](../anno117/docs/images/stamp-gallery-en.jpg). Alle fünf README-Vorschauen zeigen die aktuellen deutschen Demos mit Sprachschalter. Der geprüfte Aufnahmeweg über die Edge-DevTools steht in `AGENTS.md`. Vorhandene Aufnahmen haben dieselbe Bildbreite.

## Vorlagen ändern

1. HTML, CSS oder `THEMES` ausschliesslich im zentralen Ordner `templates/` bearbeiten.
2. `python scripts/sync_gallery_templates.py --refresh-site` ausführen. Das synchronisiert die mitgelieferten Kopien und aktualisiert die Demo-Startseite sowie den Seitenrahmen der fünf bestehenden Demo-Snapshots. Die Demo-Daten und Bildverweise bleiben erhalten; dafür sind keine Spieldaten nötig.
3. `python scripts/sync_gallery_templates.py --check`, `python scripts/validate_site.py` und `python -m unittest discover -s tests -v` ausführen.
4. Persönliche Galerien mit dem jeweiligen AnnoOrganizer-Starter aktualisieren. Bei geänderten Demo-Inhalten die Demos zusätzlich regulär neu erzeugen.

Jeder Anno-Ordner enthält den Renderer und seine Vorlagen unter `tools/`. Diese Kopien werden automatisch aus den zentralen Quellen übernommen und von den Tests geprüft. Dadurch bleibt ein einzelner Anno-Ordner ohne den Rest des Repositories nutzbar. Keine Symlinks und keine zusätzlichen Laufzeit-Abhängigkeiten sind erforderlich. Die mitgelieferten Kopien nicht separat bearbeiten.

Reine Betriebs- und Dateistatusmeldungen gehören in die Protokolle, nicht in die Galerien. Karten, Bauplan-Eigenschaften und die für ihre Verwendung nötigen Hinweise bleiben sichtbar.

## Spielstand-Gruppen

Die gemeinsame Darstellung liegt in `templates/anno_save_summary.py`, die konservative Auslesung in `templates/anno_save_statistics.py`. Beide Dateien werden zusammen mit den Vorlagen in die eigenständig nutzbaren Spielordner synchronisiert. Die Exporter liefern getrennte Zusammenfassungen pro Partie; Details werden mit nativen, zunächst geschlossenen `details`/`summary`-Elementen dargestellt. Labels und Bevölkerungsstufen liegen in beiden zentralen Sprachressourcen. [Kennzahlen und Grenzen](save-statistics.de.md).

## Bedienung des Kartenkatalogs

117 und 1800 verwenden dieselbe Profilrangliste, aufklappbare Seed-Liste, Suche, Modusfilter, Sortierung, Trefferzahl und zwei Rücksprung-Schaltflächen. Die Seed-Liste zählt die unterschiedlichen Seeds des Exports. Profillinks wählen ein exaktes Profil und springen zu den Filtern; der Rücksprung setzt Profil-, Such- und Modusfilter zurück und stellt den Fokus auf den gewählten Ranglistenlink. Die Suche verwendet `data-profiles` unabhängig von sichtbaren Kennzahlengruppen; rein numerische Eingaben treffen einen exakten Seed. Die Bedienelemente stehen unten bündig und umbrechen bei wenig Platz. Sortieren und DE/EN-Wechsel verschieben bestehende Karten und erhalten geöffnete Gruppen. In allen drei Spielen steht Geld vor Bevölkerung, Wohnhäusern und Schiffen; dadurch bleiben Bevölkerung und Wohnhäuser benachbart. Regressionstests führen die gemeinsame Laufzeit auch mit Karten ohne optionalen `.profiles`-Absatz aus.

Das gemeinsame `anno_map_variants.py` gruppiert vollständige Partiehistorien nach verständlichen Kartenoptionen und vermeidet Aufteilungen durch Patch-Änderungen. Jede Partie erscheint in genau einer Variante. Export und vorausgewählte Sortierung zeigen den neuesten Save zuerst. Jede Kartenkachel, auch bei 1404, enthält ausserhalb geschlossener Gruppen einen normalen Link zum gemeinsamen Anker `gallery-top`.

Spielbezogene Einstellungsbezeichnungen werden über `anno_game_settings.py`, `game_settings.json` und ausdrückliche `gameSetting.*`-Sprachbindungen erzeugt. Sie nehmen nicht an der allgemeinen Worterkennung teil, damit Normal/Regular/Medium nicht vermischt werden. [Quellen und Enum-Zuordnungen](game-settings.de.md).
