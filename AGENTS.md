# Arbeitsregeln für AnnoOrganizer

Gilt für das gesamte Repository. Diese Datei hält die dauerhaft wichtigen
Entscheidungen aus den lokalen Aufgaben vom 21. und 22. November 2026 fest.
Konkrete neue Benutzeranweisungen haben Vorrang. Frühere Freigaben für einen
bestimmten Commit oder Release sind keine pauschale Freigabe für spätere Aufgaben.

## Vor Arbeitsbeginn

- `git status --short` prüfen und vorhandene Benutzeränderungen erhalten.
- Die betroffenen Anleitungen und vergleichbaren Implementierungen lesen.
- Bei Veröffentlichungen zuerst [docs/publishing.md](docs/publishing.md),
  [docs/publishing.de.md](docs/publishing.de.md) und die vorhandenen Workflows
  unter `.github/workflows/` prüfen. Release- und Pages-Automatisierung existieren
  bereits; den etablierten Ablauf verwenden.
- Bei Galerieänderungen [docs/gallery-templates.md](docs/gallery-templates.md)
  und bei Pfadänderungen [docs/settings.de.md](docs/settings.de.md) beachten.
- Versionen, Testzahlen und Workflow-Status jeweils aktuell ermitteln; historische
  Chat-Aussagen sind kein Beleg für den heutigen Arbeitsstand.

## Sprache und Git

- Mit dem Benutzer Deutsch in Schweizer Schreibweise kommunizieren (`ss`).
- Code, technische Datei-, Funktions- und Variablennamen, Kommentare, Docstrings,
  Konfigurationsschlüssel und CLI-Parameter auf Englisch verfassen.
- **Commit-Texte sind Englisch**, auch wenn die Aufgabe auf Deutsch gestellt wird.
  Der feste Zusatz lautet **` - Mithilfe von Codex`**. Beispiel:
  `fix: preserve cosmetic asset-group provenance - Mithilfe von Codex`.
  Ein einzelner abweichender Commit begründet keinen Wechsel der Konvention.
- `README.md` ist Englisch, `README.de.md` Deutsch, jeweils auch in den drei
  Spielordnern. Betroffene Sprachfassungen und Verweise gemeinsam aktualisieren.
  Bereits zweisprachige Fachanleitungen ebenfalls in beiden Fassungen pflegen.
- Commit, Push, Tag und Veröffentlichung nur im beauftragten Umfang ausführen.
  «Committen und pushen» umfasst beides; reine Implementierungsaufträge nicht.
  Eine beauftragte Veröffentlichung umfasst die dafür nötigen Release-Schritte.
- Vor einem Commit den vollständigen betroffenen Diff prüfen, nur passende Dateien
  stagen und `git diff --cached --check` ausführen. Keine privaten Dateien mitstagen.
- Push und Tag-Push getrennt nachprüfen: Remote-Commit bzw. Remote-Tag muss auf den
  beabsichtigten Stand zeigen. Bestehende veröffentlichte Historie nicht wegen einer
  abweichenden Commit-Sprache umschreiben.

## Architektur und einfacher Einstieg

- Ein Repository für `anno117/`, `anno1800/` und `anno1404/`. Jeder Spielordner
  bleibt unabhängig nutzbar, mit eigenem Starter, Einstellungen, Abhängigkeiten,
  Anleitungen und Lizenz. Keine Abhängigkeit vom Hauptordner oder anderen Spielen
  in den eigenständig verwendeten Werkzeugen einführen.
- `Launch.cmd` und `launch.py` bleiben der einfache Einstieg. Neue Benutzer sollen
  mit den mitgelieferten Demos schnell ein Ergebnis sehen; idealerweise müssen sie
  nur den Spielpfad kontrollieren oder angeben. Anno 1404 benötigt für die Demo
  keine Spielinstallation.
- Einstellungen pro Spiel über `settings.json` bzw. `--config`; öffentliche
  Vorlagen in `settings.example.json`. Vorhandene persönliche Werte erhalten.
  Relative Pfade beziehen sich auf die verwendete Konfigurationsdatei.
  Windows-Dokumentenumleitung und `${DOCUMENTS}` berücksichtigen.
