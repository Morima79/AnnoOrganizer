'Update Excel reports and island galleries from local Anno 117 saves.'
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from anno_settings import settings_for, protect_output
from anno_gallery import render_gallery
from anno_save_summary import collect_statistics, render_statistics, statistics_sources, label as summary_label
from anno_save_statistics import FileDBStatistics
CONFIG = settings_for('anno117')

from anno_profile_playtime import profile_name, profile_playtime, ranking_html, RANKING_CSS
import struct
import sys
from tempfile import TemporaryDirectory

from anno_file_formats import fields, members, rda_index, read_asset, val

HERE = Path(__file__).resolve().parent
ACCOUNT = CONFIG.path('account')
GAME = CONFIG.path('game_data')
REGIONS = {3245: 'Latium', 6627: 'Albion', 149679: 'Aegyptus'}
MAP_TYPES = {43181:'Zufällig', 43182:'Archipel', 43183:'Atoll', 43184:'Graben',
             89065:'Ecken', 90702:'Inselkette'}
# German labels from config.rda (assets.xml and texts_german.xml).
DLC_NAMES = {67902:'Verheißung des Vulkans', 67903:'Das Hippodrom', 67904:'Erwachen des Deltas'}
RIVALS = {31099:'Dorian', 31100:'Tarragon', 31101:'Licia Ma'}
EMPERORS = {31637:'Gnaeus Firmius Calidus', 31721:'Kaiser Lucius Augustus', 31722:'Julia Augusta'}
AMOUNTS = {0:'Karg', 1:'Normal', 2:'Im Überfluss'}
SIZES = {0:'Klein', 1:'Regulär', 2:'Gross'}
VALUE_NAMES = {
    'SetupMapTemplateType':MAP_TYPES, 'DefaultStartProvince':REGIONS,
    'ActiveDLCs':DLC_NAMES, 'DefaultSecondParties':RIVALS, 'SetupStartEmperor':EMPERORS,
    'SetupFertility':AMOUNTS, 'SetupRawMaterial':AMOUNTS,
    'SetupStartSessionIslandDifficulty':{0:'Normal',1:'Schwer'},
    'SetupStartForestSize':{0:'Karg', 1:'Normal', 2:'Im Überfluss'},
    'EnableCampaign':{0:'Nein', 1:'Ja'},
}
DETAIL_LABELS = {'DefaultSecondParties':'Rivalen (Standard)', 'SetupStartEmperor':'Kaiser',
                 'EnableCampaign':'Kampagne', 'GameSeed':'Seed'}
GEO_SETTINGS = {
    'SetupMapTemplateType':'Kartentyp', 'SetupStartSession':'Weltgrösse',
    'SetupStartSessionIslandSize':'Inselgrösse', 'SetupStartSessionIslandDifficulty':'Inselschwierigkeit',
    'SetupFertility':'Fruchtbarkeit', 'SetupRawMaterial':'Vorkommen', 'SetupStartForestSize':'Wald',
    'DefaultStartProvince':'Startprovinz', 'ActiveDLCs':'Aktive DLCs',
}
TIME_COLUMNS = ['Ältester Save des Seeds','Neuester Save des Seeds','Ältester Save der Variante',
                'Neuester Save der Variante','Spielzeit im neuesten Save','Längste gespeicherte Spielzeit',
                'Datum des Saves mit längster Spielzeit','Save mit längster Spielzeit']
MAP_KEYS = set(GEO_SETTINGS) | {'GameSeed','EnableCampaign','EnableScenario','CreativeMode',
                               'SetupContinentalIslandStart','SetupContinentalIslandAllowRivalSettling',
                               'DefaultSecondParties','ActiveMods','ActiveLocalMods'}
SETTINGS = list(GEO_SETTINGS.values())


def int_pair(raw):
    return struct.unpack('<ii', raw)


