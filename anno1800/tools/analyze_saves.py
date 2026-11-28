'Update Excel reports, HTML galleries and maps from local Anno 1800 saves.'
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import sys
from anno_settings import settings_for, protect_output
from anno_execution import checkpoint
from anno_output_lock import reserve_paths
from anno_output_transaction import temporary_directory, publish_files
import anno_game_settings as game_labels
from anno_map_catalog import render_card, render_catalog_page
from anno_map_variants import campaign_variants, latest_known_values
from anno_save_summary import collect_statistics, variant_totals
from anno_save_statistics import FileDBStatistics
from functools import lru_cache
CONFIG = None

from anno_profile_playtime import profile_name, profile_playtime, ranking_html
from zoneinfo import ZoneInfo
import struct as st
import zlib

ACCOUNT = None
HERE = Path(__file__).resolve().parent
ARCHIVE = None

def members(path, wanted):
    with path.open('rb') as f:
        def read(pos, n):
            f.seek(pos)
            result = f.read(n)
            if len(result) != n:
                raise ValueError('Unvollständiger RDA-Block')
            return result
        if read(0,18) != b'Resource File V2.2':
            raise ValueError('Kein RDA V2.2')
        off, = st.unpack('<Q', read(0x310,8))
        seen = set()
        while off not in seen and 0 < off < path.stat().st_size:
            seen.add(off)
            flags,n,packed,plain,nxt = st.unpack('<IIQQQ',read(off,32))
            if flags & 2:
                raise ValueError('Verschlüsselter RDA-Block')
            directory = read(off-packed,packed)
            if flags & 1:
                directory = zlib.decompress(directory)
            if len(directory) != plain or n * 560 != plain:
                raise ValueError('Ungültiges RDA-Verzeichnis')
            for i in range(n):
                p = i*560
                name = directory[p:p+520].decode('utf-16le','replace').split('\0',1)[0]
                if name in wanted:
                    pos, length = st.unpack_from('<QQ',directory,p+520)
                    raw = read(pos,length)
                    yield name, inflate(zlib.decompress(raw) if flags & 1 else raw)
            off = nxt

def inflate(raw):
    out = bytearray()
    while raw:
        dec = zlib.decompressobj()
        piece = dec.decompress(raw)
        if not dec.eof:
            raise ValueError('Unvollständiger zlib-Stream')
        raw = dec.unused_data
        if not piece:
            if len(raw) < 4 or st.unpack_from('<I',raw)[0] != len(out):
                raise ValueError('Falsche Länge des inneren Streams')
            return out
        out.extend(piece)
    raise ValueError('Fehlender zlib-Endmarker')

def legacy_fields(data):
    end, = st.unpack_from('<I',data,len(data)-4)
    if not 0 < end < len(data)-4:
        raise ValueError('Ungültiges FileDB-V1-Verzeichnis')
    def varint(p):
        n = 0
        for shift in range(0,35,7):
            b = data[p]
            p += 1
            n |= (b&127)<<shift
            if not b&128: return n,p
        raise ValueError('Ungültige FileDB-V1-Länge')
    names = {1:'[]',0x8000:'[]'}
    p = end
    for _ in range(2):
        n,p = varint(p)
        for _ in range(n):
            stop=data.index(0,p)
            code, = st.unpack_from('<H',data,stop+1)
            names[code] = data[p:stop].decode('utf-8','replace')
            p=stop+3
    if p != len(data)-4: raise ValueError('Unbekannte FileDB-Version')
    p=0
    stack=[]
    view=memoryview(data)
    while p+2 <= end:
        code,=st.unpack_from('<H',data,p)
        p+=2
        if code==0:
            if not stack: break
            stack.pop()
        elif code&0x8000:
            size,p=varint(p)
            if p+size>end: raise ValueError('Unvollständiges FileDB-V1-Feld')
            yield (*stack,names.get(code,str(code))),view[p:p+size]
            p+=size
        else:
            stack.append(names.get(code,str(code)))


def fields(data, keep=None):
    _,tags,attrs,_,magic = st.unpack_from('<5I',data,len(data)-20)
    if magic not in (0xfffffffd,0xfffffffe):
        yield from legacy_fields(data)
        return
    names = {1:'[]',0x8000:'[]'}
    for pos in (tags,attrs):
        n, = st.unpack_from('<I',data,pos)
        ids = st.unpack_from(f'<{n}H',data,pos+4)
        p = pos+4+2*n
        for code in ids:
            end = data.index(0,p)
            names[code] = data[p:end].decode('utf-8','replace')
            p = end+1
    stack = []
    p = 0
    view = memoryview(data)
    while p+8 <= tags:
        size,code = st.unpack_from('<IH',data,p)
        p += 8
        if code == 0:
            if not stack:
                break
            stack.pop()
        elif code & 0x8000:
            name = names.get(code, str(code))
            if keep is None or name in keep or any(t in keep for t in stack):
                yield (*stack,name), view[p:p+size]
            p += (size+7)&~7
        else:
            stack.append(names.get(code,str(code)))

def val(v):
    v = bytes(v)
    if len(v) in (1,2,4,8):
        return int.from_bytes(v,'little')
    if len(v)%2==0 and v[1::2].count(0) > len(v)//4:
        s = v.decode('utf-16le','replace').rstrip('\0')
        if s.isprintable(): return s
    s = v.rstrip(b'\0').decode('utf-8','replace')
    return s if s.isprintable() and '\ufffd' not in s else v.hex()

