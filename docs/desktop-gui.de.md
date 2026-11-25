# Vorschlag für eine Desktop-GUI

[English](desktop-gui.md) · [Deutsch](desktop-gui.de.md) · [Wishlist](wishlist.de.md)

Status: Vorschlag; noch nicht implementiert.

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

## Empfohlene Architektur

Zunächst Python mit Tkinter/ttk und PyInstaller einsetzen. Die GUI bleibt schlank und verwendet die bestehenden Launcher, Parser und Generatoren. Wiederverwendbare Dienste bei Bedarf aus der CLI extrahieren; keine doppelte Verarbeitungslogik oder interaktiven Konsolenabfragen im GUI-Modus. Längere Arbeiten ausserhalb des UI-Threads ausführen und Fortschrittsereignisse an den UI-Thread übergeben. Möglichst kooperativen Abbruch mit sicheren Abbruchpunkten vorsehen und Teilergebnisse kenntlich machen. Bei unbekanntem Gesamtumfang keinen prozentualen Fortschritt vortäuschen.

Alternative: VB.NET/WPF mit .NET 10 LTS und separat paketierter Python-CLI-Engine. Dafür ist ein definierter Prozessvertrag für Argumente, Fortschrittsereignisse, Exitcodes und Abbruch nötig. Erst bei deutlich komplexerer Desktop-Oberfläche erneut bewerten; zwei Laufzeit- und Build-Umgebungen sind für den initialen Umfang nicht erforderlich.

## Konfiguration und Daten

Das bestehende spielspezifische settings.json-Schema einschliesslich --config, relativen Pfaden, ${DOCUMENTS} und ${HOME} weiterverwenden. Unbekannte Schlüssel und bestehende Einstellungen erhalten. Pfade validieren, Benutzereinstellungen bei Updates nicht überschreiben und persönliche Einstellungen von paketierten Ressourcen trennen. Vor der Implementierung einen beschreibbaren Konfigurationsort (z. B. LocalAppData) und Regeln für Migration bzw. expliziten Import festlegen; CLI-Kompatibilität erhalten. Ausgabepfade bleiben konfigurierbar. Originalspielstände und Stempel niemals verändern. Ressourcen unabhängig vom Arbeitsverzeichnis auflösen; nicht in das interne PyInstaller-Ressourcenverzeichnis schreiben.

## UI-Konzept

Ein Fenster mit Spielnavigation links und spielspezifischen Pfaden/Aktionen rechts. Einstellungen und Info, Generieren, Abbrechen und Galerien öffnen sowie Fortschritts-/Statusbereich und Logzugriff vorsehen. Nicht relevante Steuerelemente deaktivieren (z. B. Stempel bei Anno 1404). Vorhandene HTML-Galerien beibehalten, keinen Desktop-Galerieviewer nachbauen.

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

## Umsetzungsschritte

1. Launcher- und Konfigurationsschnittstellen prüfen; nicht interaktiven Ausführungs- und Fortschrittsvertrag definieren.
2. GUI und Einstellungsverwaltung implementieren; Pfad- und Konfigurationskompatibilität testen.
3. Hintergrundverarbeitung, Abbruch, Logging und Ausgabe-Navigation ergänzen.
4. Windows-Paket erstellen und testen; Publishing-Workflow und Schnellstart-Dokumentation ergänzen.
5. Auf einem sauberen Windows-System abnehmen und Community-Beitrag mit Screenshots, Demo- und Release-Link vorbereiten.

Dieser Vorschlag legt weder einen verbindlichen Release-Termin noch eine endgültige Technologieentscheidung fest.
