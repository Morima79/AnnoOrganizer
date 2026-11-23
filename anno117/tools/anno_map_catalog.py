"""Render the shared Anno 117/1800 map catalogue and card structure."""
from collections import Counter
from html import escape
import json
from pathlib import Path
import re

from anno_gallery import render_gallery
from anno_save_summary import label, message, render_statistics, totals_html


def text(key, **params):
    attributes = escape(json.dumps(params, ensure_ascii=False), quote=True)
    return (f'<span data-i18n="{key}" data-i18n-params="{attributes}">'
            + escape(message(key).format(**params)) + '</span>')


def describe_options(options):
    """Keep labels and known menu values separately localisable by the binder."""
    return ' · '.join('<span>' + escape(name) + '</span>: <span>' + escape(value) + '</span>'
                      for name, value in options)


def render_card(seed, variant, mode, profiles, profile_text, sort, statistics,
                save_count, save_details, maps, settings, description=''):
    """Exporters supply domain-specific detail markup; card layout is shared."""
    data = dict(seed=seed, variant=variant, mode=mode, profiles=json.dumps(profiles, ensure_ascii=False))
    for key, value in sort.items():
        data[re.sub(r'[A-Z]', lambda match: '-' + match[0].lower(), key)] = value
    attrs = ' '.join(f'data-{key}="{escape(str(value), quote=True)}"' for key, value in data.items())
    fallback = '' if statistics else '<p class="profiles" data-i18n-ignore>' + escape(profile_text).replace('\n', '<br>') + '</p>'
    return (f'<article {attrs}><h2>' + text('map.seedVariant', seed=seed, variant=f'{variant:03d}')
            + '</h2><p>' + escape(mode) + '</p>'
            + ('<p class="variant-description">' + description + '</p>' if description else '')
            + totals_html(statistics, save_count) + fallback + render_statistics(statistics)
            + '<details class="map-source"><summary>' + label('history.mapSource') + '</summary>'
            + save_details + '</details><div class="maps">' + maps + '</div><details><summary>'
            + label('stats.settings') + '</summary>' + settings + '</details>'
            + '<p class="card-navigation"><a href="#gallery-top">' + label('nav.top') + '</a></p></article>')


def render_catalog_page(game, cards, seeds, save_count, updated_at, total_playtime, ranking, extra=''):
    folder = Path(__file__).parent / 'gallery_templates'
    counts = Counter(seeds)
    chips = ''.join(f'<button type="button" data-filter="{escape(str(seed), quote=True)}" '
                    f'title="{escape(message("map.seedTooltip").format(count=count), quote=True)}" '
                    f'data-i18n-title="map.seedTooltip" data-i18n-title-params="{{&quot;count&quot;:{count}}}">'
                    + escape(str(seed)) + '</button>' for seed, count in sorted(counts.items()))
    number = game.removeprefix('anno')
    scope = 'Pax Romana' if game == 'anno117' else label('map.scope1800')
    values = dict(TITLE=text('map.title', game=number), SCOPE=scope,
                  UPDATED=escape(updated_at.strftime('%d.%m.%Y %H:%M')),
                  UPDATED_ISO=escape(updated_at.isoformat(timespec='minutes'), quote=True),
                  TOTAL=text('map.total', time=total_playtime),
                  SUMMARY=text('map.summary', seeds=len(counts), variants=len(cards), saves=save_count),
                  GEOMETRY=label('map.geometry' + number), TIME_NOTE=label('map.time' + number),
                  RANKING=ranking, SEED_SUMMARY=text('map.showSeeds', count=len(counts)), SEEDS=chips,
                  CARDS=''.join(cards), EXTRA=extra,
                  SCRIPT=(folder / 'map_catalog.js').read_text(encoding='utf-8'))
    template = (folder / 'map_catalog.html').read_text(encoding='utf-8')
    page = re.sub(r'@@([A-Z_]+)@@', lambda match: values[match[1]], template)
    # A title is plain text; the heading keeps its explicit localisation binding.
    page = page.replace('<title>' + values['TITLE'] + '</title>',
                        '<title>' + escape(message('map.title').format(game=number)) + '</title>')
    return render_gallery(page, game, 'map')
