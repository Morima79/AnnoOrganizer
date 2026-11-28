# Shared gallery templates

[English](gallery-templates.md) · [Deutsch](gallery-templates.de.md) · [README](../README.md)

The five galleries use two centrally maintained page templates:

| Gallery | HTML | Colours and layout |
|---|---|---|
| Maps | [map_gallery.html](../templates/map_gallery.html) | [map_gallery.css](../templates/map_gallery.css) |
| Stamps | [stamp_gallery.html](../templates/stamp_gallery.html) | [stamp_gallery.css](../templates/stamp_gallery.css) |
| Demo landing page | [demo_index.html](../templates/demo_index.html) | Page styles in the template, shared switch CSS |

The shared [anno_gallery.py](../templates/anno_gallery.py) renderer assembles the page frame, logo and colour theme. Anno 117 and 1800 additionally share the complete catalogue in `templates/map_catalog.html`, its `map_catalog.js` runtime and the card/page renderer `anno_map_catalog.py`. Their exporters supply game-specific maps and detail values. Anno 1404 retains its terrain-card grid and edition filter, using the same frame, theme resources and statistic groups. Images, CSS and logos remain local or embedded; generated galleries do not require a web server.

Map and stamp galleries consistently use `system-ui, sans-serif`, including page and card headings. Page headings share their font size, weight and line height. README previews use one shared table with images set to 360 pixels wide; capture new screenshots at an image width of 1264 pixels (1280-pixel browser width including the scrollbar).

The logo and DE/EN switch share a top-aligned row. The renderer measures the logo's visible alpha bounds and hides transparent margins in layout while preserving the embedded original PNG bytes. On narrow screens the logo shrinks and the language buttons remain accessible. [Compact header preview](images/gallery-header.jpg).

Both stamp headers show the unfiltered number of exported stamps and the number of regions represented by those stamps. The shared renderer derives these totals from the cards; shared `stamp-totals` styles give each badge one border. Translation spans do not receive badge styling.

## Colours

Colours are inspired by each game's interface. Transparent logos blend into those surfaces. `THEMES` in the shared renderer defines the background and readable text, border and link colours:

- Anno 117: beige (`#f1e5cc`).
- Anno 1800: dark blue (`#173345`).
- Anno 1404: light parchment (`#f3ead8`) with brown and gold accents.

Map galleries use this theme throughout the page. Stamp galleries use it for the header banner, keeping the search and blueprint area light. The logo has no separate background panel. Both stamp footers contain only the update timestamp (`Stand:` / `Updated:`).

## DE / EN languages

All five galleries share a language switch in their header. All galleries also provide it inside the modal image viewer. Switching preserves search, filter values, sorting, selected profiles, expanded details and the open image with its zoom state. The HTML language, page title, placeholders and accessible image/button descriptions also change.

The demo landing page uses the same DE/EN switch and stored language choice. Navigation to a gallery and back through its demo link retains the selected language when browser storage is available. Its title, meta description, introduction, gallery links and footer use the central `demo.*` resources. `--refresh-site` renders `templates/demo_index.html` into `site/index.html`; `--check` detects a stale landing page. [English landing-page preview](images/demo-home-en.jpg).

The five gallery links open separate tabs and announce this in their translated accessible labels. The landing page remains open. Anno 1404 terrain images use one sea colour (`#366d7c`) for both open water and the water within island bounds, avoiding rectangular patches. Existing cached images are regenerated after a renderer version change or `--rescan`.

The canonical resources are [locales/de.json](../templates/locales/de.json) and [locales/en.json](../templates/locales/en.json). Both use matching stable keys and placeholders, for example `stamp.count` with `{shown}` and `{total}`. `.one` variants handle singular forms. Missing keys or mismatched placeholders stop the export with an explanatory error.

[anno_i18n.py](../templates/anno_i18n.py) binds known interface messages and generated labels to resource keys. Templates can contain explicit bindings such as `<span data-i18n="filters.allRegions">Alle Regionen</span>`. Dynamic exporter scripts use `galleryI18n.t('stamp.count', {shown, total})` and listen for `gallerylanguagechange`. Only text and labels change; option values stay stable. Identity text and paths are excluded. Use `data-i18n-ignore` for additional content that must remain unchanged.

The renderer embeds both JSON resources, [gallery_i18n.js](../templates/gallery_i18n.js) and switch CSS into each generated HTML file. There are no language-file requests or new runtime dependencies, so switching also works when opening a local HTML file directly. German is the default. The browser stores the choice under `annoorganizer.gallery.language` when storage is available; blocked storage does not prevent switching. With JavaScript disabled the German interface remains readable.

Custom profile, folder and stamp names, paths, raw technical values and object/DLC names read from game data remain unchanged. Labels inside PNGs, Excel reports, launcher menus and logs are outside the HTML language switch.

Maintain both canonical JSON files, then synchronise the templates and refresh the demos. Tests cover matching keys/placeholders, valid bindings on all five pages, identity preservation, safe embedding, independent game bundles and JavaScript behaviour with blocked or invalid browser storage. Run `node --test tests/gallery_i18n_runtime.cjs tests/map_catalog_runtime.cjs` for the JavaScript tests alone; Python tests also run them when Node.js is available.

[English gallery preview with the DE/EN switch](../anno117/docs/images/stamp-gallery-en.jpg). All five galleries have matching German (`*-gallery.jpg`) and English (`*-gallery-en.jpg`) screenshots. Each README uses its own language, with clickable 360-pixel previews and a source image width of 1264 pixels. The verified Edge DevTools capture workflow is documented in `AGENTS.md`.

## Island graphics

