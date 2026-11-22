# Gemeinsame Galerie-Vorlagen

[English](gallery-templates.md) · [Deutsch](gallery-templates.de.md) · [README](../README.de.md)

Die fünf Galerien verwenden zwei zentral gepflegte Seitenvorlagen:

| Galerie | HTML | Farben und Layout |
|---|---|---|
| Karten | [map_gallery.html](../templates/map_gallery.html) | [map_gallery.css](../templates/map_gallery.css) |
| Stempel | [stamp_gallery.html](../templates/stamp_gallery.html) | [stamp_gallery.css](../templates/stamp_gallery.css) |

Der gemeinsame Renderer [anno_gallery.py](../templates/anno_gallery.py) setzt den Seitenrahmen, das Logo und das Farbthema zusammen. Spielbezogene Karten, Gebäudeangaben, Filter und JavaScript bleiben bei den jeweiligen Exportern. Bilder, CSS und Logo werden wie bisher lokal eingebunden; für die erzeugte Galerie ist kein Webserver erforderlich.

Karten- und Stempelgalerien verwenden einheitlich `system-ui, sans-serif`, einschliesslich Haupt- und Kartentiteln. Haupttitel teilen sich Schriftgrösse, Gewicht und Zeilenhöhe. Die README-Vorschauen stehen in einer gemeinsamen Tabelle mit einheitlich 360 Pixel breiten Bildern; neue Screenshots werden mit 1264 Pixel Bildbreite aufgenommen (1280 Pixel Browserbreite einschliesslich Scrollleiste).

## Farben

Die Farben orientieren sich an der jeweiligen Spieloberfläche. Die transparenten Logos fügen sich in diese Flächen ein. `THEMES` im gemeinsamen Renderer legt Hintergrund sowie lesbare Text-, Rahmen- und Linkfarben fest:

- Anno 117: Beige (`#f1e5cc`).
- Anno 1800: Dunkelblau (`#173345`).
- Anno 1404: Helle Pergamentoptik (`#f3ead8`) mit Braun- und Goldtönen.

Bei Kartengalerien gilt dieses Thema für die gesamte Seite. Bei Stempelgalerien gilt es für den Header-Banner; der Bereich mit Suche und Bauplänen bleibt hell. Das Logo selbst bekommt keine separate Hintergrundfläche. Beide Stempel-Fusszeilen enthalten ausschliesslich `Stand: <Datum Uhrzeit>`.

## Vorlagen ändern

1. HTML, CSS oder `THEMES` ausschliesslich im zentralen Ordner `templates/` bearbeiten.
2. `python scripts/sync_gallery_templates.py --refresh-site` ausführen. Das synchronisiert die mitgelieferten Kopien und aktualisiert den Seitenrahmen der fünf bestehenden Demo-Snapshots. Die Demo-Daten und Bildverweise bleiben erhalten; dafür sind keine Spieldaten nötig.
3. `python scripts/sync_gallery_templates.py --check`, `python scripts/validate_site.py` und `python -m unittest discover -s tests -v` ausführen.
4. Persönliche Galerien mit dem jeweiligen AnnoTools-Starter aktualisieren. Bei geänderten Demo-Inhalten die Demos zusätzlich regulär neu erzeugen.

Jeder Anno-Ordner enthält den Renderer und seine Vorlagen unter `tools/`. Diese Kopien werden automatisch aus den zentralen Quellen übernommen und von den Tests geprüft. Dadurch bleibt ein einzelner Anno-Ordner ohne den Rest des Repositories nutzbar. Keine Symlinks und keine zusätzlichen Laufzeit-Abhängigkeiten sind erforderlich. Die mitgelieferten Kopien nicht separat bearbeiten.

Reine Betriebs- und Dateistatusmeldungen gehören in die Protokolle, nicht in die Galerien. Karten, Bauplan-Eigenschaften und die für ihre Verwendung nötigen Hinweise bleiben sichtbar.
