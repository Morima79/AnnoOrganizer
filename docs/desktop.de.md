# Desktop-Oberfläche

[English](desktop.md) · [Deutsch](desktop.de.md) · [README](../README.de.md)

Die Desktop-Vorschau konfiguriert und startet die vorhandenen Werkzeuge für Anno 117, 1800 und 1404. Sie lässt sich als portables Windows-x64-Paket oder aus dem Quellcode mit Python 3.11 oder neuer einschliesslich Tkinter starten. Die bestehenden Konsolenstarter und einzeln kopierten Spielordner funktionieren weiterhin.

## Portables Windows-Paket

Das vollständige mit `scripts/build_desktop.py` gebaute ZIP entpacken und **AnnoOrganizer.exe** öffnen. `_internal/` bleibt neben der EXE. Python und Laufzeitpakete sind enthalten; auf dem Zielrechner werden weder Python noch pip oder ein Installer benötigt. Das Paket ist für Windows 10/11 x64 vorgesehen. Es ist nicht signiert; Windows kann eine SmartScreen-Reputationswarnung anzeigen. Herkunft und SHA-256-Prüfsumme prüfen; Signierung ist ein separater Schritt. Es werden keine Sicherheitsmechanismen umgangen oder automatischen Updates installiert.

Die EXE benutzt denselben Worker mit `--worker --game ...` und speichert persönliche Daten ausserhalb ihrer internen Ressourcen. `BUILD.json` enthält Quellcommit, Paketversion und Ressourcen-Prüfsummen; `THIRD-PARTY-NOTICES.txt` und `licenses/` enthalten Lizenznachweise. Der [vorhandene Release-Workflow](publishing.de.md) ist für spätere Veröffentlichungen um den Windows-Build ergänzt. Ein lokaler Build ist noch kein veröffentlichtes Release.

## Start aus dem Quellcode und erste Demo

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

Die Tabs **Eingaben** und **Ausgaben und Zeitzone** enthalten die spielspezifischen Felder. Bei Anno 1404 hat jeder Spielstandordner ein eigenes einzeiliges Pfadfeld ohne Zeilenumbruch; **Ordner hinzufügen** und **Entfernen** verwalten mehrere Ordner. Leere optionale Ausgabeziele verwenden die bisherigen Standardunterordner. Auch bei kleinen Fenstern bleiben die Felder über die Scrollleisten erreichbar. Details zu Schlüsseln und Platzhaltern: [Einstellungen](settings.de.md).

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

Position, Grösse und Maximierungszustand von Hauptfenster, Info und Protokollen werden in `gui.json` gespeichert und beim nächsten Öffnen wiederhergestellt. Minimiert wird nicht wiederhergestellt; nach einem Monitorwechsel werden Fenster in einen erreichbaren Bildschirmbereich verschoben. Info und Protokolle gehören zum Hauptfenster und bleiben über ihm. Der gewählte Tab und die aktive Sprache sind goldgelb markiert; die Tab-Grösse bleibt beim Wechsel gleich.

Beim ersten Start bestimmt die bevorzugte Windows-Anzeigesprache die Oberfläche: `de`, `de-DE`, `de-CH` oder `de-AT` ergeben Deutsch, alle anderen Sprachen und Erkennungsfehler Englisch. **DE/EN** kann jederzeit umgeschaltet werden; die manuelle Auswahl wird gespeichert und hat künftig Vorrang. Eingaben, Spiel, Aktion und gewählter Tab bleiben beim Umschalten erhalten. Die Sprachwahl der HTML-Galerien bleibt unabhängig; Rohdaten, Pfade und Logs werden nicht übersetzt.

Die Statusanzeige nennt den aktuellen Verarbeitungsschritt. Die bewegte Anzeige zeigt Aktivität und keinen geschätzten Prozentwert. **Abbrechen** fordert einen kooperativen Abbruch an. Ein laufender Parser oder eine Veröffentlichung darf bis zur nächsten sicheren Grenze fertiglaufen. Beim Schliessen während einer Verarbeitung kann ein Abbruch angefordert werden; das Fenster wartet dann weiter auf den Prozessabschluss.

Erfolg wird erst angezeigt, wenn Worker-Abschluss und Prozess-Exitcode zusammenpassen. Bei Fehler oder Abbruch werden mögliche Teilergebnisse genannt; Galerien lassen sich über den Erfolgsbutton erst nach einem erfolgreichen Lauf öffnen. **Protokolle** zeigt Diagnosen und die Aktionslogs, auch während eines laufenden Auftrags. **Info** zeigt den Entwicklungsstand, Lizenzhinweise und einen Link zu den GitHub-Releases; es erfolgt kein automatisches Update.

## Aktuelle Grenzen

Die Oberfläche ist ein Entwicklungsstand. Lokal wurde die entpackte EXE mit allen fünf Demo-Galerien und den installierten 117-/1800-Spielressourcen geprüft; der Prozess lief aus einem anderen Arbeitsordner mit unbrauchbaren Python-Suchpfaden. DE/EN, Zustandswechsel, Konfigurationsimport und ein GUI-Demolauf für 1404 wurden separat geprüft. Eine unabhängige Abnahme auf einem frischen Windows-System ohne installierte Entwicklungswerkzeuge steht weiterhin aus; diese wird durch manipulierte Python-Suchpfade nicht vollständig ersetzt. GUI, CLI und direkte Generatoraufrufe reservieren nun ihre tatsächlichen Ausgabeziele einschliesslich verschachtelter Ordner, Logs und Stempel-Caches prozessübergreifend. Betriebssystemsperren geben Reservierungen auch nach einem Prozessabsturz frei. Stempelgalerien und Ressourcen-Caches werden in Arbeitskopien erzeugt und erst nach erfolgreicher Verarbeitung veröffentlicht. Abbruch vorher erhält bestehende Inhalte; ein Veröffentlichungsfehler löst eine Wiederherstellung aus. Falls ein externes Programm auch diese blockiert, bleiben die Sicherungskopien samt `RECOVERY.json` am im Log genannten Ort erhalten. Originalspielstände und Stempel werden weiterhin nur gelesen. Überlappende Stempel-/Cacheziele und Verknüpfungen innerhalb dieser Ausgabebäume werden abgewiesen. Mehrere Demo-Aktionen bilden keine gemeinsame Transaktion; bereits abgeschlossene Aktionen können bei späterem Fehler bestehen bleiben.

Inoffizielles Projekt von Morima79, ohne Verbindung zu Ubisoft. Nutzung auf eigene Gefahr gemäss [MIT-Lizenz](../LICENSE). Weitere Architektur- und Abnahmepunkte: [GUI-Vorschlag](desktop-gui.de.md).
