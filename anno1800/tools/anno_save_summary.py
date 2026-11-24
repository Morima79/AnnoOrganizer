"""Render current campaign statistics without exposing collapsed details."""
from datetime import datetime
from html import escape
import json
import math
import struct
from pathlib import Path
from functools import lru_cache
from xml.etree.ElementTree import ParseError


@lru_cache(maxsize=None)
def message(key):
    resources = Path(__file__).parent / 'gallery_templates/locales/de.json'
    if not resources.is_file():
        resources = Path(__file__).parent / 'locales/de.json'
    return json.loads(resources.read_text(encoding='utf-8'))[key]


def label(key):
    return f'<span data-i18n="{key}">{escape(message(key))}</span>'


def number(value, signed=False):
    if value is None or not isinstance(value, (float, int)) or not math.isfinite(value):
        return label('stats.unavailable')
    rounded = round(value, 2)
    if rounded == 0:
        rounded = 0
    text = format(rounded, '+,.2f' if signed else ',.2f').rstrip('0').rstrip('.')
    return escape(text.replace(',', '’'))


def named_rows(rows):
    if rows is None:
        return '<p>' + label('stats.unavailable') + '</p>'
    if not rows:
        return '<p>' + number(0) + '</p>'
    result = []
    for row in rows:
        name = label(row['key']) if row.get('key') else '<span data-i18n-ignore>' + escape(row['name']) + '</span>'
        result.append('<div><dt>' + name + '</dt><dd>' + number(row['count']) + '</dd></div>')
    return '<dl class="stat-breakdown">' + ''.join(result) + '</dl>'


def group(key, summary, content):
    return ('<details class="stat-group"><summary>' + label(key) + ': <strong>' + summary
            + '</strong></summary><div class="stat-detail">' + content + '</div></details>')


def duration(milliseconds):
    if milliseconds is None:
        return label('stats.unavailable')
    seconds = milliseconds // 1000
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours}:{minutes:02d}:{seconds:02d}'


def campaign_history(candidates, latest, zone):
    """Compare save times only inside one already identified campaign."""
    def order(item):
        return item['stamp'], item.get('live', True), str(item['path'])
    def saved(item):
        return dict(date=datetime.fromtimestamp(item['stamp'], zone).strftime('%d.%m.%Y %H:%M:%S'),
                    source=item['source'], play_ms=item.get('play_ms'))
    oldest = min(candidates, key=order)
    known = [item for item in candidates if item.get('play_ms') is not None]
    record = max(known, key=lambda item: (item['play_ms'], order(item))) if known else None
    delta = (record['play_ms'] - latest['play_ms']
             if record and latest.get('play_ms') is not None and record['stamp'] < latest['stamp']
             and record['play_ms'] > latest['play_ms'] else 0)
    return dict(count=len(candidates), oldest=saved(oldest), latest=saved(latest),
                record=saved(record) if record else None, delta_ms=delta)


def history_html(entry):
    history = entry.get('history')
    if history is None:
        return ''
    content = '<p>' + label('history.saveCount') + ': ' + number(history['count']) + '</p><dl>'
    for key in ('oldest', 'latest', 'record'):
        item = history[key]
        value = (escape(item['date']) + '<br><span data-i18n-ignore>' + escape(item['source']) + '</span>'
                 if item else label('stats.unavailable'))
        content += '<div><dt>' + label('history.' + key) + '</dt><dd>' + value + '</dd></div>'
    for key, item in (('latestTime', history['latest']), ('recordTime', history['record'])):
        content += '<div><dt>' + label('history.' + key) + '</dt><dd>' + duration(item['play_ms'] if item else None) + '</dd></div>'
    content += '</dl>'
    if history['delta_ms']:
        content += '<p class="marker">' + label('history.extra') + ': +' + duration(history['delta_ms']) + '</p>'
    return '<details class="campaign-history"><summary>' + label('history.details') + '</summary>' + content + '</details>'


def variant_totals(entries, save_count):
    records = [entry.get('history', {}).get('record') for entry in entries]
    total = sum(record['play_ms'] for record in records) if records and all(records) else None
    return dict(campaigns=len(entries), saves=save_count, play_ms=total)