def read_save(file):
    payloads = dict(members(file, {'gamesetup.a7s','header.a7s','meta.a7s'}))
    setup = defaultdict(list)
    for key, raw in fields(payloads['gamesetup.a7s']):
        if key[0]=='GameSetupManager' and len(key)>1 and key[-1]!='count' and (
            key[1] in MAP_KEYS or key[1].startswith('Setup') and key[1]!='SetupSlots'
        ):
            setup[key[1]].append(val(raw))
    header = {key[-1]:val(raw) for key,raw in fields(payloads['header.a7s'])
              if len(key)==2 and key[0]=='CorporationProfile' and key[-1] in
              {'GameSeed','SavedActivePlaytime','CorporationTime','WallTimeOnSave','ID'}}
    meta = {key[-1]:val(raw) for key,raw in fields(payloads['meta.a7s']) if key==('LastModTime',)}
    seed = setup['GameSeed'][0]
    stamp = meta['LastModTime']
    play = header.get('SavedActivePlaytime', header['CorporationTime'])
    if seed != header['GameSeed'] or not all(isinstance(v,int) for v in (seed,stamp,play)):
        raise ValueError('Seed oder Zeitangaben konnten nicht bestätigt werden.')
    campaign_id = header['ID']
    if not isinstance(campaign_id, int) or campaign_id <= 0:
        raise ValueError('Partie-ID fehlt oder ist ungültig')
    return dict(setup=setup, seed=seed, stamp=stamp, play=play, campaign_id=campaign_id,
                active='SavedActivePlaytime' in header)


def scan(accounts, cache, refresh):
    old = json.loads(cache.read_text(encoding='utf8')) if cache.is_file() and not refresh else {}
    files = sorted(file for file in accounts.rglob('*.a8s')
                   if file.is_file() and not file.name.lower().startswith('accountdata'))
    if not files:
        raise ValueError(f'Keine .a8s-Spielstände unter {accounts} gefunden.')

    def read(file):
        stat = file.stat()
        signature = [stat.st_size,stat.st_mtime_ns,stat.st_ino,stat.st_ctime_ns]
        relative = str(file.relative_to(accounts))
        cached = old.get(relative)
        if cached and 'campaign_id' in cached and cached['signature']==signature:
            return relative, cached
        try:
            row = read_save(file)
        except (KeyError,ValueError,OSError,IndexError,struct.error) as exc:
            raise ValueError(f'{file.name}: {exc}') from exc
        after = file.stat()
        if [after.st_size,after.st_mtime_ns,after.st_ino,after.st_ctime_ns]!=signature:
            raise ValueError(f'Der Save {file.name} wurde während der Auswertung geändert.')
        return relative, {**row,'signature':signature}

    with ThreadPoolExecutor(max_workers=6) as workers:
        return dict(workers.map(read,files))


def maps_for(file):
    _, data = next(members(file, {'data.a7s'}))
    guid = None
    generation = {}
    for key, raw in fields(data):
        if key[:2]!=('MetaGameManager','GameSessions'):
            continue
        if key[-2:]==('SessionDesc','SessionGUID'):
            guid = val(raw)
            generation = {}
        if 'MapGeneratorSettings' in key and key[-1] in ('mapSize','islandSize'):
            generation[key[-1]] = val(raw)
        if key[-2:]!=('SessionData','BinaryData'):
            continue
        region = {'guid':guid,'islands':[],'shift':(0,0),'generation':generation}
        island = None
        for tag, value in fields(bytes(raw)):
            if tag[:2]!=('GameSessionManager','MapTemplate'):
                continue
            if tag[2:]==('Size',):
                region['size'] = int_pair(value)
            elif tag[2:]==('IslandShift',):
                region['shift'] = int_pair(value)
            elif tag[2:]==('PlayableArea',):
                region['area'] = struct.unpack('<4i',value)
            elif tag[2:]==('Filename',):
                region['template'] = bytes(value).decode('utf-16le').rstrip('\0')
            elif tag[2:4]==('TemplateElement','Element'):
                if tag[-1]=='Position':
                    island = {'position':int_pair(value), 'rotation':0}
                    region['islands'].append(island)
                elif island is not None and tag[-1]=='MapFilePath':
                    island['file'] = bytes(value).decode('utf-16le').rstrip('\0').lower()
                elif island is not None and tag[-1]=='Rotation90':
                    island['rotation'] = val(value)
        region['islands'] = [island for island in region['islands'] if 'file' in island]
        if region['islands'] and 'size' in region:
            yield region


