'Update Excel reports, HTML galleries and maps from local Anno 1800 saves.'
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import sys
from anno_settings import settings_for, protect_output
from anno_gallery import render_gallery
CONFIG = settings_for('anno1800')

from anno_profile_playtime import profile_name, profile_playtime, ranking_html, RANKING_CSS
from zoneinfo import ZoneInfo
import struct as st
import zlib

ACCOUNT = CONFIG.path('account')
HERE = Path(__file__).resolve().parent
ARCHIVE = CONFIG.path('archive') or CONFIG.output/'unused-archive'

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
                  if not (p.parent == ACCOUNT and p.name.lower().startswith('accountdata'))]

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
        rows = list(pool.map(one, sorted(candidates)))
    failures = [row for row in rows if 'error' in row]
    if failures:
        for row in failures[:10]:
            print(f"{row['source']}: {row['path']}  ({row['error']})", file=sys.stderr)
        raise ValueError(f'{len(failures)} Spielstände konnten nicht vollständig gelesen werden.')
    if not rows:
        raise ValueError('Keine Spielstände gefunden.')
    return rows




GAME = CONFIG.path('game_data')

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

def index_game():
    entries={}
    for path in sorted(GAME.glob('data*.rda'),key=lambda p:int(p.stem[4:])):
        for n,record in rda_index(path):
            if any(x in n for x in ('moderate_l_12','assets.xml','mapgenerator')) or n.endswith(('.a7minfo','.a7tinfo')) or ('/islands/' in n and n.endswith('.png')):
                entries[n]=record
    return entries



WORLD_KEYS = {'GameSeed','SetupMapType','SetupStartSession','SetupStartSessionIslandSize',
              'SetupStartSessionIslandDifficulty','SetupFertility','SetupRawMaterial',
              'EnableCampaign','EnableScenario','CreativeMode','Maps','ThirdParties',
              'SecondParties','ActiveDLCs','ActiveMods','ActiveLocalMods','SetupStartWithKontor'}

def norm(setup):
    return tuple((tuple(k),v) for k,v in setup if k[-1]!='count' and k[0] in WORLD_KEYS
                 and (k[0] not in ('EnableCampaign','EnableScenario','CreativeMode') or v!=0))

def bucket(rows):
    groups=defaultdict(list)
    for r in rows:
        if 'setup' in r:
            # Keep ordering of participants, normalise order of different settings.
            groups[tuple(sorted(norm(r['setup']),key=lambda e:e[0][0]))].append(r)
    return sorted(groups.items(),key=lambda g:(dict(g[0]).get(('GameSeed',),-1),repr(g[0])))

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
MAPTYPES={1:'Archipel',2:'Atoll',3:'Inselbogen',4:'Ecken',5:'Schneeflocke'}
SIZES={0:'Klein',1:'Mittel',2:'Gross'}
AMOUNTS={0:'Knapp',1:'Normal',2:'Reichlich'}
DIFF={0:'Normal',1:'Schwer'}
PARTIES={73:'Anne Harlow',76:'Jean La Fortune',29:'Isabel Sarmento',46:'Eli Bleakworth',78:'Madame Kahina'}
DLC={410040:'Versunkene Schätze',410041:'Botanika',410042:'Die Passage',
     410083:'Speicherstadt',24963:'Aufstieg der Neuen Welt',24961:'Keim der Hoffnung',
     410059:'Paläste der Macht',410070:'Reiche Ernte',410071:'Land der Löwen',
     410084:'Reisezeit',410085:'Dächer der Stadt',24962:'Reich der Lüfte',4100010:'Die Anarchisten'}

ZONE_NAME = CONFIG.zone
STANDARD_REGIONS = (180023, 180025, 110934, 180045, 112132)
GAME_SETTINGS = [
    'Kartentyp', 'Weltgrösse', 'Inselgrösse', 'Inselschwierigkeit', 'Fruchtbarkeit',
    'Rohstoffvorkommen', 'KI-Slots (IDs)', 'Händler und Piraten (Stufe als ID)', 'Aktive DLCs',
]
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


