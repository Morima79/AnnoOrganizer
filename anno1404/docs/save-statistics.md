# Current save statistics

[English](save-statistics.md) · [Deutsch](save-statistics.de.md)

The Anno 117, 1800 and 1404 map galleries include the current state of each identified campaign. **Last played on**, **Population**, **Wealth and Balance** inside **Finances**, **Residences** and **Ships** are directly visible. Population, finances, residences and ships start collapsed. Clicking or using the keyboard opens only that group. Population tiers and settled islands, income/expenses, residences by tier and blueprints, and ship types appear inside the corresponding group. Previous save dates, playtime records, file counts and sources are grouped under **Save details**; map settings have their own collapsed group.

All statistics for a campaign come from the same latest save. Different campaigns sharing a seed are never added together. A map variant may therefore contain several separate campaign summaries. Map images remain reconstructions of saved terrain, without building or ownership overlays. Statistic and map sources are listed in the save details. The DE/EN switch works offline and preserves expanded groups.

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