class Maps:
    def __init__(self, game, directory):
        self.directory = directory
        self.assets = {}
        for archive in sorted(game.glob('*.rda')):
            if 'provinces' not in archive.name and not archive.name.startswith('zz_patch'):
                continue
            for name, record in rda_index(archive):
                if name.endswith(('gamemapimage.png','gamemapimage_0.dds',
                                  '.a7minfo','combinedprovince_mapimage.png')) and record[-1]:
                    self.assets[name] = record
        if not self.assets:
            raise ValueError(f'Keine Kartengrafiken unter {game} gefunden.')

    @lru_cache(maxsize=160)
    def tile(self, island):
        from PIL import Image
        parent, _, name = island.rpartition('/')
        name = Path(name).stem
        key = f'{parent}/_gamedata/{name}/gamemapimage'
        for suffix in ('.png','_0.dds'):
            if key+suffix in self.assets:
                return Image.open(BytesIO(read_asset(self.assets[key+suffix]))).convert('RGBA')
        return None

    @lru_cache(maxsize=200)
    def bounds(self, island):
        asset = self.assets.get(island+'info')
        if asset is None:
            return None
        info = {key[-1]:value for key,value in fields(read_asset(asset))
                if key in (('MapSize',), ('ActiveMapRect',))}
        if 'MapSize' not in info or 'ActiveMapRect' not in info:
            return None
        return int_pair(info['MapSize']), struct.unpack('<4i',info['ActiveMapRect'])

    def render(self, region):
        from PIL import Image, ImageDraw, ImageFont
        guid = region['guid']
        label = REGIONS.get(guid, f'Provinz {guid}')
        image_data = {key:value for key,value in region.items() if key != 'generation'}
        name = f'{guid}-{sha256(("2"+json.dumps(image_data,sort_keys=True)).encode()).hexdigest()[:14]}.png'
        path = self.directory/name
        if path.exists():
            return {'path':'map-images/'+name,'label':label}
        size_x,size_y = region['size']
        if not (0 < size_x <= 15000 and 0 < size_y <= 15000):
            raise ValueError(f'Ungültige Kartengrösse für {label}: {region["size"]}')
        scale = 820/max(size_x,size_y)
        width,height = round(size_x*scale),round(size_y*scale)
        image = Image.new('RGBA',(width+48,height+104),'#14232a')
        draw = ImageDraw.Draw(image)
        draw.rectangle((24,56,width+23,height+55), fill='#214655')
        missing = 0
        layer = Image.new('RGBA',(width,height))
        layer_draw = ImageDraw.Draw(layer)
        if guid==149679:
            # Aegyptus has four terrain quadrants under the saved settlement areas.
            for x in range(2):
                for y in range(2):
                    name_part = f'egypt_island_quadrant_01_x{x}_y{y}'
                    path_part = f'data/dlc03/provinces/egypt/islands/pool/{name_part}/{name_part}.a7m'
                    tile = self.tile(path_part)
                    if tile:
                        side = round(960*scale)
                        layer.alpha_composite(tile.resize((side,side),Image.Resampling.LANCZOS),
                                              (round(x*960*scale),height-round((y+1)*960*scale)))
        shift_x,shift_y = region['shift']
        for island in region['islands']:
            file = island['file']
            x,y = island['position']
            rotation = island['rotation']%4
            tile,bounds = self.tile(file), self.bounds(file)
            if tile is None or bounds is None:
                missing += 1
                px = round((x+shift_x)*scale)
                py = height-round((y+shift_y)*scale)
                layer_draw.ellipse((px-4,py-4,px+4,py+4),outline='#ffd68d',width=2)
                continue
            (mw,mh),(x0,y0,x1,y1) = bounds
            # Save positions refer to the untrimmed island rectangle.
            crop_boxes = ((x0,y0,x1,y1),(mh-y1,x0,mh-y0,x1),
                          (mw-x1,mh-y1,mw-x0,mh-y0),(y0,mw-x1,y1,mw-x0))
            left,bottom,right,top = crop_boxes[rotation]
            tile = tile.rotate(90*rotation,expand=True)
            tile = tile.resize((max(1,round((right-left)*scale)),max(1,round((top-bottom)*scale))),
                               Image.Resampling.LANCZOS)
            layer.alpha_composite(tile,(round((x+shift_x+left)*scale),
                                        height-round((y+shift_y+top)*scale)))
        image.alpha_composite(layer,(24,56))
        detail = f'{len(region["islands"])} Kartenelemente'
        if missing:
            detail += f' · {missing} ohne Grafik'
        fonts = Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'
        draw.text((24,12),label,font=ImageFont.truetype(str(fonts/'segoeuib.ttf'),28),fill='#f5eddb')
        draw.text((24,height+70),f'{detail} · {size_x} × {size_y}',
                  font=ImageFont.truetype(str(fonts/'segoeui.ttf'),15),fill='#d5e1e2')
        image.convert('RGB').save(path)
        return {'path':'map-images/'+name,'label':label}


