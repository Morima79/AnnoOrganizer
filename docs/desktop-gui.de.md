# Vorschlag für eine Desktop-GUI

[English](desktop-gui.md) · [Deutsch](desktop-gui.de.md) · [Wishlist](wishlist.de.md)

Status: Quellcode-Vorschau mit Oberfläche, Einstellungsverwaltung und Worker; noch kein portables EXE-Paket.

## Ziel

Eine portable Windows-Anwendung soll Anno-Spielern ermöglichen, die vorhandenen Werkzeuge ohne Python-Installation, manuelle JSON-Bearbeitung oder Kommandozeile zu konfigurieren und zu starten. Bestehende CLI, eigenständig nutzbare Spielordner und HTML-Galerien bleiben erhalten. Eine erste nutzbare GUI sollte möglichst vor der breiteren Community-Veröffentlichung bereitstehen.

## MVP

- Spielauswahl: Anno 117, Anno 1800 und Anno 1404 inklusive unterstützter Editionen.
- Automatische Erkennung der Spielinstallationen und Benutzerverzeichnisse mit vorhandener Erkennungslogik; manuelle Korrektur ermöglichen.
- Spielspezifische Installations-, Spielstand-/Account-, Stempel- (nur 117/1800) und Ausgabepfade.
- Kartenanalyse/Excel-Berichte oder Stempelgalerie/Blueprints entsprechend den vorhandenen Funktionen auswählen. Keine nicht unterstützten Kombinationen oder noch nicht implementierten unabhängigen Exportoptionen anbieten.
- Mitgelieferte Demos mit getrennten Eingaben/Ausgaben und unveränderten persönlichen Einstellungen starten.
- Konfiguration vor der Verarbeitung prüfen; verständliche Fehlermeldungen und Zugriff auf Logs anbieten.
- Fortschritt, aktuellen Verarbeitungsschritt und Abbruch unterstützen; parallele Verarbeitung desselben Ausgabeziels verhindern.
- Erzeugte Galerien im Standardbrowser und Ausgabeordner öffnen.
- Deutsche und englische Oberfläche, Versionsanzeige und manuelle Release-Prüfung.
- Beim ersten Start die bevorzugte Windows-Anzeigesprache übernehmen: Deutsch für Sprachkennungen mit `de` als Sprachanteil (z. B. `de-DE`, `de-CH`, `de-AT`), sonst Englisch. Falls die Erkennung fehlschlägt, Englisch verwenden. Ein sichtbarer DE/EN-Schalter erlaubt jederzeit eine manuelle Auswahl; diese in `gui.json` speichern und bei späteren Starts vor der Systemsprache bevorzugen. Dafür die Anzeigesprache statt Zahlenformat, Region oder Tastaturlayout auswerten. Die Auswahl betrifft die GUI; bestehende Sprachregeln für HTML-Galerien, Logs und Exporte bleiben erhalten.

## Empfohlene Architektur

Zunächst Python mit Tkinter/ttk und PyInstaller einsetzen. Die GUI bleibt schlank und verwendet die bestehenden Launcher, Parser und Generatoren. Wiederverwendbare Dienste bei Bedarf aus der CLI extrahieren; keine doppelte Verarbeitungslogik oder interaktiven Konsolenabfragen im GUI-Modus. Längere Arbeiten ausserhalb des UI-Threads ausführen und Fortschrittsereignisse an den UI-Thread übergeben. Möglichst kooperativen Abbruch mit sicheren Abbruchpunkten vorsehen und Teilergebnisse kenntlich machen. Bei unbekanntem Gesamtumfang keinen prozentualen Fortschritt vortäuschen.

Alternative: VB.NET/WPF mit .NET 10 LTS und separat paketierter Python-CLI-Engine. Dafür ist ein definierter Prozessvertrag für Argumente, Fortschrittsereignisse, Exitcodes und Abbruch nötig. Erst bei deutlich komplexerer Desktop-Oberfläche erneut bewerten; zwei Laufzeit- und Build-Umgebungen sind für den initialen Umfang nicht erforderlich.

Die folgende Grafik zeigt die VB.NET/WPF-Alternative; die zunächst empfohlene Python-/Tkinter-Architektur ist im Text oben beschrieben.

