# AnnoOrganizer

[![Tests](https://github.com/Morima79/AnnoOrganizer/actions/workflows/tests.yml/badge.svg?branch=main&event=push)](https://github.com/Morima79/AnnoOrganizer/actions/workflows/tests.yml)
[![Aktuelle Version](https://img.shields.io/github/v/release/Morima79/AnnoOrganizer?sort=semver&label=Release)](https://github.com/Morima79/AnnoOrganizer/releases/latest)
[![Demo-Galerien](https://img.shields.io/badge/Demo-Galleries-2ea44f)](https://morima79.github.io/AnnoOrganizer/)

[English](README.md) · [Deutsch](README.de.md) · [Changelog](CHANGELOG.md)

Lokale Windows-Werkzeuge für **Anno 117: Pax Romana**, **Anno 1800** und **Anno 1404** einschliesslich Venedig und History Edition. Sie erstellen HTML-Galerien, Bauplan-PNGs, rekonstruierte Karten und Excel-Auswertungen aus deinen lokalen Dateien. Ein laufendes Spiel oder Codex wird nicht benötigt.

| Funktion | Anno 117 | Anno 1800 | Anno 1404 |
|---|---|---|---|
| Spielstände nach Seed und Kartenvariante auswerten | Ja | Ja | Ja |
| Kartengalerie und Excel-Ausgabe | Ja | Ja | Ja |
| Stempelgalerie mit Bauplan-PNGs | Ja | Ja | Noch nicht implementiert |
| Zusätzliche Stempelfilter | Ceres-Feldgrössen, kosmetische DLCs | DLCs, Traktoren, Silos, Strom, Rathaus, Handelskammer | — |

**Quelldateien werden ausschliesslich gelesen.** Konsolenausgaben liegen standardmässig in `<spiel>/local-data/`; neue Desktop-Konfigurationen verwenden `Dokumente/AnnoOrganizer/Anno <Nummer>/`. Der Ausgabeordner ist konfigurierbar. Jeder Anno-Ordner ist unabhängig nutzbar und enthält seinen eigenen Starter, Einstellungen, Abhängigkeiten, Anleitungen und Lizenz. Der Hauptstarter bietet zusätzlich ein gemeinsames Auswahlmenü.

## Online-Demos und Releases

[Alle fünf Galerien im Browser ausprobieren](https://morima79.github.io/AnnoOrganizer/) · [Windows-Paket herunterladen (ZIP)](https://github.com/Morima79/AnnoOrganizer/releases/download/v0.1.14/AnnoOrganizer-v0.1.14-windows-x64.zip) · [Alle Versionen und Quellcode](https://github.com/Morima79/AnnoOrganizer/releases/latest)

| Spiel | Kartengalerie | Stempelgalerie |
|---|---|---|
| Anno 117 | [Demo](https://morima79.github.io/AnnoOrganizer/anno117/maps/) | [Demo](https://morima79.github.io/AnnoOrganizer/anno117/stamps/) |
| Anno 1800 | [Demo](https://morima79.github.io/AnnoOrganizer/anno1800/maps/) | [Demo](https://morima79.github.io/AnnoOrganizer/anno1800/stamps/) |
| Anno 1404 | [Demo](https://morima79.github.io/AnnoOrganizer/anno1404/maps/) | — |

Die Online-Demos benötigen keine Installation. Sie sind geprüfte Momentaufnahmen der mitgelieferten Beispiele mit interaktiven Filtern und Bildvorschauen. Die Veröffentlichung erfolgt über GitHub Pages; persönliche Einstellungen und lokale Ausgaben werden nicht hochgeladen.

Demo-Startseite und Galerien verwenden denselben **DE/EN-Schalter**. Die gespeicherte Sprachwahl wird beim Wechsel zwischen diesen Seiten übernommen, sofern Browserspeicher verfügbar ist.

Demo-Excel herunterladen (deutsche Arbeitsmappen): [Anno 117](site/downloads/anno117-map-demo.xlsx) / [ZIP](site/downloads/anno117-map-demo.zip) · [Anno 1800](site/downloads/anno1800-map-demo.xlsx) / [ZIP](site/downloads/anno1800-map-demo.zip) · [Anno 1404](site/downloads/anno1404-map-demo.xlsx) / [ZIP](site/downloads/anno1404-map-demo.zip). Das ZIP enthält die Kartenbilder; für funktionierende Bildlinks vollständig entpacken. Kennzahlen und Geld erscheinen als Ganzzahlen mit Tausendertrennzeichen, Seeds ohne Trennzeichen. Datum und Spielzeit behalten ihre bisherigen Formate.

Kartenbilder öffnen in allen drei Spielen einen Dialog mit Originalgrösse/Einpassen, PNG-Download und DE/EN-Schalter. Browser-Zurück schliesst das Bild und erhält die Galeriefilter; Vorwärts öffnet es wieder.

## Galerie-Vorschau

Die Vorschauen zeigen alle fünf mitgelieferten Demo-Galerien auf Deutsch; ein Klick öffnet das Bild in voller Auflösung. Die englische README verwendet die entsprechenden englischen Aufnahmen. Die Kartendemos enthalten Einwohner- und Wohnhauszahlen in kompakten aufklappbaren Gruppen. Alle Galerien verwenden Spiel-Logos und passende Farben; Anno 1404 eine helle Pergamentoptik.

| Galerie | Anno 117 | Anno 1800 | Anno 1404 |
|---|---|---|---|
| Stempel | [<img src="anno117/docs/images/stamp-gallery.jpg" alt="Anno-117-Demo mit Stadtbauplänen, Ceres-Filtern und Lavendel-Ausbaureserve" width="360">](anno117/docs/images/stamp-gallery.jpg) | [<img src="anno1800/docs/images/stamp-gallery.jpg" alt="Anno-1800-Demo mit Filtern für Traktoren, Silos, Strom, Rathaus und Handelskammer" width="360">](anno1800/docs/images/stamp-gallery.jpg) | Nicht implementiert |
| Karten | [<img src="anno117/docs/images/map-gallery.jpg" alt="Anno 117 Demo-Kartengalerie mit Bevölkerung und Wohnhäusern" width="360">](anno117/docs/images/map-gallery.jpg) | [<img src="anno1800/docs/images/map-gallery.jpg" alt="Anno 1800 Demo-Kartengalerie mit Bevölkerung und Wohnhäusern" width="360">](anno1800/docs/images/map-gallery.jpg) | [<img src="anno1404/docs/images/map-gallery.jpg" alt="Anno 1404 Demo-Kartengalerie mit Bevölkerung und Wohnhäusern" width="360">](anno1404/docs/images/map-gallery.jpg) |

## Schnellstart

1. **Python 3.11 oder neuer** installieren, falls es noch fehlt.
2. Das Repository herunterladen, entpacken und **Launch.cmd** doppelklicken.
3. Eine **Anno-Demo** wählen. Steam-/Ubisoft-Installationen werden nach Möglichkeit automatisch erkannt. Falls das nicht klappt, nur den Installationspfad eingeben. Für die Anno-1404-Demo ist keine Spielinstallation erforderlich.

Der Starter erstellt die lokale Python-Umgebung, installiert beim ersten Start die benötigten Pakete und legt fehlende Einstellungen an. Für diese erste Paketinstallation wird eine Internetverbindung benötigt. Es muss nichts ins Spiel kopiert werden. Nach der Auswertung öffnen sich die Galerien automatisch.

**Allenfalls muss nur der Spielpfad geprüft oder eingegeben werden.** Die Pfade der Demo-Spielstände und -Stempel sind bereits eingerichtet. Sowohl der Installationsordner als auch dessen `maindata`-Unterordner werden akzeptiert. Vorhandene persönliche Einstellungen bleiben erhalten; die Demo verwendet getrennte Eingaben und einen eigenen Ausgabeunterordner.

| Mitgelieferte Beispiele | Spielstände | Stempel |
|---|---:|---:|
| Anno 117 | 3 unterschiedliche Seeds | 5 Layouts, darunter angepasste Städte und Lavendelvarianten |
| Anno 1800 | 3 unterschiedliche Seeds | 5 Layouts aus allen vier Regionen |
| Anno 1404 | 3 Saves: Grundspiel, Venedig, History Edition | Nicht implementiert |

Die Beispiele umfassen zusammen rund **7,4 MB** und wurden aus den Dateien des Projektinhabers kopiert. Ein Demo-Lauf liest nur diese Beispiele und schreibt nach `<eingestellte Ausgabe>/demo/`; persönliche Spielordner werden nicht ausgewertet. Details: [117](anno117/demo/README.de.md), [1800](anno1800/demo/README.de.md), [1404](anno1404/demo/README.de.md).

## Desktop-Vorschau

Mit `Launch.cmd --gui` öffnet sich eine deutsche oder englische Oberfläche mit Spielauswahl, Pfadverwaltung, Konfigurationsimport, Demo-/Exportaktionen und Abbruch. Der Quellcode-Start benötigt Python einschliesslich Tkinter. Der ergänzte Windows-Build erstellt ausserdem ein portables EXE-Paket mit Laufzeit und Prüfsumme; lokale Builds sind noch keine veröffentlichten Releases. [Bedienung und aktuelle Grenzen](docs/desktop.de.md).

## Kommandozeile

```powershell
.\.venv\Scripts\python.exe launch.py --game anno117 --action demo
.\.venv\Scripts\python.exe launch.py --game anno1800 --action demo
.\.venv\Scripts\python.exe launch.py --game anno1404 --action demo
```

`--action analyze` erstellt die Karten-/Excel-Auswertung der konfigurierten Eingaben. `--action stamps` erzeugt die Stempelgalerie für 117 und 1800. Vor einer Aktualisierung die bisherige Arbeitsmappe in Excel schliessen. Für eigene Dateien später `account`, `stamps` beziehungsweise `save_folders` in der jeweiligen `settings.json` anpassen. Für den Demo-Einstieg sind diese Änderungen nicht nötig.

Die Installation kann alternativ manuell erfolgen:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Optionen und Einstellungen

- `--check`: Pfade und Python-Pakete prüfen, ohne Ausgaben anzulegen.
- `--non-interactive`: mit explizitem `--game` und `--action` ohne Abfragen oder automatische Einstellungsanlage starten; vorhandene Konfiguration verwenden. Mit `--no-open` auch den Browserstart unterdrücken.
- `--no-open`: aktualisieren, ohne den Browser zu öffnen.
- `--rescan`: bei `--action analyze` den Metadaten-Zwischenspeicher ignorieren.
- `--config PFAD`: eine andere lokale Einstellungsdatei verwenden.
- `--init-settings`: fehlende Einstellungen anlegen; vorhandene erhalten.
- `--help`: alle Kommandozeilenoptionen anzeigen.

Beim regulären Start werden fehlende Einstellungen automatisch angelegt. Jeder Spielordner besitzt eine eigene `settings.json` mit englischen Schlüsseln und Schemaversion 1. `settings.example.json` dient als Vorlage. `${DOCUMENTS}` berücksichtigt den tatsächlichen Windows-Dokumentenordner samt OneDrive-Umleitung; `${HOME}` verweist auf den Benutzerordner. Relative Pfade beziehen sich auf den Ordner der Konfigurationsdatei.

Die technische Benennung und der Code sind Englisch. **Alle fünf Galerien bieten einen DE/EN-Schalter**, auch beim direkten Offline-Öffnen. Die Auswahl wird nach Möglichkeit im Browser gespeichert. Startermenüs und Protokollmeldungen bleiben Deutsch. Ausführliche Anleitungen: [Einstellungen](docs/settings.de.md), [Formate und Grenzen](docs/formats-and-limitations.de.md). Einzelne Werkzeuge: [Anno 117](anno117/README.de.md), [Anno 1800](anno1800/README.de.md), [Anno 1404](anno1404/README.de.md).

## Struktur und Ausgaben

```text
launch.py                 Gemeinsames Auswahlmenü
anno117/                  Eigenständig nutzbare Anno-117-Werkzeuge
anno1800/                 Eigenständig nutzbare Anno-1800-Werkzeuge
anno1404/                 Eigenständig nutzbare Anno-1404-Werkzeuge
  Launch.cmd              Windows-Starter dieses Spiels
  launch.py               Einstiegspunkt dieses Spiels
  settings.example.json   Öffentliche Beispielkonfiguration
  settings.json           Persönliche Einstellungen, von Git ausgeschlossen
  tools/                  Leser, Exporte und HTML-Vorlagen
  demo/                   Beispiel-Saves, Stempel und Dateimanifeste
  local-data/             Erzeugte Ausgaben, von Git ausgeschlossen
tests/                    Automatisierte Regressionstests
docs/                     Ausführliche Dokumentation auf Deutsch
```

Die Galerien liegen unter `stamps/stamp-gallery.html` und `reports/map-gallery.html` im eingestellten Ausgabeordner. Protokolle stehen unter `logs/`. Stempelnamen und Spielordner behalten ihre vorhandenen Bezeichnungen. Alte Ausgaben mit deutschen Dateinamen bleiben erhalten; neue Ausgaben verwenden die englischen Pfade.

## Entwicklung und Veröffentlichung

Vorgemerkte Erweiterungen stehen in der [Wunschliste](docs/wishlist.de.md).

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Der vorbereitete GitHub-Actions-Workflow testet unter Windows mit synthetischen Daten. Nur die ausdrücklich ausgewählten Demo-Saves und Demo-Stempel gehören ins Repository. Andere persönliche Einstellungen, Stempel, Spielstände, Galerien ausserhalb der freigegebenen `site/`-Momentaufnahmen, Spieldaten, Caches und Sicherungen bleiben ausgeschlossen. `.gitignore` berücksichtigt neue und bisherige lokale Dateinamen. Python-Abhängigkeiten werden über pip installiert. Die Spiel-Logos sind zur Kennzeichnung enthalten. Bibliotheks- und Spieldatenarchive werden nicht mitgeliefert.

Inoffizielles Projekt ohne Verbindung zu Ubisoft. Die Ausgaben sind Rekonstruktionen und keine Zusage über Bauplatz, Versorgung, Reichweite oder Spielbetrieb. Der Werkzeugcode steht unter der [MIT-Lizenz](LICENSE).

## Aktuelle Spielstand-Kennzahlen

Die Kartengalerie zeigt pro Partie den neuesten Save mit Bevölkerung, Vermögen, Bilanz, Wohnhäusern und Schiffen. Jede Kennzahlengruppe bleibt zunächst geschlossen; Stufen, Baupläne und weitere Details erscheinen erst beim Anklicken. Frühere Save- und Spielzeitangaben stehen unter **Save-Details**. Nicht zuverlässig auslesbare Werte werden als **nicht verfügbar** angezeigt. Excel erhält das zusätzliche Blatt **Aktuelle Spielstände**. [Datenquellen und Grenzen](docs/save-statistics.de.md).

## Nutzung und Weiterveröffentlichung

Die Verwendung dieser Skripte erfolgt auf eigene Gefahr. Sie werden ohne Gewähr bereitgestellt. Es gilt der Gewährleistungs- und Haftungsausschluss in der [Lizenz](LICENSE).

Bei einer Weiterveröffentlichung der Skripte, auch in geänderter Form, müssen der Urheberhinweis auf **Morima79** samt Verweis auf das [Original-Repository AnnoOrganizer](https://github.com/Morima79/AnnoOrganizer) und die MIT-Lizenzhinweise erhalten bleiben.

## Galerie-Vorlagen

Karten- und Stempelgalerien verwenden jeweils eine gemeinsame Seitenvorlage mit an die Spieloberfläche angelehnten Farben. Die Anno-Ordner bleiben eigenständig nutzbar. Pflege und Synchronisation sind in der [Vorlagen-Anleitung](docs/gallery-templates.de.md) beschrieben.

## Automatische Veröffentlichung

Release-ZIPs und die Demo-Seite werden über GitHub Actions veröffentlicht. Details zur Release-Erstellung, GitHub-Pages-Einrichtung und Demo-Aktualisierung stehen in der [Veröffentlichungsanleitung](docs/publishing.de.md).

Save-Anzahl und Spielzeitangaben stehen pro Partie in deren Save-Details. Kartenvarianten zeigen nur die Gesamtsummen; Spielzeitvergleiche bleiben innerhalb derselben Partie.

Karten- und Spieleinstellungen verwenden geprüfte DE/EN-Spieltexte und kontextbezogene Wertzuordnungen. Unbekannte Werte bleiben erkennbar. [Originalbezeichnungen und Grenzen](docs/game-settings.de.md).