- Keine unnötigen Kompatibilitätsschichten für bereits abgelöste erste Entwürfe
  einführen. Vorhandene persönliche Daten und sinnvolle Pfadunterstützung erhalten.
- Anno 1404 hat derzeit nur eine Kartengalerie. Insgesamt existieren fünf Galerien:
  drei Karten- und zwei Stempelgalerien.

## Private Daten und lokale Ordner

- Die Werkzeuge liegen zentral in AnnoOrganizer. Die private Arbeitsstruktur des
  Projektinhabers liegt daneben in `../Anno 117 Pax Romana/`, `../Anno 1800/`
  und `../Anno 1404/`: `settings.json`, `Auswertung/`, `Stempel/` (117/1800),
  `logs/` und `.annoorganizer/`. Für private Aktualisierungen die jeweilige externe
  Konfiguration verwenden. Diese Rechnerstruktur nicht in öffentliche Defaults
  oder fest codierte Benutzerpfade übernehmen.
- Private Einstellungen verwenden getrennte `report_output`, `stamp_output` und
  `log_output`; `output` kann auf `.annoorganizer/` zeigen. Neue Standardinstallationen
  verwenden weiterhin `<spiel>/local-data/`. Demoläufe bleiben unter `<output>/demo/`.
- Alte `LokaleDaten`- und `Stadtstempel`-Werkzeugstrukturen nicht neu anlegen.
  Verknüpfungen verwenden die zentralen Werkzeuge und die externe Konfiguration.
  Namen: `Kartengalerie aktualisieren und öffnen` bzw.
  `Stempelgalerie aktualisieren und öffnen`; nach Aktualisierung die Galerie öffnen.
- Spielstände, Stempel, Benutzeranpassungen und Spieldaten werden von den
  Analysewerkzeugen ausschliesslich gelesen. Änderungen an Stempeln brauchen einen
  entsprechenden Auftrag; Originale erhalten und Varianten separat erstellen.
- Persönliche Einstellungen, normale lokale Galerien, Protokolle, Caches,
  Sicherungen und Spielarchive bleiben aus Git, Release und Pages ausgeschlossen.
  Ausnahmen sind die ausdrücklich freigegebenen Demo-Dateien und `site/`-Snapshots.
  Demo-Manifeste und Prüfsummen bei Änderungen beachten.
- Aufräumen darf keine aktuellen Originale, Anpassungen, Referenzen, benötigten
  Caches oder finalen Sicherungen entfernen. Veraltete Inhalte und Dubletten anhand
  von Nutzung und nötigenfalls Prüfsummen bestimmen. Frühere Aufräumaufträge sind
  keine allgemeine Löschfreigabe. Beauftragtes Entfernen nach Möglichkeit über den
  Papierkorb; danach Links und Starter prüfen.
- Bei Anno-117-Stempeldateien die Spiel-/Kontosynchronisierung berücksichtigen:
  externes Umbenennen oder Löschen kann Dubletten oder Wiederherstellung auslösen.
  Alte Pakete bei einem Austausch durch neue Varianten im Spiel entfernen lassen.

## Galerievorlagen, Gestaltung und Sprachen

- Gemeinsame Quellen sind `templates/`, insbesondere `anno_gallery.py`,
  `anno_i18n.py`, HTML/CSS, JavaScript und `locales/de.json` / `locales/en.json`.
  Synchronisierte Kopien unter den Spielordnern nicht separat bearbeiten.
- Nach zentralen Änderungen ausführen:

  ```powershell
  .\.venv\Scripts\python.exe scripts/sync_gallery_templates.py --refresh-site
  .\.venv\Scripts\python.exe scripts/sync_gallery_templates.py --check
  .\.venv\Scripts\python.exe scripts/validate_site.py
  ```

  `--refresh-site` aktualisiert Startseite und Rahmen der fünf vorhandenen
  Demo-Snapshots. Für geänderte Demo-Inhalte zusätzlich die regulären Exporte mit
  den mitgelieferten Demo-Eingaben ausführen. Private Galerien bei beauftragter
  Aktualisierung separat mit den externen Einstellungen neu erzeugen.
- Einheitliche Schrift (`system-ui, sans-serif`), Titel und Kopfzeilen über die
  vorhandenen Vorlagen erhalten. Farben orientieren sich am Spiel: 117 beige,
  1800 dunkelblau, 1404 helles Pergament mit Braun-/Goldtönen.