def clock(seconds):
    hours, minutes = divmod(seconds,3600)
    minutes, seconds = divmod(minutes,60)
    return f'{hours}:{minutes:02d}:{seconds:02d}'


def mode_for(setup):
    for key, label in (('EnableCampaign','Kampagne'),('EnableScenario','Szenario'),('CreativeMode','Kreativmodus')):
        if any(setup.get(key,[])):
            return label
    return 'Sandkasten'


def setting_value(key, values):
    if not values:
        return '—'
    labels = VALUE_NAMES.get(key)
    if labels is None:
        return ', '.join(map(str, values))
    return ', '.join(labels.get(value, f'ID {value}') for value in values)


def generated_size(geometry, key):
    sizes = {region['generation'][key] for region in geometry
             if region.get('generation', {}).get(key) is not None}
    if len(sizes) == 1:
        size = sizes.pop()
        return SIZES.get(size, f'ID {size}')
    return ', '.join(f"{REGIONS.get(region['guid'], region['guid'])}: {SIZES.get(size, f'ID {size}')}"
                     for region in geometry
                     if (size := region.get('generation', {}).get(key)) is not None) or '—'


def prepare(saves, accounts, map_writer, zone, cached_maps, statistics=None):
    groups = defaultdict(list)
    seed_bounds = defaultdict(list)
    for path, row in saves.items():
        setup = row['setup']
        settings = tuple((key,tuple(setup[key])) for key in sorted(MAP_KEYS & setup.keys()))
        groups[row['seed'],settings].append((path,row))
        seed_bounds[row['seed']].append(row['stamp'])
    results = []
    new_maps = {}
    def chronological(save):
        return save[1]['stamp'], save[0]
    for index, ((seed,_), rows) in enumerate(sorted(groups.items(),key=lambda entry:(entry[0][0],repr(entry[0][1]))),1):
        rows.sort(key=chronological)
        latest_name,latest = rows[-1]
        record_name,record = max(rows,key=lambda save:(save[1]['play'],chronological(save)))
        first,last = min(seed_bounds[seed]),max(seed_bounds[seed])
        stamps = (first,last,rows[0][1]['stamp'],latest['stamp'],record['stamp'])
        dates = [datetime.fromtimestamp(stamp,zone) for stamp in stamps]
        epoch = datetime(1899,12,30)
        serials = [(dt.replace(tzinfo=None)-epoch).total_seconds()/86400 for dt in dates]
        display = [dt.strftime('%d.%m.%Y %H:%M:%S') for dt in dates]
        newest_seconds, record_seconds = latest['play']//1000,record['play']//1000
        delta = record_seconds-newest_seconds if record['stamp']<latest['stamp'] else 0
        geometry = []
        source = latest_name
        for name, row in reversed(rows):
            old = cached_maps.get(name)
            if old and old.get('format')==2 and old['signature']==row['signature']:
                geometry = old['maps']
            else:
                geometry = list(maps_for(accounts/name))
            new_maps[name] = {'signature':row['signature'],'maps':geometry,'format':2}
            if geometry:
                source = name
                break
        links = [map_writer.render(region) for region in geometry]
        profiles = Counter(str(Path(name).parent) for name,_ in rows)
        profiles = '\n'.join(f'{name} ({n})' for name,n in sorted(profiles.items()))
        settings = [setting_value(key,latest['setup'].get(key,[])) for key in GEO_SETTINGS]
        settings[1] = generated_size(geometry, 'mapSize')
        settings[2] = generated_size(geometry, 'islandSize')
        start = [*serials[:4],newest_seconds/86400,record_seconds/86400,serials[4],record_name]
        details = [*display[:4],clock(newest_seconds),clock(record_seconds),display[4],record_name]
        results.append(dict(identity=[seed,index,mode_for(latest['setup'])],links=links,
                            settings=[len(rows),profiles,*settings,source,*start],delta=delta,
                            fields=[*settings,*details],raw=latest['setup'],sizes=[
                                (link['label'],*region['size']) for link,region in zip(links,geometry,strict=True)],
                            sort={'first':stamps[2],'latest':stamps[3],'recordDate':stamps[4],
                                  'latestTime':newest_seconds,'recordTime':record_seconds},
                            profiles=profiles,source=source,
                            profile_names=sorted({profile_name('Spielkonto', name) for name,_ in rows}),
                            statistics=[statistics[key] for key in sorted({f"{r['seed']}:{r['campaign_id']}" for _, r in rows})
                                        if statistics and key in statistics]))
    return results,new_maps


