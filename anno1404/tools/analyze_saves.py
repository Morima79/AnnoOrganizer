
'Build local map reports for Anno 1404, Venice and the History Edition.'
import argparse
from array import array
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import hashlib
from html import escape
import json
import os
from pathlib import Path
import sys
from anno_settings import settings_for, protect_output
CONFIG = settings_for('anno1404')

import re
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import quote
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import zlib

from PIL import Image

HERE = Path(__file__).resolve().parent
HTML = 'map-gallery.html'
XLSX = 'anno1404-map-seeds.xlsx'
CACHE = '.anno-1404-cache.json'
CACHE_VERSION = 2
NEEDED = {'game2.xml', 'stats.xml', 'save.sww'}
SETTINGS = {
    'RandomMap': 'Zufallskarte beim Start', 'WorldSize': 'Weltgrösse', 'IslandSize': 'Inselgrösse', 'IslandDifficulty': 'Inselschwierigkeit',
    'Fertilities': 'Fruchtbarkeiten', 'Resources': 'Rohstoffe', 'NeutralBuildingAmount': 'Neutrale Gebäude',
    'CorsairStrength': 'Korsaren', 'Difficulty': 'Schwierigkeit', 'MissionDifficulty': 'Missionsschwierigkeit',
    'StartWithWarehouse': 'Kontor zu Beginn', 'StartShips': 'Startschiffe', 'StartCredit': 'Startkapital',
    'StartHonour': 'Startruhm', 'StartItems': 'Startitems', 'DiscoveredMap': 'Aufgedeckte Karte',
    'QuestFrequency': 'Auftragshäufigkeit', 'DemolitionReturn': 'Rückerstattung beim Abriss',
    'Disasters': 'Katastrophen', 'Espionage': 'Spionage', 'TownAcquisition': 'Ratsitze',
    'EnableTraderQuests': 'Händleraufträge', 'InitialPeaceTreaty': 'Friedensvertrag zu Beginn',
}
MODES = {0: 'Endlosspiel', 1: 'Szenario', 4: 'Kampagne', 5: 'Szenario'}
DATE_COLUMNS = (8, 10, 14)
TIME_COLUMNS = (12, 13, 16)
HEADERS = [
    'Seed', 'Variante', 'Spielmodus', 'Editionen im Archiv', 'Kartenbild', 'Saves', 'Profile', 'KI-Gegner',
    'Ältester Save am', 'Ältester Save', 'Neuester Save am', 'Neuester Save', 'Spielzeit im neuesten Save',
    'Längste Spielzeit', 'Längste Spielzeit am', 'Save mit längster Spielzeit', 'Mehr Spielzeit im älteren Save',
    'Weltgrösse (Felder)', 'Inseln', *SETTINGS.values(),
]
WIDTHS = [80, 120, 145, 215, 115, 70, 155, 265, 155, 190, 155, 190, 140, 120, 155, 190, 145, 135, 80]


def source_folders():
    return CONFIG.saves()


