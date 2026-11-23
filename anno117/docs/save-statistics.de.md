# Aktuelle Spielstand-Kennzahlen

[English](save-statistics.md) · [Deutsch](save-statistics.de.md)

Die Kartengalerien für Anno 117, 1800 und 1404 zeigen zusätzlich den aktuellen Stand jeder erkannten Partie. Direkt sichtbar sind **Zuletzt gespielt am**, **Bevölkerung**, **Vermögen und Bilanz** in der Gruppe **Geld**, **Wohnhäuser** und **Schiffe**. Bevölkerung, Geld, Wohnhäuser und Schiffe sind zunächst geschlossene Gruppen. Ein Klick oder die Tastatur öffnet nur die betreffende Gruppe. Bevölkerungsstufen und besiedelte Inseln, Einnahmen/Ausgaben, Wohnhäuser pro Stufe und Baupläne sowie Schiffstypen erscheinen erst dort. Die bisherigen Save-Zeitpunkte, Spielzeitrekorde, Dateizahlen und Quellen stehen unter **Save-Details**; die Karteneinstellungen besitzen eine eigene geschlossene Gruppe.

Alle Kennzahlen einer Partie stammen aus demselben neuesten Save. Unterschiedliche Partien mit demselben Seed werden nicht addiert. Eine Kartenvariante kann deshalb mehrere getrennte Partiezusammenfassungen enthalten. Die Kartenbilder bleiben Rekonstruktionen des gespeicherten Geländes und erhalten keine Gebäude- oder Besitzüberlagerung. Die Quellen der Kennzahlen und der Kartenbilder sind in den Save-Details nachvollziehbar. Der DE/EN-Schalter funktioniert offline und erhält die geöffneten Gruppen.

## Auswahl und Aktualisierung

Bei 117 und 1800 bestimmen Seed und gespeicherte Partie-ID die Partie, der interne Speicherzeitpunkt bestimmt den neuesten Save. Bei Gleichstand wird in 1800 das Spielkonto vor einer Archivkopie bevorzugt. Profilordner allein sind keine Partie-ID. Bei 1404 wird die vorhandene Kombination aus Spiel-ID, vollständiger Kartenvariante und Profilen verwendet; die Datierung beruht wie bisher auf dem Dateizeitstempel. «Zuletzt gespielt am» bezeichnet den Zeitpunkt des neuesten vorhandenen Saves, nicht einen darüber hinaus bekannten Spielstart.

Die neue Auslesung öffnet nur den neuesten Save pro Partie. Die bestehende Archiv-/Spielzeitstatistik bleibt erhalten. Für die neuen Kennzahlen gibt es einen getrennten Zwischenspeicher `anno117-statistics.json`, `anno1800-statistics.json` beziehungsweise `anno1404-statistics.json` im Berichtsordner. Dateisignaturen, Ausleseversion und bei 117/1800 die Signatur der installierten Spieldaten bestimmen seine Gültigkeit. `--rescan` erneuert auch diese Kennzahlen. Anno 1800 verwendet bei `--render-only` ausschliesslich bereits gültige Kennzahlen-Zwischendaten; fehlende Einträge erscheinen als nicht verfügbar. Ein nicht auslesbarer neuester Save wird nicht durch ältere Zahlen ersetzt. Originaldateien und persönliche Einstellungen werden ausschliesslich gelesen.

Die Excel-Ausgabe enthält das zusätzliche Blatt **Aktuelle Spielstände**, mit einer Zeile pro Partie, Speicherzeitpunkt, Seed, Hauptkennzahlen, besiedelten Inseln, Bauplänen und Save-Quelle. Die bisherigen Karten- und Spielzeitblätter bleiben erhalten. Excel bleibt deutsch und wird nicht durch den HTML-Sprachschalter verändert.

## Verfügbare Daten und Grenzen

| Angabe | Anno 117 | Anno 1800 | Anno 1404 |
|---|---|---|---|
| Gesamteinwohner und Vermögen | Gespeicherte Profilwerte | Gespeicherte Profilwerte, sofern vorhanden | `stats.xml` |
| Bevölkerungsstufen | Wohnhäuser plus zuordenbare Beiträge anderer Gebäude, mit Gegenprüfung | Gespeicherte Wohnhausbewohner, mit Gegenprüfung | Gespeicherte Spielerzähler, mit Gegenprüfung |
| Bilanz, Einnahmen und Ausgaben | Gespeicherte Minutenwerte, mit Gegenrechnung | nicht verfügbar | nicht verfügbar |
| Gebaute Wohnhäuser | Eigene Wohnhausobjekte | Eigene Wohnhausobjekte | Eigene `ResidenceBuilding`-Objekte |
| Wohnhaus-Baupläne | Separat | Separat | nicht verfügbar |
| Eigene Schiffe | Assettyp und eindeutige Schiffs-ID | Assettyp und eindeutige Schiffs-ID | Spieler-Schiffsliste, gegen Objekte geprüft |
| Besiedelte Inseln | Aktuelle Besitzdaten; für Aegyptus-Sektoren nicht verfügbar | Aktuelle Besitzdaten; Anteile zählen nicht als Inselbesitz | Eigene gestartete Kontore, je Insel einmal |