def write_html(rows, total, stage, updated_at, total_playtime, profiles):
    cards = []
    for row in rows:
        seed,index,mode = row['identity']
        data = {'seed':seed,'variant':index,'mode':mode,'first':row['sort']['first'],
                'latest':row['sort']['latest'],'record-date':row['sort']['recordDate'],
                'latest-time':row['sort']['latestTime'],'record-time':row['sort']['recordTime'],
                'profiles':json.dumps(row['profile_names'], ensure_ascii=False)}
        attrs = ' '.join(f'data-{key}="{escape(str(value),quote=True)}"' for key,value in data.items())
        cards.append(f'<article {attrs}><h2>Seed {seed} · Variante {index:03d}</h2>'
                     f'<p>{mode}</p>')
        if not row.get('statistics'):
            cards.append(f'<p class="profiles">{escape(row["profiles"]).replace(chr(10),"<br>")}</p>')
        cards.append(render_statistics(row.get('statistics', [])))
        cards.append('<details class="save-details"><summary>' + summary_label('stats.saveDetails') + '</summary>')
        cards.append(statistics_sources(row.get('statistics', [])))
        cards.append(f'<p>{row["settings"][0]} Saves</p>')
        if row['delta']:
            cards.append(f'<p class="marker">Älterer Save: +{clock(row["delta"])} mehr Spielzeit</p>')
        cards.append('<dl>')
        for field_label,value in zip(TIME_COLUMNS,row['fields'][len(SETTINGS):],strict=True):
            cards.append(f'<div><dt>{escape(field_label)}</dt><dd>{escape(value)}</dd></div>')
        cards.append(f'</dl><p>Kartenstand: {escape(row["source"])}</p></details><div class="maps">')
        for link in row['links']:
            path,label = escape(link['path']),escape(link['label'])
            cards.append(f'<figure><a href="{path}"><img src="{path}" loading="lazy" alt="{label}"></a>'
                         f'<figcaption>{label}</figcaption></figure>')
        cards.append('</div><details><summary>' + summary_label('stats.settings') + '</summary><dl>')
        for field_label,value in zip(SETTINGS,row['fields'][:len(SETTINGS)],strict=True):
            cards.append(f'<div><dt>{escape(field_label)}</dt><dd>{escape(value)}</dd></div>')
        for field_label,x,y in row['sizes']:
            cards.append(f'<div><dt>{escape(field_label)} · Kartengrösse</dt><dd>{x} × {y}</dd></div>')
        for key,values in sorted(row['raw'].items()):
            field_label = DETAIL_LABELS.get(key, GEO_SETTINGS.get(key, key))
            value = setting_value(key, values)
            if key in ('SetupStartSession', 'SetupStartSessionIslandSize'):
                # Setup values can be defaults. The visible sizes above come from the generated region.
                field_label += ' (gespeicherter Setup-Wert)'
            cards.append(f'<div><dt>{escape(field_label)}</dt><dd>{escape(value)}</dd></div>')
        cards.append('</dl></details></article>')
    template=(HERE/'map_gallery_template.html').read_text(encoding='utf8')
    template = template.replace('@@UPDATED_ISO@@', updated_at.isoformat(timespec='minutes'))
    template = template.replace('@@UPDATED_AT@@', updated_at.strftime('%d.%m.%Y %H:%M'))
    template = template.replace('@@TOTAL_PLAYTIME@@', total_playtime)
    template = template.replace('@@PROFILE_CSS@@', RANKING_CSS)
    template = template.replace('@@PROFILE_RANKING@@', ranking_html(profiles, clock))
    template=template.replace('@@CARDS@@',''.join(cards)).replace('@@SUMMARY@@',
        f'{len({row["identity"][0] for row in rows})} Seeds · {len(rows)} Kartenvarianten · {total} Spielstände')
    (stage/'map-gallery.html').write_text(render_gallery(template, 'anno117', 'map'),encoding='utf8')