[![Architekturskizze der VB.NET/WPF-Alternative mit paketierter Python-Engine und HTML-, Excel- und Blueprint-Ausgaben](images/desktop-gui-architecture.png)](images/desktop-gui-architecture.png)

[Architekturgrafik als SVG](images/desktop-gui-architecture.svg)

## Konfiguration und Daten

Das bestehende spielspezifische settings.json-Schema einschliesslich --config, relativen Pfaden, ${DOCUMENTS} und ${HOME} weiterverwenden. Unbekannte Schlüssel und bestehende Einstellungen erhalten. Pfade validieren, Benutzereinstellungen bei Updates nicht überschreiben und persönliche Einstellungen von paketierten Ressourcen trennen. Konfigurationsort und Importregeln sind unten konkretisiert; CLI-Kompatibilität erhalten. Ausgabepfade bleiben konfigurierbar. Originalspielstände und Stempel niemals verändern. Ressourcen unabhängig vom Arbeitsverzeichnis auflösen; nicht in das interne PyInstaller-Ressourcenverzeichnis schreiben.

## Konkretisierung der drei technischen Punkte

Die folgenden Festlegungen beschreiben den vorgesehenen ersten Implementierungsstand. Sie sind erst teilweise umgesetzt; der aktuelle Stand und die verbleibenden Schnittstellen sind unten beschrieben.

### 1. Ausführung im Quellcode und im Windows-Paket

- Die GUI startet pro Auftrag einen separaten Arbeitsprozess. Im Quellcodebetrieb ist dies ein Python-Worker-Modul; im paketierten Betrieb startet dieselbe EXE mit einem internen `--worker`-Modus, der vor der GUI-Initialisierung ausgewertet wird. `sys.executable` wird im Paket nicht als Python-Interpreter für eine `.py`-Datei verwendet. Ein Auftrag umfasst Spiel, Aktion (`demo`, `analyze`, `stamps`), absoluten Konfigurationspfad und gegebenenfalls `rescan`.
- Der Worker ruft nicht interaktive, spielspezifische Dienste auf. Diese werden aus den bestehenden Einstiegspunkten extrahiert und von GUI und CLI verwendet. Die heutigen Skriptstarts und Konsolenabfragen werden dabei gezielt abgelöst; Parser und Generatoren bleiben die gemeinsame Fachlogik. Jeder Spielordner behält die für seinen Einzelbetrieb erforderlichen Dienste ohne Abhängigkeit vom Hauptordner.
- GUI und Worker tauschen versionierte UTF-8-JSON-Zeilen aus: auf stdout Ereignisse mit `protocol_version`, `run_id`, `type` und Nutzdaten; über stdin einen Abbruchauftrag. Ereignistypen sind `started`, `stage`, `progress`, `diagnostic` und `finished`. Fortschritt enthält nur bei bekanntem Umfang `completed` und `total`. Bestehende Textausgaben gehen ins Log und dürfen den Ereigniskanal nicht verunreinigen; stderr dient unerwarteten Prozessfehlern.
- `finished` enthält den Zustand `success`, `failed` oder `cancelled`, tatsächlich erzeugte Galeriepfade, Logpfad und einen Hinweis auf Teilergebnisse. Exitcodes: `0` Erfolg, `1` Verarbeitungsfehler, `2` ungültiger Auftrag/Konfiguration, `130` Abbruch. Fehlendes oder widersprüchliches Abschlussereignis wird als Fehler behandelt. Die GUI öffnet neue Ergebnisse erst nach bestätigtem Erfolg. Ein Hintergrundleser übergibt Ereignisse per Queue an den Tk-Hauptthread; nur dieser verändert Widgets.
- Der paketierte Worker verwendet ausschliesslich mitgelieferte Module und Ressourcen. Ein Smoke-Test nach dem Entpacken startet alle drei Demos ohne installiertes Python, aus einem anderen Arbeitsverzeichnis und mit den jeweils erforderlichen Spielressourcen.

### 2. Speicherort und Übernahme bestehender Einstellungen

