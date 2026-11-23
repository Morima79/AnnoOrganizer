# Automatische Veröffentlichung

[English](publishing.md) · [Deutsch](publishing.de.md) · [Zur deutschen README](../README.de.md)

Anleitung für die Pflege des Repositories: Releases erstellen, GitHub Pages veröffentlichen und die Demo-Galerien aktualisieren.

- **Release-ZIP:** Ein gepushter Versions-Tag wie `v0.1.1` startet `.github/workflows/release.yml`. Erst nach erfolgreichen Windows-Tests mit Python 3.11 und 3.14 werden `AnnoOrganizer-<Version>.zip` und die SHA-256-Datei aus genau diesem Git-Stand erstellt und als GitHub-Release veröffentlicht. Bestehende Releases werden nicht überschrieben. `Actions → Release ZIP → Run workflow` baut nur ein herunterladbares Test-Artefakt und veröffentlicht kein Release.
- **Release-Text:** Vor dem Taggen einen Abschnitt wie `## [v0.1.2] - 2026-11-21` in [CHANGELOG.md](../CHANGELOG.md) mit englischen und deutschen Hinweisen ergänzen und committen. Der Workflow übernimmt genau diesen Versionsabschnitt als Beschreibung des GitHub-Releases. Fehlt der Eintrag, ist er leer oder doppelt vorhanden, wird kein Release veröffentlicht. Auch ein manueller ZIP-Test-Build benötigt einen passenden Eintrag für die gewählte Version.
- **Webseite:** Änderungen an `site/` auf `main` werden nach einer Link- und Pfadprüfung automatisch über GitHub Pages veröffentlicht. Einmalig muss unter `Settings → Pages → Source` die Option **GitHub Actions** aktiviert sein.
- **Demo aktualisieren:** Neue Ausgaben lokal ausschliesslich aus den mitgelieferten Demo-Dateien erzeugen. Die fünf `index.html`-Dateien unter `site/<Spiel>/maps/` bzw. `stamps/` und nur ihre referenzierten Bilder ersetzen. Relative Bildpfade beibehalten, absolute lokale Pfade entfernen und die Rücklinks zur Demo-Startseite erhalten. Danach `python scripts/validate_site.py` ausführen. Die Originalgalerien und persönlichen Einstellungen bleiben unverändert. GitHub erzeugt diese Momentaufnahmen nicht neu, da die Werkzeuge dafür teilweise installierte Spieldaten benötigen.

`site/` enthält ausschliesslich HTML und benötigte Vorschau-/Bauplanbilder, keine Spieldatenarchive, Caches oder privaten Konfigurationen. `scripts/build_release.py` paketiert ausschliesslich versionierte Dateien; lokale Einstellungen und Ausgabeordner bleiben ausgeschlossen.

## Projektumbenennung

Das Repository heisst [Morima79/AnnoOrganizer](https://github.com/Morima79/AnnoOrganizer), die Demo-Webseite liegt unter [https://morima79.github.io/AnnoOrganizer/](https://morima79.github.io/AnnoOrganizer/). Bestehende Releases und Tags behalten ihre ursprünglichen Namen und Dateien; künftige Releases verwenden den neuen Archivnamen. Veröffentlichte Releases wegen der Umbenennung nicht neu bauen oder ersetzen.

Pages verwendet relative Navigation und eingebettete CSS-, JavaScript- und Sprachressourcen. Dadurch funktionieren alle fünf Galerien unter dem neuen Repository-Pfad und beim lokalen Öffnen. Der Workflow übernimmt die Deployment-URL von GitHub Pages, ohne den Repository-Namen fest vorzugeben. Unter **Settings → Pages → Source** weiterhin **GitHub Actions** verwenden; ein Push des aktualisierten `site/` auf `main` veröffentlicht die umbenannten Inhalte. Manuell gesetzte Repository-Homepage und externe Links separat prüfen; die alte Pages-URL kann statt einer Weiterleitung HTTP 404 liefern.

Lokale Kompatibilitätskennungen (`ANNOTOOLS_SETTINGS`, `.annotools-game.json`, `.annotools.lock`, bestehende `.annotools/`-Ausgabeordner und `annotools.gallery.language`) bleiben unverändert. Vorhandene Konfigurationen, Spielkennungsprüfungen, Aktualisierungssperren und Sprachpräferenzen funktionieren dadurch weiter. Der lokale Repository-Ordner muss nicht umbenannt werden; persönliche Verknüpfungen bei einem Verschieben separat anpassen.

## Node.js-Warnung der Pages-Action

Die aktuelle offizielle `actions/deploy-pages@v5` enthält noch eine Abhängigkeit, die Nodes veraltetes `punycode`-Modul lädt. Der Pages-Workflow verwendet deshalb ausschliesslich für diesen Deploy-Schritt einen [lokalen Kompatibilitätsadapter](../.github/actions/pages-runtime/README.md). Er lädt die unveränderte, mit MIT-Lizenz und Prüfsummen dokumentierte Userland-Implementierung, statt Warnungen zu unterdrücken. Andere Warnungen bleiben sichtbar; Berechtigungen und OIDC-Deployment bleiben unverändert.

Vor dem Deployment prüft `node --test tests/pages_runtime.cjs` die Korrektur unter Node 24. Nach einer künftigen offiziellen Behebung kann der Adapter gemäss seiner Anleitung wieder entfernt werden. Die Korrektur wird erst mit einem Commit und Push des Workflows auf GitHub wirksam.
