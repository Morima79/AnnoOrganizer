# Automatische Veröffentlichung

[English](publishing.md) · [Deutsch](publishing.de.md) · [Zur deutschen README](../README.de.md)

Anleitung für die Pflege des Repositories: Releases erstellen, GitHub Pages veröffentlichen und die Demo-Galerien aktualisieren.

- **Release-ZIP:** Ein gepushter Versions-Tag wie `v0.1.1` startet `.github/workflows/release.yml`. Erst nach erfolgreichen Windows-Tests mit Python 3.11 und 3.14 werden `AnnoTools-<Version>.zip` und die SHA-256-Datei aus genau diesem Git-Stand erstellt und als GitHub-Release veröffentlicht. Bestehende Releases werden nicht überschrieben. `Actions → Release ZIP → Run workflow` baut nur ein herunterladbares Test-Artefakt und veröffentlicht kein Release.
- **Release-Text:** Vor dem Taggen einen Abschnitt wie `## [v0.1.2] - 2026-11-21` in [CHANGELOG.md](../CHANGELOG.md) mit englischen und deutschen Hinweisen ergänzen und committen. Der Workflow übernimmt genau diesen Versionsabschnitt als Beschreibung des GitHub-Releases. Fehlt der Eintrag, ist er leer oder doppelt vorhanden, wird kein Release veröffentlicht. Auch ein manueller ZIP-Test-Build benötigt einen passenden Eintrag für die gewählte Version.
- **Webseite:** Änderungen an `site/` auf `main` werden nach einer Link- und Pfadprüfung automatisch über GitHub Pages veröffentlicht. Einmalig muss unter `Settings → Pages → Source` die Option **GitHub Actions** aktiviert sein.
- **Demo aktualisieren:** Neue Ausgaben lokal ausschliesslich aus den mitgelieferten Demo-Dateien erzeugen. Die fünf `index.html`-Dateien unter `site/<Spiel>/maps/` bzw. `stamps/` und nur ihre referenzierten Bilder ersetzen. Relative Bildpfade beibehalten, absolute lokale Pfade entfernen und die Rücklinks zur Demo-Startseite erhalten. Danach `python scripts/validate_site.py` ausführen. Die Originalgalerien und persönlichen Einstellungen bleiben unverändert. GitHub erzeugt diese Momentaufnahmen nicht neu, da die Werkzeuge dafür teilweise installierte Spieldaten benötigen.

`site/` enthält ausschliesslich HTML und benötigte Vorschau-/Bauplanbilder, keine Spieldatenarchive, Caches oder privaten Konfigurationen. `scripts/build_release.py` paketiert ausschliesslich versionierte Dateien; lokale Einstellungen und Ausgabeordner bleiben ausgeschlossen.