- Die GUI verwaltet je Spiel `%LOCALAPPDATA%/AnnoOrganizer/<game>/settings.json`; reine GUI-Präferenzen liegen getrennt in `%LOCALAPPDATA%/AnnoOrganizer/gui.json`. Den Windows-Ordner über die Betriebssystemauflösung ermitteln und Schreibbarkeit prüfen. «Portabel» bedeutet im MVP ohne Installer startbar; Einstellungen werden nicht automatisch neben der EXE gespeichert. CLI-Standardorte und explizites `--config` bleiben erhalten.
- Bei der Ersteinrichtung kann der Benutzer eine vorhandene Konfiguration **am bisherigen Ort verwenden** oder ausdrücklich **als Kopie importieren**. Die Auswahl zeigt Quellpfad und aufgelöste Eingabe-/Ausgabeziele. Es gibt keine automatische Suche in privaten Spielständen und keine stillschweigende Migration. Eine externe Datei wird nur nach ausdrücklichem Speichern bearbeiteter Einstellungen geändert.
- Beim Kopieren alle bekannten Pfadfelder (`game_data`, `account`, `stamps`, `archive`, `save_folders`, `output`, `report_output`, `stamp_output`, `log_output`) mit derselben Logik wie in `Settings` relativ zur Quelldatei auflösen und relative Angaben als absolute Ziele in die Kopie übernehmen. Auch implizite Standardziele wie `./local-data` müssen erhalten bleiben. Leere optionale Werte bleiben leer; absolute Angaben und Platzhalter können unverändert bleiben, wenn ihre Auflösung am Ziel identisch ist. Unbekannte Schlüssel und Werte unverändert erhalten; unbekannte relative Zeichenfolgen nicht als Pfade interpretieren.
- Für neue GUI-Konfigurationen zeigt `output: ./local-data` auf den Unterordner beim jeweiligen GUI-Konfigurationsort. Die Oberfläche zeigt diesen absoluten Zielpfad vor dem ersten Lauf. Quellcodeinstallationen behalten `<spiel>/local-data/`; importierte Konfigurationen behalten ihre bisherigen Ziele. Neue Demo-Eingaben kommen aus den paketierten Ressourcen, Demo-Ausgaben ausschliesslich nach `<output>/demo/` und ignorieren getrennte persönliche Ausgabeziele.
- Speichern erfolgt nach Validierung über eine eindeutige temporäre Datei im selben Ordner und atomaren Dateiersatz. Vor Änderungen eine Sicherung der bestehenden Konfiguration erstellen und zwischenzeitliche externe Änderungen erkennen; bei Konflikt erneut laden statt überschreiben. Updates ersetzen nur Programmressourcen. Tests müssen direkte externe Nutzung, Import mit relativen/impliziten Pfaden, unbekannte Schlüssel und Neustart/Upgrade abdecken.

### 3. Abbruch, Teilergebnisse und Ausgabesperren

- Der Worker prüft einen kooperativen Abbruch vor jedem Verarbeitungsschritt, zwischen Eingabedateien und vor der Veröffentlichung neuer Ergebnisse. Während nicht unterbrechbarer Parser- oder Bibliotheksaufrufe zeigt die GUI «Abbruch angefordert» bis zum nächsten sicheren Punkt. Für Demos gilt ein Abbruch auch für die noch ausstehenden Aktionen. Im MVP gibt es keinen erzwungenen Prozessabbruch über die Oberfläche; beim Schliessen eines laufenden Fensters Abbruch anfordern und bis zur Bestätigung weiter reagieren.
- Neue Berichte, Galerien und zugehörige Bilder zunächst in einem laufbezogenen temporären Ausgabeordner erzeugen und prüfen. Eine Galerie darf erst auf vollständig veröffentlichte Ressourcen verweisen. Einzeldateien über atomaren Ersatz veröffentlichen; bei mehreren Dateien benötigte Ressourcen vor den HTML-/Excel-Einstiegsdateien bereitstellen und bestehende referenzierte Ressourcen erhalten. Mehrere getrennte Ausgabeordner bilden keine atomare Gesamttransaktion: Eine bereits veröffentlichte Teilausgabe im Abschlussstatus und Log ausdrücklich nennen. Bestehende gültige Ausgaben bei Abbruch vor Veröffentlichung erhalten; nur eigene temporäre Dateien entfernen.
- Die heutige `.annotools.lock` schützt lediglich `settings.output`. GUI und CLI müssen künftig dieselbe prozessübergreifende Sperrverwaltung verwenden und vor dem ersten Schreiben alle tatsächlich verwendeten Ziele reservieren: `output`, aktives Berichts-/Stempelziel, Logziel und beschreibbare Cacheziele. Bei Demos nur die effektiven Demo-Ziele verwenden. Unterschiedliche Konfigurationen mit gemeinsamem `report_output`, `stamp_output` oder `log_output` dürfen die Sperre nicht umgehen.
- Ziele als aufgelöste Windows-Pfade vergleichen, einschliesslich Gross-/Kleinschreibung, kurzer Pfadnamen und Verzeichnisverknüpfungen. Gleiche sowie ineinander verschachtelte Schreibziele zwischen Aufträgen gelten als Konflikt. Reservierungen aller Ziele gemeinsam unter einer benutzerweiten Betriebssystemsperre prüfen und eintragen, damit keine zwei Prozesse gleichzeitig freie Ziele beanspruchen. Eine zweite GUI-Instanz und CLI-Aufrufe müssen dieselben Reservierungen sehen; verwaiste Einträge nur nach bestätigtem Ende des zugehörigen Prozesses entfernen. Sperren bis zum Abschluss der Veröffentlichung und Logausgabe halten und in `finally` freigeben.
- Regressionen: zwei Aufträge mit verschiedenen `output`-Werten, aber gemeinsamem Berichts-/Logziel; verschachtelte oder aliasierte Ziele; Abbruch beim Einlesen und vor der Veröffentlichung; gesperrte Excel-Datei; unerwartetes Worker-Ende; fehlgeschlagene Veröffentlichung nach einer erfolgreichen Demo-Teilaktion. Ein Fehler oder Abbruch darf weder als Gesamterfolg erscheinen noch Originaldaten verändern.