- Logos ohne separate Hintergrundfläche. Sichtbare Logo-Oberkante und DE/EN-Buttons
  stehen bündig; transparente Bildränder dürfen keinen unnötigen Leerraum erzeugen.
  Original-Logoassets erhalten. Auch schmale Ansichten prüfen.
- Technische Betriebs- und Dateistatusmeldungen gehören in Protokolle. Die
  Stempelgalerie-Fusszeile enthält nur `Stand:` / `Updated:` mit Datum und Uhrzeit.
- Alle fünf Galerien und die Demo-Startseite bieten DE/EN über zentrale Ressourcen.
  Beide JSON-Dateien mit identischen Schlüsseln und passenden Platzhaltern pflegen.
  Dynamische Texte, Metadaten und zugängliche Beschreibungen berücksichtigen.
- Umschalten muss offline beim direkten Öffnen funktionieren. Suchtext, Filter,
  Sortierung, Profilwahl, aufgeklappte Details und Bild-/Zoomzustand erhalten.
  Sprachwahl nach Möglichkeit speichern und über Demo-Navigation übernehmen;
  gesperrter Browserspeicher darf die Umschaltung nicht verhindern.
- Eigene Profil-, Ordner- und Stempelnamen, Pfade, technische Rohwerte und aus
  Spieldaten gelesene Objekt-/DLC-Namen nicht automatisch übersetzen. PNG-Texte,
  Excel, Startermenüs und Protokolle liegen ausserhalb des HTML-Sprachschalters;
  Startermenüs und Protokollmeldungen bleiben Deutsch.
- README-Screenshots zeigen die aktuellen Demos. Alle fünf Aufnahmen gleich breit:
  1264 Pixel Bildbreite bei 1280 Pixel Browserbreite inklusive Scrollbar.
  Vorschauen 360 Pixel breit, anklickbar in voller Auflösung; betroffene Haupt-
  und Spiel-READMEs in beiden Sprachen gemeinsam aktualisieren.

### Hintergrundaufnahmen für README-Screenshots

**Bevorzugter Weg: unsichtbarer integrierter Browser über `cua_repl`.**
Am Sonntag, 22. November 2026, wurden damit lokale HTTP-Demos aufgenommen.
Am 24. November wurden sowohl die veröffentlichte HTTPS-Demo als auch dieselbe
lokale Demo erneut erfolgreich unsichtbar aufgenommen. Eine Veröffentlichung ist
keine Voraussetzung. Die Edge-DevTools weiter unten sind eine Alternative.

1. Neue Demo-Inhalte zuerst exportieren und `site/` aktualisieren. Für noch nicht
   veröffentlichte Änderungen immer die lokale Ausgabe aufnehmen. Im Repo einen
   temporären Server nur für die öffentlichen Demo-Dateien starten:

   ```powershell
   .\.venv\Scripts\python.exe -u -m http.server 8771 --bind 127.0.0.1 --directory site
   ```

   Den Server über eine laufende Tool-Sitzung betreiben und deren ID für das
   spätere Beenden aufbewahren. Kein sichtbares Terminalfenster erforderlich.
   Falls `Start-Process` verwendet wird, mit `-WindowStyle Hidden` starten.
   Bei `WinError 10013` oder einem nur im Browser auftretenden Timeout zuerst
   den Server mit einem lokalen HTTP-Abruf prüfen. Der Test am 24. November
   benötigte für Server und Kontrollabruf die genehmigte Ausführung ausserhalb
   der Netzwerk-Sandbox (`require_escalated`). Danach funktionierte die Seite
   auch im integrierten Browser. Bindung an `127.0.0.1` und Verzeichnis `site/`
   beibehalten; weder Firewallregeln ändern noch private Verzeichnisse anbieten.