def totals_html(entries, save_count):
    totals = variant_totals(entries, save_count)
    return ('<p class="variant-totals">' + number(totals['campaigns']) + ' ' + label('history.campaigns.one' if totals['campaigns'] == 1 else 'history.campaigns')
            + ' · ' + number(save_count) + ' ' + label('history.filesTotal.one' if save_count == 1 else 'history.filesTotal') + ' · '
            + label('history.totalTime') + ': ' + duration(totals['play_ms']) + '</p>')


def render_statistics(entries):
    """Each entry is one campaign's latest save, never a sum across campaigns."""
    result = []
    for entry in entries:
        stats = entry['values']
        date = escape(entry['date'])
        result.append('<section class="campaign-statistics" data-campaign="' + escape(entry['campaign'], quote=True) + '">')
        result.append('<p class="stat-profile" data-i18n-ignore>' + escape(entry['profile']) + '</p>')
        result.append('<p class="last-played">' + label('stats.lastPlayed') + ': <time>' + date + '</time></p>')
        result.append('<div class="stat-groups">')
        population = named_rows(stats.get('population_levels'))
        if stats.get('population_residences') is not None:
            population = '<p>' + label('stats.residencePopulation') + ': ' + number(stats['population_residences']) + '</p>' + population
        if stats.get('population_levels') is not None and stats.get('population') is not None and sum(r['count'] for r in stats['population_levels']) != stats['population']:
            population += '<p class="stat-note">' + label('stats.populationCountersDiffer' if stats.get('population_residences') is not None else 'stats.rounding') + '</p>'
        population += '<p>' + label('stats.islands') + ': ' + number(stats.get('islands')) + '</p>'
        money = label('stats.wealth') + ' ' + number(stats.get('money')) + ' · ' + label('stats.balance') + ' ' + number(stats.get('balance'), True)
        if stats.get('balance') is not None:
            money += ' ' + label('stats.perMinute')
        finance = '<dl class="stat-breakdown">'
        for key in ('income', 'expenses'):
            finance += '<div><dt>' + label('stats.' + key) + '</dt><dd>' + number(stats.get(key)) + ' ' + label('stats.perMinute') + '</dd></div>'
        finance += '</dl>'
        result.append(group('stats.money', money, finance))
        population_key = 'stats.population' if stats.get('population') is not None or stats.get('population_residences') is None else 'stats.residencePopulation'
        population_value = stats.get('population') if population_key == 'stats.population' else stats['population_residences']
        result.append(group(population_key, number(population_value), population))
        houses = named_rows(stats.get('house_levels'))
        houses += '<p>' + label('stats.blueprints') + ': ' + number(stats.get('blueprints')) + '</p>'
        result.append(group('stats.houses', number(stats.get('houses')), houses))
        ships = named_rows(stats.get('ship_types'))
        if stats.get('airships') is not None:
            ships += '<p>' + label('stats.airships') + ': ' + number(stats['airships']) + '</p>'
        result.append(group('stats.ships', number(stats.get('ships')), ships))
        result.append('</div>' + history_html(entry) + '</section>')
    return ''.join(result)


def statistics_sources(entries):
    return ('<p>' + label('stats.source') + '</p><dl class="stat-breakdown">'
            + ''.join('<div><dt data-i18n-ignore>' + escape(entry['profile'])
                      + '</dt><dd data-i18n-ignore>' + escape(entry['source']) + '</dd></div>'
                      for entry in entries) + '</dl>')


def latest_campaigns(candidates):
    chosen = {}
    for item in candidates:
        key = item['campaign']
        order = (item['stamp'], item.get('live', True), str(item['path']))
        if key not in chosen or order > chosen[key][0]:
            chosen[key] = order, item
    return {key: item for key, (_, item) in chosen.items()}