Anno 117 uses runtime DDS graphics for every island, without falling back to PNG previews. Latium, Albion and Aegyptus use region-specific midtone brightness ranges and gently reduced saturation. Dark Roman islands receive less brightening, while Albion greens and Egyptian sand retain their regional character. Alpha, coastlines and neutral rock colours remain intact. Aegyptus is framed at the outer edges of its four terrain quadrants (1920 × 1920 tiles), removing the empty water above and to the right and enlarging the terrain by one third within the same image width. Saved map dimensions are preserved; the image footer identifies the cropped view. All decoded and colour-adjusted island graphics are reused across exports from `terrain-cache/` in the configured report output. The cache key includes the renderer version, archive entry, archive size and modification time; damaged entries are regenerated. Aegyptus terrain overlaps are feathered only over existing terrain, preserving coastlines and covering the quadrants' black placeholder areas. Differences in the source textures can still remain visible.

## Changing templates

1. Edit HTML, CSS or `THEMES` in the canonical `templates/` folder only.
2. Run `python scripts/sync_gallery_templates.py --refresh-site`. This synchronises the bundled copies, updates the demo landing page and refreshes the frames of the five existing demo snapshots. Demo data and image references are preserved; game data is not needed for this operation.
3. Run `python scripts/sync_gallery_templates.py --check`, `python scripts/validate_site.py` and `python -m unittest discover -s tests -v`.
4. Refresh personal galleries using the relevant AnnoOrganizer launcher. If demo contents changed, regenerate the demos through the regular exporters as well.

Each Anno folder includes the renderer and template copies under `tools/`. These are synchronised from the canonical sources and checked by tests, so each game folder remains independently usable. No symlinks or additional runtime dependencies are required. Do not edit bundled copies separately.

Operational and file-status messages belong in logs rather than galleries. Maps, blueprint properties and information needed to use them remain visible.

## Save statistic groups

Shared presentation lives in `templates/anno_save_summary.py`; conservative readers live in `templates/anno_save_statistics.py`. Both are synchronised into the independently usable game bundles together with the templates. Exporters supply separate campaign summaries; native `details`/`summary` elements keep details collapsed initially. Labels and population tiers are maintained in both central language resources. [Statistics and limitations](save-statistics.md).

## Image navigation

All five galleries open images in a dialog with zoom and PNG download. All three map galleries share `templates/map_viewer.html` and `map_viewer.js`, with original-size/fit controls, image-click zoom and an in-dialog DE/EN switch. Native PNG links remain available without JavaScript and for modified clicks. The existing stamp dialogs and all map dialogs share history handling in `templates/stamp_viewer.js`, using separate history keys. Opening a dialog adds one entry with the unchanged gallery URL. Browser Back closes it; Forward reopens the same image. Close, Escape and backdrop clicks also return to the gallery entry. Filters stay on the page; language changes retain the zoom state. Blocked history access leaves the dialog usable, but cannot provide browser navigation. Run `node --test tests/map_viewer_runtime.cjs tests/stamp_viewer_runtime.cjs` for navigation and viewer regressions.

## Map catalogue controls

Anno 1404 likewise restores search, edition, sorting and profile selection on its own history entry.

117/1800 store search, mode, sorting and exact profile selection on the current browser history entry. Opening a map image and returning with Back restores those controls and the result count, including when the browser reloads the page instead of using its page cache. Separate gallery entries remain independent. Blocked history access does not prevent filtering, but restoration is then unavailable.

117 and 1800 use the same profile ranking, collapsed seed list, search, mode filter, sorting, result count and two return buttons. The seed list counts distinct seeds in the export. Profile links select an exact profile and scroll to the filters; returning clears the profile/search/mode filters and restores focus to the selected ranking link. Search uses `data-profiles`, independent of visible statistic groups, and numeric queries match an exact seed. The controls align along their bottom edge and wrap on narrow screens. Sorting and DE/EN changes move existing cards and preserve their open groups. Finances precede population, residences and ships in all three games, keeping population and residences adjacent. Regression tests execute the shared runtime, including cards without the optional `.profiles` paragraph.

The shared `anno_map_variants.py` groups full campaign histories by player-facing map options, excluding patch drift. Each campaign appears in one variant only. Exports and the initial sort control use newest save first. Every map card, including 1404, has a native link to the shared `gallery-top` anchor outside collapsed groups.

Game-specific setting labels are rendered by `anno_game_settings.py` from `game_settings.json` and explicit `gameSetting.*` locale bindings. They are excluded from generic text matching to avoid ambiguous translations such as Normal/Regular/Medium. [Setting sources and enum mappings](game-settings.md).

## Temporary working files

Map and stamp exports stage intermediate files outside OneDrive. The user temporary directory is the default. Set the optional `ANNOORGANIZER_TEMP_DIR` environment variable to an existing writable absolute directory to override it locally. Missing, unusable or OneDrive-based overrides fall back to user temp. No machine-specific path is bundled. Restart the application after changing its environment. Configured or recognisable OneDrive locations are rejected. Final galleries, caches and logs retain their configured destinations. Publication supports separate temporary/output volumes and restores existing files if copying fails. If restoration fails, the working directory and its rollback files are retained; the error names their location and `RECOVERY.json` records unresolved files when writable. Do not delete these recovery files before restoring the output.

## Illustrated user guide

The demo home page links to `site/guide/index.html`. The desktop **User guide** button opens `docs/user-guide.html` offline in the selected language; packaged builds include this page and its images. Both HTML versions are generated from `docs/desktop.md` and `docs/desktop.de.md` using `templates/user_guide.html`, `templates/user_guide.js` and the shared language resources. Edit the Markdown sources, then run `scripts/sync_gallery_templates.py --refresh-site`; `--check` also verifies both generated pages and the eight copied guide screenshots. `scripts/validate_site.py` checks all seven public pages. Keep command-line and advanced configuration instructions in the separate `desktop-reference` guides.
