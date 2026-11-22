# Formate, Quellen und Grenzen

## Anno 117

Die Stempelgalerie liest die JSON-Stempelpakete mit ihren binären PipetteData-Blöcken. Grundflächen und Texte werden aus der lokal installierten Spielversion gelesen. Feldflächen, Strassen und Gebäude erscheinen als schematische PNGs. Ceres-Feldgrössen und kosmetische DLCs werden aus den tatsächlich enthaltenen Objekten und ihren Eigenschaften abgeleitet; unsichere Fälle sind gekennzeichnet.

Die CDLC-Erkennung berücksichtigt zusätzlich die Herkunft aus den kosmetischen Assetgruppen des exportierten `assets.xml` (CDLC01: `-1574124720`, CDLC02: `-417418295`, CDLC03: `385980937`). Namen und Grafikpfade allein reichen nicht aus: Ambrosianischer Wald (`158417`) und Keltischer Wald (`158418`) verwenden Grundspielpfade und stehen im Spiel unter «Klassisch», gehören aber zur Assetgruppe von Blütezeit (CDLC02). Enthaltene Waldflächen werden deshalb als Blütezeit erkannt. Die Zuordnung wird beim Einlesen der vollständigen Assetstruktur erhalten und gilt auch für tatsächlich gewählte Skin-Assets; ungenutzte optionale Skins zählen weiterhin nicht als Voraussetzung. Bei neuen kosmetischen Assetgruppen muss diese Herkunftszuordnung überprüft und ergänzt werden. Ein `data/base/`-Pfad oder die Baukategorie «Klassisch» ist kein Nachweis für CDLC-Freiheit.

Die bestehende Sonderbehandlung der Ausbaureserve für `Lavendel ohne Ceres` bleibt im Werkzeugcode erhalten. Sie verwendet `Lavendel ohne CDLC` aus der eingelesenen Bibliothek oder eine optionale lokale Referenz unter `<Spielausgabe>/stamps/references/Lavendel ohne CDLC.json`. Persönliche Stempel oder Referenzdateien werden nicht mitgeliefert.

Kartenbilder werden aus Save-Regionen und lokalen Inselgrafiken rekonstruiert. Bei zusammengesetzten Geländeabschnitten sind sichtbare Nähte möglich.

## Anno 1800

Die Stempeldateien werden als zlib-komprimierte FileDB-Daten gelesen. Grundflächen stammen aus RDA-Archiven und bei resident gespeicherten Dateien zusätzlich aus `file.db`. Die Galeriefilter berücksichtigen enthaltene Traktormodule, Silos, strompflichtige Gebäude, mögliche Stromboni, Kraftwerke, Rathäuser und Handelskammern. Ein Traktor als Dekoration zählt nicht als Modul. Regionale Rathaus-/Handelskammer-Varianten werden über ihre Gebäude-Assetvererbung erkannt.

DLC-Hinweise beschreiben die erkannten Standardobjekte und zuordenbaren Skins. Nicht verwendete optionale Skins zählen nicht als Voraussetzung. Items, Reichweiten, Strassenanschlüsse, Brennstoff- oder Futterversorgung und Produktionsverhältnisse werden nicht simuliert. Die Karten-/Spielstandauswertung zeigt gespeicherte Karten und Metadaten, keine Gebäudestände oder Besitzverhältnisse.

## Anno 1404

Die Spielstandauswertung liest RDA-V2.0-Archive und die darin enthaltenen XML-/BIN-Daten. Karten werden aus dem im Save gespeicherten Gelände rekonstruiert. Identische Save-Kopien werden für die Auswertung zusammengefasst. Eine Stempelgalerie ist für Anno 1404 derzeit nicht implementiert.

## Referenzen

Diese Projekte dienen als Dokumentations- und Formatreferenzen. Es werden weder deren vollständige Programme noch Spieldaten mitgeliefert.

- [FileDBReader](https://github.com/anno-mods/FileDBReader)
- [IFO-Dokumentation](https://github.com/anno-mods/modding-guide/blob/main/documentation/ifo-file.md)
- [Anno Designer](https://github.com/AnnoDesigner/anno-designer)
- [Anno-117-Spielstandstruktur](https://github.com/ewjax/Anno-117-IslandSelection/blob/main/savegame_structure.md)
- [Anno-117-Kartenformat](https://github.com/Taludas/Anno-117-Seed-Finder/blob/main/CAVEATS.md)
- [RDA-Formatdokumentation](https://github.com/lysanntranvouez/RDAExplorer/wiki/RDA-File-Format)

Unterstützung hängt von den Formaten der jeweiligen Spielversion ab. Unbekannte Objekte oder Grundflächen können eine Aktualisierung der Werkzeuge erfordern. Keine der Ausgaben ersetzt einen Test im Spiel.

## Galeriesprache

Alle fünf Galerien besitzen einen DE/EN-Schalter. Die Umschaltung betrifft die HTML-Oberfläche; eigene Namen, Dateipfade, technische Rohwerte, aus den Spieldaten übernommene Objekt-/DLC-Namen, Beschriftungen innerhalb der PNGs und Excel-Auswertungen behalten ihre bisherige Sprache.