def read_archive(path):
    """Read RDA V2.0 entries. Active save archives use unencrypted blocks."""
    with path.open('rb') as file:
        size = os.fstat(file.fileno()).st_size

        def read(position, length):
            if not (0 <= position <= position + length <= size):
                raise ValueError('RDA-Bereich ausserhalb der Datei')
            file.seek(position)
            data = file.read(length)
            if len(data) != length:
                raise ValueError('RDA-Datei wurde während der Auswertung geändert')
            return data

        if read(0, 36).decode('utf-16le').rstrip('\0') != 'Resource File V2.0':
            raise ValueError('Unbekanntes Save-Archivformat')
        offset, = struct.unpack('<I', read(1044, 4))
        seen = set()
        entries = {}
        while offset not in (0xffffffff, size):
            if offset in seen or offset < 1048:
                raise ValueError('Ungültige RDA-Blockkette')
            seen.add(offset)
            flags, count, packed, plain, next_offset = struct.unpack('<5I', read(offset, 20))
            if flags & 2:
                raise ValueError('Verschlüsselter RDA-Block')
            if not flags & 8:
                resident = flags & 4
                start = offset - packed - (8 if resident else 0)
                directory = read(start, packed)
                if flags & 1:
                    directory = zlib.decompress(directory)
                if len(directory) != plain or plain != count * 540:
                    raise ValueError('Ungültiges RDA-Verzeichnis')
                payload = None
                for index in range(0, plain, 540):
                    name = directory[index:index+520].decode('utf-16le').partition('\0')[0].lower()
                    if name not in NEEDED:
                        continue
                    position, length, raw_length = struct.unpack_from('<III', directory, index+520)
                    if resident:
                        if payload is None:
                            stored, _ = struct.unpack('<II', read(offset-8, 8))
                            payload = read(start-stored, stored)
                            if flags & 1:
                                payload = zlib.decompress(payload)
                        data = payload[position:position+raw_length]
                    else:
                        data = read(position, length)
                        if flags & 1:
                            data = zlib.decompress(data)
                    entries[name] = data
            if NEEDED == entries.keys():
                return entries
            offset = next_offset
    raise ValueError('Save-Metadaten oder Kartendaten fehlen')


def unpack(data):
    if not data.startswith(b'ZZZZ'):
        return data
    expected, = struct.unpack_from('<I', data, 4)
    # The game can omit the zlib trailer. The wrapper declares the exact output size.
    decoder = zlib.decompressobj()
    expanded = decoder.decompress(data[8:], expected+1)
    if len(expanded) != expected:
        raise ValueError('Ungültige Länge der komprimierten Spielstanddaten')
    return expanded


def binary_fields(data):
    """Yield node paths and values from the BIN tree used by older Anno games."""
    end, = struct.unpack_from('<I', data, len(data)-4)
    if data[:4] != b'BIN ' or data[end:end+4] != b'MAP ' or data[-8:-4] != b'END ':
        raise ValueError('Unbekanntes BIN-Format')
    count, = struct.unpack_from('<I', data, end+4)
    pos = end+8
    names = {}
    for _ in range(count):
        length = data[pos]
        name = data[pos+1:pos+length].decode('utf-8', 'replace')
        pos += length+1
        code, = struct.unpack_from('<I', data, pos)
        names[code] = name
        pos += 4
    if pos != len(data)-8:
        raise ValueError('Ungültiges BIN-Wörterbuch')
    pos = 4
    stack = []
    view = memoryview(data)
    while pos < end:
        code, = struct.unpack_from('<i', data, pos)
        pos += 4
        if code == -1:
            stack.pop()
            continue
        length, = struct.unpack_from('<i', data, pos)
        pos += 4
        stop = data.index(0, pos, end) if length == -1 else pos + length
        if stop < pos or stop > end:
            raise ValueError('Ungültiges BIN-Feld')
        yield stack, names[code], view[pos:stop], length == -1
        stack.append(names[code])
        pos = stop + (length == -1)


def metadata_tree(raw):
    data = unpack(raw)
    if data.startswith(b'BIN '):
        root = ET.Element('Root')
        nodes = [root]
        for parents, name, value, is_text in binary_fields(data):
            del nodes[len(parents)+1:]
            node = ET.SubElement(nodes[-1], name)
            if value:
                node.text = bytes(value).decode('utf-8' if is_text else 'utf-16le', 'replace').strip('\0')
            nodes.append(node)
        return root

    out = bytearray(b'<Root>')
    pos = 0
    while (start := data.find(b'CDATA[', pos)) != -1:
        begin = start+10
        length, = struct.unpack_from('<I', data, start+6)
        end = begin+length
        if data[end:end+1] != b']':
            raise ValueError('Ungültiger CDATA-Abschnitt')
        out.extend(data[pos:start])
        tag = data[data.rfind(b'<', pos, start)+1:start-1]
        if tag in (b'Name', b'LevelName', b'Version', b'LevelFilename'):
            value = data[begin:end].decode('utf-16le', 'replace').strip('\0')
            out.extend(escape(value).encode('utf-8'))
        pos = end+1
    out.extend(data[pos:])
    out.extend(b'</Root>')
    # Game files use XML fragments with custom binary CDATA and occasional control characters.
    return ET.fromstring(re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]', b'', out))