def save_path(row):
    root = ACCOUNT if row['source'] == 'Spielkonto' else ARCHIVE
    return root / row['path']


def load_cache(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return default


def scan(cache_path, refresh=False):
    previous = {} if refresh else {
        (row['source'], row['path']): row
        for row in load_cache(cache_path, [])
        if 'stamp' in row and 'play_ms' in row and 'signature' in row and 'campaign_id' in row
    }
    candidates = [(root,p) for root in (ACCOUNT,ARCHIVE) for p in root.rglob('*.a7s')
                  if not p.name.lower().startswith('accountdata')]

    def one(item):
        root, path = item
        source = 'Spielkonto' if root == ACCOUNT else 'Archiv'
        relative = str(path.relative_to(root))
        try:
            stat = path.stat()
            signature = [stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_ctime_ns]
            cached = previous.get((source, relative))
            if cached and cached['signature'] == signature:
                return cached
            parts = dict(members(path, {'gamesetup.a7s', 'header.a7s', 'meta.a7s'}))
            pairs = [(key[1:],val(value)) for key,value in fields(parts['gamesetup.a7s'])
                     if key[0]=='GameSetupManager' and len(key)>1 and key[1] not in
                     ('Peers','SavegameFolderW','SessionName','ActiveHappyDayEvents','SavegameFolder')]
            if not any(k == ('GameSeed',) and isinstance(value, int) for k, value in pairs):
                raise ValueError('Kein Kartenseed gespeichert')
            stamp = next(val(v) for k,v in fields(parts['meta.a7s']) if k == ('LastModTime',))
            profile = {k[-1]:val(v) for k,v in fields(parts['header.a7s'])
                       if k in (('CorporationProfile','ID'), ('CorporationProfile','CorporationTime'))}
            play_ms = profile['CorporationTime']
            campaign_id = profile['ID']
            if not isinstance(campaign_id, int) or campaign_id <= 0:
                raise ValueError('Partie-ID fehlt oder ist ungültig')
            if not isinstance(stamp, int) or not isinstance(play_ms, int) or stamp <= 0 or play_ms < 0:
                raise ValueError('Ungültige Save-Zeitangaben')
            after = path.stat()
            if [after.st_size, after.st_mtime_ns, after.st_ino, after.st_ctime_ns] != signature:
                raise ValueError('Datei wurde während der Auswertung geändert')
            return {'source':source, 'path':relative, 'time':stat.st_mtime,
                    'signature':signature, 'setup':pairs, 'stamp':stamp, 'play_ms':play_ms,
                    'campaign_id':campaign_id}
        except Exception as e:
            return {'source':source, 'path':relative, 'error':str(e) or type(e).__name__}

    print(f'Spielstände prüfen: {len(candidates):,}', flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = []
        for row in pool.map(one, sorted(candidates)):
            checkpoint()
            rows.append(row)
    failures = [row for row in rows if 'error' in row]
    if failures:
        for row in failures[:10]:
            print(f"{row['source']}: {row['path']}  ({row['error']})", file=sys.stderr)
        raise ValueError(f'{len(failures)} Spielstände konnten nicht vollständig gelesen werden.')
    if not rows:
        raise ValueError('Keine Spielstände gefunden.')
    return rows




GAME = None

def rda_index(path):
    with path.open('rb') as f:
        f.seek(0x310)
        off,=st.unpack('<Q',f.read(8))
        size=path.stat().st_size
        seen=set()
        while 0<off<size and off not in seen:
            seen.add(off)
            f.seek(off)
            flags,n,packed,plain,nxt=st.unpack('<IIQQQ',f.read(32))
            f.seek(off-packed)
            buf=f.read(packed)
            if flags&1: buf=zlib.decompress(buf)
            if flags&8:
                # Memory-resident blocks have a 16-byte size footer before the directory.
                f.seek(off-packed-16)
                packed_data,raw_data=st.unpack('<QQ',f.read(16))
                base=off-packed-16-packed_data
            else:
                base=0
                packed_data=0
            for i in range(0,n*560,560):
                name=buf[i:i+520].decode('utf-16le','replace').split('\0',1)[0].lower()
                pos,length,raw=st.unpack_from('<QQQ',buf,i+520)
                yield name,(str(path),flags,base,packed_data,pos,length,raw)
            off=nxt

@lru_cache(maxsize=1)
def index_game():
    entries={}
    for path in sorted(GAME.glob('data*.rda'),key=lambda p:int(p.stem[4:])):
        for n,record in rda_index(path):
            if any(x in n for x in ('moderate_l_12','assets.xml','mapgenerator')) or n.endswith(('.a7minfo','.a7tinfo','/texts_german.xml')) or ('/islands/' in n and n.endswith('.png')):
                entries[n]=record
    return entries



WORLD_KEYS = {'GameSeed','SetupMapType','SetupStartSession','SetupStartSessionIslandSize',
              'SetupStartSessionIslandDifficulty','SetupFertility','SetupRawMaterial',
              'EnableCampaign','EnableScenario','CreativeMode','Maps','ThirdParties',
              'SecondParties','ActiveDLCs','ActiveMods','ActiveLocalMods','SetupStartWithKontor'}

def bucket(rows):
    entries = []
    for row in rows:
        if 'setup' not in row:
            continue
        seed = next(value for path, value in row['setup'] if path == ['GameSeed'] or path == ('GameSeed',))
        entries.append(dict(seed=seed, campaign=row['campaign_id'], order=save_order(row),
                            setup=row['setup'], item=row))
    groups = []
    for _, saves in campaign_variants('anno1800', entries):
        known = latest_known_values(row['setup'] for row in sorted(saves, key=save_order, reverse=True))
        setup = tuple(((key,), value) for key, values in known.items() if key in WORLD_KEYS for value in values)
        groups.append((setup, saves))
    return groups


def maps_for(path):
    _,data=next(members(path,{'data.a7s'}))
    guid=None
    for key,b in fields(data):
        if key[:2]!=('MetaGameManager','GameSessions'):
            continue
        if key[-2:]==('SessionDesc','SessionGUID'):
            guid=val(b)
        if key[-2:]==('SessionData','BinaryData'):
            details={'guid':guid,'islands':[]}
            item={}
            item_type=None
            for k,v in fields(bytes(b)):
                if k[:2]!=('GameSessionManager','MapTemplate'):
                    continue
                if k[2:]==('Size',) and len(v)==8: details['size']=st.unpack('<ii',v)
                elif k[2:]==('Filename',): details['template']=v.tobytes().decode('utf-16le','replace').rstrip('\0')
                elif k[2:]==('TemplateElement','ElementType'):
                    item_type=val(v)
                    item={}
                elif k[2:4]==('TemplateElement','Element'):
                    if k[-1]=='Position' and len(v)==8:
                        item={'type':item_type,'pos':st.unpack('<ii',v)}
                        details['islands'].append(item)
                    if k[-1]=='Rotation90': item['rotation']=val(v)
                    if k[-1]=='MapFilePath':
                        item['file']=v.tobytes().decode('utf-16le','replace').rstrip('\0')
                    if k[-1] in ('ProfileGUID','Asset','ThirdPartyGUID'): item[k[-1]]=val(v)
            if details['islands']:
                yield details

def collect_maps(groups, previous):
    # A variant number can change when a new seed is added. Reuse geometry only for the same save.
    cached = {(r['source'], r['path'], tuple(r['signature'])): r['maps']
              for r in previous if r.get('maps') and 'signature' in r}
    result = []
    for i, (_, rows) in enumerate(groups, 1):
        checkpoint()
        profiles = defaultdict(list)
        for row in rows:
            profiles[row['source'], Path(row['path']).parent].append(row)
        def map_recency(row):
            return row['time'], row['source'] == 'Spielkonto', row['path']

        choices = sorted((max(profile, key=map_recency) for profile in profiles.values()),
                         key=map_recency, reverse=True)
        error = ''
        for row in choices[:3]:
            maps = []
            try:
                identity = (row['source'], row['path'], tuple(row['signature']))
                maps = cached[identity] if identity in cached else list(maps_for(save_path(row)))
                if maps:
                    break
                error = 'Keine generierte Karte gespeichert'
            except Exception as exc:
                error = str(exc) or type(exc).__name__
        result.append({'id':i, 'source':row['source'], 'path':row['path'],
                       'signature':row['signature'], 'maps':maps, 'error':error if not maps else ''})
        if i % 20 == 0 or i == len(groups):
            print(f'Karten geprüft: {i}/{len(groups)}', flush=True)
    return result


def read_asset(rec):
    path,flags,base,packed_data,pos,n,plain=rec
    if flags&2: raise ValueError('Verschlüsseltes Spielasset')
    with open(path,'rb') as f:
        if flags&8:
            f.seek(base)
            block=f.read(packed_data)
            if flags&1: block=zlib.decompress(block)
            return block[pos:pos+plain]
        f.seek(pos)
        data=f.read(n)
        return zlib.decompress(data) if flags&1 else data


REGIONS = {655:'Szenario · Eden Burning',24734:'Szenario · Seasons of Silver',100811:'Szenario · Pride and Peddlers',180023:'Alte Welt',180025:'Neue Welt',110934:'Kap Trelawney',
           180045:'Arktis',112132:'Enbesa',180014:'Kampagnenprolog'}
PARTIES={73:'Anne Harlow',76:'Jean La Fortune',29:'Isabel Sarmento',46:'Eli Bleakworth',78:'Madame Kahina'}
DLC={410040:'Versunkene Schätze',410041:'Botanika',410042:'Die Passage',
     410083:'Speicherstadt',24963:'Aufstieg der Neuen Welt',24961:'Keim der Hoffnung',
     410059:'Paläste der Macht',410070:'Reiche Ernte',410071:'Land der Löwen',
     410084:'Reisezeit',410085:'Dächer der Stadt',24962:'Reich der Lüfte',4100010:'Die Anarchisten'}

ZONE_NAME = 'Europe/Zurich'
STANDARD_REGIONS = (180023, 180025, 110934, 180045, 112132)
MAP_SETTING_KEYS = ['SetupMapType', 'SetupStartSession', 'SetupStartSessionIslandSize',
                    'SetupStartSessionIslandDifficulty', 'SetupFertility', 'SetupRawMaterial']
GAME_SETTINGS = [*(game_labels.name('anno1800', key) for key in MAP_SETTING_KEYS),
                 'KI-Slots (IDs)', 'Händler und Piraten (Stufe als ID)', 'Aktive DLCs']

TIME_COLUMNS = [
    'Ältester Save des Seeds', 'Neuester Save des Seeds',
    'Ältester Save der Variante', 'Neuester Save der Variante', 'Spielzeit im neuesten Save',
    'Längste gespeicherte Spielzeit', 'Datum des Saves mit längster Spielzeit',
    'Save mit längster Spielzeit',
]


def save_order(row):
    return row['stamp'], row['source'] == 'Spielkonto', row['time'], row['path']


def duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours}:{minutes:02d}:{seconds:02d}'


def time_values(saves, seed_times, zone):
    latest = max(saves, key=save_order)
    record = max(saves, key=lambda row: (row['play_ms'], save_order(row)))
    first = min(row['stamp'] for row in saves)
    latest_time = latest['play_ms'] // 1000
    record_time = record['play_ms'] // 1000
    delta = record_time - latest_time if record['stamp'] < latest['stamp'] else 0
    dates = [datetime.fromtimestamp(stamp, zone) for stamp in
             (*seed_times, first, latest['stamp'], record['stamp'])]
    epoch = datetime(1899, 12, 30)
    source = f"{record['source']}: {record['path']}"
    local = [d.strftime('%d.%m.%Y %H:%M:%S') for d in dates]
    serials = [(d.replace(tzinfo=None) - epoch).total_seconds() / 86400 for d in dates]
    return {
        'display': [*local[:4], duration(latest_time), duration(record_time), local[4], source],
        'excel': [*serials[:4], latest_time / 86400, record_time / 86400, serials[4], source],
        'sort': {'first':first, 'latest':latest['stamp'], 'record-date':record['stamp'],
                 'record-time':record_time, 'latest-time':latest_time},
        'delta': delta,
    }


MAP_RENDER_VERSION = '3'


def reduce_island_shadow(image):
    """Reduce translucent black map shadows while preserving terrain pixels."""
    from PIL import ImageChops
    red, green, blue, alpha = image.split()
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    black = maximum.point(lambda value: 255 if value == 0 else 0)
    translucent = alpha.point(lambda value: 255 if value < 255 else 0)
    shadow = ImageChops.multiply(alpha, ImageChops.multiply(black, translucent))
    result = image.copy()
    result.putalpha(ImageChops.subtract(alpha, shadow.point(lambda value: round(value * 0.75))))
    return result


def island_image_bounds(position, rotation, map_size, active_rect, image_size):
    """Place a padded, two-pixels-per-tile graphic relative to the map origin."""
    x, y = position
    map_width, map_height = map_size
    left, bottom, right, top = active_rect
    center_x, center_y = (left + right) / 2, (bottom + top) / 2
    width, height = (value / 2 for value in image_size)
    for _ in range(rotation % 4):
        center_x, center_y = map_height - center_y, center_x
        map_width, map_height = map_height, map_width
        width, height = height, width
    return x + center_x - width / 2, y + center_y - height / 2, width, height


def island_map_view(guid, size, terrain_bounds):
    """Trim open sea with a 64-tile margin, preserving all known terrain."""
    width, height = size
    full = (0, 0, width, height)
    if guid not in (112132, 180045) or not terrain_bounds:
        return full
    left = max(0, min(box[0] for box in terrain_bounds) - 64)
    bottom = max(0, min(box[1] for box in terrain_bounds) - 64)
    # The Arctic mainland retains its original top and right map edges.
    right, top = width, height
    if guid == 112132:
        right = min(width, max(box[2] for box in terrain_bounds) + 64)
        top = min(height, max(box[3] for box in terrain_bounds) + 64)
    if right <= left or top <= bottom:
        return full
    return left, bottom, right, top


def render_catalog(rows, groups, maps, stage, updated_at, total_playtime, profile_totals, statistics=None):
    from functools import lru_cache
    from PIL import Image, ImageDraw, ImageFont
    from html import escape as esc
    from io import BytesIO
    from urllib.parse import quote
    maps={r['id']:r for r in maps}
    base=stage/'map-images'
    base.mkdir(exist_ok=True)
    idx=index_game()
    by_image=defaultdict(list)
    for n in idx:
        if n.endswith('/gamemapimage.png'):
            by_image[n.split('/')[-2]].append(n)
    @lru_cache(maxsize=360)
    def tile(file):
        path=file.lower().replace('\\','/')
        folder,_,stem=path.rpartition('/')
        stem=Path(stem).stem
        n=f'{folder}/_gamedata/{stem}/gamemapimage.png'
        if n not in idx:
            if len(by_image[stem])!=1: return None
            n=by_image[stem][0]
        folder, generated = n.split('/_gamedata/')
        info = f"{folder}/{generated.split('/')[0]}.a7minfo"
        if info not in idx: return None
        raw = read_asset(idx[info])
        if not raw: return None
        metadata = dict(fields(raw))
        if ('MapSize',) not in metadata or ('ActiveMapRect',) not in metadata: return None
        map_size = st.unpack('<ii', metadata[('MapSize',)])
        active_rect = st.unpack('<4i', metadata[('ActiveMapRect',)])
        img=Image.open(BytesIO(read_asset(idx[n]))).convert('RGBA')
        img=reduce_island_shadow(img)
        image_size = img.size
        # Retain enough detail for the tighter regional views.
        img = img.resize((max(1,round(img.width*.3)),max(1,round(img.height*.3))),Image.Resampling.LANCZOS)
        return img, map_size, active_rect, image_size

    @lru_cache(maxsize=None)
    def font(name,size):
        return ImageFont.truetype(f'C:/Windows/Fonts/{name}.ttf',size)

    pictures={}
    def image(s, seed, i):
        if 'size' not in s or not all(0<x<=15000 for x in s['size']): return None
        ils=[e for e in s['islands'] if e.get('file') and 'pos' in e]
        if not ils: return None
        geometry=(s['guid'],tuple(s['size']),tuple(sorted((e['file'],tuple(e['pos']),e.get('rotation',0)) for e in ils)))
        if geometry in pictures: return pictures[geometry]
        graphics = [(element, tile(element['file'])) for element in ils]
        terrain_bounds = []
        if all(graphic is not None for _, graphic in graphics):
            for element, (_, map_size, rect, _) in graphics:
                terrain_size = (2*(rect[2]-rect[0]), 2*(rect[3]-rect[1]))
                x, y, width, height = island_image_bounds(
                    element['pos'], element.get('rotation', 0), map_size, rect, terrain_size)
                terrain_bounds.append((x, y, x+width, y+height))
        view_left, view_bottom, view_right, view_top = island_map_view(s['guid'], s['size'], terrain_bounds)
        view_size = (view_right-view_left, view_top-view_bottom)
        scale=830/max(view_size)
        w,h=(round(x*scale) for x in view_size)
        canvas=Image.new('RGBA',(w+60,h+116),'#0b202c')
        draw=ImageDraw.Draw(canvas)
        draw.rectangle((30,62,w+29,h+61),fill='#123a4c',outline='#426579')
        for j in range(1,8):
            x=30+round(w*j/8); y=62+round(h*j/8)
            draw.line((x,63,x,h+60),fill='#204759')
            draw.line((31,y,w+28,y),fill='#204759')
        missing=[]
        layer = Image.new('RGBA', (w, h))
        layer_draw = ImageDraw.Draw(layer)
        for e, graphic in graphics:
            x,y=e['pos']
            cx,cy=round((x-view_left)*scale),round(h-(y-view_bottom)*scale)
            if graphic is None:
                missing.append(Path(e['file']).stem)
                layer_draw.ellipse((cx-5,cy-5,cx+5,cy+5),outline='#ffcb84',width=2)
                continue
            im, map_size, active_rect, image_size = graphic
            angle=e.get('rotation',0)%4
            if angle: im=im.rotate(90*angle,expand=True)
            left, bottom, world_width, world_height = island_image_bounds(
                e['pos'], angle, map_size, active_rect, image_size)
            width,height=(max(1,round(a*scale)) for a in (world_width,world_height))
            im=im.resize((width,height),Image.Resampling.LANCZOS)
            layer.alpha_composite(im,(round((left-view_left)*scale),round(h-(bottom+world_height-view_bottom)*scale)))
        canvas.alpha_composite(layer, (30, 62))
        region=REGIONS.get(s['guid'],f"Szenario / Region {s['guid']}")
        draw.text((30,15),region,font=font('segoeuib',28),fill='#ecf5f8')
        dimensions = f'{view_size[0]:g} × {view_size[1]:g}'
        if (view_left, view_bottom, view_right, view_top) != (0, 0, *s['size']):
            dimensions = f'Ausschnitt: {dimensions}'
        subtitle=f"{len(ils)} Inseln  ·  {dimensions}"
        if missing: subtitle+=f"  ·  {len(missing)} ohne Grafik"
        draw.text((30,h+77),subtitle,
                  font=font('segoeui',15),fill='#aac5d3')
        digest = hashlib.sha256(repr((MAP_RENDER_VERSION, geometry)).encode()).hexdigest()[:8]
        fn=f"Seed-{seed}_{i:03d}_{s['guid']}_{digest}.png"
        canvas.convert('RGB').save(base/fn)
        pictures[geometry]=(fn,region,len(ils),missing)
        return pictures[geometry]
    def get(setup,k):
        return [v for p,v in setup if p[0]==k and p[-1]!='count']
    def one(setup,k,default=None):
        return next(iter(get(setup,k)),default)
    def mode(setup):
        return next((label for k,label in [('EnableScenario','Szenario'),('EnableCampaign','Kampagne'),
             ('CreativeMode','Kreativmodus')] if one(setup,k,0)), 'Sandkasten')
    def groupset(r):
        return tuple((tuple(k),v) for k,v in r['setup'] if k[-1]!='count')
    def folder(r):
        return str(Path(r['path']).parent)
    def show_values(data):
        return ', '.join(map(str,data)) or '—'
    def details(setup):
        d=defaultdict(list)
        for k,v in setup:
            d['/'.join(k)].append(v)
        return '<dl>'+''.join(game_labels.row('anno1800', k.split('/')[0], v, k) for k,v in d.items())+'</dl>'
    def preset_details():
        chunks=[]
        played={one(k,'GameSeed') for k,_ in groups}
        for p in sorted(((ACCOUNT.parent if ACCOUNT.name.lower()=='accounts' else ACCOUNT.parent.parent)/'GameSettings').glob('*.xml'),key=lambda p:p.stem.lower()):
            try:
                setup=[(k[1:],val(v)) for k,v in fields(p.read_bytes())
                       if k[0]=='GameSetupManager' and len(k)>1 and k[1] not in ('Peers','SavegameFolderW','SavegameFolder','ActiveHappyDayEvents')]
                seed=one(setup,'GameSeed')
                if seed is None: raise ValueError()
                label='Seed in Spielständen gefunden' if seed in played else 'Seed nur in Vorlage gefunden'
                chunks.append(f'<details><summary>{esc(p.stem)} · {seed} · {label}</summary>{details(setup)}</details>')
            except Exception:
                chunks.append(f'<p>{esc(p.stem)}: nicht auslesbar</p>')
        return ''.join(chunks)
    seed_bounds = {}
    for key, saves in groups:
        seed = one(key, 'GameSeed')
        first = min(r['stamp'] for r in saves)
        last = max(r['stamp'] for r in saves)
        previous = seed_bounds.get(seed, (first, last))
        seed_bounds[seed] = min(first, previous[0]), max(last, previous[1])
    parts=[]
    excel_rows = []
    ordered_groups = sorted(enumerate(groups, 1),
                            key=lambda entry: max(row['stamp'] for row in entry[1][1]), reverse=True)
    for i, (k, rs) in ordered_groups:
        seed=one(k,'GameSeed')
        prof=Counter((r['source'],folder(r)) for r in rs)
        card=maps.get(i,{})
        ims=[image(s,seed,i) for s in sorted(card.get('maps',[]),key=lambda s:([180023,180025,110934,180045,112132].index(s['guid']) if s['guid'] in [180023,180025,110934,180045,112132] else 10))]
        pics=[]
        links=[]
        for im in filter(None,ims):
            fn,region,num,miss=im
            url='map-images/'+quote(fn)
            tip=f'{num} Inseln' + (f' · {len(miss)} ohne Grafik' if miss else '')
            pics.append(f'<figure><a href="{url}"><img src="{url}" loading="lazy" alt="{esc(region)}"></a><figcaption>{esc(region)} · {tip}</figcaption></figure>')
            links.append({'path':f'map-images/{fn}', 'label':region})
        source=f"{card.get('source','')}: {card.get('path','')}" if pics else card.get('error','Noch keine Karte exportiert')
        profiles = [f'{p} ({n})'+(' [Archiv]' if s=='Archiv' else '') for (s,p),n in sorted(prof.items())]
        variants=Counter(groupset(r) for r in rs)
        third=get(k,'ThirdParties')
        traders=[f'{PARTIES.get(p, f"ID {p}")} ({("0","1","2")[d] if d in (0,1,2) else d})' for p,d in zip(third[::2],third[1::2])]
        values = [*(game_labels.value('anno1800', key, get(k, key)) for key in MAP_SETTING_KEYS),
                  show_values(get(k, 'SecondParties')), show_values(traders),
                  show_values([DLC.get(n, f'ID {n}') for n in get(k, 'ActiveDLCs')])]
        times = time_values(rs, seed_bounds[seed], updated_at.tzinfo)
        table = ''.join(game_labels.row('anno1800', key, get(k, key)) for key in MAP_SETTING_KEYS)
        table += ''.join(f'<div><small>{esc(h)}</small><span data-i18n-ignore>{esc(v)}</span></div>'
                         for h,v in zip(GAME_SETTINGS[6:], values[6:], strict=True))
        campaign_statistics = [statistics[key] for key in sorted({f"{seed}:{r['campaign_id']}" for r in rs})
                               if statistics and key in statistics]
        raw=''.join(f'<details><summary>Einstellungen · {n} Datei(en)</summary>{details(v)}</details>' for v,n in variants.most_common())
        profile_names = sorted({profile_name(r['source'], r['path']) for r in rs})
        totals = variant_totals(campaign_statistics, len(rs))
        sort_values = dict(first=times['sort']['first'], latest=times['sort']['latest'],
                           totalTime=totals['play_ms']//1000 if totals['play_ms'] is not None else 0)
        parts.append(render_card(seed, i, mode(k), profile_names, '\n'.join(profiles),
                                 sort_values, campaign_statistics, len(rs),
                                 f'<p class="source">{esc(source)}</p>',
                                 ''.join(pics), f'<div class="settings">{table}</div>{raw}',
                                 game_labels.description('anno1800', ((key, get(k, key)) for key in MAP_SETTING_KEYS))))
        excel_rows.append({'identity':[seed, i, mode(k)], 'links':links,
                           'settings':[len(rs), '\n'.join(profiles), *values, source, totals['campaigns'],
                                       totals['play_ms']/86400000 if totals['play_ms'] is not None else None],
                           'delta':0, 'statistics':campaign_statistics, 'totals':totals})
    extra = ('<section><h2>Gespeicherte Spielvorlagen</h2>'
             '<p>Diese Dateien sind keine Spielstände und zählen nicht zur Seed-Aufstellung. '
             'Die Kennzeichnung vergleicht nur die Seed-Zahl.</p>' + preset_details() + '</section>'
             '<p class="source"><span data-i18n="map.references">Formatreferenzen:</span> '
             '<a href="https://github.com/EMRECAN-1907/anno1800-save-tools">A7S / FileDB</a> · '
             '<a href="https://github.com/anno-mods/FileDBReader">FileDB V1</a> · '
             '<a href="https://github.com/pan324/anno1800_seedfinder" data-i18n="map.graphicsReference">'
             'Inselgrafiken und Darstellung</a>.</p>')
    seeds = [one(key, 'GameSeed') for key, _ in groups]
    page = render_catalog_page('anno1800', parts, seeds, len(rows), updated_at, total_playtime,
                               ranking_html(profile_totals, duration), extra)
    (stage/'map-gallery.html').write_text(page, encoding='utf-8')
    print(f'{len(set(seeds))} Seeds, {len(groups)} Varianten, {len(pictures)} Kartenbilder', flush=True)
    return excel_rows

def excel_target(output, explicit):
    return explicit.resolve() if explicit else output/'anno1800-map-seeds.xlsx'


def add_excel_links(stage, workbook, output):
    from urllib.parse import quote, unquote
    from xml.dom import minidom
    from zipfile import ZipFile

    main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    package = 'http://schemas.openxmlformats.org/package/2006/relationships'
    sheet_part = 'xl/worksheets/sheet1.xml'
    rel_part = 'xl/worksheets/_rels/sheet1.xml.rels'
    links = load_cache(stage/'links.json', [])
    with ZipFile(stage/'base.xlsx') as base:
        sheet = minidom.parseString(base.read(sheet_part))
        relations = minidom.parseString(base.read(rel_part))
        hyperlinks = sheet.createElementNS(main, 'hyperlinks')
        hyperlinks.setAttribute('xmlns', main)
        root = sheet.documentElement
        anchor = next(node for node in root.childNodes
                      if node.localName in ('pageMargins','pageSetup','drawing','tableParts','extLst'))
        if links:
            root.insertBefore(hyperlinks, anchor)
            hyperlinks.setAttribute('xmlns:r', rel)
        existing = {node.getAttribute('Id') for node in
                    relations.getElementsByTagNameNS(package, 'Relationship')}
        for index, link in enumerate(links, 1):
            rid = f'rIdMap{index}'
            path = Path(link['path'])
            if rid in existing or not (stage/path).is_file():
                raise ValueError(f'Ungültiger Kartenlink: {link["path"]}')
            target = quote(os.path.relpath(output/path, workbook.parent).replace('\\','/'), safe='/')
            external = relations.createElementNS(package, 'Relationship')
            external.setAttribute('xmlns', package)
            for key, value in {'Id':rid, 'Type':rel+'/hyperlink',
                               'Target':target, 'TargetMode':'External'}.items():
                external.setAttribute(key, value)
            relations.documentElement.appendChild(external)
            cell = sheet.createElementNS(main, 'hyperlink')
            cell.setAttribute('ref', link['address'])
            cell.setAttributeNS(rel, 'r:id', rid)
            hyperlinks.appendChild(cell)
        parts = {sheet_part:sheet.toxml(encoding='utf-8'),
                 rel_part:relations.toxml(encoding='utf-8')}
        with ZipFile(stage/'report.xlsx', 'w') as report:
            for member in base.infolist():
                report.writestr(member, parts.get(member.filename) or base.read(member))
    with ZipFile(stage/'report.xlsx') as report:
        if report.testzip() is not None:
            raise ValueError('Excel-Datei ist unvollständig.')
        written = minidom.parseString(report.read(rel_part))
        paths = [node.getAttribute('Target') for node in written.getElementsByTagNameNS(package, 'Relationship')
                 if node.getAttribute('Type') == rel+'/hyperlink']
        if len(paths) != len(links) or any(
            not (stage / (workbook.parent / unquote(target)).resolve().relative_to(output)).is_file()
            for target in paths
        ):
            raise ValueError('Excel-Kartenlinks sind unvollständig.')


def write_excel(rows, stage, workbook, output, updated_at, total_playtime, profiles):
    from anno_excel_export import write_workbook
    write_workbook(rows, GAME_SETTINGS, ['Partien insgesamt', 'Gespeicherte Gesamtspielzeit'], ZONE_NAME, stage, workbook, output,
                   updated_at, None, total_playtime, profiles)


def publish(stage, output, workbook):
    checkpoint()
    workbook.parent.mkdir(parents=True, exist_ok=True)
    images = output / 'map-images'
    images.mkdir(exist_ok=True)
    for name in ('map-gallery.html', 'anno-scan.json', 'anno-maps.jsonl'):
        if (output / name).exists() and not (output / name).is_file():
            raise ValueError(f'Ausgabeziel ist keine Datei: {output/name}')
    pairs = [(image, images / image.name) for image in (stage / 'map-images').glob('*.png')
             if not (images / image.name).is_file() or image.read_bytes() != (images / image.name).read_bytes()]
    pairs.append((stage / 'report.xlsx', workbook))
    pairs.extend((stage / name, output / name) for name in
                 ('map-gallery.html', 'anno-scan.json', 'anno-maps.jsonl', 'anno1800-statistics.json'))
    publish_files(pairs, stage / 'previous')


def configure(settings):
    """Bind one explicit configuration within this game worker process."""
    global CONFIG, ACCOUNT, ARCHIVE, GAME, ZONE_NAME
    if settings.game != 'anno1800':
        raise ValueError('Die Einstellungsdatei gehört nicht zu anno1800.')
    checkpoint()
    settings.validate('analyze')
    CONFIG = settings
    ACCOUNT = settings.path('account')
    ARCHIVE = settings.path('archive') or settings.output / 'unused-archive'
    GAME = settings.path('game_data')
    ZONE_NAME = settings.zone
    index_game.cache_clear()


def run(settings, *, rescan=False):
    """Generate outputs from explicit settings without parsing process arguments."""
    main(['--rescan'] if rescan else [], settings=settings)
    return settings.report_output / 'map-gallery.html'


def main(argv=None, *, settings=None):
    global ACCOUNT, ARCHIVE, GAME
    configure(settings if settings is not None else settings_for('anno1800'))
    import msvcrt
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account', type=Path, default=ACCOUNT, help='Ordner des Spielkontos')
    parser.add_argument('--archive', type=Path, default=ARCHIVE, help='Ordner der Save-Kopien')
    parser.add_argument('--game-data', type=Path, default=GAME, help='maindata der Anno-Installation')
    parser.add_argument('--output', type=Path, default=CONFIG.report_output, help='Ordner für Galerie, Bilder und Zwischendaten')
    parser.add_argument('--excel', type=Path, help='Excel-Ziel innerhalb des Ausgabeordners')
    parser.add_argument('--rescan', action='store_true', help='Zwischendaten ignorieren')
    parser.add_argument('--render-only', action='store_true', help='Beide Berichte aus vorhandenen Zwischendaten schreiben')
    opts = parser.parse_args(argv)
    if opts.render_only and opts.rescan:
        parser.error('--render-only und --rescan sind Alternativen.')
    ACCOUNT, ARCHIVE, GAME = (path.resolve() for path in (opts.account, opts.archive, opts.game_data))
    with reserve_paths([CONFIG.output, opts.output, CONFIG.log_output]):
        CONFIG.validate('analyze')
        protect_output(opts.output, CONFIG.all_sources()+[opts.account,opts.archive,opts.game_data])
        output = opts.output.resolve()
        target = excel_target(output, opts.excel)
        if not target.is_relative_to(output) or target.suffix.lower() != '.xlsx':
            parser.error('Das Excel-Ziel muss eine .xlsx-Datei innerhalb des Ausgabeordners sein.')
        if not ACCOUNT.is_dir() or not (GAME/'data0.rda').is_file():
            parser.error('Spielkonto oder maindata fehlt. Pfade mit --account und --game-data prüfen.')
        zone = ZoneInfo(ZONE_NAME)
        try:
            import PIL.Image  # Check Pillow before scanning.
        except ImportError as exc:
            raise ValueError('Pillow fehlt. Installation: python -m pip install Pillow') from exc
        output.mkdir(parents=True, exist_ok=True)
        excel_locks = (target.parent/('~$'+target.name), target.parent/('~$'+target.name[2:]))
        if any(lock.exists() for lock in excel_locks):
            raise ValueError('Bitte die Arbeitsmappe in Excel schliessen.')
        scan_path = output/'anno-scan.json'
        maps_path = output/'anno-maps.jsonl'
        with (output/'.anno-analysis.lock').open('a+b') as lock:
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError('Eine Auswertung für diesen Ausgabeordner läuft bereits.') from exc
            old_maps = []
            if not opts.rescan and maps_path.exists():
                try:
                    old_maps = [json.loads(line) for line in maps_path.read_text(encoding='utf-8').splitlines()]
                except ValueError:
                    pass
            if opts.render_only:
                rows = load_cache(scan_path, [])
                if not rows or not all('stamp' in row and 'play_ms' in row and 'campaign_id' in row for row in rows):
                    raise ValueError('Zwischendaten fehlen oder sind veraltet. Ohne --render-only starten.')
            else:
                rows = scan(scan_path, opts.rescan)
            groups = bucket(rows)
            maps = collect_maps(groups, old_maps)
            with temporary_directory(prefix='.anno-export-') as temp:
                stage = Path(temp)
                updated_at = datetime.now(zone)
                profiles = profile_playtime(
                    (dict(settings)[('GameSeed',)], row, row['source'], row['path'], row['play_ms'], False)
                    for settings, saves in groups for row in saves
                )
                total_playtime = duration(sum(ms for _, _, ms in profiles) // 1000)
                statistics, statistics_cache = collect_statistics(
                    [dict(campaign=f"{dict(settings)[('GameSeed',)]}:{row['campaign_id']}", path=save_path(row),
                          source=f"{row['source']}: {row['path']}", profile=profile_name(row['source'], row['path']),
                          seed=dict(settings)[('GameSeed',)], stamp=row['stamp'], play_ms=row['play_ms'], live=row['source']=='Spielkonto')
                     for settings, saves in groups for row in saves],
                    FileDBStatistics('anno1800', GAME, index_game), output/'anno1800-statistics.json', zone, opts.rescan,
                    cache_only=opts.render_only)
                (stage/'anno1800-statistics.json').write_text(json.dumps(statistics_cache,ensure_ascii=False),encoding='utf-8')
                excel_rows = render_catalog(rows, groups, maps, stage, updated_at, total_playtime, profiles, statistics)
                write_excel(excel_rows, stage, target, output, updated_at, total_playtime, profiles)
                (stage/'anno-scan.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
                (stage/'anno-maps.jsonl').write_text(
                    ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in maps), encoding='utf-8')
                publish(stage, output, target)
        print(f'Excel: {target}')
        print(f"HTML: {output / 'map-gallery.html'}")
        missing = [row for row in maps if row['error']]
        if missing:
            print(f'{len(missing)} Varianten ohne Karte. Gründe stehen in der Galerie.', file=sys.stderr)



if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError) as exc:
        sys.exit(f'Aktualisierung abgebrochen: {exc}')
