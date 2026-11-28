# Automatische Veröffentlichung

[English](publishing.md) · [Deutsch](publishing.de.md) · [Zur deutschen README](../README.de.md)

Anleitung für die Pflege des Repositories: Releases erstellen, GitHub Pages veröffentlichen und die Demo-Galerien aktualisieren.

- **Release-ZIPs:** Ein gepushter Versions-Tag wie `v0.1.21` startet `.github/workflows/release.yml`. Erst nach erfolgreichen Windows-Tests mit Python 3.11 und 3.14 werden `AnnoOrganizer-<Version>-windows-x64.zip` und `AnnoSaveManager-<Version>-windows-x64.zip`, jeweils mit SHA-256-Datei, aus dem geprüften Commit erstellt und als GitHub-Release veröffentlicht. Bestehende Releases werden nicht überschrieben. `Actions → Release ZIP → Run workflow` baut nur ein herunterladbares Test-Artefakt und veröffentlicht kein Release.
- **Release-Text:** Vor dem Taggen einen Abschnitt wie `## [v0.1.2] - 2026-11-21` in [CHANGELOG.md](../CHANGELOG.md) mit englischen und deutschen Hinweisen ergänzen und committen. Der Workflow übernimmt genau diesen Versionsabschnitt als Beschreibung des GitHub-Releases. Fehlt der Eintrag, ist er leer oder doppelt vorhanden, wird kein Release veröffentlicht. Auch ein manueller ZIP-Test-Build benötigt einen passenden Eintrag für die gewählte Version.
- **Webseite:** Änderungen an `site/` auf `main` werden nach einer Link- und Pfadprüfung automatisch über GitHub Pages veröffentlicht. Einmalig muss unter `Settings → Pages → Source` die Option **GitHub Actions** aktiviert sein.
- **Demo aktualisieren:** Neue Ausgaben lokal ausschliesslich aus den mitgelieferten Demo-Dateien erzeugen. Die fünf `index.html`-Dateien unter `site/<Spiel>/maps/` bzw. `stamps/` und nur ihre referenzierten Bilder ersetzen. Relative Bildpfade beibehalten, absolute lokale Pfade entfernen und die Rücklinks zur Demo-Startseite erhalten. Danach `python scripts/validate_site.py` ausführen. Die Originalgalerien und persönlichen Einstellungen bleiben unverändert. GitHub erzeugt diese Momentaufnahmen nicht neu, da die Werkzeuge dafür teilweise installierte Spieldaten benötigen.

`site/` enthält HTML, benötigte Vorschau-/Bauplanbilder und die sechs freigegebenen Demo-Downloads als Arbeitsmappen/ZIPs, keine Spieldatenarchive, Caches oder privaten Konfigurationen. Der Release-Workflow lädt nur die beiden EXE-Pakete und ihre Prüfsummen hoch. GitHub bietet pro Release automatisch Quellcode-Downloads als ZIP und tar.gz an; ein zusätzliches eigenes Quellcode-ZIP wird nicht mehr hochgeladen. `scripts/build_release.py` bleibt für lokale Git-Snapshot-Archive verfügbar. Lokale Einstellungen und Ausgabeordner bleiben ausgeschlossen.

## Projektumbenennung

