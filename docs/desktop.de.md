# Desktop-Oberfläche

[English](desktop.md) · [Deutsch](desktop.de.md) · [README](../README.de.md)

Die Desktop-Vorschau konfiguriert und startet die vorhandenen Werkzeuge für Anno 117, 1800 und 1404. Sie lässt sich als portables Windows-x64-Paket oder aus dem Quellcode mit Python 3.11 oder neuer einschliesslich Tkinter starten. Die bestehenden Konsolenstarter und einzeln kopierten Spielordner funktionieren weiterhin.

## Portables Windows-Paket

Das vollständige mit `scripts/build_desktop.py` gebaute ZIP entpacken und **AnnoOrganizer.exe** öffnen. `_internal/` bleibt neben der EXE. Python und Laufzeitpakete sind enthalten; auf dem Zielrechner werden weder Python noch pip oder ein Installer benötigt. Das Paket ist für Windows 10/11 x64 vorgesehen. Es ist nicht signiert; Windows kann eine SmartScreen-Reputationswarnung anzeigen. Herkunft und SHA-256-Prüfsumme prüfen; Signierung ist ein separater Schritt. Es werden keine Sicherheitsmechanismen umgangen oder automatischen Updates installiert.

Die EXE benutzt denselben Worker mit `--worker --game ...` und speichert persönliche Daten ausserhalb ihrer internen Ressourcen. `BUILD.json` enthält Quellcommit, Paketversion und Ressourcen-Prüfsummen; `THIRD-PARTY-NOTICES.txt` und `licenses/` enthalten Lizenznachweise. Der [vorhandene Release-Workflow](publishing.de.md) ist für spätere Veröffentlichungen um den Windows-Build ergänzt. Ein lokaler Build ist noch kein veröffentlichtes Release.

## Start aus dem Quellcode und Erstausführung

Im Hauptordner starten:

```powershell
.\Launch.cmd --gui
```

Der Starter richtet wie bisher die Python-Umgebung und benötigten Pakete ein. Mit einer bereits vorbereiteten Umgebung geht auch:

```powershell
.\.venv\Scripts\python.exe launch.py --gui
```

Beim ersten Öffnen eines Spiels erstellt die GUI automatisch dessen `settings.json`. Windows liefert den tatsächlichen, gegebenenfalls umgeleiteten Dokumente-Ordner; Steam-/Ubisoft-Registrierungen liefern nach Möglichkeit die 117-/1800-Spielinstallation. Die üblichen Spielstand- und Stempelordner unter Dokumente werden eingetragen. Für 1404 werden vorhandene `Savegames`-Ordner von Grundspiel und Venedig berücksichtigt. Neue Ausgaben liegen unter `Dokumente/AnnoOrganizer/Anno 117/`, `Anno 1800/` bzw. `Anno 1404/`, mit `reports/`, `stamps/` und `logs/` als Unterordnern. Eingabeordner werden nicht angelegt oder geändert.

Links das gewünschte Spiel wählen, die erkannten Pfade prüfen und **Erzeugen** drücken. Ohne gespeicherte Auswahl ist **Karten und Excel** aktiv. Fehlende Installationen oder Eingabeordner müssen in den Feldern ergänzt werden; die Meldung nennt den betroffenen Pfad. Bestehende Einstellungen und ausgewählte externe Dateien bleiben unverändert.

**Mitgelieferte Demo** ist als separate Aktion verfügbar und liest ausschliesslich die Beispiele. Beim Start erscheint nur für diese Aktion ein Hinweis mit dem Demo-Ausgabeordner und der Information, dass persönliche Galerien dabei nicht aktualisiert werden. Während des Laufs steht im Status ausdrücklich **Demo wird erstellt**. Normale Exporte und **Alle Galerien aktualisieren** zeigen diesen Hinweis nicht. Anno 117 und 1800 benötigen auch für Demos ihre Spielressourcen. Die Anno-1404-Demo benötigt keine Spielinstallation. Demo-Ausgaben bleiben unter `<output>/demo/`.

Das absolute Ausgabeziel steht vor dem Start unter den Eingaben. Während der Verarbeitung bleibt das Fenster reaktionsfähig; Eingaben, Spiel-/Sprachwechsel, Tabs und die übrigen Aktionsbuttons sind gesperrt. **Abbrechen** und das lesende Öffnen bereits vorhandener Galerien bleiben verfügbar. Die Galerien öffnen im Standardbrowser. Es werden keine privaten Daten hochgeladen.