def read_land(data):
    dimensions = {}
    islands = []
    island_path = ['WorldConfig', 'Islands', 'v', 'IslandConfig']
    keys = ('Filename', 'PositionX', 'PositionZ', 'Width', 'Height', 'Direction', 'Type', 'Clime')
    for parents, name, value, _ in binary_fields(data):
        if parents == ['WorldConfig'] and name in ('m_Width', 'm_Height'):
            dimensions[name] = int(bytes(value))
        if parents == island_path and name in keys:
            island[name] = bytes(value).decode('utf-8', 'replace').lower().replace('\\', '/')
        if name == 'IslandConfig' and parents == island_path[:-1]:
            island = {}
            islands.append(island)
        if name == 'm_HeightMap' and parents == ['WorldConfig', 'm_GOPManager', 'm_GRIDManager']:
            width, height = dimensions['m_Width'], dimensions['m_Height']
            if width <= 0 or height <= 0 or len(value) != 2*width*height:
                raise ValueError('Ungültige Grösse des Höhenrasters')
            layout = sorted(tuple(i.get(k, '') for k in keys) for i in islands if i.get('Filename'))
            if not layout:
                layout = [hashlib.sha256(value).hexdigest()]
            return width, height, layout, value
    raise ValueError('Höhenraster fehlt')


def draw_map(target, width, height, value):
    elevations = array('h', value.tobytes())
    if sys.byteorder != 'little':
        elevations.byteswap()
    pixels = bytes(0 if h < -4096 else 1 if h <= 0 else
                   2 if h < 340 else 3 if h < 1100 else 4 if h < 2500 else 5 if h < 4000 else 6
                   for h in elevations)
    image = Image.frombytes('P', (width, height), pixels)
    image.putpalette([26, 62, 82, 54, 109, 124, 203, 183, 129, 116, 151, 85,
                      85, 119, 66, 115, 113, 82, 161, 148, 113])
    image = image.convert('RGB')
    image.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
    image.save(target, optimize=True)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_save(path, stage, output):
    files = read_archive(path)
    game = metadata_tree(files['game2.xml'])
    stats = metadata_tree(files['stats.xml'])
    version = stats.findtext('.//Version', '').strip()
    match = re.search(r'v?(\d+)', version)
    major = int(match[1]) if match else None
    seed = int(game.findtext('.//Seed'))
    mode = int(game.findtext('.//GameType'))
    duration = int(stats.findtext('.//PlayingTimeMilliSec'))
    players = game.findall('.//PlayerInfos/i') or game.findall('.//FactionInfos/i')
    profiles = []
    computer_names = {}
    for player in players:
        role = (player.findtext('Type/PlayerType') or player.findtext('Type', '')).strip()
        name = player.findtext('Name', '').strip()
        profile = player.findtext('Profile', '').strip()
        if role in ('1', 'Human') and name:
            profiles.append(name)
        if role in ('2', 'Computer') and (profile or name):
            computer_names[profile or name] = name or f'Profil {profile}'
    computers = sorted(computer_names.values())
    settings = {k: game.findtext(f'.//{k}', '').strip() for k in SETTINGS}
    difference = game.findtext('.//GameTypeVariation', '')
    scenario = game.findtext('.//ScenarioID', '')
    width, height, islands, elevations = read_land(unpack(files['save.sww']))
    map_key = digest([width, height, islands])
    # Identical settings and island placements can span several editions and several campaigns.
    variant = digest([mode, seed, difference, scenario if mode != 0 else '', map_key, {k: v for k, v in settings.items() if k != 'RandomMap'}, sorted(computer_names)])
    image = f'map-images/{map_key[:24]}.png'
    if not (output/image).is_file() and not (stage/image).is_file():
        draw_map(stage/image, width, height, elevations)
    return {
        'content': hashlib.sha256(files['save.sww']).hexdigest(),
        'variant': variant, 'map': image, 'seed': seed, 'mode': mode,
        'modeLabel': ('Kampagne · Kapitel ' + str(int(difference)+1) if mode == 4 and difference.isdigit()
                      else MODES.get(mode, f'Spielmodus {mode}')),
        'edition': ('History Edition' if major is not None and major >= 3 else
                    'Venedig' if major == 2 else 'Anno 1404' if major == 1 else (version or 'Unbekannt')),
        'settings': settings, 'world': f'{width} × {height}', 'islands': len(islands) if isinstance(islands[0], tuple) else None,
        'duration': duration, 'profiles': list(dict.fromkeys(profiles)) or ['Unbekannt'], 'computers': computers,
        'game': game.findtext('.//gameId', '') or '0', 'chapter': difference,
    }