## UI-Konzept

Ein Fenster mit Spielnavigation links und spielspezifischen Pfaden/Aktionen rechts. Einstellungen und Info, Generieren, Abbrechen und Galerien öffnen sowie Fortschritts-/Statusbereich und Logzugriff vorsehen. Nicht relevante Steuerelemente deaktivieren (z. B. Stempel bei Anno 1404). Vorhandene HTML-Galerien beibehalten, keinen Desktop-Galerieviewer nachbauen.

Der visuelle Entwurf zeigt die geplante Spielnavigation, Pfadauswahl und Ausgabeaktionen mit englischen Beispieltexten. Die dargestellten Pfade und einzelnen Export-Checkboxen sind illustrative Beispiele; für Standardpfade und verfügbare Aktionskombinationen gelten die Festlegungen dieses Vorschlags.

[![GUI-Entwurf für Anno 117 mit Spielnavigation, Ordnerauswahl und Aktionen zur Galerieerzeugung](images/desktop-gui-concept.png)](images/desktop-gui-concept.png)

[GUI-Entwurf als SVG](images/desktop-gui-concept.svg)

## Bereitstellung

Zunächst PyInstaller im onedir- und --windowed-Modus verwenden und als portables Windows-ZIP über GitHub Releases bereitstellen. Windows-Build in bestehende Release-Pipeline integrieren oder separaten Workflow anlegen. Erforderliche Templates, Demodateien und Laufzeitabhängigkeiten mitliefern, Lizenzhinweise erhalten und Drittanbieter-Lizenzen dokumentieren. Keine Spielressourcenarchive oder persönlichen Daten paketieren. Keine pip-Installation zur Laufzeit. Bestehendes Quellcode-Paket weiterhin bereitstellen. Ressourcenauflösung und Abhängigkeiten im paketierten Build prüfen; onefile erst später erwägen. SHA-256-Prüfsummen veröffentlichen, mögliche SmartScreen-Warnungen bei unsignierten EXE-Dateien erklären und Signierung separat bewerten. Keine Umgehung von Sicherheitsmechanismen empfehlen. Installer, automatische Updates und integrierter Browser gehören nicht zum MVP.

## Abnahmekriterien