2. In `cua_repl` eine unsichtbare lokale Browserseite öffnen. Bei der ersten
   Verwendung muss dieser Einstieg allein im Tool-Aufruf stehen:

   ```javascript
   var tab = await cua.createBrowserTab(
     'iab', 'http://127.0.0.1:8771/anno117/stamps/', {visible:false});
   ```

   Für bereits veröffentlichte Inhalte funktioniert stattdessen beispielsweise
   `https://morima79.github.io/AnnoOrganizer/anno117/stamps/`.
   Die fünf Pfade lauten `anno117/maps/`, `anno1800/maps/`, `anno1404/maps/`,
   `anno117/stamps/` und `anno1800/stamps/`. `file://` ist kein gleichwertiger
   Einstieg: Der integrierte Browser kann dieses Protokoll ablehnen. Eine solche
   Ablehnung belegt keinen Fehler des unterstützten HTTP-/HTTPS-Aufnahmewegs.
3. Die aktuelle Browser-Dokumentation sowie `screenshots`,
   `local-web-development` und die `viewport`-Capability lesen. Den beim Einstieg
   zurückgegebenen Browser-Identifier verwenden, keine historische ID fest
   einbauen. Für die vereinbarten README-Abmessungen setzen:

   ```javascript
   var viewport = await browser.capabilities.get('viewport');
   await viewport.set({width:1280,height:900});
   nodeRepl.write(await tab.playwright.domSnapshot());
   ```

   DE wählen und bei Karten die Profilrangliste einklappen. Alle Such- und
   Filterfelder bleiben für die Aufnahme leer. Mit anhand des aktuellen DOM
   gewählten Überschriften bis zur letzten Karte scrollen, etwa durch einen
   Klick auf deren Überschrift; anschliessend über den DE-Button zum Kopfbereich
   zurückkehren. Nach Aktionen den Zustand prüfen. `fullPage` allein garantiert
   nicht, dass entfernte Lazy-Loading-Bilder bereits geladen sind.
4. Geladene Bilder und Seitenhöhe über eine lesende DOM-Prüfung kontrollieren,
   dann direkt JPEG-Bytes aufnehmen; keine Bildschirmaufnahme des Desktop nötig:

   ```javascript
   var metrics = await tab.playwright.evaluate(() => ({
     height: document.documentElement.scrollHeight,
     loaded: [...document.images].filter(i => i.getAttribute('src'))
       .every(i => i.complete && i.naturalWidth > 0)
   }));
   if (!metrics.loaded) throw Error('Demo images are still loading');
   var shot = await tab.screenshot({fullPage:true,
     clip:{x:0,y:0,width:1264,height:metrics.height}});
   var fs = await import('node:fs/promises');
   var os = await import('node:os');
   var out = await fs.mkdtemp(os.tmpdir()+'/anno-screenshots-');
   await fs.writeFile(out+'/stamp-gallery.jpg',shot);
   nodeRepl.write(out);
   await nodeRepl.emitImage(shot);
   await viewport.reset();
   ```

   Die Screenshot-API liefert JPEG, unabhängig vom Dateinamen. Temporären
   Ausgabeordner ausgeben lassen und anschliessend die geprüften Bilder mit dem
   Dateisystem-Tool ins Repo kopieren. Der Browser-Tempordner kann anders liegen
   als der Shell-Tempordner; keinen AppContainer-Pfad fest einbauen. Bei direktem
   Schreiben ins Repo auftretende Pfadfehler nicht als Aufnahmefehler behandeln.
5. Nach der Browserarbeit die vorgeschriebene `browser-complete`-Meldung senden,
   bevor andere Tools verwendet werden. Mit Pillow JPEG-Format, positive Höhe
   und exakt 1264 Pixel Breite prüfen. Bilder visuell kontrollieren; nur dann
   nach `<spiel>/docs/images/map-gallery.jpg` bzw. `stamp-gallery.jpg` übernehmen.
   Deutsche Aufnahmen verwenden `*-gallery.jpg`, englische `*-gallery-en.jpg`;
   jede README-Sprachfassung verlinkt ihre eigene Bildsprache.
   Keine README-Bilder allein für einen Ablauf-Test überschreiben. Beide
   README-Sprachen gemeinsam pflegen und vorhandene 360-Pixel-Verweise erhalten.
6. Viewport auch im Fehlerfall zurücksetzen, temporäre Tabs unmarkiert lassen
   und nur den eigenen Testserver über seine Tool-Sitzung mit `Ctrl+C` beenden.
   Nicht wegen eines nicht erreichbaren lokalen Servers ersatzweise veraltete
   veröffentlichte Demos als aktuellen lokalen Stand ausgeben.

