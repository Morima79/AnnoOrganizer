# Anno 1404, Venedig und History Edition

[![Tests](https://github.com/Morima79/AnnoOrganizer/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Morima79/AnnoOrganizer/actions/workflows/tests.yml)
[![Aktuelle Version](https://img.shields.io/github/v/release/Morima79/AnnoOrganizer?sort=semver&label=Release)](https://github.com/Morima79/AnnoOrganizer/releases/latest)
[![Demo-Galerien](https://img.shields.io/badge/Demo-Galleries-2ea44f)](https://morima79.github.io/AnnoOrganizer/)

[English](README.md) · [Deutsch](README.de.md)

Dieser Ordner ist unabhängig nutzbar und enthält seinen eigenen Starter, Einstellungen, Abhängigkeiten und Lizenz. Die anderen Anno-Ordner und der Hauptstarter werden nicht benötigt. Quelldateien werden ausschliesslich gelesen. Die technische Benennung ist Englisch; Menüs, Meldungen und Galerien bleiben Deutsch.

## Vorschau

Einheitlicher Galerie-Kopfbereich und drei Kartenvarianten aus Anno 1404, Venedig und der History Edition.

[Kompakte Kartengalerie als HTML-Demo öffnen](https://morima79.github.io/AnnoOrganizer/anno1404/maps/)

## Schnellstart

Falls nötig Python 3.11 oder neuer installieren. Danach **Launch.cmd** doppelklicken und **Demo** wählen oder Enter drücken. Die Python-Umgebung und benötigten Pakete werden beim ersten Start automatisch eingerichtet; dafür wird eine Internetverbindung benötigt. Fehlende Einstellungen legt der Starter selbst an.

Dieser Ordner enthält **3 Spielstände und 0 Stempel**. Die Demo verwendet diese Dateien, ohne persönliche Einstellungen zu verändern. Für 117 und 1800 wird die Installation nach Möglichkeit automatisch erkannt; andernfalls wird nur der Spielpfad abgefragt. Für 1404 ist keine Spielinstallation nötig. Save-/Stempelpfade müssen nicht bearbeitet und keine Dateien ins Spiel importiert werden. Die Ergebnisse öffnen sich im Browser und liegen unter `<eingestellte Ausgabe>/demo/`.

[Mitgelieferte Beispiele](demo/README.de.md). Nach der Einrichtung geht auch:

```powershell
.\.venv\Scripts\python.exe launch.py --action demo
```

## Starten

Karten-/Spielstandgalerie mit Excel-Ausgabe:

```powershell
.\.venv\Scripts\python.exe launch.py --action analyze
```

Eine Stempelgalerie ist für Anno 1404 noch nicht implementiert.

`--check` prüft Pfade ohne neue Ausgaben. `--no-open` unterdrückt den Browserstart. `--config PFAD` wählt eine andere Einstellungsdatei. `--rescan` ignoriert den Metadaten-Zwischenspeicher der Spielstandauswertung. Die bestehende Excel-Arbeitsmappe vor dem Aktualisieren schliessen.

Neue Ausgaben liegen standardmässig in `local-data/` neben dem Starter; übernommene Ausgabeordner bleiben erhalten. Die Galeriepfade sind `reports/map-gallery.html` und bei unterstützten Spielen `stamps/stamp-gallery.html`. Protokolle stehen unter `logs/` im Ausgabeordner. Stempelnamen, eigene Layouts und Quelldateien werden nicht umbenannt oder verändert.

- [Einstellungen](docs/settings.de.md)
- [Formate und Grenzen](docs/formats-and-limitations.de.md)
- [MIT-Lizenz](LICENSE)

Inoffizielles Projekt ohne Verbindung zu Ubisoft. Spiel-Logos sind zur Kennzeichnung enthalten und nicht Teil der MIT-Lizenz des Werkzeugcodes; Spieldatenarchive werden nicht mitgeliefert; Python-Abhängigkeiten stehen in `requirements.txt`.

Galerien lassen sich oben rechts mit **DE / EN** umschalten, in Stempelgalerien auch in der Grossansicht. Suche, Filter und offene Ansichten bleiben erhalten. Die Sprachwahl wird nach Möglichkeit im Browser gespeichert. Beide Sprachen sind in der HTML-Datei enthalten und funktionieren offline. Eigene Namen, Dateipfade, Beschriftungen in PNGs und Excel-Auswertungen behalten ihre bisherige Sprache.

## Aktuelle Spielstand-Kennzahlen

Die Kartengalerie zeigt pro Partie den neuesten Save mit Bevölkerung, Vermögen, Bilanz, Wohnhäusern und Schiffen. Jede Kennzahlengruppe bleibt zunächst geschlossen; Stufen, Baupläne und weitere Details erscheinen erst beim Anklicken. Frühere Save- und Spielzeitangaben stehen unter **Save-Details**. Nicht zuverlässig auslesbare Werte werden als **nicht verfügbar** angezeigt. Excel erhält das zusätzliche Blatt **Aktuelle Spielstände**. [Datenquellen und Grenzen](docs/save-statistics.de.md).

## Nutzung und Weiterveröffentlichung

Die Verwendung dieser Skripte erfolgt auf eigene Gefahr. Sie werden ohne Gewähr bereitgestellt. Es gilt der Gewährleistungs- und Haftungsausschluss in der [Lizenz](LICENSE).

Bei einer Weiterveröffentlichung der Skripte, auch in geänderter Form, müssen der Urheberhinweis auf **Morima79** samt Verweis auf das [Original-Repository AnnoOrganizer](https://github.com/Morima79/AnnoOrganizer) und die MIT-Lizenzhinweise erhalten bleiben.

## Online-Demos

[Map gallery / Kartengalerie](https://morima79.github.io/AnnoOrganizer/anno1404/maps/) · [All demos / Alle Demos](https://morima79.github.io/AnnoOrganizer/)

Die Online-Galerien zeigen die mitgelieferten Beispiele ohne Installation. Automatische Releases und GitHub Pages sind in der [Veröffentlichungsanleitung](../docs/publishing.de.md) beschrieben.