- [ ] Auf einem frischen unterstützten Windows-System ohne Python lässt sich die Anwendung entpacken und starten.
- [ ] Pfade aller drei Spiele werden erkannt oder manuell konfiguriert; Einstellungen bleiben bei Neustart und Upgrade erhalten.
- [ ] Bestehende CLI und eigenständige Spielordner funktionieren weiterhin; Regressionstests bestehen.
- [ ] Alle fünf unterstützten Demo-Galerien funktionieren unter den bestehenden Spielressourcen-Voraussetzungen; Demos durchsuchen keine persönlichen Dateien.
- [ ] Persönliche Karten-/Excel- und unterstützte Stempelausgaben entsprechen bei gleichen Eingaben dem CLI-Verhalten.
- [ ] Pfade mit Leerzeichen, Unicode und umgeleitetem Dokumente-Ordner funktionieren; ungültige Pfade und gesperrte Excel-Dateien erzeugen verständliche Meldungen.
- [ ] GUI bleibt bedienbar; Abbruch und Fehler werden korrekt angezeigt, ohne falsche Erfolgsmeldungen oder beschädigte Quelldateien.
- [ ] Logs und Ausgaben lassen sich öffnen; deutsche und englische Oberfläche funktionieren.
- [ ] Release-ZIP ist über CI reproduzierbar, enthält erforderliche Ressourcen und Lizenzen und wird nach dem Entpacken getestet.

## Implementierungsstand: gemeinsame Ausführung vorbereiten

Der erste Umsetzungsschritt stellt jetzt `anno_execution.py` bereit. Die zentrale Quelle liegt unter `templates/`; `scripts/sync_gallery_templates.py` verteilt identische Kopien nach `<spiel>/tools/`, damit jeder Spielordner eigenständig bleibt. Alle drei Launcher verwenden diesen Dienst.

- `prepare_execution(settings, project, action, rescan=False)` übernimmt ein bereits geladenes `Settings`-Objekt, wählt die unterstützten Aktionen, isoliert die Demo und validiert alle Schritte ohne Schreibzugriffe, Rückfragen oder Browserstart. Relative Pfade und externe Einstellungen behalten die bestehende `Settings`-Semantik; persönliche Konfigurationsdateien werden nicht verändert.
- `execute_plan(plan, on_event=None, on_output=None, *, cancel_requested=None, run_id=None)` führt den Plan aus und liefert `ExecutionResult(galleries, logs)` mit `Path`-Objekten. Ausnahmen werden weitergegeben. `on_output` erhält rohe Logzeilen; `on_event` erhält Dictionaries mit `protocol_version: 1`, `run_id`, `type` und `payload`. Bisher implementiert: `started`, `stage` und `finished`. Callbacks laufen synchron im aufrufenden Thread und dürfen keine Ausnahmen auslösen; ein späterer GUI-Adapter muss Ereignisse an den UI-Thread weiterreichen.
- `finished.payload` enthält `status`, `galleries`, `logs` und `partial_output`, bei Fehler zusätzlich `message`. `galleries` nennt nur erfolgreich abgeschlossene Aktionen; `logs` nennt die vorgesehenen Logpfade bereits gestarteter Aktionen. `partial_output: true` bei einem Fehler bedeutet, dass Ausgaben möglich sind, auch wenn die fehlerhafte Aktion keine vollständige Galerie geliefert hat. Ein fehlender Galerie-Einstieg trotz Exitcode 0 gilt als Fehler. Ein `KeyboardInterrupt` oder `ExecutionCancelled` wird als `cancelled` gemeldet und weitergegeben. Ein optionaler `cancel_requested`-Callback wird an sicheren Grenzen geprüft.
- Haupt- und Spielstarter bieten `--non-interactive`. Die Aktion muss explizit sein, beim Hauptstarter zusätzlich das Spiel. Der Modus legt keine fehlenden Einstellungen an, fragt nicht nach einem Spielpfad und lässt sich nicht mit `--init-settings` kombinieren. `--check` behält seinen lesenden Rückfall auf die Beispielkonfiguration am Standardort. Zum Unterdrücken des Browserstarts weiterhin `--no-open` angeben.

Beispiel für eine bereits vorhandene externe Konfiguration:

```powershell
.\.venv\Scripts\python.exe launch.py --game anno1404 --action demo --config "D:/Anno/settings.json" --non-interactive --no-open
```

Die fünf Generatoren laden beim Import keine Konfiguration mehr. Ihr Dienst `run(settings, rescan=False)` erhält die Einstellungen ausdrücklich; die bisherigen direkten Skriptaufrufe bleiben über `main` erhalten. Der gemeinsame Dienst lädt pro Aktion ein frisches Generatormodul und ruft diesen Dienst ohne weiteren Python-Unterprozess auf. Logausgaben werden von Ereignissen getrennt erfasst. Es wird keine temporäre Demo-Konfigurationsdatei mehr benötigt; `settings.filename` bleibt erhalten. Die bisherige Sperre auf `output` gilt weiterhin über den gesamten Demo-Auftrag. Modulglobale Verarbeitungskontexte bleiben vorläufig auf einen Spielprozess begrenzt; der 1800-Spielressourcenindex wird beim Konfigurationswechsel zurückgesetzt. Ein eingefrorener Build ist damit vorbereitet, aber noch nicht erstellt oder geprüft.

