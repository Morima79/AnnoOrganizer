# Map and game settings: DE/EN labels

[English](game-settings.md) · [Deutsch](game-settings.de.md)

Galleries use a verified game-specific label table. Canonical sources are `templates/game_settings.json`, `templates/anno_game_settings.py` and the shared language resources. Copies ship with each independently usable game folder. Full game files are not distributed. Anno 1404 still needs no game installation for its demo or regular save export.

## Sources and value mappings

Local game data inspected on 2026-11-24. The table records text IDs, enum names, dataset names and SHA-256 hashes of inspected dataset files. Confirmed original headings have `label_origin: game`; descriptive tool headings have `label_origin: tool` where an original heading could not be confirmed. Technical keys and unknown values are not replaced with guessed game terms.

| Game | Evidence |
|---|---|
| 117 | `config.rda`: `data/base/config/export/assets.xml`, `properties-meta.xml`, `data/base/config/game/datasets.xml`, `data/base/config/gui/texts_german.xml` and `texts_english.xml`. `DifficultySettings` asset `2002450`, `SettingsMenu` headings and `MapTemplateType` text references. |
| 1800 | `data/config/export/main/asset/assets.xml`, `properties-toolone.xml`, `datasets.xml`, `data/config/gui/texts_german.xml` and `texts_english.xml`. Asset `2002450`: `DifficultySettings/Descriptions` and enum `ValueName` references. |
| 1404 | `data/config/game/properties.xml` and `datasets.xml`, plus DE/EN texts in `data/loca/{ger,eng}/txt/interface.txt`. Named `Choice` datasets use their declared zero-based order. Base/Venice language files were inspected; this does not replace checking every option in every edition in-game. |

Messages use `gameSetting.<game>.<key>.*` in both language files. Exporters bind these keys explicitly in HTML; they are **excluded** from global word matching. Identical words can have different translations for different options. Custom names, raw values and unmapped content remain unchanged.

## Corrected contexts

- **117:** `SetupRawMaterial` is **Bauplätze / Building Slots**; `SetupFertility` is **Fruchtbarkeiten und Vorkommen / Fertilities and Lodes**. Saved setup island size uses `DCStartSessionIslandSize`: `0 = Large`, `1 = Medium`, `2 = Small`. Generated geometry uses `IslandSize`: `0 = Small`, `1 = Medium`, `2 = Large`. Generated sizes therefore have separate descriptive labels. The previously shared size dictionary was incorrect for raw setup values.
- **117:** Non-sequential IDs follow the datasets, including research `7 = Medium` and relocation `2 = PayCredits`. Visible menu order is not used as a numeric scale.
- **1800:** Original labels include **Art der Karte / Map Type**, **Startweltgröße / Starting World Size** and **Erzvorkommen / Mineral Deposits**. Island sizes are **Mainly Small/Medium/Large** and do not share starting-world size labels.
- **1404:** Original labels include **Kartengröße / Map size**, **Inselgrößen / Island size** and **Startguthaben / Start balance**. Confirmed Choice values use contextual translations: German “normal” can mean “medium” here without changing other “Normal” messages.

Original game spelling, case and `ß` are preserved in imported text. German documentation and tool-authored messages retain Swiss spelling.

## Limitations

Unknown values retain the raw value with **unbekannte Zuordnung / unmapped value**. Missing values show **nicht verfügbar / not available**. Unconfirmed bitmasks, composite starting conditions and internal setup fields are not guessed. In particular, “Start situation” is a 1404 menu group, not a confirmed label for each individual starting field.

Current game data does not prove unchanged historical semantics. Grouping and raw data are therefore unchanged by this presentation update. Display uses the bundled verified table; future game updates need comparison against text IDs and datasets. PNG labels and custom object/profile names are outside the HTML switch. Excel uses German labels.

Regression tests cover opposite size scales, non-sequential IDs, contextual translations, unknown raw values, both languages and offline exports. File inspection does not replace an in-game visual check.