### Alternative: README-Screenshots über Edge-DevTools

Am 24. November 2026 mit Edge und dem Computer-Use-Skill geprüft:

1. Die Demo-Inhalte zuerst regulär exportieren und `site/` aktualisieren. Nur
   öffentliche Demo-Seiten aufnehmen, keine persönlichen Galerien.
2. Ein separates Edge-Fenster öffnen und die jeweilige lokale
   `site/<spiel>/maps/index.html` bzw. `stamps/index.html` über die Adressleiste
   laden. DE wählen; automatische Browserübersetzung nicht verwenden.
3. Mit `Ctrl+Shift+I` die DevTools und mit `Ctrl+Shift+M` die Geräteansicht öffnen.
   Gerätetyp **Dynamisch**, Breite **1280**, Höhe **900**, Zoom **An Fenster
   anpassen**. Eine feste Höhe vermeidet Leerraum bei schmal angedockten DevTools.
   Bei den 117-/1800-Karten die Profilrangliste einklappen; Kennzahlengruppen geschlossen
   lassen. Im Seiteninhalt einmal mit `Ctrl+End` ans Ende und mit `Ctrl+Home`
   zurück springen, damit auch Lazy-Loading-Bilder geladen sind. Vor der Aufnahme
   geladene Karten und Stempelbilder prüfen.
4. Im Drei-Punkte-Menü der Geräteansicht **Vollbild-Bildschirmfoto erfassen**
   wählen. Dies lädt ein PNG der ganzen Seite herunter, ohne Browserrahmen oder
   DevTools. Der Downloadordner kann umgeleitet sein; den tatsächlich verwendeten
   Ordner ermitteln, keinen festen Benutzerpfad voraussetzen.
5. Geräte-Pixeldichte beachten: Bei DPR 2 ist das PNG 2560 Pixel breit. Mit Pillow
   proportional auf 1280 Pixel normalisieren (`Image.Resampling.LANCZOS`), dann
   nur je 8 Pixel äusseren Rand abschneiden (`crop((8, 0, 1272, height))`). Das
   ergibt die vereinbarte Bildbreite von **1264 Pixeln**, ohne Text oder Karten
   umzugestalten. Als RGB-JPEG mit Qualität 90 unter
   `<spiel>/docs/images/map-gallery.jpg` bzw. `stamp-gallery.jpg` speichern.
6. Alle fünf fertigen Bilder visuell prüfen. Beide Haupt-READMEs und beide
   Sprachfassungen der Spiel-READMEs mit anklickbaren 360-Pixel-Vorschauen
   aktualisieren. Den Aufnahmeweg erst nach einem erfolgreichen neuen Versuch
   ändern; ein Fehler des integrierten Browsers belegt keinen Edge-Fehler.

## Fachliche Erkennung und Validierung

- DLC-/CDLC- und Technikhinweise aus tatsächlich enthaltenen Objekten und gewählten
  Skins ableiten. Ungenutzte optionale Skins zählen nicht als Voraussetzung;
  unsichere Fälle kenntlich machen. Keine Versorgung oder Spielbarkeit versprechen.
- Anno 117: Herkunft aus kosmetischen Assetgruppen beim Einlesen erhalten.
  Ambrosianischer Wald (`158417`) und Keltischer Wald (`158418`) gehören zu
  Blütezeit/CDLC02 trotz `data/base/`-Pfaden und Baukategorie «Klassisch».
  Namen, Kategorie oder Grafikpfad allein beweisen keine CDLC-Freiheit.
  Neue Gruppen gegen die aktuellen Spieldaten prüfen; Details in
  [docs/formats-and-limitations.de.md](docs/formats-and-limitations.de.md).
- Vorhandene Sonderbehandlung der Ausbaureserve für `Lavendel ohne Ceres`
  und die lokalen Referenzmöglichkeiten erhalten.
- Anno 1800: enthaltene Module von Dekorationen, Strompflicht von optionalem Bonus
  unterscheiden; regionale Rathaus-/Handelskammer-Varianten über Vererbung erkennen.