**Galerien öffnen** öffnet alle vorhandenen Karten- und Stempelgalerien dieses Spiels aus den aktuell angezeigten Ausgabezielen, einschliesslich der getrennten Demo-Ausgaben. Der kleine Pfeil daneben bietet die einzelne Auswahl. Vorhandene Seiten sind auch direkt nach einem Neustart und nach einem fehlgeschlagenen oder abgebrochenen Lauf erreichbar. Die Verfügbarkeit wird regelmässig geprüft; sie sagt nichts über den Erfolg des laufenden Auftrags aus.

Galeriebutton und Auswahlpfeil bilden ein gemeinsames Bedienelement mit einer dezenten inneren Trennlinie. Links werden alle vorhandenen Galerien geöffnet, rechts lässt sich eine einzelne wählen. Der Pfeilbereich ist kompakt und der Pfeil darin zentriert. Kann Windows die Galerie nicht im Standardbrowser öffnen, zeigt die GUI den Dateipfad zum direkten Öffnen an.

Die aufgeklappte Galerieauswahl verwendet dieselben dunklen Hintergrundfarben und hellen Texte wie die Oberfläche. Der hervorgehobene Eintrag ist goldgelb.

## Einstellungen bearbeiten und übernehmen

**Alle Galerien aktualisieren** prüft mit einem Klick Anno 117, 1800 und 1404 und aktualisiert deren nutzbare Galerien: bis zu drei Kartengalerien und zwei Stempelgalerien. Die Aktion verwendet die normalen konfigurierten Eingaben und Ausgabeziele, unabhängig von der gerade ausgewählten Einzelaktion. Bereits geladene, ungespeicherte Eingaben werden übernommen; für noch nicht geöffnete Spiele werden deren gespeicherte Konfigurationen gelesen. Persönliche Einstellungsdateien werden dabei nicht gespeichert.

Vor dem ersten Auftrag prüft die GUI sämtliche benötigten Eingaben, Spielressourcen und Ausgabeziele. Nicht gefundene Installationen, fehlende 1404-Spielstandordner oder Spiele ohne Eingabeordner werden übersprungen. Fehlt bei 117/1800 nur der Spielstand- oder Stempelordner, kann die andere Galerie trotzdem aktualisiert werden. Am Ende nennt eine Meldung die erfolgreich aktualisierten Galerien und die nicht vorhandenen bzw. nicht eingerichteten Spiele oder einzelnen Galerien mit Grund. Bei keinem nutzbaren Spiel erscheint ein Einrichtungshinweis, ohne einen Worker zu starten. So lässt sich die Funktion auch mit nur einem Spiel verwenden.

Andere Konfigurationsfehler oder überlappende Ziele verhindern den Start und werden mit Spielkennung angezeigt. Die geplanten Aufträge laufen nacheinander; der Status nennt Nummer, Spiel und Aktion. Fehler oder **Abbrechen** stoppen die verbleibenden Aufträge. Bereits veröffentlichte Galerien bleiben erhalten; der Gesamtlauf ist keine gemeinsame Transaktion. Die Zusammenfassung mit Einzelresultaten und übersprungenen Spielen steht unter `<GUI-Datenordner>/logs/all-games-last-run.json`. Galerien lassen sich wie bisher beim jeweiligen Spiel öffnen.

Die Aktionen stehen in der Reihenfolge **Karten und Excel**, **Stempelgalerie**, **Mitgelieferte Demo**. Die zuletzt gewählte Aktion wird pro Spiel sofort in `gui.json` gespeichert und bei Spielwechsel sowie beim nächsten Start wieder ausgewählt. Dafür muss die persönliche Einstellungsdatei nicht gespeichert werden. Ohne gültige gespeicherte Auswahl ist **Karten und Excel** aktiv; bei Anno 1404 ist die Stempelgalerie nicht verfügbar.