def render_catalog(rows, groups, maps, stage, updated_at, total_playtime, profile_totals):
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
        img=Image.open(BytesIO(read_asset(idx[n]))).convert('RGBA')
        return img.resize((max(1,round(img.width*.225)),max(1,round(img.height*.225))),Image.Resampling.LANCZOS)

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
        scale=830/max(s['size'])
        w,h=(round(x*scale) for x in s['size'])
        canvas=Image.new('RGBA',(w+60,h+116),'#0b202c')
        draw=ImageDraw.Draw(canvas)
        draw.rectangle((30,62,w+29,h+61),fill='#123a4c',outline='#426579')
        for j in range(1,8):
            x=30+round(w*j/8); y=62+round(h*j/8)
            draw.line((x,63,x,h+60),fill='#204759')
            draw.line((31,y,w+28,y),fill='#204759')
        missing=[]
        for e in ils:
            x,y=e['pos']
            cx,cy=30+round(x*scale),62+round(h-y*scale)
            im=tile(e['file'])
            if im is None:
                missing.append(Path(e['file']).stem)
                draw.ellipse((cx-5,cy-5,cx+5,cy+5),outline='#ffcb84',width=2)
                continue
            angle=e.get('rotation',0)%4
            if angle: im=im.rotate(90*angle,expand=True)
            width,height=(max(1,round(a*scale*2)) for a in im.size)
            im=im.resize((width,height),Image.Resampling.LANCZOS)
            canvas.alpha_composite(im,(cx-width//2,cy-height//2))
        region=REGIONS.get(s['guid'],f"Szenario / Region {s['guid']}")
        draw.text((30,15),region,font=font('segoeuib',28),fill='#ecf5f8')
        subtitle=f"{len(ils)} Inseln  ·  {s['size'][0]} × {s['size'][1]}"
        if missing: subtitle+=f"  ·  {len(missing)} ohne Grafik"
        draw.text((30,h+77),subtitle,
                  font=font('segoeui',15),fill='#aac5d3')
        fn=f"Seed-{seed}_{i:03d}_{s['guid']}_{hashlib.sha256(repr(geometry).encode()).hexdigest()[:8]}.png"
        canvas.convert('RGB').save(base/fn)
        pictures[geometry]=(fn,region,len(ils),missing)
        return pictures[geometry]
    def get(setup,k):
        return [v for p,v in setup if p[0]==k and p[-1]!='count']
    def one(setup,k,default=None):
        return next(iter(get(setup,k)),default)
    def decode(setup,k,labels):
        n=one(setup,k)
        return labels.get(n,f'ID {n}') if n is not None else '—'
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
        return '<dl>'+''.join(f'<dt>{esc(k)}</dt><dd>{esc(show_values(v))}</dd>' for k,v in d.items())+'</dl>'
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
    for i,(k,rs) in enumerate(groups,1):
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
        profile = esc(' · '.join(profiles))
        variants=Counter(groupset(r) for r in rs)
        third=get(k,'ThirdParties')
        traders=[f'{PARTIES.get(p, f"ID {p}")} ({("0","1","2")[d] if d in (0,1,2) else d})' for p,d in zip(third[::2],third[1::2])]
        def label(key,lookup): return decode(k,key,lookup)
        values = [
            label('SetupMapType', MAPTYPES), label('SetupStartSession', SIZES),
            label('SetupStartSessionIslandSize', SIZES), label('SetupStartSessionIslandDifficulty', DIFF),
            label('SetupFertility', AMOUNTS), label('SetupRawMaterial', AMOUNTS),
            show_values(get(k, 'SecondParties')), show_values(traders),
            show_values([DLC.get(n, f'ID {n}') for n in get(k, 'ActiveDLCs')]),
        ]
        times = time_values(rs, seed_bounds[seed], updated_at.tzinfo)
        table = ''.join(f'<div><small>{esc(h)}</small>{esc(v)}</div>'
                        for h,v in zip(GAME_SETTINGS + TIME_COLUMNS, values + times['display'], strict=True))
        raw=''.join(f'<details><summary>Einstellungen · {n} Datei(en)</summary>{details(v)}</details>' for v,n in variants.most_common())
        attrs = {'seed':seed, 'mode':mode(k), 'variant':i, **times['sort']}
        attrs['profiles'] = json.dumps(sorted({profile_name(r['source'], r['path']) for r in rs}), ensure_ascii=False)
        attrs = ' '.join(f'data-{name}="{esc(str(value), quote=True)}"' for name,value in attrs.items())
        marker = ''
        if times['delta'] > 0:
            attrs += ' class="has-playtime-extra"'
            marker = f'<span class="playtime-extra">Älterer Save: +{duration(times["delta"])} mehr Spielzeit</span>'
        count = f'{len(rs):,}'.replace(',', '’')
        parts.append(f'<article {attrs}><div class="top"><h2>Seed {seed}</h2>'
                     f'<span>Variante {i:03d} · {mode(k)} · {count} Dateien</span>{marker}</div>'
                     f'<p class="profiles">{profile}</p><div class="settings">{table}</div>'
                     f'<div class="maps">{"".join(pics)}</div><p class="source">{esc(source)}</p>'
                     f'<details><summary>Gespeicherte Einstellungswerte anzeigen</summary>{raw}</details></article>')
        excel_rows.append({'identity':[seed, i, mode(k)], 'links':links,
                           'settings':[len(rs), '\n'.join(profiles), *values, source, *times['excel']],
                           'delta':times['delta']})
    seed_counts=Counter(one(k,'GameSeed') for k,_ in groups)
    nseeds=len(seed_counts)
    chips=''.join(f'<button type="button" data-filter="{seed}" title="{count} Varianten">{seed}</button>' for seed,count in sorted(seed_counts.items()))
    css="""*{box-sizing:border-box}body{margin:0;background:#0c1b24;color:#e8f2f6;font:16px/1.5 system-ui,sans-serif}main{max-width:1260px;margin:auto;padding:40px 24px}header{border-bottom:1px solid #385361;padding-bottom:22px;margin-bottom:24px}h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.06;margin:8px 0 18px}h2{font-size:1.65rem;margin:0}p{margin:10px 0}small,.source,.profiles,figcaption,.top span{color:#b6cbd5}label{display:inline-flex;flex-direction:column;margin:0 14px 10px 0}input,select{background:#172f3d;color:inherit;border:1px solid #587685;border-radius:7px;padding:10px;font:inherit}article{padding:22px;margin:16px 0;background:#142936;border:1px solid #365260;border-radius:14px}.top{display:flex;align-items:baseline;gap:8px 20px;flex-wrap:wrap}.settings{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:10px;margin:16px 0}.settings div{padding:9px 11px;background:#1c3847;border-radius:6px}.settings small{display:block;font-size:.8rem}.maps{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:12px}.maps figure{margin:0;max-width:350px}.maps img{display:block;width:100%;border-radius:7px;border:1px solid #436575}figcaption,.source{font-size:.83rem}details{margin-top:8px}summary{cursor:pointer;color:#a4dce8}dl{display:grid;grid-template-columns:minmax(160px,1fr) 2fr;gap:5px 16px}dt,dd{overflow-wrap:anywhere;margin:0}dd{color:#cedee3}a{color:#a4dce8}.seeds{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 24px}.seeds button{background:#172f3d;color:#a4dce8;border:1px solid #426579;border-radius:6px;padding:5px 9px;cursor:pointer}"""
    css += '.settings div{overflow-wrap:anywhere}.has-playtime-extra{border-left:4px solid #e3a84e}.top .playtime-extra{display:inline-block;color:#ffe6b4;background:#583b1b;border-radius:5px;padding:3px 8px;font-weight:600}'
    script = r"""
document.addEventListener('gallerylanguagechange',filter);
const q = document.querySelector('#q');
const mode = document.querySelector('#mode');
const sort = document.querySelector('#sort');
const variants = document.querySelector('#variants');
const count = document.querySelector('#count');
const cards = [...variants.querySelectorAll('article')];
const profileNames = new Map(cards.map(card => [card, JSON.parse(card.dataset.profiles)]));
let selectedProfile = null;
let profileLink = null;
const backToProfiles = document.querySelectorAll('[data-back-to-profiles]');
const profileRanking = document.querySelector('#profile-ranking');

function returnToProfileRanking() {
  const returnLink = profileLink;
  selectedProfile = null;
  profileLink = null;
  q.value = '';
  mode.value = '';
  filter();
  profileRanking.open = true;
  (returnLink || profileRanking.querySelector('summary')).focus({preventScroll: true});
  profileRanking.scrollIntoView();
}

for (const button of backToProfiles) {
  button.addEventListener('click', returnToProfileRanking);
}

function filter() {
  const search = q.value.trim().toLowerCase();
  let visible = 0;
  for (const card of cards) {
    const profile = card.querySelector('.profiles').textContent.toLowerCase();
    const hit = selectedProfile !== null ? profileNames.get(card).includes(selectedProfile) :
      /^\d+$/.test(search) ? card.dataset.seed === search : profile.includes(search);
    card.hidden = !(hit && (!mode.value || card.dataset.mode === mode.value));
    if (!card.hidden) visible++;
  }
  for (const button of backToProfiles) button.hidden = selectedProfile === null;
  count.textContent = galleryI18n.t('map.visible',{count:visible});
}

function sortCards() {
  const key = sort.value;
  const direction = key === 'variant' || key === 'first' ? 1 : -1;
  const ordered = [...cards].sort((a, b) =>
    direction * (Number(a.dataset[key]) - Number(b.dataset[key])) ||
    Number(a.dataset.variant) - Number(b.dataset.variant)
  );
  variants.append(...ordered);
}

q.addEventListener('input', () => {
  selectedProfile = null;
  filter();
});
for (const link of document.querySelectorAll('[data-profile-filter]')) {
  link.addEventListener('click', event => {
    event.preventDefault();
    selectedProfile = link.dataset.profileFilter;
    profileLink = link;
    q.value = selectedProfile;
    mode.value = '';
    filter();
    q.focus({preventScroll: true});
    document.querySelector('#variant-filters').scrollIntoView();
  });
}
mode.addEventListener('change', filter);
sort.addEventListener('change', sortCards);
for (const button of document.querySelectorAll('[data-filter]')) {
  button.addEventListener('click', () => {
    selectedProfile = null;
    q.value = button.dataset.filter;
    mode.value = '';
    filter();
  });
}
filter();
"""
    css += '\n.game-logo { display: block; width: min(100%, 270px); height: auto; margin: 0 0 14px; }\n.game-logo--117 { background: #f1e5cc; border-radius: 8px; }'
    css += '\n.gallery-updated { display: block; color: #b6cbd5; margin: 0 0 4px; }'
    css += '\nheader h1{font-family:system-ui,sans-serif;font-size:clamp(2rem,5vw,3.4rem);font-weight:700;line-height:1.15;margin:0 0 10px}\nheader .gallery-scope{font-weight:600;margin:8px 0}\nheader .gallery-updated{display:block;font-size:14px;color:#b6cbd5;margin:8px 0}\nheader .gallery-summary{margin:12px 0}\nheader .gallery-description{margin:8px 0}\nheader .gallery-notes{font-size:14px;margin:12px 0 0}\nheader .gallery-notes p{margin:8px 0}\n'
    html=f"""<!doctype html><html lang="de-CH"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Anno 1800 · Kartenseeds und Karten</title><style>{css}{RANKING_CSS}</style><main>
    <header>
    <h1>Anno 1800 · Kartenseeds und Karten</h1>
    <p class="gallery-scope">Grundspiel und Erweiterungen</p>
    <p class="gallery-updated">Zuletzt aktualisiert am: <time datetime="{updated_at.isoformat(timespec='minutes')}">{updated_at.strftime('%d.%m.%Y %H:%M')}</time> · Gesamtspielzeit: {total_playtime}</p>
    <p class="gallery-summary"><strong>{nseeds} Seeds · {len(groups)} Kartenvarianten · {len(rows):,} Spielstände</strong></p>
    <p class="gallery-description">Die Galerie gruppiert lokale Spielstände nach Seed und gespeicherter Kartenkonfiguration. Ein Klick auf eine Karte öffnet die PNG-Datei in voller Grösse.</p>
    <details class="gallery-notes"><summary>Hinweise zu Karten und Spielzeit</summary>
    <p>Für die Gesamtspielzeit zählt pro gespeicherter Partie der höchste gespeicherte Spielzeitwert.</p>
    <p>Die Karten kombinieren gespeicherte Inselpositionen und Drehungen mit Grafiken der lokalen Spielinstallation. Sie zeigen Inseln und Gelände, keine Städte, Gebäude oder Besitzverhältnisse. Ein Ring markiert Inseln ohne passende Grafik. Regionen, die im gewählten Stand noch fehlen, werden nicht angezeigt.</p>
    <p>Die Zeitpunkte stammen aus den Spielständen und werden in der eingestellten Zeitzone angezeigt. Bei gleicher höchster Spielzeit erscheint der jüngste Save. Die Anzahl zählt Dateien einschliesslich Autosaves und Archivkopien. Szenarien und Kampagnen können einen Seed speichern, obwohl Teile ihrer Karten vorgegeben sind. IDs sind die gespeicherten Werte. Anzahl und Grösse der Inseln sowie aktive DLCs beziehen sich auf den jeweiligen Stand.</p>
    </details>
    </header>
    {ranking_html(profile_totals, duration)}
    <details><summary>Alle {nseeds} Seed-Werte anzeigen</summary><div class="seeds">{chips}</div></details><p></p>
    <label id="variant-filters">Seed oder Profil <input id="q" type="search" placeholder="z. B. 7398 oder Spieler"></label><label>Modus <select id="mode"><option value="">Alle</option><option>Sandkasten</option><option>Kampagne</option><option>Kreativmodus</option><option>Szenario</option></select></label><label>Sortieren nach <select id="sort"><option value="variant">Seed und Variante</option><option value="latest">Neuester Save zuerst</option><option value="first">Ältester Save zuerst</option><option value="recordDate">Datum des Saves mit längster Spielzeit</option><option value="recordTime">Längste gespeicherte Spielzeit zuerst</option><option value="latestTime">Spielzeit im neuesten Save zuerst</option></select></label><button type="button" class="profile-back" data-back-to-profiles hidden>Zurück zur Profilrangliste</button><p id="count" aria-live="polite"></p>
    <div id="variants">{''.join(parts)}</div>
<button type="button" class="profile-back" data-back-to-profiles hidden>Zurück zur Profilrangliste</button>
    <section><h2>Gespeicherte Spielvorlagen</h2><p>Diese Dateien sind keine Spielstände und zählen nicht zur Seed-Aufstellung. Die Kennzeichnung vergleicht nur die Seed-Zahl.</p>{preset_details()}</section>
    <p class="source"><span data-i18n="map.references">Formatreferenzen:</span> <a href="https://github.com/EMRECAN-1907/anno1800-save-tools">A7S / FileDB</a> · <a href="https://github.com/anno-mods/FileDBReader">FileDB V1</a> · <a href="https://github.com/pan324/anno1800_seedfinder" data-i18n="map.graphicsReference">Inselgrafiken und Darstellung</a>.</p></main><script>{script}</script></html>"""
    (stage/'map-gallery.html').write_text(
        render_gallery(html, 'anno1800', 'map').replace(f'{len(rows):,} Spielstände',
                     f'{len(rows):,} Spielstände'.replace(',', '’')), encoding='utf-8')
    print(f'{nseeds} Seeds, {len(groups)} Varianten, {len(pictures)} Kartenbilder', flush=True)
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
    write_workbook(rows, GAME_SETTINGS, TIME_COLUMNS, ZONE_NAME, stage, workbook, output,
                   updated_at, None, total_playtime, profiles)


def publish(stage, output, workbook):
    workbook.parent.mkdir(parents=True, exist_ok=True)
    images = output/'map-images'
    images.mkdir(exist_ok=True)
    for name in ('map-gallery.html', 'anno-scan.json', 'anno-maps.jsonl'):
        if (output/name).exists() and not (output/name).is_file():
            raise ValueError(f'Ausgabeziel ist keine Datei: {output/name}')
    reports = [(stage/'report.xlsx', workbook)]
    reports.extend((stage/name, output/name)
                   for name in ('map-gallery.html', 'anno-scan.json', 'anno-maps.jsonl'))
    backups = stage/'previous'
    backups.mkdir()
    for index, (_, target) in enumerate(reports):
        if target.is_file():
            shutil.copy2(target, backups/str(index))
    for image in (stage/'map-images').glob('*.png'):
        target = images/image.name
        if not target.is_file() or image.read_bytes() != target.read_bytes():
            os.replace(image, target)
    published = []
    try:
        for index, (source, target) in enumerate(reports):
            os.replace(source, target)
            published.append((index, target))
    except OSError:
        for index, target in reversed(published):
            backup = backups/str(index)
            if backup.is_file():
                os.replace(backup, target)
            else:
                target.unlink()
        raise


def main():
    global ACCOUNT, ARCHIVE, GAME
    import msvcrt
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account', type=Path, default=ACCOUNT, help='Ordner des Spielkontos')
    parser.add_argument('--archive', type=Path, default=ARCHIVE, help='Ordner der Save-Kopien')
    parser.add_argument('--game-data', type=Path, default=GAME, help='maindata der Anno-Installation')
    parser.add_argument('--output', type=Path, default=CONFIG.report_output, help='Ordner für Galerie, Bilder und Zwischendaten')
    parser.add_argument('--excel', type=Path, help='Excel-Ziel innerhalb des Ausgabeordners')
    parser.add_argument('--rescan', action='store_true', help='Zwischendaten ignorieren')
    parser.add_argument('--render-only', action='store_true', help='Beide Berichte aus vorhandenen Zwischendaten schreiben')
    opts = parser.parse_args()
    if opts.render_only and opts.rescan:
        parser.error('--render-only und --rescan sind Alternativen.')
    ACCOUNT, ARCHIVE, GAME = (path.resolve() for path in (opts.account, opts.archive, opts.game_data))
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
        with tempfile.TemporaryDirectory(prefix='.anno-export-', dir=output) as temp:
            stage = Path(temp)
            updated_at = datetime.now(zone)
            profiles = profile_playtime(
                (dict(settings)[('GameSeed',)], row, row['source'], row['path'], row['play_ms'], False)
                for settings, saves in groups for row in saves
            )
            total_playtime = duration(sum(ms for _, _, ms in profiles) // 1000)
            excel_rows = render_catalog(rows, groups, maps, stage, updated_at, total_playtime, profiles)
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
