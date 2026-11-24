# Karten- und Spieleinstellungen: DE/EN-Bezeichnungen

[English](game-settings.md) · [Deutsch](game-settings.de.md)

Die Galerien verwenden eine geprüfte, spielbezogene Beschriftungstabelle. Die kanonischen Quellen sind `templates/game_settings.json`, `templates/anno_game_settings.py` und die zentralen Sprachressourcen. Sie werden in jeden eigenständig nutzbaren Spielordner kopiert. Es werden keine vollständigen Spieldateien mitgeliefert. Anno 1404 benötigt weiterhin keine Installation für den Demo- oder normalen Save-Export.

## Quellen und Wertzuordnung

Geprüfter lokaler Spieldatenstand: 24.11.2026. Die Tabelle enthält Text-IDs, Enum-Namen, Datensatznamen und Prüfsummen der ausgewerteten Dataset-Dateien. Belegte Originalüberschriften sind mit `label_origin: game` gekennzeichnet. Wo keine eindeutige Originalüberschrift verfügbar ist, bleibt eine beschreibende Werkzeugbezeichnung mit `label_origin: tool` erhalten. Technische Schlüssel und unbekannte Werte werden nicht durch vermutete Spieltexte ersetzt.

| Spiel | Nachweis |
|---|---|
| 117 | `config.rda`: `data/base/config/export/assets.xml`, `properties-meta.xml`, `data/base/config/game/datasets.xml`, `data/base/config/gui/texts_german.xml` und `texts_english.xml`. `DifficultySettings`-Asset `2002450`, `SettingsMenu`-Überschriften und `MapTemplateType`-Textverweise. |
| 1800 | `data/config/export/main/asset/assets.xml`, `properties-toolone.xml`, `datasets.xml`, `data/config/gui/texts_german.xml` und `texts_english.xml`. Asset `2002450`: `DifficultySettings/Descriptions` und Enum-`ValueName`-Verweise. |
| 1404 | `data/config/game/properties.xml` und `datasets.xml`, dazu DE-/EN-Texte aus `data/loca/{ger,eng}/txt/interface.txt`. Benannte `Choice`-Datensätze verwenden die deklarierte nullbasierte Reihenfolge. Grundspiel/Venedig-Sprachdateien wurden gelesen; eine Sichtprüfung jeder Option in jeder Edition ist damit nicht ersetzt. |

Die Label- und Wertetexte stehen in beiden Sprachdateien unter `gameSetting.<Spiel>.<Schlüssel>.*`. Diese Schlüssel werden ausdrücklich im erzeugten HTML gebunden und nehmen **nicht** an der globalen Worterkennung teil. Gleichlautende Wörter dürfen je nach Einstellung andere Übersetzungen besitzen. Eigene Namen, Rohwerte und nicht zugeordnete Inhalte bleiben unverändert.

## Korrigierte Kontexte

- **117:** `SetupRawMaterial` bezeichnet **Bauplätze / Building Slots**, `SetupFertility` **Fruchtbarkeiten und Vorkommen / Fertilities and Lodes**. Die gespeicherte Setup-Inselgrösse verwendet `DCStartSessionIslandSize`: `0 = Large`, `1 = Medium`, `2 = Small`. Die erzeugte Kartengeometrie verwendet dagegen `IslandSize`: `0 = Small`, `1 = Medium`, `2 = Large`. Daher werden erzeugte Grössen separat als solche beschriftet. Das bisher gemeinsam verwendete Grössenwörterbuch war für die rohen Setup-Werte falsch.
- **117:** Weitere nicht fortlaufend angeordnete IDs werden anhand der Datasets zugeordnet, zum Beispiel Forschungsstufe `7 = Medium` und Gebäude-Neupositionierung `2 = PayCredits`. Die Reihenfolge sichtbarer Menüeinträge wird nicht als Zahlenskala benutzt.
- **1800:** **Art der Karte / Map Type**, **Startweltgröße / Starting World Size** und **Erzvorkommen / Mineral Deposits** verwenden Originaltexte. Inselgrössen heissen **Mehrheitlich klein/mittel/gross / Mainly Small/Medium/Large** und teilen sich nicht das Grössenwörterbuch der Startwelt.
- **1404:** Unter anderem **Kartengröße / Map size**, **Inselgrößen / Island size** und **Startguthaben / Start balance**. Die zugeordneten Choice-Werte werden kontextbezogen übersetzt. «normal» kann hier «medium» bedeuten, ohne andere «Normal»-Angaben zu verändern.

Originalschreibweisen, einschliesslich Gross-/Kleinschreibung und `ß`, bleiben in übernommenen Spieltexten erhalten. Die Dokumentation und eigene Werkzeugtexte verwenden weiterhin Schweizer Schreibweise.

## Grenzen

Anno 1800s **Hafenarbeiter / Dockworkers** ist die originale Text-ID `11017` zum gespeicherten Einstellungsfeld `SetupDistributionWorkforce`. Das Dataset benennt die Werte als Reichlich/Mittel/Spärlich. Es handelt sich um eine gespeicherte Setup-Option, keine gezählte Arbeiterzahl oder Bevölkerungsstufe. Ihre praktische Wirkung im veröffentlichten Spiel ist nicht geprüft; die Bezeichnung allein belegt keine aktive Spielmechanik.

Unbekannte Werte erscheinen mit dem unveränderten Rohwert und **unbekannte Zuordnung / unmapped value**. Fehlende Werte erscheinen als **nicht verfügbar / not available**. Für nicht eindeutig zugeordnete Bitmasken, zusammengesetzte Startbedingungen oder interne Setup-Felder werden keine Bezeichnungen geraten. Insbesondere ist «Startsituation» bei 1404 eine Menügruppe und keine belegte Übersetzung jedes einzelnen Startfelds.

Die aktuellen Spieldaten beweisen keine unveränderte historische Bedeutung aller Felder. Deshalb werden Gruppierung und Rohdaten durch diese Beschriftungsänderung nicht verändert. Die Anzeige basiert auf der mitgelieferten geprüften Tabelle; ein späteres Spielupdate muss gegen Text-IDs und Datasets geprüft werden. PNG-Beschriftungen und eigene Objekt-/Profilnamen werden durch den HTML-Sprachwechsel nicht übersetzt. Excel verwendet die deutschen Bezeichnungen.

Regressionstests prüfen die gegensätzlichen Grössenskalen, nicht fortlaufende IDs, kontextbezogene Übersetzungen, unbekannte Rohwerte, beide Sprachen sowie den Offline-Export. Die Dateiprüfung ersetzt keine Sichtprüfung im Spiel.