def collect(sources, stage, output, refresh):
    try:
        cache = json.loads((output/CACHE).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    old = cache.get('files', {}) if not refresh and cache.get('version') == CACHE_VERSION else {}
    current = {}
    by_content = {}
    failures = []
    paths = sorted({p.resolve() for folder in sources if folder.is_dir()
                    for p in folder.rglob('*.sww') if p.is_file()})
    for index, path in enumerate(paths, 1):
        try:
            stat = path.stat()
            fingerprint = [stat.st_mtime_ns, stat.st_size]
            item = old.get(str(path))
            if not item or item['fingerprint'] != fingerprint or not (output/item['data']['map']).is_file():
                item = {'fingerprint': fingerprint, 'data': read_save(path, stage, output)}
            current[str(path)] = item
            save = dict(item['data'], path=str(path), name=path.name, timestamp=stat.st_mtime)
            existing = by_content.get(save['content'])
            # A copied or imported save must not inflate the total or change its observed first date.
            if existing is None or (save['timestamp'], save['path']) < (existing['timestamp'], existing['path']):
                by_content[save['content']] = save
        except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error, ET.ParseError, zlib.error) as error:
            failures.append(f'{path} | {type(error).__name__}: {error}')
        if index % 50 == 0:
            print(f'{index}/{len(paths)} Dateien geprüft.', flush=True)
    if failures:
        (output/'anno1404-errors.txt').write_text('\n'.join(failures)+'\n', encoding='utf-8')
        raise ValueError(f'{len(failures)} Spielstände konnten nicht gelesen werden. Siehe anno1404-errors.txt.')
    if not by_content:
        raise ValueError('Keine .sww-Dateien in den Anno-1404-Spielstandordnern gefunden.')
    (stage/CACHE).write_text(json.dumps({'version': CACHE_VERSION, 'files': current}, ensure_ascii=False), encoding='utf-8')
    return list(by_content.values()), len(paths)