Ausgabesperren über getrennte Ziele und die Stempel-Veröffentlichung sind unten konkret umgesetzt. Weitere Fortschrittsereignisse und der paketierte Worker bleiben offen. Einstellungsverwaltung unter LocalAppData, GUI und automatische Spracherkennung sind als Quellcode-Vorschau implementiert. Der Quellcode-Dienst darf wegen der gleichnamigen Spielmodule nur innerhalb eines einzelnen Spielprozesses verwendet werden; für einen Spielwechsel ist künftig ein neuer Worker vorgesehen.

## Implementierungsstand: Quellcode-Worker

Jeder Spielstarter bietet intern `--worker --action <action> --config <path>` und optional `--rescan`. Dieser Einstieg wird vor dem normalen CLI-Menü ausgewertet, öffnet keinen Browser und legt keine Konfiguration an. Er verwendet `anno_worker.py`, ebenfalls zentral gepflegt und in alle Spielordner synchronisiert. Ein Worker verarbeitet genau einen Auftrag.

```powershell
.\.venv\Scripts\python.exe anno1404/launch.py --worker --action demo --config "D:/Anno/settings.json"
```

stdout enthält ausschliesslich UTF-8-JSON-Zeilen im oben beschriebenen Ereignisformat. Generatorausgaben gehen in die Aktionslogs. Die bei `started` gelieferte `run_id` gilt für alle folgenden Ereignisse. Der Prozess endet mit `0` bei Erfolg, `1` bei Verarbeitungsfehlern, `2` bei ungültigem Auftrag/Konfiguration und `130` bei Abbruch. Auch ungültige Aufträge liefern ein `started`- und `finished`-Ereignis; `finished.payload.error_code` ist dann `invalid_job`.

Ein Abbruchauftrag auf stdin hat die Form `{"protocol_version":1,"run_id":"<run_id>","type":"cancel"}` mit abschliessendem Zeilenumbruch. Nur passende Version und Auftragskennung werden akzeptiert; EOF bedeutet keinen Abbruch. Ein Hintergrundleser setzt die Abbruchanforderung. Prüfungen erfolgen vor der Ausführung, zwischen Aktionen, zwischen eingelesenen Saves bzw. Kartenvarianten, zwischen Stempeln und vor der Veröffentlichung. Laufende Parser, Threadpool-Aufgaben und einzelne Schreib-/Veröffentlichungsoperationen dürfen fertiglaufen. Erfolgreich abgeschlossene Demo-Teilaktionen werden auch bei späterem Abbruch ausgewiesen. Stempelgeneratoren verwenden inzwischen die unten beschriebene Arbeitskopie und Wiederherstellung. Bereits veröffentlichte Demo-Teilaktionen bleiben bei späterem Abbruch bestehen. Die GUI muss bis zum Abschlussereignis weiter reagieren und auf die sicheren Grenzen warten.

Ein echter Quellcode-Worker-Demolauf für 1404 sowie Protokollfehler und ein Abbruch über stdin werden automatisiert geprüft. Ein paketierter EXE-Worker und Laufzeiten mit den 117-/1800-Spielressourcen sind damit noch nicht nachgewiesen.

## Implementierungsstand: Einstellungsverwaltung

`desktop/settings_store.py` verwaltet pro Spiel eine Konfiguration unter dem tatsächlich von Windows gemeldeten LocalAppData-Ordner. Neue Konfigurationen werden zunächst nur im Speicher erstellt und zeigen auf die mitgelieferten Beispiele; erst Speichern legt Dateien an. Externe Dateien können am bisherigen Ort verwendet oder ausdrücklich kopiert werden. Beim Kopieren werden bekannte relative Pfade und implizite Ausgabeziele gegen den Quellordner aufgelöst; unbekannte Werte bleiben erhalten. Eine verschwundene externe Datei wird nicht stillschweigend neu angelegt.

