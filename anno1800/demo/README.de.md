# Anno 1800: Demodateien

[English](README.md) · [Deutsch](README.de.md)

Diese Beispiele wurden aus den Dateien des Projektinhabers für die Werkzeug-Demo ausgewählt. Spielstände sind unveränderte Binärkopien. Anno-117-Pakete enthalten ausgewählte Stempeldatensätze ohne Layoutänderung; Anno-1800-Stempel sind unverändert kopiert. `manifest.json` enthält Pfade, Grössen und SHA-256-Prüfsummen. Spieldatenarchive, Kontodatenbanken und extrahierte Spielgrafiken werden nicht mitgeliefert.

## Spielstände

Die Saves enthalten besiedelte Inseln mit gespeicherten Einwohner- und Wohnhauszahlen.

- `saves/Demo-01/demo-01.a7s` – Seed 7845
- `saves/Demo-02/demo-02.a7s` – Seed 8643
- `saves/Demo-03/demo-03.a7s` – Seed 4321

## Stempel

- Rathaus mit Platz 1
- Prod - Holz 3 mit Lager und Handelskammer
- Bananenplantage 1x TuS
- 00 Marktplatz
- Test

Im übergeordneten Ordner **Launch.cmd** öffnen und **Demo** wählen oder `python launch.py --action demo` ausführen. Die Demo liest nur die mitgelieferten Eingaben und schreibt in den Ausgabeunterordner `demo/`. Sie installiert keine Beispiele im Spiel und verändert keine persönlichen Bibliotheken. Die Dateien dienen der Auswertung; zum Laden im Spiel können die passende Spielversion und Inhalte erforderlich sein.