def report(saves, file_count, sources):
    by_variant = defaultdict(list)
    best_per_game = {}
    for save in saves:
        by_variant[save['variant']].append(save)
        # The game reuses IDs between different maps; include the map and full setup.
        game = (save['game'], save['variant'], tuple(sorted(save['profiles'])))
        key = (save['duration'], save['timestamp'], save['path'])
        if game not in best_per_game or key > best_per_game[game][0]:
            best_per_game[game] = (key, save['profiles'][0])
    totals = Counter()
    counts = Counter()
    for (duration, _, _), profile in best_per_game.values():
        totals[profile] += duration
        counts[profile] += 1

    def date(stamp):
        local = datetime.fromtimestamp(stamp)
        return (local-datetime(1899, 12, 30)).total_seconds()/86400

    rows = []
    for key, members in by_variant.items():
        members.sort(key=lambda v: (v['timestamp'], v['path']))
        first, last = members[0], members[-1]
        longest = max(members, key=lambda v: (v['duration'], v['timestamp'], v['path']))
        profiles = sorted({name for save in members for name in save['profiles']})
        editions = sorted({save['edition'] for save in members})
        seed = last['seed'] if last['seed'] or last['mode'] == 0 else None
        diff = max(0, longest['duration']-last['duration'])
        values = [
            seed, 'V-' + key[:8].upper(), last['modeLabel'], ', '.join(editions), 'Inselkarte öffnen',
            len(members), ', '.join(profiles), ', '.join(last['computers']),
            date(first['timestamp']), first['name'], date(last['timestamp']), last['name'],
            last['duration']/86400000, longest['duration']/86400000, date(longest['timestamp']),
            longest['name'], diff/86400000 if diff else None, last['world'], last['islands'],
            *(int(v) if v.lstrip('-').isdigit() else v or None for v in last['settings'].values()),
        ]
        rows.append({'values': values, 'image': last['map'], 'editions': editions, 'profiles': profiles,
                     'timestamp': last['timestamp'], 'oldest': first['timestamp'], 'longest': longest['duration'],
                     'settings': dict(zip(SETTINGS.values(), values[19:])),
                     'paths': [first['path'], last['path'], longest['path']]})
    rows.sort(key=lambda row: (-row['timestamp'], row['values'][1]))
    note = (f'{len({save["seed"] for save in saves if save["seed"] or save["mode"] == 0})} Seeds · '
            f'{len(rows)} Kartenvarianten · {len(saves)} Spielstände'
            + (f'  ·  {file_count-len(saves)} identische Kopien zusammengefasst' if file_count != len(saves) else ''))
    updated = datetime.now().strftime('%d.%m.%Y %H:%M')
    ranking = [(name, counts[name], ms) for name, ms in sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))]
    return {
        'headers': HEADERS, 'widths': WIDTHS, 'dates': DATE_COLUMNS, 'times': TIME_COLUMNS, 'rows': rows,
        'ranking': ranking, 'note': note, 'updated': updated, 'total': duration_label(sum(totals.values())),
        'sources': [str(source) for source in sources if source.is_dir()],
        'editions': dict(Counter(save['edition'] for save in saves)),
    }


def duration_label(ms):
    seconds = round(ms / 1000)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours}:{minutes:02}:{seconds:02}'