`Settings.from_data` stellt dieselbe Pfadauflösung für ungespeicherte Werte bereit. `anno_settings.py` wird jetzt ebenfalls aus `templates/` synchronisiert. Speichern prüft Schema, Pfadtypen und Überschneidungen mit Eingaben und Code; noch fehlende Spielinstallationen dürfen konfiguriert werden, die aktionsbezogene Vollprüfung bleibt vor der Verarbeitung. Änderungen verwenden eine Schreibsperre, eine Sicherung des bisherigen Inhalts und atomaren Dateiersatz. Seit dem Laden erkannte externe Änderungen führen zu einem Konflikt statt zum Überschreiben; gegen fremde Editoren ohne gemeinsame Sperre gibt es keine vollständige Transaktionsgarantie. GUI-Präferenzen und externe Dateiauswahl bleiben in `gui.json` erhalten.

## Implementierungsstand: Oberfläche

`launch.py --gui` öffnet die Tkinter/ttk-Oberfläche aus `desktop/app.py`; die reguläre CLI bleibt verfügbar. Spielnavigation, scrollbare Pfadfelder, Konfigurationsauswahl/-import/-speicherung, Demo-/Analyse-/Stempelaktionen, Ausgabeziele, Logs und Info sind eingebunden. Windows-Anzeigesprache und gespeicherte DE/EN-Auswahl werden über eigene, gleich aufgebaute Sprachressourcen unter `desktop/locales/` umgesetzt. Die GUI-Sprache verändert keine Galerie- oder Logsprache.

`desktop/worker_client.py` liest Worker-Ereignisse in einem Hintergrundthread und liefert sie per Queue an Tk. Erfolg wird erst nach konsistentem Abschlussereignis und Exitcode freigegeben. Abbruchanforderungen vor dem Worker-Start werden nach Empfang der Auftragskennung weitergeleitet. Pro Auftrag wird eine private temporäre Konfigurationskopie verwendet, damit Erzeugen keine persönliche Konfiguration speichert. Eingaben und ausgewählter Tab bleiben beim Sprachwechsel erhalten. Der Quellcode-Start, DE/EN und ein 1404-Demolauf wurden auch sichtbar geprüft; 860 × 720 Pixel bleiben mit scrollbaren Feldern nutzbar.

Bedienung und konkrete Restgrenzen: [Desktop-Anleitung](desktop.de.md). Paketierung und die verbleibende Gesamtabnahme sind weiterhin offen; die Gesamtabnahme ist deshalb noch nicht vollständig.

## Implementierungsstand: Ausgabeschutz

`anno_output_lock.py` reserviert die vollständigen Schreibziele unter einer benutzerweiten Windows-Sperrverwaltung. Gleiche und verschachtelte Ziele kollidieren auch bei unterschiedlichen Konfigurationsdateien. Kurzpfade und Verzeichnisverknüpfungen werden vor dem Vergleich aufgelöst. Reservierungsdateien tragen eine gehaltene Betriebssystemsperre; nicht mehr gesperrte Einträge werden unter der Verwaltungssperre bereinigt. `anno_output_transaction.py` erzeugt Stempelgalerien und ihren Ressourcen-Cache in separaten Arbeitskopien, prüft externe Änderungen und veröffentlicht Ressourcen vor HTML. Fehlgeschlagene Veröffentlichungen werden zurückgerollt; blockierte Wiederherstellungen behalten Sicherungsdaten und einen lokalen Wiederherstellungsindex. Die Module werden wie die übrigen gemeinsamen Quellen in alle Spielordner synchronisiert.

## Umsetzungsschritte

1. Launcher- und Konfigurationsschnittstellen prüfen; nicht interaktiven Ausführungs- und Fortschrittsvertrag definieren.
2. GUI und Einstellungsverwaltung implementieren; Pfad- und Konfigurationskompatibilität testen.
3. Hintergrundverarbeitung, Abbruch, Logging und Ausgabe-Navigation ergänzen.
4. Windows-Paket erstellen und testen; Publishing-Workflow und Schnellstart-Dokumentation ergänzen.
5. Auf einem sauberen Windows-System abnehmen und Community-Beitrag mit Screenshots, Demo- und Release-Link vorbereiten.

Dieser Vorschlag legt weder einen verbindlichen Release-Termin noch eine endgültige Technologieentscheidung fest.