Das Repository heisst [Morima79/AnnoOrganizer](https://github.com/Morima79/AnnoOrganizer), die Demo-Webseite liegt unter [https://morima79.github.io/AnnoOrganizer/](https://morima79.github.io/AnnoOrganizer/). Bestehende Releases und Tags behalten ihre ursprünglichen Namen und Dateien; künftige Releases verwenden den neuen Archivnamen. Veröffentlichte Releases wegen der Umbenennung nicht neu bauen oder ersetzen.

Pages verwendet relative Navigation und eingebettete CSS-, JavaScript- und Sprachressourcen. Dadurch funktionieren alle fünf Galerien unter dem neuen Repository-Pfad und beim lokalen Öffnen. Der Workflow übernimmt die Deployment-URL von GitHub Pages, ohne den Repository-Namen fest vorzugeben. Unter **Settings → Pages → Source** weiterhin **GitHub Actions** verwenden; ein Push des aktualisierten `site/` auf `main` veröffentlicht die umbenannten Inhalte. Manuell gesetzte Repository-Homepage und externe Links separat prüfen; die alte Pages-URL kann statt einer Weiterleitung HTTP 404 liefern.

Die Laufzeitkennungen verwenden durchgehend den aktuellen Projektnamen: `ANNOORGANIZER_SETTINGS`, `.annoorganizer-game.json`, `.annoorganizer.lock`, `.annoorganizer/`-Ausgabeordner und `annoorganizer.gallery.language`. Nur diese Namen werden unterstützt; es gibt keine Aliase oder automatischen Übernahmen veralteter Kennungen. Lokale Konfigurationen und Verwaltungsdateien vor der Nutzung gemeinsam umstellen. Die Sprachwahl im Browser beginnt wieder mit Deutsch, bis sie erneut ausgewählt wird.

## Node.js-Warnung der Pages-Action

Die aktuelle offizielle `actions/deploy-pages@v5` enthält noch eine Abhängigkeit, die Nodes veraltetes `punycode`-Modul lädt. Der Pages-Workflow verwendet deshalb ausschliesslich für diesen Deploy-Schritt einen [lokalen Kompatibilitätsadapter](../.github/actions/pages-runtime/README.md). Er lädt die unveränderte, mit MIT-Lizenz und Prüfsummen dokumentierte Userland-Implementierung, statt Warnungen zu unterdrücken. Andere Warnungen bleiben sichtbar; Berechtigungen und OIDC-Deployment bleiben unverändert.

Vor dem Deployment prüft `node --test tests/pages_runtime.cjs` die Korrektur unter Node 24. Nach einer künftigen offiziellen Behebung kann der Adapter gemäss seiner Anleitung wieder entfernt werden. Die Korrektur wird erst mit einem Commit und Push des Workflows auf GitHub wirksam.

## Demo-Excel herunterladen

Nach dem Export ausschliesslich der mitgelieferten Demo-Eingaben aller drei Spiele `python scripts/publish_demo_workbooks.py --reports-root local-data/statistics-demo` ausführen. Die Auswertung muss jeweils unter `<reports-root>/<spiel>/reports/<spiel>-map-seeds.xlsx` liegen. Das Skript prüft auf Rechnerpfade und erlaubt nur relative Links auf `map-images/*.png`. Es erstellt die drei freigegebenen Arbeitsmappen und ZIPs mit den verknüpften Bildern unter `site/downloads/`. Die ZIPs erhalten die relativen Bildlinks für die Offline-Nutzung. Persönliche Auswertungen niemals als Veröffentlichungseingaben verwenden. Startseite und beide README-Sprachen verlinken diese Momentaufnahmen; Pages veröffentlicht sie beim nächsten beauftragten Site-Push.

## Portables Windows-x64-Paket

Der vorhandene Release-Workflow baut `AnnoOrganizer-<Version>-windows-x64.zip` samt SHA-256-Datei unter Windows mit Python 3.11 und den fixierten Versionen aus `requirements-build.txt`. Vor der Veröffentlichung muss die entpackte EXE die 1404-Demo mit unbrauchbaren Python-Suchpfaden erfolgreich erzeugen. Danach übernimmt der bestehende Veröffentlichungsjob beide EXE-ZIPs samt Prüfsummen gemeinsam; ein manueller Workflow-Lauf bleibt ein Test-Artefakt ohne Release.

Lokaler Build aus einem sauberen, committeten Stand (Versionsbezeichnung frei für einen lokalen Test wählen, keine bestehenden Release-Assets ersetzen):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts/build_desktop.py --version v0.1.13-desktop-preview --output dist
.\.venv\Scripts\python.exe scripts/smoke_desktop.py --archive dist/AnnoOrganizer-v0.1.13-desktop-preview-windows-x64.zip
```

`--development` erlaubt ausdrücklich uncommittierte Änderungen und kennzeichnet das ZIP als `-dev`; solche Pakete nicht als exakten Release-Snapshot ausgeben. `--all-games` beim Smoke-Test erfordert vorhandene 117-/1800-Spielressourcen und prüft alle fünf Galerien. `--extract-to` behält Paket und Testausgaben in einem neuen oder leeren Verzeichnis. Die Prüfung manipuliert die Python-Suchpfade, ersetzt aber keine unabhängige Abnahme auf einer frischen Windows-Installation.

Der Builder nimmt keine normalen lokalen Einstellungen, Caches oder Spielressourcenarchive auf. `BUILD.json` dokumentiert Commit, Laufzeitversionen und Ressourcen-Hashes. Drittanbieter-Hinweise enthalten Python einschliesslich seiner Bibliotheksnotizen, Pillow, XlsxWriter, tzdata und den PyInstaller-Bootloader samt Ausnahme für gebaute Anwendungen. Für Pflege und Grenzen siehe die offiziellen [PyInstaller-Laufzeithinweise](https://pyinstaller.org/en/stable/runtime-information.html) und [Hinweise zum fensterlosen Modus](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html). Binäridentität über verschiedene Python-Versionen und Windows-Toolchains wird nicht zugesagt. Das Paket ist unsigniert; Hinweise dazu stehen in den mitgelieferten DE/EN-READMEs. Signierung bleibt separat.

Die Demo-Startseite verlinkt das veröffentlichte Windows-ZIP und dessen Versionsseite direkt. Bei einer neuen Desktop-Version die Download-URLs beider Programme in der gemeinsamen Startseitenvorlage und den Haupt-/Spiel-READMEs sowie `demo.downloadDetails` in den Sprachressourcen gemeinsam anpassen und `site/` aktualisieren. Den Versionstag über den vorhandenen Release-Workflow veröffentlichen und das Asset vor der Download-Ankündigung prüfen.

## Node.js-Warnung beim Artefaktdownload

`actions/download-artifact@v8` verwendet weiterhin einen ZIP-Entpacker, dessen veralteter Buffer-Konstruktor `DEP0005` auslöst ([Upstream-Korrektur](https://github.com/actions/download-artifact/pull/490)). Der Release-Workflow behält die offizielle Action und den Abbruch bei abweichendem Digest bei, speichert mit `skip-decompress: true` das unveränderte Artefakt unter `runner.temp` und startet danach `scripts/extract_desktop_artifact.py`. Python akzeptiert genau das Desktop-ZIP und die Prüfsumme der angeforderten Version, prüft SHA-256 und schreibt nur diese beiden Dateien nach `dist/`. Andere vorhandene Ausgabedateien bleiben erhalten; unerwartete Einträge, beschädigte Archive, abweichende Prüfsummen und bestehende Desktop-Dateien brechen den Job ab. Der Download-Schritt verwendet `--throw-deprecation`, damit eine neue Node-Abkündigung den Test/Build fehlschlagen lässt. Node-Warnungen werden nicht unterdrückt und Action-Bundles nicht verändert.

Mit `python -m unittest discover -s tests -p test_release_artifact.py -v` prüfen. Nach Workflow-Änderungen einen manuellen Testlauf von `Release ZIP` auf `main` mit einer bereits im Changelog dokumentierten Version starten und die Download-/Entpackprotokolle bis zum Abschluss kontrollieren. Dabei entstehen Testartefakte; der veröffentlichte Release wird nicht ersetzt. Sobald die offizielle Action ihren Entpacker korrigiert, die normale Extraktion prüfen und danach die Einstellung für den unveränderten Download samt Hilfsskript entfernen.

## Eigenständiger Spielstand-Manager im Release

Derselbe Release-Workflow baut unter Windows mit fixierten Abhängigkeiten zusätzlich `AnnoSaveManager-<Version>-windows-x64.zip` und `AnnoSaveManager-<Version>-windows-x64.sha256`. `scripts/build_save_manager.py --version vX.Y.Z --output dist` verlangt einen sauberen, committeten Stand und hält Version, Commit und Quell-Prüfsummen in `BUILD.json` fest. Ohne `--version` bleibt es ein Entwicklungsbuild. Vor dem Paketieren prüft die gebaute EXE Anno 117 und Anno 1800 mit isolierten Kopien der freigegebenen Demo-Saves. Vollständiger Programmordner, Offline-Anleitungen DE/EN und Lizenzhinweise sind enthalten; private Saves und Einstellungen bleiben ausgeschlossen.

Die Veröffentlichung wartet auf beide Windows-Pakete. Das Save-Manager-Artefakt verwendet denselben unveränderten Download mit Digest-Prüfung und strikter Python-Extraktion wie das Desktop-Artefakt, mit `--package save-manager`. Ein manueller Workflow-Lauf erzeugt beide EXE-ZIPs samt Prüfsummen, ohne einen Release zu veröffentlichen.
