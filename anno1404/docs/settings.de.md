# Einstellungen

[Zur deutschen README](../README.de.md)

Jeder Anno-Ordner besitzt seine eigene `settings.example.json` und `settings.json`. Die lokale `settings.json` ist von Git ausgeschlossen. Im jeweiligen Spielordner `python launch.py --init-settings` ausführen oder die Vorlage kopieren und anschliessend die Pfade bearbeiten. Der Hauptstarter kann mit demselben Parameter die Einstellungen für alle drei Spiele anlegen. Vorhandene Dateien werden erhalten.

JSON erlaubt keine Kommentare. Windows-Pfade lassen sich mit `/` schreiben; Backslashes müssen verdoppelt werden. Relative Pfade beziehen sich immer auf den Ordner der verwendeten Konfigurationsdatei.

| Schlüssel | Bedeutung |
|---|---|
| `version` | Schema `1` mit englischen Schlüsseln |
| `game` | Feste Spielkennung: `anno117`, `anno1800` oder `anno1404` |
| `timezone` | IANA-Zeitzone für 117 und 1800, zum Beispiel `Europe/Zurich`; 1404 zeigt lokale Dateizeitstempel |
| `output` | Ausgabeordner dieses Spiels; neue Voreinstellung `./local-data` |
| `game_data` | `maindata` der Spielinstallation; für 117 und 1800 erforderlich |
| `account` | Spielkonto oder übergeordneter `accounts`-Ordner bei 117 und 1800 |
| `stamps` | Lokale Stempelbibliothek bei 117 und 1800 |
| `archive` | Optionaler Ordner mit Save-Kopien bei 1800; `""` deaktiviert ihn |
| `save_folders` | Liste mit Anno-1404-Spielstandordnern; mindestens einer muss existieren |

Beispiel für Anno 1800:

```json
{
  "version": 1,
  "game": "anno1800",
  "timezone": "Europe/Zurich",
  "output": "./local-data",
  "game_data": "D:/Games/Anno 1800/maindata",
  "account": "${DOCUMENTS}/Anno 1800/accounts",
  "stamps": "${DOCUMENTS}/Anno 1800/stamps",
  "archive": ""
}
```

`${DOCUMENTS}` berücksichtigt die Windows-Dokumentenordner-Umleitung, `${HOME}` den Benutzerordner. Umgebungsvariablen wie `%USERPROFILE%` werden ebenfalls aufgelöst. Bei 117 erwartet `game_data` unter anderem `config.rda`, bei 1800 `data0.rda`. Für die Stempelgalerie ist `account` nicht erforderlich, für die Spielstandauswertung ist `stamps` nicht erforderlich.

Im jeweiligen Ausgabeordner entstehen:

```text
stamps/stamp-gallery.html    Stempelgalerie bei 117 und 1800
stamps/library/              Bauplan-PNGs mit den Stempelnamen
reports/map-gallery.html    Karten-/Spielstandgalerie
reports/map-images/         Rekonstruierte Karten
reports/stamp-gallery/      Stempelmetadaten und Ressourcen-Caches
logs/                       Protokolle des letzten Aufrufs
```

`--check` prüft die Konfiguration ohne neue Ausgaben. `--no-open` unterdrückt den Browserstart. Eine Datei `settings.<name>.local.json` kann über `--config PFAD` verwendet werden und ist ebenfalls von Git ausgeschlossen.

Ausgabeordner dürfen sich nicht mit Eingaben oder Codeordnern überschneiden. Verschiedene Anno-Versionen dürfen keinen gemeinsamen Ausgabeordner verwenden; eine Spielkennungsdatei schützt bereits verwendete Ausgaben. Ausgaben an externen Orten müssen bei Bedarf auch dort von Git ausgeschlossen werden.


## Demo ohne Pfadkonfiguration

`Launch.cmd` richtet fehlende Python-Pakete und Einstellungen automatisch ein. Die Beispielkonfiguration zeigt bereits auf `./demo/saves` und `./demo/stamps`; bei Anno 1404 steht `save_folders` auf `./demo/saves`. In der Auswahl zuerst **Demo** wählen. Die Demo verwendet diese mitgelieferten Eingaben unabhängig von vorhandenen persönlichen Quellpfaden und schreibt nach `<output>/demo/`. Persönliche Einstellungen werden dafür nicht umgeschrieben.

`game_data` darf leer bleiben, wenn Steam oder Ubisoft Connect die Installation auffindbar registriert haben. Ansonsten wird beim Start nur nach dem Spielpfad gefragt; akzeptiert werden der Spielordner und sein `maindata`-Unterordner. Die explizite Eingabe wird für spätere Starts gespeichert. Für 1404 ist kein Spielpfad erforderlich. `--check` fragt nichts ab und legt weder Einstellungen noch Ausgaben an.

## Einzelne Anno-Version verwenden

Den gewünschten Spielordner einzeln kopieren, eine Python-Umgebung erstellen und dessen `requirements.txt` installieren. Die eigene `settings.json` anpassen und `Launch.cmd` öffnen. Der unabhängige Starter verwendet `--action stamps` beziehungsweise `--action analyze`. Nur der Hauptstarter benötigt zusätzlich `--game`. Der Hauptordner und die anderen Annos sind für den Einzelbetrieb nicht erforderlich.

## Externe Einstellungen und getrennte Ausgabeordner

Mit `--config "D:/Projekte/Anno 117/settings.json"` kann die persönliche Einstellungsdatei ausserhalb von AnnoOrganizer liegen. Relative Pfade beziehen sich auf diesen Ordner. Starter und Verknüpfungen müssen denselben `--config`-Pfad übergeben.

Optional lassen sich die Ausgaben getrennt festlegen:

```json
"output": "./.annoorganizer",
"report_output": "./Auswertung",
"stamp_output": "./Stempel",
"log_output": "./logs"
```

`output` enthält dann nur die Spielkennung, Aktualisierungssperre und etwaige Demo-Ausgaben. Ohne die optionalen Schlüssel gelten weiterhin `reports`, `stamps` und `logs` unter `output`. Demoläufe ignorieren die getrennten Pfade und bleiben vollständig unter `<output>/demo/`. Eingabepfade und vorhandene Anpassungen bleiben erhalten.
