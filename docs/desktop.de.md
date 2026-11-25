# Desktop-Oberfläche

[English](desktop.md) · [Deutsch](desktop.de.md) · [README](../README.de.md)

Die Desktop-Vorschau konfiguriert und startet die vorhandenen Werkzeuge für Anno 117, 1800 und 1404. Sie läuft derzeit aus dem Quellcode mit Python 3.11 oder neuer einschliesslich Tkinter. Ein portables EXE-Paket ist noch nicht vorhanden. Die bestehenden Konsolenstarter und einzeln kopierten Spielordner funktionieren weiterhin.

## Start und erste Demo

Im Hauptordner starten:

```powershell
.\Launch.cmd --gui
```

Der Starter richtet wie bisher die Python-Umgebung und benötigten Pakete ein. Mit einer bereits vorbereiteten Umgebung geht auch:

```powershell
.\.venv\Scripts\python.exe launch.py --gui
```

Links ein Spiel wählen, **Mitgelieferte Demo** aktiviert lassen und **Erzeugen** drücken. Die Beispiele sind eingerichtet. Anno 117 und 1800 benötigen ihre Spielressourcen; eine leere Spielinstallation wird nach Möglichkeit automatisch erkannt. Andernfalls den Spielordner oder `maindata` auswählen. Die Anno-1404-Demo benötigt keine Spielinstallation. Demos lesen ausschliesslich die mitgelieferten Beispiele.

Das absolute Ausgabeziel steht vor dem Start unter den Eingaben. Während der Verarbeitung bleibt das Fenster bedienbar; Spielwechsel und Konfigurationsänderungen sind gesperrt. Nach Erfolg lassen sich **Galerien öffnen** und **Ausgabeordner** verwenden. Die Galerien öffnen im Standardbrowser. Es werden keine privaten Daten hochgeladen.

## Einstellungen bearbeiten und übernehmen

- **Datei verwenden**: Eine bestehende `settings.json` auswählen und die aufgelösten Ziele prüfen. Die Datei bleibt am bisherigen Ort; erst **Speichern** ändert sie. Relative Pfade bleiben auf ihren Ordner bezogen.
- **Kopie importieren**: Die Quelle auswählen und Importziel sowie aufgelöste Pfade prüfen. Die Kopie wird beim Bestätigen gespeichert. Bekannte relative Pfade und implizite Ausgabeziele werden so übernommen, dass sie auf dieselben Orte zeigen. Unbekannte Schlüssel bleiben erhalten. Die Quelle bleibt unverändert; Quelle und Ziel dürfen nicht dieselbe Datei sein. Eine bestehende Zieldatei wird nur nach zusätzlicher Bestätigung mit Sicherung ersetzt.
- **Standarddatei**: Zur gespeicherten GUI-Konfiguration dieses Spiels zurückkehren oder neue Standardwerte im Speicher laden. Eine externe Dateiauswahl wird erst beim Speichern der gewählten Standarddatei ersetzt.
- **Neu laden**: Die aktuelle Datei erneut lesen. Ungespeicherte Änderungen werden nur nach Bestätigung verworfen.
- **Speichern**: Die angezeigten Werte in die unter **Einstellungsdatei** genannte Datei schreiben. Der bisherige Inhalt wird unter `backups/` neben der Datei gesichert. Wenn eine andere Anwendung die Datei seit dem Laden geändert hat, neu laden statt überschreiben.

Die Tabs **Eingaben** und **Ausgaben und Zeitzone** enthalten die spielspezifischen Felder. Bei Anno 1404 steht jeder Spielstandordner in einer eigenen Zeile. Leere optionale Ausgabeziele verwenden die bisherigen Standardunterordner. Auch bei kleinen Fenstern bleiben die Felder über die Scrollleisten erreichbar. Details zu Schlüsseln und Platzhaltern: [Einstellungen](settings.de.md).