**Nicht zuverlässig auslesbare Werte erscheinen als «nicht verfügbar» / «not available», niemals als erfundene Null.** Das betrifft auch unvollständige Demos, unbekannte Formate, ungesicherte Spielerzuordnung oder eine nicht bestätigte Stufenaufteilung. Eine bestätigte Null bleibt dagegen `0`. Fehlende Detailwerte verhindern nicht die Ausgabe unabhängig bestätigter Gesamtwerte.

Anno 117 speichert Einwohnerwerte teilweise als Float32. Ein reines Summieren der Wohnhausbewohner reicht nicht: Bevölkerungsbeiträge von Markt-/Tavernen- und anderen Effekten auf Nichtwohngebäude gehören ebenfalls zur Gesamtzahl. Die Zuordnung verwendet lokale Gebäude- und Bevölkerungsassets und wird gegen den gespeicherten Gesamtwert geprüft. Arbeitskraftboni von Wohnhäusern dürfen nicht als zusätzliche Einwohner interpretiert werden. Bruchteile bleiben bei der Berechnung erhalten; Stufen werden für die Anzeige einzeln abgerundet und können deshalb zusammen um einzelne Einwohner vom Gesamtwert abweichen. Unbekannte beziehungsweise nicht passende Beiträge führen zu «nicht verfügbar» bei der Stufenaufteilung. Baupläne werden nicht als gebaute Häuser gezählt; leere gebaute Häuser zählen als Häuser.

Schiffsmodule sind keine zusätzlichen Schiffe. Schiffe ohne eingebaute Module werden über ihre Assets erkannt; Regionswechsel dürfen keine Doppelzählung erzeugen. Bei 1800 können Luftschiffe als Teil der erkannten Flotte separat ausgewiesen werden. Nicht auflösbare eigene Expeditionsschiff-Verweise führen zu «nicht verfügbar» statt zu einer unvollständigen Flottenzahl. Schiffstypnamen stammen aus den lokalen Spieldaten und werden nicht automatisch übersetzt. Bei 1404 ist die Typaufteilung derzeit nicht verfügbar. Sonderzustände wie unbekannte Ruinenmarkierungen, Mods und noch ungeprüfte Formatversionen können die Verfügbarkeit einschränken. Die Datenprüfung ersetzt keinen Abgleich mit der Anzeige im Spiel.

Die neuen Funktionen verwenden keine Online-Dienste. Persönliche Kennzahlen, Caches und Protokolle gehören nicht in Git, Releases oder Pages. Die öffentlichen Seiten werden ausschliesslich aus den mitgelieferten Demo-Eingaben erzeugt; fehlende Angaben in einem Demo-Save bleiben sichtbar als nicht verfügbar gekennzeichnet.

## Was ist eine Kartenvariante?

Eine Variante gruppiert Kartenkonfigurationen, keine Fortschritte oder Save-Daten. Mehrere Partien können dieselbe Variante verwenden; derselbe Seed kann mehrere Varianten haben. Bevölkerung, Vermögen, Wohnhäuser und Schiffe gehen nicht in die Gruppierung ein. Die aufklappbaren Karteneinstellungen zeigen die gespeicherten Vergleichswerte.

| Spiel | Unterscheidende gespeicherte Angaben |
|---|---|
| 117 | Kartentyp, Welt-/Inselgrösse und Schwierigkeit, Fruchtbarkeit/Vorkommen, Wald, Startprovinz, Modus, Kontinentalstart-/Besiedlungsregeln, Standardrivalen, aktive DLCs und Mods |
| 1800 | Kartentyp, Welt-/Inselgrösse und Schwierigkeit, Fruchtbarkeit/Vorkommen, Modus, gespeicherte Kartendefinitionen, Händler/Piraten und Rivalen, aktive DLCs/Mods und Kontorstart |
| 1404 | Modus, Seed, Spieltypvariation (einschliesslich Kampagnenkapitel), Szenario ausserhalb des Endlosspiels, tatsächliches Insellayout oder Geländeersatz, Karteneinstellungen ohne `RandomMap` und KI-Namen |

Bei 117/1800 ist die angezeigte Variantennummer ein Exportindex und kann sich durch zusätzliche Gruppen ändern. Die Varianten-ID bei 1404 wird aus dem Gruppierungs-Hash abgeleitet. Eine Variante ist von der Partiekennung zu unterscheiden, über die der neueste Kennzahlenstand gewählt wird. Konfigurationsunterschiede können getrennte Varianten erzeugen, selbst wenn die Kartenvorschauen gleich aussehen; daraus folgt kein Unterschied im Gelände.