def collect_statistics(candidates, reader, cache_path, zone, refresh=False, cache_only=False):
    """Read only latest saves; a failed latest save never falls back to an older one."""
    from anno_save_statistics import empty_statistics, STATISTICS_VERSION
    try:
        old = json.loads(Path(cache_path).read_text(encoding='utf-8')) if not refresh else {}
    except (OSError, ValueError):
        old = {}
    signature = reader.signature
    previous = old.get('files', {}) if old.get('version') == STATISTICS_VERSION and old.get('assets') == signature else {}
    histories = {}
    for candidate in candidates:
        histories.setdefault(candidate['campaign'], []).append(candidate)
    current, entries = {}, {}
    for campaign, item in latest_campaigns(candidates).items():
        path = Path(item['path'])
        key = str(path)
        try:
            stat = path.stat()
            fingerprint = [stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_ctime_ns]
            cached = previous.get(key)
            cached_valid = cached and cached['signature'] == fingerprint
            if cached_valid:
                values = cached['values']
            elif cache_only:
                values = empty_statistics()
            else:
                values = reader(path)
                after = path.stat()
                if fingerprint != [after.st_size, after.st_mtime_ns, after.st_ino, after.st_ctime_ns]:
                    raise ValueError('Spielstand wurde während der Kennzahlen-Auslesung geändert')
            if cached_valid or not cache_only:
                current[key] = {'signature': fingerprint, 'values': values}
        except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error, ParseError) as error:
            print(f'Kennzahlen nicht verfügbar: {path.name}: {error}')
            values = empty_statistics()
        entries[campaign] = {'profile': item['profile'], 'source': item['source'],
                             'seed': item.get('seed'), 'campaign': str(campaign),
                             'date': datetime.fromtimestamp(item['stamp'], zone).strftime('%d.%m.%Y %H:%M:%S'),
                             'values': values, 'history': campaign_history(histories[campaign], item, zone)}
    return entries, {'version': STATISTICS_VERSION, 'assets': signature, 'files': current}


def write_statistics_sheet(book, entries):
    """Keep existing map worksheets intact and add one current row per campaign."""
    sheet = book.add_worksheet('Aktuelle Spielstände')
    sheet.freeze_panes(1, 2)
    sheet.set_column(0, 0, 25)
    sheet.set_column(1, 1, 22)
    sheet.set_column(2, 9, 18)
    sheet.set_column(10, 10, 65)
    heading = book.add_format({'bold': True, 'text_wrap': True})
    numeric = book.add_format({'num_format': '#,##0'})
    seed_format = book.add_format({'num_format': '0'})
    date_format = book.add_format({'num_format': 'dd.mm.yyyy hh:mm:ss'})
    headers = ['Profil', 'Zuletzt gespielt am', 'Seed', 'Bevölkerung', 'Vermögen', 'Bilanz / min',
               'Wohnhäuser', 'Schiffe', 'Besiedelte Inseln', 'Wohnhaus-Baupläne', 'Save']
    headers += ['Save-Dateien dieser Partie', 'Ältester Save am', 'Ältester Save', 'Spielzeit im neuesten Save',
                'Längste gespeicherte Spielzeit', 'Save mit längster Spielzeit am', 'Save mit längster Spielzeit',
                'Mehr Spielzeit im älteren Save', 'Bevölkerung in Wohnhäusern']
    hours = book.add_format({'num_format': '[h]:mm:ss'})
    sheet.set_column(11, 18, 24)
    sheet.write_row(0, 0, headers, heading)
    for index, entry in enumerate(entries, 1):
        stats = entry['values']
        values = [entry['profile'], entry['date'], entry.get('seed'),
                  *(stats.get(key) for key in ('population', 'money', 'balance', 'houses', 'ships', 'islands', 'blueprints')),
                  entry['source']]
        for column, value in enumerate(values):
            if column == 1:
                sheet.write_datetime(index, column, datetime.strptime(value, '%d.%m.%Y %H:%M:%S'), date_format)
                continue
            fmt = seed_format if column == 2 else numeric if isinstance(value, (int, float)) else None
            sheet.write(index, column, 'nicht verfügbar' if value is None else value, fmt)
        sheet.write(index, 19, 'nicht verfügbar' if stats.get('population_residences') is None else stats['population_residences'], numeric)
        history = entry.get('history')
        if history:
            record = history['record']
            extra = [history['count'], history['oldest']['date'], history['oldest']['source'],
                     history['latest']['play_ms'], record['play_ms'] if record else None,
                     record['date'] if record else None, record['source'] if record else None, history['delta_ms']]
            for column, value in enumerate(extra, 11):
                if value is None:
                    sheet.write(index, column, 'nicht verfügbar')
                elif column in (12, 16):
                    sheet.write_datetime(index, column, datetime.strptime(value, '%d.%m.%Y %H:%M:%S'), date_format)
                elif column in (14, 15, 18):
                    sheet.write_number(index, column, value / 86400000, hours)
                else:
                    sheet.write(index, column, value, numeric if isinstance(value, (int, float)) else None)
    if entries:
        sheet.autofilter(0, 0, len(entries), len(headers) - 1)
