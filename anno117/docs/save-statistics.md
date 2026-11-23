# Current save statistics

[English](save-statistics.md) · [Deutsch](save-statistics.de.md)

The Anno 117, 1800 and 1404 map galleries include the current state of each identified campaign. **Last played on**, **Population**, **Wealth and Balance** inside **Finances**, **Residences** and **Ships** are directly visible. Population, finances, residences and ships start collapsed. Clicking or using the keyboard opens only that group. Population tiers and settled islands, income/expenses, residences by tier and blueprints, and ship types appear inside the corresponding group. Save dates, playtime records, file counts and sources are grouped per campaign under **Save details for this campaign**; map settings have their own collapsed group.

All statistics for a campaign come from the same latest save. Each campaign belongs to exactly one variant; its current date and values are not copied into older technical subgroups. Different campaigns sharing a seed are never added together. A map variant may therefore contain several separate campaign summaries. Map images remain reconstructions of saved terrain, without building or ownership overlays. Statistic and map sources are listed in the save details. The DE/EN switch works offline and preserves expanded groups.

## Selection and refresh

For 117 and 1800, the seed and saved campaign ID identify a campaign, and its internal save timestamp selects the latest save. On ties, 1800 prefers the live account over an archive copy. A profile folder alone is not a campaign identity. For 1404, the existing combination of game ID, full map variant and profiles is used; dates continue to use file timestamps. “Last played on” means the date of the latest available save, not an independently observed game launch.

The new reader opens only the latest save per campaign. Existing archive/playtime statistics remain intact. Separate `anno117-statistics.json`, `anno1800-statistics.json` or `anno1404-statistics.json` caches live in the report directory. File signatures, reader version and, for 117/1800, installed game-data signatures determine validity. `--rescan` refreshes these statistics too. Anno 1800 `--render-only` uses only existing valid statistic cache entries; missing entries show not available. An unreadable latest save never falls back to older statistics. Source files and personal settings are read only.

Excel includes an additional **Aktuelle Spielstände** worksheet with one row per campaign, its save date, seed, main statistics, settled islands, blueprints and save source. Existing map and playtime worksheets remain intact. Excel stays German and is outside the HTML language switch.

## Available data and limitations

| Value | Anno 117 | Anno 1800 | Anno 1404 |
|---|---|---|---|
| Total population and wealth | Saved profile values | Saved profile values where present | `stats.xml` |
| Population tiers | Residences plus attributable contributions from other buildings, cross-checked | Saved residence inhabitants, cross-checked | Saved per-player counters, cross-checked |
| Balance, income and expenses | Saved per-minute values, arithmetic checked | not available | not available |
| Built residences | Owned residence objects | Owned residence objects | Owned `ResidenceBuilding` objects |
| Residence blueprints | Separate count | Separate count | not available |
| Owned ships | Asset type and unique ship ID | Asset type and unique ship ID | Player ship list checked against objects |
| Settled islands | Current ownership; unavailable for Aegyptus sectors | Current ownership; shares are not island ownership | Started owned warehouses, once per island |

**Values that cannot be read reliably show “not available” / “nicht verfügbar”, never an invented zero.** This includes incomplete demo saves, unknown formats, uncertain player identity or an unconfirmed tier breakdown. A confirmed zero remains `0`. Missing detail values do not prevent independently confirmed totals from being shown.

Anno 117 stores some population values as Float32. Simply summing residence inhabitants misses population contributed by market/tavern and other effects on non-residential buildings. The reader uses local building and population definitions, and checks the result against the saved total. Residence workforce bonuses must not be mistaken for additional population. Fractional values are retained during calculation; individual tiers are rounded down for display and may therefore sum to slightly less than the overall total. Unknown or inconsistent contributions make the tier breakdown unavailable. Blueprints are excluded from built residences; empty built residences still count.

Ship modules are not additional ships. Ships without installed modules are recognised from their assets; region transfers must not duplicate them. For 1800, airships can be listed separately as part of the recognised fleet. Unresolved owned expedition-ship references make the fleet count unavailable rather than silently incomplete. Ship type names come from local game data and are not automatically translated. The 1404 ship-type breakdown is currently unavailable. Special states such as unknown ruin markers, mods and untested format versions may restrict availability. File-level checks do not replace an in-game comparison.

The new features use no online services. Personal statistics, caches and logs must stay out of Git, releases and Pages. Public pages are generated only from the bundled demo inputs; missing demo statistics remain explicitly marked unavailable.

## What is a map variant?

For Anno 117 and 1800, a campaign keeps its complete save history together. Grouping compares the latest known map options. When the latest save lacks an option, its last known value from the same campaign is used; unknown values are not guessed as defaults. Technical fields, DLC/mod lists, participant lists, warehouse/continental-start flags and patch-added internal fields do not create additional variants. Original raw values remain available in map settings.

Different campaigns sharing a seed are grouped by these player-facing map options:

| Game | Comparable map options |
|---|---|
| 117 | Map type, world/island size, island difficulty, fertility, resources, forest and starting province, plus game mode |
| 1800 | Map type, world/island size, island difficulty, fertility and resources, plus game mode; scenario map for scenarios |
| 1404 | Unchanged: mode, seed, game-type variation (including campaign chapter), scenario outside sandbox, actual island layout or terrain fallback, map settings except `RandomMap`, and AI names |

The 117/1800 card titles are followed by readable map options for direct comparison. A variant preview comes from one of its saves; identical menu options do not prove identical terrain when mods are involved. Population, wealth and playtime changes alone do not create a variant. Unknown map options in unrelated campaigns are not assumed equal.

The 117/1800 variant number is an export index and may change when groups are added; the 1404 variant ID derives from a hash. Each assigned campaign shows its own latest save with its own date and statistics. The gallery defaults to **Newest save first**, including without JavaScript. Every card has an always-visible **Back to top** link at its bottom right; the jump preserves filters and expanded groups.

## Save counts and playtime per campaign

Each campaign block has its own initially collapsed **Save details for this campaign**: file count, oldest/newest save and source, playtime in the latest save, and the longest saved playtime with date/source. The older-save playtime warning only compares saves of that same campaign. Different campaigns sharing a profile name remain separate.

A variant shows only **total campaigns**, **total save files** and **total campaign playtime**. The latter adds the longest saved playtime of each campaign once; autosave playtimes are not added together. The map preview source has a separate disclosure. Sorting by total playtime uses that same sum.

117/1800 file counts include scanned archive copies. 1404 keeps its existing content deduplication: identical save copies count once, and extra copies are reported in the page header. Variant and campaign counts use the same basis.

Excel lists campaign counts, save dates, playtimes and sources on **Aktuelle Spielstände**. **Kartenseeds** shows only variant totals for these values, without comparing playtime across campaigns.
