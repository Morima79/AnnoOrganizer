'Read the stamp library and export blueprint PNGs and a local gallery.'
from pathlib import Path
import sys
from anno_settings import settings_for, protect_output
from anno_gallery import render_gallery
CONFIG = None

import base64,zlib,struct as st,json,math,hashlib,collections,html,re,datetime
from urllib.parse import quote
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
from anno_file_formats import rda_index,read_asset
from anno_stamp_requirements import requirements,asset_cdlc_sources

HERE=Path(__file__).resolve().parent
ROOT = None
REGIONS={3225:'Latium',6626:'Albion',149678:'Aegyptus'}
GAME = None
LIB = None
OUT = None
CACHE = None
RENDER_VERSION=2

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def archive_obsolete(previous,current):
    """Move only formerly generated files; never touch the game library."""
    live={e[key] for e in current for key in ('png','thumb')}
    old={e[key] for e in previous for key in ('png','thumb')}
    archive=(CONFIG.stamp_output)/'backups'/'gallery'/datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S-%f')
    count=0
    for relative in old-live:
        source=((CONFIG.stamp_output)/relative).resolve()
        if not source.is_relative_to(OUT.resolve()) or not source.is_file():continue
        destination=(archive/source.relative_to(OUT.resolve())).resolve()
        assert destination.is_relative_to(((CONFIG.stamp_output)/'backups'/'gallery').resolve())
        destination.parent.mkdir(parents=True,exist_ok=True)
        source.rename(destination);count+=1
    return count

def records(raw):
    _,tags,attrs,_,magic=st.unpack_from('<5I',raw,len(raw)-20)
    assert magic in (0xfffffffd,0xfffffffe)
    names={1:'[]',0x8000:'[]'}
    for off in (tags,attrs):
        n,=st.unpack_from('<I',raw,off);ids=st.unpack_from(f'<{n}H',raw,off+4);p=off+4+2*n
        for code in ids:
            end=raw.index(0,p);names[code]=raw[p:end].decode();p=end+1
    p=0;stack=[]
    while p<tags:
        size,code=st.unpack_from('<IH',raw,p);p+=8
        if code==0:
            if not stack:break
            stack.pop()
        elif code&0x8000:
            yield tuple(stack+[names[code]]),raw[p:p+size]
            p+=(size+7)&~7
        else:stack.append(names[code])