**Erzeugen verwendet die angezeigten Werte, ohne die persönliche Einstellungsdatei zu speichern.** Jeder Auftrag bekommt eine vorübergehende Konfigurationskopie mit denselben aufgelösten Pfadzielen. Diese Kopie wird nach Prozessende entfernt. Demoläufe bleiben unter `<output>/demo/` und ignorieren getrennte persönliche Berichts-, Stempel- und Logziele.

Neue GUI-Dateien liegen unter `%LOCALAPPDATA%/AnnoOrganizer/<spiel>/settings.json`, neue Ausgaben unter dessen `local-data/`. Der tatsächliche Windows-Ordner wird über das Betriebssystem ermittelt. GUI-Präferenzen stehen daneben in `gui.json`. Updates ändern diese Daten nicht. Die Konsolenstarter behalten ihre bisherigen Standardorte. Für einen ausdrücklich gewählten anderen GUI-Datenordner:

```powershell
.\Launch.cmd --gui --gui-data-dir "D:/AnnoOrganizer Data"
```

Eine externe Konfiguration lässt sich auch direkt öffnen:

```powershell
.\Launch.cmd --gui --game anno1404 --config "D:/Meine Annos/1404/settings.json"
```

## Sprache, Status und Abbruch

Beim ersten Start bestimmt die bevorzugte Windows-Anzeigesprache die Oberfläche: `de`, `de-DE`, `de-CH` oder `de-AT` ergeben Deutsch, alle anderen Sprachen und Erkennungsfehler Englisch. **DE/EN** kann jederzeit umgeschaltet werden; die manuelle Auswahl wird gespeichert und hat künftig Vorrang. Eingaben, Spiel, Aktion und gewählter Tab bleiben beim Umschalten erhalten. Die Sprachwahl der HTML-Galerien bleibt unabhängig; Rohdaten, Pfade und Logs werden nicht übersetzt.

Die Statusanzeige nennt den aktuellen Verarbeitungsschritt. Die bewegte Anzeige zeigt Aktivität und keinen geschätzten Prozentwert. **Abbrechen** fordert einen kooperativen Abbruch an. Ein laufender Parser oder eine Veröffentlichung darf bis zur nächsten sicheren Grenze fertiglaufen. Beim Schliessen während einer Verarbeitung kann ein Abbruch angefordert werden; das Fenster wartet dann weiter auf den Prozessabschluss.

Erfolg wird erst angezeigt, wenn Worker-Abschluss und Prozess-Exitcode zusammenpassen. Bei Fehler oder Abbruch werden mögliche Teilergebnisse genannt; Galerien lassen sich über den Erfolgsbutton erst nach einem erfolgreichen Lauf öffnen. **Protokolle** zeigt Diagnosen und die Aktionslogs, auch während eines laufenden Auftrags. **Info** zeigt den Entwicklungsstand, Lizenzhinweise und einen Link zu den GitHub-Releases; es erfolgt kein automatisches Update.

## Aktuelle Grenzen

Die Oberfläche ist eine Quellcode-Vorschau. Geprüft sind insbesondere DE/EN, Zustandswechsel, Konfigurationsimport und ein vollständiger Anno-1404-Demolauf. Ein EXE-Paket ohne Python, eine Abnahme auf einem frischen Windows-System und GUI-Läufe mit Anno-117-/1800-Spielressourcen stehen noch aus. Die bisherige Sperre auf `output` gilt weiterhin; verschiedene Konfigurationen mit getrenntem `output`, aber gemeinsamem Berichts-/Stempel-/Logziel noch nicht gleichzeitig starten. Stempelbilder und Caches werden teilweise direkt geschrieben; bei Abbruch sind Teilergebnisse möglich, eine vollständige Rücknahme ist noch nicht implementiert.

Inoffizielles Projekt von Morima79, ohne Verbindung zu Ubisoft. Nutzung auf eigene Gefahr gemäss [MIT-Lizenz](../LICENSE). Weitere Architektur- und Abnahmepunkte: [GUI-Vorschlag](desktop-gui.de.md).