- **Datei verwenden**: Eine bestehende `settings.json` auswählen und die aufgelösten Ziele prüfen. Die Datei bleibt am bisherigen Ort; erst **Speichern** ändert sie. Relative Pfade bleiben auf ihren Ordner bezogen.
- **Kopie importieren**: Die Quelle auswählen und Importziel sowie aufgelöste Pfade prüfen. Die Kopie wird beim Bestätigen gespeichert. Bekannte relative Pfade und implizite Ausgabeziele werden so übernommen, dass sie auf dieselben Orte zeigen. Unbekannte Schlüssel bleiben erhalten. Die Quelle bleibt unverändert; Quelle und Ziel dürfen nicht dieselbe Datei sein. Eine bestehende Zieldatei wird nur nach zusätzlicher Bestätigung mit Sicherung ersetzt.
- **Standarddatei**: Zur gespeicherten GUI-Konfiguration dieses Spiels zurückkehren oder eine fehlende Standarddatei mit automatisch erkannten Werten anlegen. Eine externe Dateiauswahl wird erst beim Speichern der gewählten Standarddatei ersetzt.
- **Neu laden**: Die aktuelle Datei erneut lesen. Ungespeicherte Änderungen werden nur nach Bestätigung verworfen.
- **Speichern**: Die angezeigten Werte in die unter **Einstellungsdatei** genannte Datei schreiben. Der bisherige Inhalt wird unter `backups/` neben der Datei gesichert. Wenn eine andere Anwendung die Datei seit dem Laden geändert hat, neu laden statt überschreiben.

Die Tabs **Eingaben** und **Ausgaben und Zeitzone** enthalten die spielspezifischen Felder. Bei Anno 1404 hat jeder Spielstandordner ein eigenes einzeiliges Pfadfeld ohne Zeilenumbruch; **Ordner hinzufügen** und **Entfernen** verwalten mehrere Ordner. Leere optionale Ausgabeziele verwenden die bisherigen Standardunterordner. Auch bei kleinen Fenstern bleiben die Felder über die Scrollleisten erreichbar. Details zu Schlüsseln und Platzhaltern: [Einstellungen](settings.de.md).

**Durchsuchen** öffnet den aufgelösten Pfad des jeweiligen Feldes. Relative Pfade beziehen sich auf die Einstellungsdatei; Platzhalter wie `${DOCUMENTS}` werden berücksichtigt. Bei noch nicht vorhandenen Zielen öffnet sich der nächste vorhandene Oberordner. Für die Spielinstallation werden EXE-Dateien angezeigt: Die Spiel-EXE auswählen, auch in einem `Bin`-Unterordner. Die GUI ermittelt und prüft den passenden `maindata`-Ordner und trägt ihn ein. Spiel- oder `maindata`-Ordner können weiterhin direkt eingegeben werden.

**Zeitzone** steuert die Zeitangaben in Auswertungen und muss normalerweise nicht geändert werden. Für die Schweiz passt `Europe/Zurich`, inklusive Sommer-/Winterzeit. Andere IANA-Zeitzonen bleiben für andere Regionen oder bestehende Konfigurationen einstellbar. Die Anno-1404-Kartengalerie verwendet für Dateizeitstempel die lokale Windows-Zeit; die Statistik-Auswertung berücksichtigt die konfigurierte Zeitzone.

**Erzeugen verwendet die angezeigten Werte, ohne die persönliche Einstellungsdatei zu speichern.** Jeder Auftrag bekommt eine vorübergehende Konfigurationskopie mit denselben aufgelösten Pfadzielen. Diese Kopie wird nach Prozessende entfernt. Demoläufe bleiben unter `<output>/demo/` und ignorieren getrennte persönliche Berichts-, Stempel- und Logziele.

Neue GUI-Dateien werden unter `%LOCALAPPDATA%/AnnoOrganizer/<spiel>/settings.json` angelegt, neue Ausgaben unter dem ermittelten Dokumente-Ordner in `AnnoOrganizer/Anno <Nummer>/`. GUI-Präferenzen stehen daneben in `gui.json`. Updates überschreiben keine vorhandenen Einstellungen oder persönlichen Pfade. Die Konsolenstarter behalten ihre bisherigen Standardorte. Für einen ausdrücklich gewählten anderen GUI-Datenordner:

```powershell
.\Launch.cmd --gui --gui-data-dir "D:/AnnoOrganizer Data"
```

Pro GUI-Datenordner läuft nur eine Oberfläche gleichzeitig. Ein weiterer Start zeigt einen Hinweis, statt konkurrierende Einstellungen zu speichern. Die Betriebssystemsperre wird auch nach einem Prozessabsturz freigegeben. Unabhängige GUI-Datenordner bleiben möglich; die bestehenden Sperren schützen weiterhin gemeinsame Ausgabeziele.

Eine externe Konfiguration lässt sich auch direkt öffnen:

```powershell
.\Launch.cmd --gui --game anno1404 --config "D:/Meine Annos/1404/settings.json"
```

## Sprache, Status und Abbruch