- Bei Codeänderungen passende Regressionstests ergänzen und die betroffenen Checks
  ausführen. Regulärer Gesamtlauf:

  ```powershell
  .\.venv\Scripts\python.exe -m unittest discover -s tests -v
  ```

  Für Sprach-/Pages-JavaScript zusätzlich die einschlägigen Node-Tests:
  `node --test tests/gallery_i18n_runtime.cjs` und
  `node --test tests/pages_runtime.cjs`. CI testet Windows mit Python 3.11 und 3.14.
- Windows-Pfadvergleiche nach Auflösung normalisieren; kurze Benutzernamen wie
  `RUNNER~1` können denselben Pfad wie `runneradmin` bezeichnen.
- Statische Checks, Laufzeittests, Browser-Sichtprüfung und Benutzertests im Spiel
  getrennt ausweisen. Bei Format-/Erkennungsänderungen echte lokale Daten ergänzend
  prüfen, sofern verfügbar und beauftragt. Synthetische Tests ersetzen keinen Spieltest.
- UTF-8 explizit verwenden, `.gitattributes` beachten (`.cmd` CRLF, übrige erfasste
  Textformate LF, Demo-Eingaben binär). Vor Abschluss Diff und Kodierung prüfen.

## Releases und GitHub Pages

- **Der vorhandene Release-Workflow ist der reguläre Veröffentlichungsweg.**
  Nicht ersatzweise lokal ZIPs hochladen oder manuell einen parallelen Release bauen.
- Vor dem Tag einen eindeutigen, nicht leeren Abschnitt
  `## [vX.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md` mit `### English` und `### Deutsch`
  erstellen und committen. Änderungen zunächst unter `[Unreleased]` sammeln.
  Bei Release-Aufträgen neue Version anhand vorhandener Tags bestimmen; bereits
  veröffentlichte Tags und Releases nicht überschreiben.
- Den freigegebenen Commit und Versionstag pushen. Ein Tag `v*` startet
  `.github/workflows/release.yml`: Windows-Tests, ZIP aus dem exakten Git-Snapshot,
  SHA-256-Datei und GitHub-Release mit Beschreibung aus dem Versionsabschnitt.
  `workflow_dispatch` erzeugt nur ein Testartefakt, keinen veröffentlichten Release.
- `scripts/build_release.py` nutzt `git archive` von `HEAD`; uncommittete Änderungen
  sind nicht enthalten. Paketinhalt gegen den Tag unter Beachtung der Git-Attribute
  und Zeilenenden prüfen. ZIP-Integrität, Dateiliste, enthaltene Änderungen,
  Ausschluss privater Daten und veröffentlichte Prüfsumme kontrollieren.
- Pages ist ein eigener Workflow: `.github/workflows/pages.yml` veröffentlicht
  `site/` bei passenden Änderungen auf `main` oder manuell. Ein Release-Tag allein
  aktualisiert Pages nicht. GitHub erzeugt die Galerien nicht aus Spieldaten neu.
- Nur freigegebene Demo-Snapshots und benötigte Bilder nach `site/` übernehmen;
  relative Links und Rücklinks erhalten, lokale absolute Pfade entfernen.
- Nach beauftragter Veröffentlichung die relevanten Actions-Läufe bis zum Abschluss
  prüfen: Tests, Release und gegebenenfalls Pages separat. Nicht allein aus HTTP 200
  auf eine aktuelle Website schliessen; ausgelieferten Inhalt mit dem beabsichtigten
  Stand vergleichen. Erfolgreicher Release und fehlgeschlagenes Pages separat melden.
- Bei Aufträgen zur warnungsfreien Veröffentlichung auch die Protokolle prüfen.
  Node-Warnungen an den verwendeten Actions beheben, nicht durch eine lokale
  Node-Installation oder pauschales Unterdrücken von Warnungen.
  Den auf den Pages-Deploy-Schritt begrenzten `punycode`-Adapter samt Lizenz,
  Herkunft und Prüfsummen beachten; Wartungshinweise stehen in
  [.github/actions/pages-runtime/README.md](.github/actions/pages-runtime/README.md).
- Öffentliche Dokumentation soll leicht zugänglich bleiben. Veröffentlichungsdetails
  unter `docs/` pflegen und in den READMEs kurz verlinken. Hinweise auf eigene Gefahr,
  MIT-Lizenz, Morima79 und das Original-Repository erhalten.