def write_html(stage, payload):
    def esc(value):
        return escape(str(value), quote=True)

    ranking = ''.join(
        f'<tr><td>{i}</td><td><button type="button" data-profile="{esc(name)}">{esc(name)}</button></td>'
        f'<td>{count}</td><td>{duration_label(ms)}</td></tr>'
        for i, (name, count, ms) in enumerate(payload['ranking'], 1)
    )
    editions = ''.join(f'<option>{esc(name)}</option>' for name in sorted(payload['editions']))
    cards = []
    for row in payload['rows']:
        v = row['values']
        anchor = f'Seed {v[0]}' if v[0] is not None else v[2]
        details = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(value)}</dd>' for k, value in row['settings'].items()
                          if value is not None)
        saves = []
        for column, label, path in zip((8, 10, 14), ('Ältester Save', 'Neuester Save', 'Längste Spielzeit'), row['paths']):
            local = datetime(1899, 12, 30) + timedelta(seconds=round(v[column]*86400))
            extra = f' · {duration_label(v[12 if column == 10 else 13]*86400000)}' if column != 8 else ''
            saves.append(f'<dt>{label}</dt><dd title="{esc(path)}">{esc(v[column+1])}<br>'
                         f'{local:%d.%m.%Y %H:%M:%S}{extra}</dd>')
        diff = (f'<p class="delta">Älterer Save mit +{duration_label(v[16]*86400000)} Spielzeit</p>' if v[16] else '')
        cards.append(f'''<article data-editions="{esc(json.dumps(row['editions']))}"
          data-profiles="{esc(json.dumps(row['profiles']))}" data-seed="{v[0] if v[0] is not None else 99999999}"
          data-timestamp="{row['timestamp']}" data-oldest="{row['oldest']}" data-time="{row['longest']}">
          <a href="{row['image']}"><img loading="lazy" src="{row['image']}" alt="Inselkarte – {esc(anchor)}"></a>
          <div class="body"><h2>{esc(anchor)}</h2><p>{esc(v[1])} · {esc(v[2])} · {esc(v[3])}</p>
          <p>{esc(v[17])} Felder · {f'{v[18]} Inseln · ' if v[18] is not None else ''}{v[5]} Spielstände</p>
          <p>{esc(v[6])}{' · KI: '+esc(v[7]) if v[7] else ''}</p>
          <dl>{''.join(saves)}</dl>{diff}<details><summary>Karteneinstellungen</summary><dl>{details}</dl></details></div>
          </article>''')
    template = (HERE/'map_gallery_template.html').read_text(encoding='utf-8')
    data = {'UPDATED': esc(payload['updated']), 'TOTAL': esc(payload['total']), 'NOTE': esc(payload['note']),
            'RANKING': ranking, 'CARDS': ''.join(cards), 'EDITIONS': editions,
            'SOURCES': ''.join(f'<li>{esc(path)}</li>' for path in payload['sources'])}
    page = re.sub(r'@@([A-Z]+)@@', lambda match: data[match[1]], template)
    (stage/HTML).write_text(page, encoding='utf-8')


def write_excel(stage, payload):
    from anno_excel_export import write_workbook
    write_workbook(stage/XLSX, payload)


def publish(stage, output):
    image_dir = output/'map-images'
    image_dir.mkdir(exist_ok=True)
    targets = (XLSX, HTML, CACHE)
    backups = stage/'previous'
    backups.mkdir()
    for name in targets:
        if (output/name).exists():
            shutil.copy2(output/name, backups/name)
    for image in (stage/'map-images').glob('*.png'):
        os.replace(image, image_dir/image.name)
    published = []
    try:
        for name in targets:
            os.replace(stage/name, output/name)
            published.append(name)
    except OSError:
        for name in reversed(published):
            if (backups/name).is_file():
                os.replace(backups/name, output/name)
            else:
                (output/name).unlink()
        raise


def main():
    import msvcrt

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save-folder', type=Path, action='append', help='Zusätzlicher Ordner mit Anno-1404-Saves')
    parser.add_argument('--output', type=Path, default=CONFIG.output/'reports')
    parser.add_argument('--rescan', action='store_true')
    args = parser.parse_args()
    CONFIG.validate('analyze')
    protect_output(args.output, CONFIG.all_sources()+(args.save_folder or []))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted(set(source_folders()) | {p.resolve() for p in (args.save_folder or [])})
    with (output/'.anno-1404.lock').open('a+b') as lock:
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise ValueError('Die Auswertung läuft in diesem Ordner bereits.') from error
        with TemporaryDirectory(prefix='.anno-1404-', dir=output) as temp:
            stage = Path(temp)
            (stage/'map-images').mkdir()
            saves, count = collect(sources, stage, output, args.rescan)
            payload = report(saves, count, sources)
            write_html(stage, payload)
            write_excel(stage, payload)
            with ZipFile(stage/XLSX) as archive:
                if archive.testzip():
                    raise ValueError('Excel-Datei ist unvollständig.')
            publish(stage, output)
        (output/'anno1404-errors.txt').unlink(missing_ok=True)
    print(payload['note'])
    print('Editionen: ' + ', '.join(f'{k} ({v})' for k, v in sorted(payload['editions'].items())))
    print(f'Excel, HTML und Kartenbilder: {output}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Aktualisierung abgebrochen: {error}', file=sys.stderr)
        sys.exit(1)
