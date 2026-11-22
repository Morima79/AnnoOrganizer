# Shared gallery templates

[English](gallery-templates.md) · [Deutsch](gallery-templates.de.md) · [README](../README.md)

The five galleries use two centrally maintained page templates:

| Gallery | HTML | Colours and layout |
|---|---|---|
| Maps | [map_gallery.html](../templates/map_gallery.html) | [map_gallery.css](../templates/map_gallery.css) |
| Stamps | [stamp_gallery.html](../templates/stamp_gallery.html) | [stamp_gallery.css](../templates/stamp_gallery.css) |

The shared [anno_gallery.py](../templates/anno_gallery.py) renderer assembles the page frame, logo and colour theme. Game-specific maps, building details, filters and JavaScript stay with their exporters. Images, CSS and logos remain local or embedded; generated galleries do not require a web server.

Map and stamp galleries consistently use `system-ui, sans-serif`, including page and card headings. Page headings share their font size, weight and line height. README previews use one shared table with images set to 360 pixels wide; capture new screenshots at an image width of 1264 pixels (1280-pixel browser width including the scrollbar).

## Colours

Colours are inspired by each game's interface. Transparent logos blend into those surfaces. `THEMES` in the shared renderer defines the background and readable text, border and link colours:

- Anno 117: beige (`#f1e5cc`).
- Anno 1800: dark blue (`#173345`).
- Anno 1404: light parchment (`#f3ead8`) with brown and gold accents.

Map galleries use this theme throughout the page. Stamp galleries use it for the header banner, keeping the search and blueprint area light. The logo has no separate background panel. Both stamp footers contain only the update timestamp (`Stand:` / `Updated:`).

## DE / EN languages

All five galleries share a language switch in their header. Stamp galleries also provide it inside the modal image viewer. Switching preserves search, filter values, sorting, selected profiles, expanded details and the open image with its zoom state. The HTML language, page title, placeholders and accessible image/button descriptions also change.

The canonical resources are [locales/de.json](../templates/locales/de.json) and [locales/en.json](../templates/locales/en.json). Both use matching stable keys and placeholders, for example `stamp.count` with `{shown}` and `{total}`. `.one` variants handle singular forms. Missing keys or mismatched placeholders stop the export with an explanatory error.

[anno_i18n.py](../templates/anno_i18n.py) binds known interface messages and generated labels to resource keys. Templates can contain explicit bindings such as `<span data-i18n="filters.allRegions">Alle Regionen</span>`. Dynamic exporter scripts use `galleryI18n.t('stamp.count', {shown, total})` and listen for `gallerylanguagechange`. Only text and labels change; option values stay stable. Identity text and paths are excluded. Use `data-i18n-ignore` for additional content that must remain unchanged.

The renderer embeds both JSON resources, [gallery_i18n.js](../templates/gallery_i18n.js) and switch CSS into each generated HTML file. There are no language-file requests or new runtime dependencies, so switching also works when opening a local HTML file directly. German is the default. The browser stores the choice under `annotools.gallery.language` when storage is available; blocked storage does not prevent switching. With JavaScript disabled the German interface remains readable.

Custom profile, folder and stamp names, paths, raw technical values and object/DLC names read from game data remain unchanged. Labels inside PNGs, Excel reports, launcher menus and logs are outside the HTML language switch.

Maintain both canonical JSON files, then synchronise the templates and refresh the demos. Tests cover matching keys/placeholders, valid bindings on all five pages, identity preservation, safe embedding, independent game bundles and JavaScript behaviour with blocked or invalid browser storage. Run `node --test tests/gallery_i18n_runtime.cjs` for the JavaScript tests alone; Python tests also run them when Node.js is available.

[English gallery preview with the DE/EN switch](../anno117/docs/images/stamp-gallery-en.jpg). The five existing README previews show the German interface with its language switch; all captures use the same image width.

## Changing templates

1. Edit HTML, CSS or `THEMES` in the canonical `templates/` folder only.
2. Run `python scripts/sync_gallery_templates.py --refresh-site`. This synchronises the bundled copies and refreshes the frames of the five existing demo snapshots. Demo data and image references are preserved; game data is not needed for this operation.
3. Run `python scripts/sync_gallery_templates.py --check`, `python scripts/validate_site.py` and `python -m unittest discover -s tests -v`.
4. Refresh personal galleries using the relevant AnnoTools launcher. If demo contents changed, regenerate the demos through the regular exporters as well.

Each Anno folder includes the renderer and template copies under `tools/`. These are synchronised from the canonical sources and checked by tests, so each game folder remains independently usable. No symlinks or additional runtime dependencies are required. Do not edit bundled copies separately.

Operational and file-status messages belong in logs rather than galleries. Maps, blueprint properties and information needed to use them remain visible.