### Fester lokaler Release-Ordner

- Der eigenständige Save Manager liegt unter
  `D:/Workspace/Releases/AnnoSaveManager/`. Die Desktop-Verknüpfung
  **ANNO - Save Manager** zeigt ohne Zusatzargumente auf die dortige
  `AnnoSaveManager.exe`; Arbeitsverzeichnis und Symbol bleiben in diesem Ordner.
  Bei Releases mit beiden EXE-Paketen beide lokalen Programme mit den nachfolgenden
  Paket-, Versions- und Verknüpfungsprüfungen aktualisieren.
- **Pro Programm genau eine Rückfallkopie behalten:** den unmittelbar zuvor
  verwendeten, nachweislich funktionierenden Stand. Das kann auch ein erfolgreich
  geprüfter lokaler Entwicklungsstand sein. Ältere Programm-Rückfallkopien erst
  nach erfolgreichem Austausch und Prüfung des neuen Programmpakets über den
  Papierkorb entfernen. Die verbleibende Rückfallkopie anhand von `BUILD.json`,
  Paketvergleich und nötigenfalls isoliertem Smoke-Test bestimmen, nicht allein
  anhand des Ordnerdatums. Bei fehlgeschlagenem Austausch oder gesperrten Dateien
  keine Rückfallkopien bereinigen. Diese Aufbewahrungsregel gilt nur für die lokalen
  Programmstände von AnnoOrganizer und AnnoSaveManager, nicht für Save-Sicherungen,
  persönliche Einstellungen oder andere Benutzerdaten.
- Auf dem Windows-Rechner des Projektinhabers liegt die jeweils aktuelle
  veröffentlichte Windows-Version unter `D:/Workspace/Releases/AnnoOrganizer/`.
  Die Desktop-Verknüpfung **ANNO - Organizer** zeigt ohne Zusatzargumente auf
  `D:/Workspace/Releases/AnnoOrganizer/AnnoOrganizer.exe`; ihr Arbeitsverzeichnis
  und Symbolpfad zeigen ebenfalls in diesen festen Programmordner. Den tatsächlichen,
  gegebenenfalls umgeleiteten Desktop über Windows ermitteln. Diese lokale Einrichtung
  ist keine öffentliche Programmeinstellung und gehört nicht in Standardkonfigurationen.
- **Nach jedem beauftragten, erfolgreich abgeschlossenen Release diesen lokalen
  Release-Ordner auf die gerade veröffentlichte Version aktualisieren.** Das ist Teil
  des Release-Abschlusses auf diesem Rechner. GitHub Actions aktualisiert diesen
  lokalen Ordner nicht selbst; keine automatische Hintergrundaktualisierung behaupten.
- Das veröffentlichte Windows-ZIP samt SHA-256-Datei herunterladen. In einem eigenen
  geprüften temporären Ordner ausserhalb OneDrive bereitstellen, Prüfsumme,
  ZIP-Integrität, `BUILD.json` (Version, Commit, Ressourcen) und Offline-Anleitung
  prüfen. Den vorhandenen portablen Smoke-Test mit isolierten Testdaten ausführen.
- Erst das geprüfte vollständige Programmpaket in den festen Ordner übernehmen,
  einschliesslich `_internal/`, Lizenz und Begleitdateien; keine alten und neuen
  Paketdateien vermischen. Bei späteren Updates den bisherigen Programmstand bis zum
  erfolgreichen Austausch als Rückfallmöglichkeit erhalten. Läuft die installierte
  Anwendung noch oder sind Dateien gesperrt, den bisherigen Stand erhalten und um
  Schliessen bitten; die Anwendung nicht ungefragt beenden.
- Die Verknüpfung nach dem Austausch prüfen bzw. bei Bedarf erneuern. Version und
  Commit am endgültigen Ort kontrollieren. Persönliche Einstellungen unter
  `%LOCALAPPDATA%/AnnoOrganizer/`, externe Konfigurationen, Spielstände, Stempel und
  Galerien erhalten. Keine lokalen Release-Pakete, Backups oder Verknüpfungen in Git
  aufnehmen. Ist dieser Rechner bzw. Laufwerk `D:` nicht verfügbar, die ausstehende
  lokale Aktualisierung ausdrücklich melden.