Position, Grösse und Maximierungszustand von Hauptfenster, Info und Protokollen werden in `gui.json` gespeichert und beim nächsten Öffnen wiederhergestellt. Minimiert wird nicht wiederhergestellt; nach einem Monitorwechsel werden Fenster in einen erreichbaren Bildschirmbereich verschoben. Info und Protokolle gehören zum Hauptfenster und bleiben über ihm. Der gewählte Tab und die aktive Sprache sind goldgelb markiert; die Tab-Grösse bleibt beim Wechsel gleich.

Beim ersten Start bestimmt die bevorzugte Windows-Anzeigesprache die Oberfläche: `de`, `de-DE`, `de-CH` oder `de-AT` ergeben Deutsch, alle anderen Sprachen und Erkennungsfehler Englisch. **DE/EN** kann ausserhalb laufender Aufträge umgeschaltet werden; die manuelle Auswahl wird gespeichert und hat künftig Vorrang. Eingaben, Spiel, Aktion und gewählter Tab bleiben beim Umschalten erhalten. Die Sprachwahl der HTML-Galerien bleibt unabhängig; Rohdaten, Pfade und Logs werden nicht übersetzt.

Die Statusanzeige nennt den aktuellen Verarbeitungsschritt. Die bewegte Anzeige zeigt Aktivität und keinen geschätzten Prozentwert. **Abbrechen** fordert einen kooperativen Abbruch an. Ein laufender Parser oder eine Veröffentlichung darf bis zur nächsten sicheren Grenze fertiglaufen. Beim Schliessen während einer Verarbeitung fragt die GUI nach einem Abbruch. **Nein** lässt den Auftrag weiterlaufen; **Ja** fordert den Abbruch an und wartet vor dem Schliessen auf das Prozessende. Anschliessend werden ungespeicherte Einstellungen wie beim normalen Schliessen angeboten. Erzwungenes Beenden über den Task-Manager ist kein geordneter Abbruch.

Erfolg wird erst angezeigt, wenn Worker-Abschluss und Prozess-Exitcode zusammenpassen. Bei Fehler oder Abbruch werden mögliche Teilergebnisse genannt. **Protokolle** zeigt Diagnosen und die Aktionslogs. **Info** zeigt den Entwicklungsstand, Lizenzhinweise und einen Link zu den GitHub-Releases; es erfolgt kein automatisches Update.

Der letzte Auftrag jedes Spiels wird samt Fehlerdetails unter `<GUI-Datenordner>/logs/<spiel>-last-run.json` gespeichert. Dadurch bleiben auch Fehler vor dem Start eines Generatorlogs nach dem Schliessen lesbar. Diese Dateien können persönliche Pfade enthalten und bleiben lokal.

## Aktuelle Grenzen

Die Oberfläche ist ein Entwicklungsstand. Lokal wurde die entpackte EXE mit allen fünf Demo-Galerien und den installierten 117-/1800-Spielressourcen geprüft; der Prozess lief aus einem anderen Arbeitsordner mit unbrauchbaren Python-Suchpfaden. DE/EN, Zustandswechsel, Konfigurationsimport und ein GUI-Demolauf für 1404 wurden separat geprüft. Eine unabhängige Abnahme auf einem frischen Windows-System ohne installierte Entwicklungswerkzeuge steht weiterhin aus; diese wird durch manipulierte Python-Suchpfade nicht vollständig ersetzt. GUI, CLI und direkte Generatoraufrufe reservieren nun ihre tatsächlichen Ausgabeziele einschliesslich verschachtelter Ordner, Logs und Stempel-Caches prozessübergreifend. Betriebssystemsperren geben Reservierungen auch nach einem Prozessabsturz frei. Stempelgalerien und Ressourcen-Caches werden in Arbeitskopien erzeugt und erst nach erfolgreicher Verarbeitung veröffentlicht. Abbruch vorher erhält bestehende Inhalte; ein Veröffentlichungsfehler löst eine Wiederherstellung aus. Falls ein externes Programm auch diese blockiert, bleiben die Sicherungskopien samt `RECOVERY.json` am im Log genannten Ort erhalten. Originalspielstände und Stempel werden weiterhin nur gelesen. Überlappende Stempel-/Cacheziele und Verknüpfungen innerhalb dieser Ausgabebäume werden abgewiesen. Mehrere Demo-Aktionen bilden keine gemeinsame Transaktion; bereits abgeschlossene Aktionen können bei späterem Fehler bestehen bleiben.

Inoffizielles Projekt von Morima79, ohne Verbindung zu Ubisoft. Nutzung auf eigene Gefahr gemäss [MIT-Lizenz](../LICENSE). Weitere Architektur- und Abnahmepunkte: [GUI-Vorschlag](desktop-gui.de.md).