def decode(stamp):
    blob=base64.b64decode(stamp['PipetteData'],validate=True)
    dec=zlib.decompressobj();raw=dec.decompress(blob)
    assert dec.eof and dec.unused_data==bytes.fromhex('78da030000000001')+st.pack('<I',len(raw))
    result={'buildings':[],'polygons':[],'edges':[]}
    b=p=e=None
    for key,v in records(raw):
        if key[:3]==('PipetteData','BuildingInfo','[]'):
            if key[-1]=='Pos':b={'pos':st.unpack('<ff',v),'dir':0};result['buildings'].append(b)
            elif key[-1]=='GUID':b['guid']=int.from_bytes(v,'little')
            elif 'Dir' in key:b['dir']=int.from_bytes(v,'little')
            elif key[-1]=='ComplexOwnerID':b['owner']=int.from_bytes(v,'little')
            elif key[-1]=='Skin':b['skin']=int.from_bytes(v,'little')
        elif key[:3]==('PipetteData','Polygons','[]'):
            if key[-1]=='GUID':p={'guid':int.from_bytes(v,'little')};result['polygons'].append(p)
            elif key[-1] in ['x','y']:p[key[-1]]=int.from_bytes(v,'little')
            elif key[-1]=='bits':p['bits']=v
            elif key[-1]=='RelativePos':p['pos']=st.unpack('<ff',v)
            elif key[-1]=='ComplexOwnerID':p['owner']=int.from_bytes(v,'little')
        elif key[:5]==('PipetteData','MeshGraphData','Edges','Edges','[]'):
            if key[-1]=='guid':e={'guid':int.from_bytes(v,'little')};result['edges'].append(e)
            elif key[-1] in ['PosMin','PosMax']:e[key[-1]]=st.unpack('<ii',v)
        elif key==('PipetteData','DragRectCenter'):result['centre']=st.unpack('<ff',v)
    for p in result['polygons']:
        assert p['x']%4==0
        stride=((p['x']+31)//32)*4;assert len(p['bits'])==stride*p['y']
        p['cells']={}
        for y in range(p['y']):
            for x in range(p['x']//4):
                nib=(p['bits'][y*stride+x//2]>>(4*(x%2)))&15
                if nib:p['cells'][(p['pos'][0]+x,p['pos'][1]+y)]=nib
        p.pop('bits')
    for e in result['edges']:
        for key in ['PosMin','PosMax']:
            e[key]=(e[key][0]/2-result['centre'][0],e[key][1]/2-result['centre'][1])
    return result

def safe(s):
    s=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',s).rstrip(' .')
    assert s and s not in ['.','..']
    return s

def configure(settings):
    """Bind one explicit configuration within this game worker process."""
    global CONFIG, ROOT, GAME, LIB, OUT, CACHE
    if settings.game != 'anno117':
        raise ValueError('Die Einstellungsdatei gehört nicht zu anno117.')
    settings.validate('stamps')
    CONFIG = settings
    ROOT = settings.output
    GAME = settings.path('game_data')
    LIB = settings.path('stamps')
    OUT = settings.stamp_output / 'library'
    CACHE = settings.report_output / 'stamp-gallery'


def run(settings, *, rescan=False):
    """Generate outputs from explicit settings without parsing process arguments."""
    if rescan:
        raise ValueError('--rescan gilt für die Spielstandauswertung.')
    main(settings=settings)
    return settings.stamp_output / 'stamp-gallery.html'


def main(*, settings=None):
    configure(settings if settings is not None else settings_for('anno117'))
    CONFIG.validate('stamps')
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    inventoryfile=CACHE/'inventory.json'
    previous=json.loads(inventoryfile.read_text(encoding='utf-8')) if inventoryfile.exists() else []
    previous_by_path={e['png']:e for e in previous}
    # Store the generator version as part of every render fingerprint.
    generator=digest(Path(__file__))
    snapshot={p:p.read_bytes() for p in LIB.rglob('*') if p.is_file()}
    entries=[]
    for path,data in sorted(snapshot.items()):
        if path.suffix.lower()!='.json':continue
        content=json.loads(data.decode('utf-8-sig'))
        for s in content['Stamps']:
            if not s.get('PipetteData'):continue
            region=REGIONS[s['RegionGUID']]
            entries.append({'name':s['Name'],'folder':s.get('FolderName',''),'region':region,'source':str(path.relative_to(LIB)),'stamp_hash':hashlib.sha256(json.dumps(s,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'data':decode(s)})
    print(f'{len(entries)} Stempel gelesen.',flush=True)
    assetsfile=CACHE/'assets.xml';textsfile=CACHE/'texts_german.xml';templatesfile=CACHE/'templates.xml'
    if not assetsfile.exists() or not textsfile.exists() or not templatesfile.exists():
        for name,rec in rda_index(GAME/'config.rda'):
            if name.endswith('/assets.xml') or name.endswith('/texts_german.xml') or name.endswith('/templates.xml'):(CACHE/Path(name).name).write_bytes(read_asset(rec))
    asset_tree=ET.parse(assetsfile)
    cdlc_sources=asset_cdlc_sources(asset_tree.getroot())
    assets={int(a.findtext('Values/Standard/GUID')):a for a in asset_tree.findall('.//Asset') if a.findtext('Values/Standard/GUID')}
    texts={t.findtext('LineId'):t.findtext('Text') for t in ET.parse(textsfile).findall('./Texts/Text')}
    templates={t.findtext('Name'):t for t in ET.parse(templatesfile).findall('.//Template') if t.findtext('Name')}
    for entry in entries:entry['requirements']=requirements(entry['data'],assets,texts,templates,cdlc_sources)
    needed={b['guid'] for e in entries for b in e['data']['buildings']}
    shapes={};wanted={};unknown=[]
    for g in needed:
        a=assets.get(g)
        if a is None:unknown.append(g);continue
        filenames=[v.text for v in a.findall('Values/Object/Variations/Item/Filename') if v.text]
        if not filenames:
            preview=a.findtext('Values/MeshGraphStyle/PerSkinConfig/Item/FilePath1x1Preview')
            if preview:filenames=[preview]
        if filenames:wanted[filenames[0][:-4]+'.ifo']=g
        else:unknown.append(g)
    # Blockers are cached as compact JSON so subsequent gallery refreshes are fast.
    cachefile=CACHE/'footprints.json'
    old=json.loads(cachefile.read_text(encoding='utf-8')) if cachefile.exists() else {}
    signature=[(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in sorted(GAME.glob('*.rda'))]
    if old.get('signature')==[list(v) for v in signature]:shapes={int(k):v for k,v in old.get('shapes',{}).items() if int(k) in needed}
    missing=needed-set(shapes)
    if missing:
        archives=['graphics_roman.rda','graphics_celtic.rda','graphics_roman_celtic.rda','shared_configs.rda','graphics_library.rda','graphics_skins.rda','cdlc01_graphics.rda','cdlc02_graphics.rda','cdlc03_graphics.rda','dlc03_graphics_01.rda','dlc03_graphics_02.rda','dlc01_graphics.rda','dlc02_graphics.rda']+[p.name for p in sorted(GAME.glob('zz_patchfiles*.rda'))]
        for filename in archives:
            if not (GAME/filename).is_file():continue
            for name,rec in rda_index(GAME/filename):
                key=name.replace('shared/','data/',1)
                if key in wanted and wanted[key] in missing:
                    g=wanted[key];info=ET.fromstring(read_asset(rec))
                    points=[(float(v.findtext('xf','0')),float(v.findtext('zf','0'))) for v in info.findall('BuildBlocker/Position')]
                    if not points and assets[g].findtext('Template')=='Hedge' and assets[g].findtext('Values/MeshGraphStyle/PerSkinConfig/Item/FilePath1x1Preview'):
                        # Meshgraph endpoints have a declared 1x1 preview, not a building blocker.
                        points=[(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]
                    if points:shapes[g]=points;missing.remove(g)
            if not missing:break
    assert not missing,('Keine Grundflaeche gefunden',sorted(missing))
    cachefile.write_text(json.dumps({'signature':signature,'shapes':shapes}),encoding='utf-8')
    print(f'{len(shapes)} Gebaeudegrundflaechen geladen.',flush=True)
    for entry in entries:
        for b in entry['data']['buildings']:
            angle=b['dir']*math.pi/4;c=math.cos(angle);s=math.sin(angle)
            b['points']=[(b['pos'][0]+x*c-y*s,b['pos'][1]+x*s+y*c) for x,y in shapes[b['guid']]]
    reference=next((e for e in entries if e['name']=='Lavendel ohne CDLC'),None)
    if reference is None:
        saved_reference=(CONFIG.stamp_output)/'references'/'Lavendel ohne CDLC.json'
        if saved_reference.exists():
            stamp=json.loads(saved_reference.read_text(encoding='utf-8-sig'))['Stamps'][0]
            reference={'data':decode(stamp),'stamp_hash':hashlib.sha256(json.dumps(stamp,sort_keys=True).encode()).hexdigest()}
    reserve_count=0
    for e in entries:
        e['data']['reserve']=set()
        if e['name']=='Lavendel ohne Ceres' and reference:
            crops={2220,2732,2744,2743,31751}
            current={(p['guid'],p['owner']):p for p in e['data']['polygons'] if p['guid'] in crops}
            for p in reference['data']['polygons']:
                if p['guid'] not in crops:continue
                q=current.get((p['guid'],p['owner']))
                if q is None:continue
                e['data']['reserve'].update(p['cells'].keys()-q['cells'].keys())
            reserve_count=len(e['data']['reserve'])
    manifest=[];paths=set();thumbdir=OUT/'_thumbnails';thumbdir.mkdir(exist_ok=True)
    rendered=0;reused=0
    for i,entry in enumerate(entries):
        sub=OUT/entry['region']
        if entry['folder']:sub=sub/safe(entry['folder'])
        sub.mkdir(parents=True,exist_ok=True)
        path=sub/(safe(entry['name'])+'.png')
        assert path not in paths,('Namenskonflikt',str(path))
        paths.add(path)
        relative=path.relative_to((CONFIG.stamp_output)).as_posix()
        fingerprint=hashlib.sha256(json.dumps({'stamp':entry['stamp_hash'],'game':signature,'renderer':generator,'version':RENDER_VERSION,'reserve':sorted(entry['data']['reserve'])},sort_keys=True).encode()).hexdigest()
        oldentry=previous_by_path.get(relative)
        if oldentry and oldentry.get('fingerprint')==fingerprint and path.is_file() and oldentry.get('png_hash')==digest(path):
            metadata={k:oldentry[k] for k in ['width','height','buildings','reserve']};reused+=1
        else:
            metadata=render(entry,path,assets,texts);rendered+=1
        thumbnail=thumbdir/f'{i:03d}.jpg'
        if not (oldentry and oldentry.get('fingerprint')==fingerprint and oldentry.get('thumb')==thumbnail.relative_to((CONFIG.stamp_output)).as_posix() and thumbnail.is_file() and oldentry.get('thumb_hash')==digest(thumbnail)):
            with Image.open(path) as im:
                im.thumbnail((640,500));im.convert('RGB').save(thumbnail,quality=86)
        manifest.append({k:entry[k] for k in ['name','region','folder','source','requirements']}|metadata|{'png':relative,'thumb':thumbnail.relative_to((CONFIG.stamp_output)).as_posix(),'fingerprint':fingerprint,'png_hash':digest(path),'thumb_hash':digest(thumbnail)})
    assert all(p.read_bytes()==b for p,b in snapshot.items()),'Bibliothek wurde waehrend der Erstellung geaendert.'
    assert {p for p in LIB.rglob('*') if p.is_file()}==set(snapshot)
    archived=archive_obsolete(previous,manifest)
    write_gallery(manifest)
    inventoryfile.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    for p in paths:
        with Image.open(p) as im:im.verify()
    print(json.dumps({'stamps':len(entries),'rendered':rendered,'reused':reused,'archived_files':archived,'regions':dict(collections.Counter(e['region'] for e in entries)),'reserve_tiles':reserve_count,'gallery':str((CONFIG.stamp_output)/'stamp-gallery.html'),'library_unchanged':True},ensure_ascii=True),flush=True)
    # The compact blocker cache and manifest are sufficient for inspection.
    assetsfile.unlink();textsfile.unlink();templatesfile.unlink()

def render(entry,path,assets,texts):
    data=entry['data'];buildings=data['buildings'];polys=data['polygons'];edges=data['edges'];reserve=data['reserve']
    points=[pt for b in buildings for pt in b['points']]
    for p in polys:
        for x,y in p['cells']:points.extend([(x,y),(x+1,y+1)])
    for x,y in reserve:points.extend([(x,y),(x+1,y+1)])
    for e in edges:points.extend([e['PosMin'],e['PosMax']])
    assert points,entry['name']
    xmin=math.floor(min(x for x,y in points)-1);xmax=math.ceil(max(x for x,y in points)+1)
    ymin=math.floor(min(y for x,y in points)-1);ymax=math.ceil(max(y for x,y in points)+1)
    w,h=xmax-xmin,ymax-ymin
    scale=min(22,2700/max(w,h));margin=32;header=100;sidebar=410
    types=collections.Counter(b['guid'] for b in buildings)
    def label(g):return texts.get(assets[g].findtext('Values/Text/OasisId')) or assets[g].findtext('Values/Standard/Name') or str(g)
    order=sorted(types,key=lambda g:(assets[g].findtext('Template')=='OrnamentalBuilding',label(g)))
    legend={g:i+1 for i,g in enumerate(order)}
    image=Image.new('RGB',(max(1050,int(w*scale)+margin*2+sidebar),max(700,int(h*scale)+header+80,(len(order)+len({p['guid'] for p in polys}))*24+header+220)),'#f1eee4')
    draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27)
    def xy(x,y):return margin+(x-xmin)*scale,header+(ymax-y)*scale
    def box(x,y,ww,hh,color):
        a,b=xy(x,y+hh);c,d=xy(x+ww,y);draw.rectangle((a,b,c,d),fill=color)
    # Colour by land use and product, with a per-plan legend.
    known={31751:'#70aa7a',31763:'#70aa7a',2743:'#527b57',2220:'#ddd18a',2732:'#e7bb62',2744:'#ad83cf',82636:'#b5c78b',81091:'#b9b9ae',158418:'#345d37',144930:'#cbb28a',152343:'#c99ee6',152345:'#e3cfdb'}
    palette=['#b2c583','#c7b58c','#8daaaa','#bc9a9a','#8fb293','#c2ba80','#b49ec1']
    for p in polys:
        g=p['guid'];color=known.get(g,palette[g%len(palette)])
        for (x,y),nib in p['cells'].items():
            if nib==15:box(x,y,1,1,color)
            else:
                for bit in range(4):
                    if nib&(1<<bit):box(x+(bit%2)/2,y+(bit//2)/2,.5,.5,color)
    for x,y in reserve:
        box(x,y,1,1,'#ffda8c');a,b=xy(x,y);c,d=xy(x+1,y+1)
        draw.line((a,b,c,d),fill='#b07820',width=1)
    for e in edges:
        a=assets.get(e['guid']);typ=a.findtext('Template','') if a is not None else ''
        name=label(e['guid']) if a is not None else ''
        road=typ=='Street'
        color=('#bdab91' if 'stein' in name.lower() or 'pflaster' in name.lower() else '#cfb68f') if road else ('#35603b' if typ=='Hedge' else '#799fac')
        draw.line((*xy(*e['PosMin']),*xy(*e['PosMax'])),fill=color,width=max(1,round(scale if road else scale*.22)))
    def bcolor(g):
        a=assets[g];typ=a.findtext('Template','');n=a.findtext('Values/Standard/Name','')
        if typ in ['OrnamentalBuilding','Hedge']:return '#4d773f'
        if 'Module' in typ:return '#c5b995'
        if 'Residence' in typ:return '#d6c99c'
        if any(k in typ for k in ['Institution','PublicService','Warehouse','GuestHouse','Governor'] ) or 'Warehouse' in n:return '#8aa8ba'
        return '#b47d59'
    for b in buildings:
        g=b['guid'];shape=[xy(*p) for p in b['points']];draw.polygon(shape,fill=bcolor(g),outline='#494b3b')
        if assets[g].findtext('Template') in ['OrnamentalBuilding','Hedge']:continue
        width=(max(x for x,y in b['points'])-min(x for x,y in b['points']))*scale
        height=(max(y for x,y in b['points'])-min(y for x,y in b['points']))*scale
        if width<12 or height<11:continue
        text=label(g);bbox=draw.textbbox((0,0),text,font=small)
        if bbox[2]+6>width:text=str(legend[g])
        bbox=draw.textbbox((0,0),text,font=small);x,y=xy(*b['pos'])
        draw.text((x-bbox[2]/2,y-7),text,font=small,fill='#161f21')
    draw.text((margin,15),entry['name'],font=title,fill='#24382d')
    folder=entry['folder'] or 'Direkt in der Region'
    draw.text((margin,53),f"{entry['region']} / {folder}  |  ca. {w-2} x {h-2} Kacheln  |  {len(buildings)} Gebaeude/Module",font=font,fill='#4e5c52')
    lx=int(w*scale)+margin*2+15;ly=header
    draw.text((lx,ly),'Gebaeude und Module',font=font,fill='#24382d');ly+=32
    for g in order:
        draw.rectangle((lx,ly+3,lx+12,ly+15),fill=bcolor(g))
        text=f'{legend[g]:02d}  {label(g)}  ({types[g]}x)'
        while draw.textlength(text,font=small)>sidebar-45:text=text[:-5]+'...'
        draw.text((lx+20,ly),text,font=small,fill='#24382d');ly+=23
    ly+=20;draw.text((lx,ly),'Flaechen und Verbindungen',font=font,fill='#24382d');ly+=30
    for g in sorted({p['guid'] for p in polys},key=label):
        color=known.get(g,palette[g%len(palette)]);draw.rectangle((lx,ly+3,lx+12,ly+15),fill=color)
        text=label(g)
        while draw.textlength(text,font=small)>sidebar-55:text=text[:-5]+'...'
        draw.text((lx+20,ly),text,font=small,fill='#24382d');ly+=23
    if reserve:
        draw.rectangle((lx,ly+3,lx+12,ly+15),fill='#ffda8c');draw.text((lx+20,ly),f'Ausbaureserve: {len(reserve)} Kacheln',font=small,fill='#674619');ly+=24
        draw.text((lx,ly),'Schraffiert = gegenueber Ceres freigelassen',font=small,fill='#674619');ly+=22
    draw.text((margin,image.height-43),'Massstaeblicher Grundriss aus der Stempeldatei; Farben sind schematisch. Keine Spielansicht.',font=small,fill='#627064')
    # Recompute canvas height when a long list of field types extends the sidebar.
    if ly>image.height-60:
        enlarged=Image.new('RGB',(image.width,ly+80),'#f1eee4');enlarged.paste(image,(0,0));image=enlarged
    image.save(path)
    return {'width':w-2,'height':h-2,'buildings':len(buildings),'reserve':len(reserve)}

def write_gallery(entries):
    cards=[]
    for i,e in enumerate(entries):
        esc=html.escape;png=quote(e['png'],safe='/');thumb=quote(e['thumb'],safe='/')
        req=e['requirements'];packs=' '.join(p['id'] for p in req['cdlc_packs'])
        cereslabel={'yes':'Ceres-Feldgrössen','no':'Normale Feldgrössen','unknown':'Ceres: prüfen'}[req['ceres']]
        cdlclabel={'yes':'CDLC: '+', '.join(p['name'] for p in req['cdlc_packs']),'no':'Keine CDLC','unknown':'CDLC: prüfen'}[req['cdlc']]
        badges=f'<div class="badges"><span class="badge {req["ceres"]}">{esc(cereslabel)}</span><span class="badge {req["cdlc"]}">{esc(cdlclabel)}</span></div>'
        details=req['ceres_details']+req['cdlc_details']
        info=('<details><summary>Voraussetzungen im Detail</summary><ul>'+''.join('<li>'+esc(d)+'</li>' for d in dict.fromkeys(details))+'</ul></details>') if details else ''
        search=esc((e['name']+' '+e['region']+' '+e['folder']+' '+cereslabel+' '+cdlclabel).casefold(),quote=True)
        cards.append(f'''<article class="card" data-region="{esc(e['region'])}" data-folder="{esc(e['folder'],quote=True)}" data-ceres="{req['ceres']}" data-cdlc="{req['cdlc']}" data-packs="{packs}" data-search="{search}">
<button class="preview" data-full="{png}" data-name="{esc(e['name'],quote=True)}" aria-label="Bauplan {esc(e['name'],quote=True)} öffnen"><img src="{thumb}" loading="lazy" alt="Bauplan {esc(e['name'],quote=True)}"></button>
<div class="body"><p class="crumb">{esc(e['region'])} / {esc(e['folder'] or 'Direkt in der Region')}</p><h2>{esc(e['name'])}</h2>{badges}<p>{e['width']} × {e['height']} Kacheln · {e['buildings']} Gebäude/Module</p>{f'<p class="reserve">{e["reserve"]} Kacheln Ausbaureserve markiert</p>' if e['reserve'] else ''}{info}<a href="{png}" download="{esc(e['name'],quote=True)}.png">PNG herunterladen ↗</a></div></article>''')
    payload=json.dumps([{'region':e['region'],'folder':e['folder']} for e in entries],ensure_ascii=False).replace('<','\\u003c')
    pack_options=''.join(f'<option value="{html.escape(p["id"])}">{html.escape(p["name"])}</option>' for p in sorted({p['id']:p for e in entries for p in e['requirements']['cdlc_packs']}.values(),key=lambda p:p['name']))
    content='''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Anno 117 · Stempelbibliothek</title>
<style>
:root{color-scheme:light;--ink:#203b30;--muted:#647467;--paper:#f5f1e7;--accent:#a27336}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px system-ui,sans-serif}header{padding:48px max(24px,5vw) 30px;background:#203b30;color:#faf7ee}header p{max-width:850px;color:#c7d4c8;line-height:1.7}header .eyebrow{text-transform:uppercase;letter-spacing:.18em;font-size:12px;color:#dfc79d}h1{font:clamp(30px,4vw,54px) Georgia,serif;margin:12px 0}main{padding:26px max(24px,5vw) 60px}.controls{display:grid;grid-template-columns:2fr 1fr 1.4fr 1.3fr 1.4fr;gap:14px;margin-bottom:16px}label{font-size:12px;text-transform:uppercase;letter-spacing:.08em}input,select{display:block;width:100%;margin-top:7px;border:1px solid #c8cebf;border-radius:8px;padding:12px;background:#fffef9;color:var(--ink);font:15px system-ui}#count{color:var(--muted);margin-bottom:24px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(295px,1fr));gap:22px}.card{border:1px solid #d6d8cb;background:#fffef8;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px #203b3006}.preview{width:100%;height:255px;padding:10px;border:0;background:#e9e8dc;cursor:zoom-in}.preview img{width:100%;height:100%;object-fit:contain}.body{padding:20px}.crumb{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}h2{font:23px Georgia,serif;margin:10px 0 14px}.body p{font-size:13px;color:var(--muted)}a{color:#7c571e;font-size:13px;text-decoration:none;border-bottom:1px solid #d0b487;padding-bottom:2px}.reserve{color:#8b651e!important}.badges{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.badge{border-radius:6px;padding:5px 8px;font-size:11px;line-height:1.5;background:#edf0e6;color:#405743}.badge.yes{background:#f2e2c1;color:#795217}.badge.unknown{background:#f3d9cb;color:#8a3e28}details{margin:14px 0;font-size:12px;color:#58684e}summary{cursor:pointer}details li{margin:6px 0;line-height:1.5}article[hidden]{display:none}.note{border-left:3px solid #bd904b;padding-left:16px;line-height:1.7;color:var(--muted);font-size:14px;margin:0 0 28px}dialog{max-width:96vw;width:96vw;height:94vh;border:0;border-radius:12px;padding:0;background:#faf7ef}dialog::backdrop{background:#102219dc}.modalbar{display:flex;align-items:center;gap:20px;padding:12px 20px;border-bottom:1px solid #ccd2c4}.modalbar strong{flex:1}.modalbar button{padding:8px 14px;border:1px solid #aab9a7;background:#fffdf5;border-radius:6px;cursor:pointer}.canvas{height:calc(94vh - 65px);overflow:auto;text-align:center;padding:16px}.canvas img{max-width:100%;max-height:100%;object-fit:contain;cursor:zoom-in}.canvas img.zoomed{max-width:none;max-height:none;cursor:zoom-out}footer{margin-top:40px;font-size:12px;color:var(--muted)}@media(max-width:700px){header{padding-top:30px}.controls{grid-template-columns:1fr}.preview{height:230px}.modalbar{flex-wrap:wrap}}
</style><header><div class="eyebrow">Anno 117 · Persönliche Bibliothek</div><h1>Deine Baupläne, an einem Ort.</h1><p>Alle Stempel aus deiner aktuellen Spielbibliothek. Nach Regionen und Spielordnern gegliedert, mit massstäblichen Grundrissen und PNGs zum Herunterladen.</p></header><main>
<div class="controls"><label>Stempel suchen<input id="search" type="search" placeholder="Name, Produktion oder Stadt …"></label><label>Region<select id="region"><option value="">Alle Regionen</option><option>Latium</option><option>Albion</option><option>Aegyptus</option></select></label><label>Stempelordner<select id="folder"><option value="">Alle Ordner</option></select></label><label>Ceres<select id="ceres"><option value="">Alle Feldgrössen</option><option value="no">Normale Feldgrössen</option><option value="yes">Ceres-Feldgrössen</option><option value="unknown">Unklar / prüfen</option></select></label><label>Kosmetische DLCs<select id="cdlc"><option value="">Alle Voraussetzungen</option><option value="no">Ohne CDLC</option><option value="yes">Mit CDLC</option><option value="unknown">Unklar / prüfen</option>__PACK_OPTIONEN__</select></label></div>
<p id="count" role="status"></p><p class="note">Bei <strong>Lavendel ohne Ceres</strong> markieren gelb schraffierte Flächen die gegenüber der Ceres-Fassung freien Ausbaukacheln. Ein Klick auf einen Plan öffnet die Grossansicht; dort lässt sich durch Klick auf das Bild die Originalgrösse anzeigen. Ceres wird anhand der gespeicherten Feldflächen und ihres Grundbedarfs erkannt; die Kennzeichnung gilt für die vollständigen Feldflächen, nicht für Gebäude-Freischaltungen. CDLC-Angaben beziehen sich auf enthaltene Dekorationen. Unklare Zuordnungen sind gesondert markiert. Die Darstellung ist schematisch, keine Spielansicht.</p>
<p id="empty" hidden>Keine passenden Stempel. Passe die Filter oder den Suchbegriff an.</p><section class="grid" id="grid">'''+''.join(cards)+'</section><footer>Stand: __AKTUALISIERT__</footer></main>\n<dialog id="viewer"><div class="modalbar"><strong id="modalname"></strong><a id="download">PNG herunterladen ↗</a><button id="close" aria-label="Grossansicht schliessen">Schliessen ✕</button></div><div class="canvas"><img id="full" alt=""></div></dialog>\n<script>\nconst inventory='+payload+''';
const search=document.querySelector('#search'),region=document.querySelector('#region'),folder=document.querySelector('#folder'),ceres=document.querySelector('#ceres'),cdlc=document.querySelector('#cdlc'),cards=[...document.querySelectorAll('.card')],viewer=document.querySelector('#viewer'),full=document.querySelector('#full');
const regionCount=new Set(cards.map(card=>card.dataset.region)).size;
function folders(){const keep=folder.value,values=[...new Set(inventory.filter(e=>!region.value||e.region===region.value).map(e=>e.folder))].sort((a,b)=>a.localeCompare(b,galleryI18n.language,{numeric:true}));folder.replaceChildren(new Option(galleryI18n.t('filters.allFolders'),''));for(const v of values)folder.add(new Option(v||galleryI18n.t('filters.rootFolder'),v||'__root__'));if([...folder.options].some(o=>o.value===keep))folder.value=keep;}
function matchesRequirements(c,ceresValue,cdlcValue){return (!ceresValue||c.dataset.ceres===ceresValue)&&(!cdlcValue||c.dataset.cdlc===cdlcValue||c.dataset.packs.split(' ').includes(cdlcValue));}
function filter(){const q=search.value.toLocaleLowerCase(galleryI18n.language);let n=0;for(const c of cards){const match=(!region.value||c.dataset.region===region.value)&&(!folder.value||(folder.value==='__root__'?!c.dataset.folder:c.dataset.folder===folder.value))&&matchesRequirements(c,ceres.value,cdlc.value)&&(c.dataset.search+' '+galleryI18n.searchText(c)).toLocaleLowerCase(galleryI18n.language).includes(q);c.hidden=!match;if(match)n++;}document.querySelector('#count').textContent=galleryI18n.t('stamp.count117',{shown:n,total:cards.length,region:region.value||galleryI18n.t(regionCount===1?'stamp.regions.one':'stamp.regions',{count:regionCount})});document.querySelector('#empty').hidden=n!==0;}
search.addEventListener('input',filter);region.addEventListener('change',()=>{folders();filter()});folder.addEventListener('change',filter);folders();filter();
ceres.addEventListener('change',filter);cdlc.addEventListener('change',filter);
document.querySelectorAll('.preview').forEach(b=>b.addEventListener('click',()=>{full.src=b.dataset.full;full.alt=galleryI18n.t('stamp.alt',{name:b.dataset.name});full.classList.remove('zoomed');document.querySelector('#modalname').textContent=b.dataset.name;const d=document.querySelector('#download');d.href=b.dataset.full;d.download=b.dataset.name+'.png';viewer.showModal();}));
document.querySelector('#close').addEventListener('click',()=>viewer.close());full.addEventListener('click',()=>full.classList.toggle('zoomed'));viewer.addEventListener('click',e=>{if(e.target===viewer)viewer.close()});
document.addEventListener('gallerylanguagechange',()=>{folders();filter();if(full.getAttribute('src'))full.alt=galleryI18n.t('stamp.alt',{name:document.querySelector('#modalname').textContent});});
</script></html>'''
    content=content.replace('__AKTUALISIERT__',datetime.datetime.now().strftime('%d.%m.%Y %H:%M')).replace('__PACK_OPTIONEN__',pack_options)
    ((CONFIG.stamp_output)/'stamp-gallery.html').write_text(render_gallery(content, 'anno117', 'stamp'),encoding='utf-8')

if __name__=='__main__':main()