def publish(stage, output):
    pairs=[(stage/name,output/name) for name in
           ('anno117-map-seeds.xlsx','map-gallery.html','anno117-scan.json','anno117-maps.json','anno117-statistics.json')]
    old = {}
    for i,(_, target) in enumerate(pairs):
        if target.is_file():
            backup=stage/f'backup-{i}'
            backup.write_bytes(target.read_bytes())
            old[target]=backup
    images=output/'map-images'
    images.mkdir(exist_ok=True)
    for source in (stage/'map-images').glob('*.png'):
        os.replace(source,images/source.name)
    completed=[]
    try:
        for source,target in pairs:
            os.replace(source,target)
            completed.append(target)
    except OSError:
        for target in reversed(completed):
            if target in old:
                os.replace(old[target],target)
            else:
                target.unlink()
        raise


def main():
    import msvcrt
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--account',type=Path,default=ACCOUNT,help='Ordner accounts oder einzelnes Spielkonto')
    parser.add_argument('--game-data',type=Path,default=GAME,help='maindata der Spielinstallation')
    parser.add_argument('--output',type=Path,default=CONFIG.report_output)
    parser.add_argument('--rescan',action='store_true')
    args=parser.parse_args()
    from zoneinfo import ZoneInfo
    from anno_excel_export import write_workbook
    CONFIG.validate('analyze')
    protect_output(args.output, CONFIG.all_sources()+[args.account,args.game_data])
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    account=args.account.resolve()
    with (output/'.anno117-analysis.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        saves=scan(account,output/'anno117-scan.json',args.rescan)
        cache=output/'anno117-maps.json'
        maps=json.loads(cache.read_text(encoding='utf8')) if cache.is_file() and not args.rescan else {}
        with TemporaryDirectory(prefix='.anno117-',dir=output) as temp:
            stage=Path(temp)
            cards=stage/'map-images'
            cards.mkdir()
            zone = ZoneInfo(CONFIG.zone)
            statistics, statistics_cache = collect_statistics(
                [dict(campaign=f"{row['seed']}:{row['campaign_id']}", path=account/name,
                      source=name, profile=profile_name('Spielkonto', name), seed=row['seed'], stamp=row['stamp'])
                 for name, row in saves.items()], FileDBStatistics('anno117', args.game_data),
                output/'anno117-statistics.json', zone, args.rescan)
            rows,new_maps=prepare(saves,account,Maps(args.game_data,cards),zone,maps,statistics)
            (stage/'anno117-statistics.json').write_text(json.dumps(statistics_cache,ensure_ascii=False),encoding='utf-8')
            updated_at = datetime.now(zone)
            profiles = profile_playtime(
                (row['seed'], row, 'Spielkonto', path, row['play'], row['active'])
                for path, row in saves.items()
            )
            total_playtime = clock(sum(ms for _, _, ms in profiles) // 1000)
            write_html(rows,len(saves),stage,updated_at,total_playtime,profiles)
            report='anno117-map-seeds.xlsx'
            write_workbook(rows,SETTINGS,TIME_COLUMNS,CONFIG.zone,stage,output/report,output,updated_at, None, total_playtime, profiles)
            (stage/'report.xlsx').rename(stage/report)
            for name,data in (('anno117-scan.json',saves),('anno117-maps.json',new_maps)):
                (stage/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
            publish(stage,output)
    print(f'{len(saves)} Spielstände, {len(rows)} Kartenvarianten.')
    print(f'Excel und HTML: {output}')


if __name__=='__main__':
    try:
        main()
    except (OSError,ValueError,ImportError,KeyError) as exc:
        sys.exit(f'Aktualisierung abgebrochen: {exc}')
