# Shared gallery templates

[English](gallery-templates.md) · [Deutsch](gallery-templates.de.md) · [README](../README.md)

The five galleries use two centrally maintained page templates:

| Gallery | HTML | Colours and layout |
|---|---|---|
| Maps | [map_gallery.html](../templates/map_gallery.html) | [map_gallery.css](../templates/map_gallery.css) |
| Stamps | [stamp_gallery.html](../templates/stamp_gallery.html) | [stamp_gallery.css](../templates/stamp_gallery.css) |

The shared [anno_gallery.py](../templates/anno_gallery.py) renderer assembles the page frame, logo and colour theme. Game-specific maps, building details, filters and JavaScript stay with their exporters. Images, CSS and logos remain local or embedded; generated galleries do not require a web server.

## Colours

Colours are inspired by each game's interface. Transparent logos blend into those surfaces. `THEMES` in the shared renderer defines the background and readable text, border and link colours:

- Anno 117: beige (`#f1e5cc`).
- Anno 1800: dark blue (`#173345`).
- Anno 1404: light parchment (`#f3ead8`) with brown and gold accents.

Map galleries use this theme throughout the page. Stamp galleries use it for the header banner, keeping the search and blueprint area light. The logo has no separate background panel. Both stamp footers contain only `Stand: <date time>`.

## Changing templates

1. Edit HTML, CSS or `THEMES` in the canonical `templates/` folder only.
2. Run `python scripts/sync_gallery_templates.py --refresh-site`. This synchronises the bundled copies and refreshes the frames of the five existing demo snapshots. Demo data and image references are preserved; game data is not needed for this operation.
3. Run `python scripts/sync_gallery_templates.py --check`, `python scripts/validate_site.py` and `python -m unittest discover -s tests -v`.
4. Refresh personal galleries using the relevant AnnoTools launcher. If demo contents changed, regenerate the demos through the regular exporters as well.

Each Anno folder includes the renderer and template copies under `tools/`. These are synchronised from the canonical sources and checked by tests, so each game folder remains independently usable. No symlinks or additional runtime dependencies are required. Do not edit bundled copies separately.

Operational and file-status messages belong in logs rather than galleries. Maps, blueprint properties and information needed to use them remain visible.
