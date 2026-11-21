'Read Anno 1800 stamps and update their blueprints and gallery.'
from pathlib import Path
import sys
from anno_settings import settings_for, protect_output
from anno_gallery import render_gallery
CONFIG = settings_for('anno1800')

import json,struct as st,collections,math,re,hashlib,datetime,copy,html,os
from urllib.parse import quote
import xml.etree.ElementTree as ET
from PIL import Image
from anno_file_formats import inflate,rda_index,read_asset
from anno_stamp_blueprint import render
from anno_resident_files import index_resident,read_resident
from anno_stamp_technology import analyze_technology
HERE=Path(__file__).resolve().parent
ROOT=CONFIG.output
LIB=CONFIG.path('stamps')
GAME=CONFIG.path('game_data')
CACHE=(CONFIG.report_output)/'stamp-gallery'
OUT=(CONFIG.stamp_output)/'library'
REGIONS={'The Old World':'Alte Welt','The New World':'Neue Welt','The Arctic':'Arktis','Enbesa':'Enbesa'}
MAIN='data/config/export/main/asset/'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(s):
    s=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',s).rstrip(' .')
    assert s and s not in ['.','..']
    return s

def tree(raw):
    _,tp,ap,_,magic=st.unpack_from('<5I',raw,len(raw)-20)
    assert magic==0xfffffffd,'Unbekanntes Stempelformat'
    names={1:'[]',0x8000:'[]'}
    for off in (tp,ap):
        n,=st.unpack_from('<I',raw,off);ids=st.unpack_from(f'<{n}H',raw,off+4);pos=off+4+2*n
        for code in ids:
            end=raw.index(0,pos);names[code]=raw[pos:end].decode();pos=end+1
    pos=0
    def read():
        nonlocal pos
        size,code=st.unpack_from('<IH',raw,pos);pos+=8
        if not code:return None
        if code&0x8000:
            value=bytes(raw[pos:pos+size]);pos+=(size+7)&~7
            return names[code],value
        children=[]
        while (child:=read()) is not None:children.append(child)
        return names[code],children
    roots=[]
    while pos<tp:
        n=read()
        if n is None:break
        roots.append(n)
    return roots

def attrlist(nodes):return {k:v for k,v in nodes if isinstance(v,bytes)}
def flatten(nodes):
    for k,v in nodes:
        if isinstance(v,bytes):yield v
        else:yield from flatten(v)

def decode(path):
    roots=tree(inflate(path.read_bytes()));data={'buildings':[],'polygons':[],'edges':[],'reserve':set()};streets=[];rails=[]
    for key,nodes in roots:
        if key=='BuildingInfo':
            for _,node in nodes:
                a=attrlist(node)
                assert 'GUID' in a
                data['buildings'].append({'guid':int.from_bytes(a['GUID'],'little'),'pos':st.unpack('<ff',a.get('Pos',bytes(8))),'angle':st.unpack('<f',a.get('Dir',bytes(4)))[0],'variation':int.from_bytes(a.get('Variation',bytes(4)),'little'),'skin':int.from_bytes(a.get('Skin',bytes(4)),'little'),'owner':int.from_bytes(a.get('ComplexOwnerID',bytes(8)),'little')})
        elif key=='StreetInfo':
            # Each group starts with an attribute [] holding the street GUID.
            guid=None
            for k,v in nodes:
                if isinstance(v,bytes):guid=int.from_bytes(v,'little')
                else:
                    assert guid is not None
                    coords=[st.unpack('<f',b)[0] for b in flatten(v)];assert len(coords)%2==0
                    streets.extend((guid,(coords[i],coords[i+1])) for i in range(0,len(coords),2))
        elif key=='RailwayInfos':
            for _,node in nodes:
                pts=[st.unpack('<ii',b) for b in flatten(node)]
                rails.append(pts)
    # Roads are stored as individual tile centres. Merge only direct neighbours.
    byguid=collections.defaultdict(set)
    for guid,p in streets:byguid[guid].add(p)
    for guid,pts in byguid.items():
        for x,y in sorted(pts):
            neighbours=[(x+1,y),(x,y+1)]
            made=False
            for q in neighbours:
                if q in pts:data['edges'].append({'guid':guid,'PosMin':(x,y),'PosMax':q});made=True
            if not made and (x-1,y) not in pts and (x,y-1) not in pts:
                data['edges'].append({'guid':guid,'PosMin':(x-.2,y),'PosMax':(x+.2,y)})
    for pts in rails:
        for a,b in zip(pts,pts[1:]):data['edges'].append({'guid':-1,'PosMin':a,'PosMax':b})
    data['street_tiles']=len(streets);data['rail_points']=sum(map(len,rails))
    assert data['buildings'] or data['edges'],path
    return data

def resources(signature):
    signaturefile=CACHE/'game-signature.json';indexfile=CACHE/'rda-index.json'
    old=json.loads(signaturefile.read_text(encoding='utf-8')) if signaturefile.exists() else None
    if old!=signature or not indexfile.exists() or MAIN+'properties.xml' not in json.loads(indexfile.read_text(encoding='utf-8')):
        index={};targets={MAIN+'assets.xml',MAIN+'templates.xml',MAIN+'properties.xml','data/config/gui/texts_german.xml'}
        for archive in sorted(GAME.glob('data*.rda'),key=lambda p:int(p.stem[4:])):
            for n,rec in rda_index(archive):
                if not rec[1]&4 and (n.endswith('.ifo') or n in targets):index[n]=rec
        indexfile.write_text(json.dumps(index),encoding='utf-8')
        signaturefile.write_text(json.dumps(signature),encoding='utf-8')
    else:index=json.loads(indexfile.read_text(encoding='utf-8'))
    return index,old!=signature

def merge(base,override):
    result=copy.deepcopy(base)
    if override.text is not None and override.text.strip():result.text=override.text
    if any(c.tag=='Item' for c in override):return copy.deepcopy(override)
    for c in override:
        old=result.find(c.tag)
        if old is None:result.append(copy.deepcopy(c))
        else:
            i=list(result).index(old);result.remove(old);result.insert(i,merge(old,c))
    return result

def metadata(needed,index,changed):
    cachefile=CACHE/'object-definitions.json'
    found=json.loads(cachefile.read_text(encoding='utf-8')) if cachefile.exists() and not changed else {}
    def pending():
        extra=set()
        for xml in found.values():
            a=ET.fromstring(xml)
            base=a.findtext('BaseAssetGUID')
            if base:extra.add(int(base))
            extra.update(int(e.text) for e in a.findall('Values/Object/Skins/SkinList/Item/SkinAssetGuid') if e.text)
            promotion=a.findtext('Values/UplayProduct/PromotionAsset')
            if promotion:extra.add(int(promotion))
        return (needed|extra)-set(map(int,found))
    missing=pending()
    if missing or not found:
        xmlfile=CACHE/'assets.xml'
        if changed or not xmlfile.exists():xmlfile.write_bytes(read_asset(index[MAIN+'assets.xml']))
        for _ in range(6):
            missing=pending();added=0
            for _,a in ET.iterparse(xmlfile,events=['end']):
                if a.tag!='Asset':continue
                g=a.findtext('Values/Standard/GUID')
                product=a.findtext('Template')=='UplayProduct'
                if g and (int(g) in missing or product):
                    xml=ET.tostring(a,encoding='unicode')
                    if g not in found:added+=1
                    found[g]=xml
                a.clear()
            if not pending() or not added:break
        cachefile.write_text(json.dumps(found,ensure_ascii=False),encoding='utf-8')
    rawassets={int(g):ET.fromstring(xml) for g,xml in found.items()}
    assets={}
    def effective(g,visited=None):
        if g in assets:return assets[g]
        a=rawassets.get(g)
        if a is None:return None
        visited=set() if visited is None else visited
        assert g not in visited,('Zirkulaere Vererbung',g)
        base=a.findtext('BaseAssetGUID')
        parent=effective(int(base),visited|{g}) if base else None
        assets[g]=merge(parent,a) if parent is not None else copy.deepcopy(a)
        return assets[g]
    for g in rawassets:effective(g)
    textsfile=CACHE/'texts_german.xml'
    if changed or not textsfile.exists():textsfile.write_bytes(read_asset(index['data/config/gui/texts_german.xml']))
    translations={}
    for _,t in ET.iterparse(textsfile,events=['end']):
        if t.tag=='Text' and t.find('GUID') is not None:
            translations[t.findtext('GUID')]=t.findtext('Text') or '';t.clear()
    def label(g,seen=None):
        seen=set() if seen is None else seen
        if g in seen:return str(g)
        a=assets[g]
        promotion=a.findtext('Values/UplayProduct/PromotionAsset')
        if promotion and int(promotion) in assets:
            key=assets[int(promotion)].findtext('Values/UplayProductPromotion/DLCName')
            if key in translations:return translations[key]
        override=a.findtext('Values/Text/TextOverride')
        if override and int(override) in assets:return label(int(override),seen|{g})
        line=a.findtext('Values/Text/LineID')
        return translations.get(override) or translations.get(str(g)) or a.findtext('Values/Text/LocaText/German/Text') or a.findtext('Values/Text/LocaText/English/Text') or a.findtext('Values/Standard/Name') or str(g)
    labels={g:' '.join(re.sub(r'<[^>]*>','',label(g)).split()) for g in assets}
    return assets,labels

def packids(a):
    if a is None:return set()
    values=[a.findtext('Values/Standard/Name','')]
    values.extend(e.text or '' for e in a.findall('Values/Object/Variations/Item/Filename'))
    values.extend(e.text or '' for e in a.findall('Values/MeshGraphStyle/PerSkinConfig/Item[1]/*'))
    packs=set()
    for v in values:
        for kind,n in re.findall(r'(c?dlc)0*(\d+)',v,re.I):packs.add(kind.lower()+str(int(n)).zfill(2))
    return packs

def build_shapes(entries,assets,index,changed):
    cachefile=CACHE/'footprints.json';shapes=json.loads(cachefile.read_text(encoding='utf-8')) if cachefile.exists() and not changed else {}
    wanted=set()
    resident=index_resident(GAME,CACHE)
    for e in entries:
        for b in e['data']['buildings']:
            a=assets.get(b['guid']);files=[] if a is None else [n.text for n in a.findall('Values/Object/Variations/Item/Filename') if n.text]
            i=b['variation']
            if files:b['model']=files[i if i<len(files) else 0].lower()[:-4]+'.ifo';wanted.add(b['model'])
    for model in wanted-set(shapes):
        blob=read_resident(GAME,resident,model)
        if blob is not None or model in index:
            info=ET.fromstring(blob if blob is not None else read_asset(index[model]));pts=[]
            for p in info.findall('BuildBlocker/Position'):
                x=p.findtext('xf');y=p.findtext('zf')
                if x is None:x=str(float(p.findtext('x','0'))/4096)
                if y is None:y=str(float(p.findtext('z','0'))/4096)
                pts.append((float(x),float(y)))
            if pts:shapes[model]=pts
    cachefile.write_text(json.dumps(shapes),encoding='utf-8')
    unresolved=collections.Counter()
    for e in entries:
        e['unknown_shapes']=[]
        for b in e['data']['buildings']:
            pts=shapes.get(b.get('model',''))
            if pts is None:
                pts=[(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)];e['unknown_shapes'].append(b['guid']);unresolved[b['guid']]+=1
            angle=b['angle'];quarter=round(angle/(math.pi/2));angle=quarter*math.pi/2 if abs(angle-quarter*math.pi/2)<1e-4 else angle
            c=round(math.cos(angle),10);s=round(math.sin(angle),10)
            b['points']=[(b['pos'][0]+x*c-y*s,b['pos'][1]+x*s+y*c) for x,y in pts]
    return dict(unresolved)

def archive_old(old,current):
    live={r[k] for r in current for k in ['png','thumb']}
    archive=(CONFIG.stamp_output)/'backups'/'gallery'/datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S-%f')
    for row in old:
        for key in ['png','thumb']:
            relative=row[key]
            if relative in live:continue
            source=((CONFIG.stamp_output)/relative).resolve();destination=(archive/source.relative_to(OUT.resolve())).resolve()
            assert source.is_relative_to(OUT.resolve()) and destination.is_relative_to(archive.resolve())
            if source.is_file():destination.parent.mkdir(parents=True,exist_ok=True);source.rename(destination)

def main():
    CONFIG.validate('stamps')
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    snapshot={p:sha(p) for p in LIB.rglob('*') if p.is_file()};entries=[]
    for path,digest in sorted(snapshot.items()):
        if path.suffix.lower()=='.ini':continue
        relative=path.relative_to(LIB);region=REGIONS.get(relative.parts[0],relative.parts[0]);folder='/'.join(relative.parts[1:-1])
        entries.append({'name':path.name,'region':region,'folder':folder,'source':str(relative),'stamp_hash':digest,'data':decode(path)})
    print(f'{len(entries)} Anno-1800-Stempel gelesen.',flush=True)
    signature=[(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in sorted(GAME.glob('data*.rda'))]
    signature=[list(s) for s in signature]+[['file.db',(GAME/'file.db').stat().st_size,(GAME/'file.db').stat().st_mtime_ns]]
    index,changed=resources(signature)
    needed={b['guid'] for e in entries for b in e['data']['buildings']}|{s['guid'] for e in entries for s in e['data']['edges'] if s['guid']!=-1}
    assets,labels=metadata(needed,index,changed)
    templatexml=ET.fromstring(read_asset(index[MAIN+'templates.xml']))
    templates={t.findtext('Name'):t for t in templatexml.findall('.//Template') if t.findtext('Name')}
    propertyxml=ET.fromstring(read_asset(index[MAIN+'properties.xml']))
    defaults={}
    for component in ['Industrializable','Electrifiable']:
        for node in propertyxml.iter(component):
            for child in node:
                if child.text and child.text.strip():defaults[component+'/'+child.tag]=child.text.strip()
    print(f'{len(needed)} verwendete Objektarten; {len(needed-set(assets))} unbekannte GUIDs.',flush=True)
    unresolved=build_shapes(entries,assets,index,changed)
    print(f'Grundflaechen geladen; {len(unresolved)} Objektarten ohne aufgeloeste Grundflaeche.',flush=True)
    simple={};texts={}
    for g in needed|{-1}:
        a=assets.get(g);typ='Railway' if g==-1 else a.findtext('Template','Unknown') if a is not None else 'Unknown'
        label='Eisenbahn' if g==-1 else labels.get(g,f'Unbekanntes Objekt {g}')
        x=ET.Element('Asset');ET.SubElement(x,'Template').text=typ;values=ET.SubElement(x,'Values')
        ET.SubElement(ET.SubElement(values,'Standard'),'Name').text=label;ET.SubElement(ET.SubElement(values,'Text'),'OasisId').text=str(g)
        simple[g]=x;texts[str(g)]=label
    packnames={}
    for g,a in assets.items():
        if a.findtext('Template')!='UplayProduct':continue
        identity=a.findtext('Values/Standard/ID','')+' '+a.findtext('Values/Standard/Name','')
        for kind,n in re.findall(r'(c?dlc)0*(\d+)',identity,re.I):packnames.setdefault(kind.lower()+str(int(n)).zfill(2),labels[g])
    inventoryfile=CACHE/'inventory.json';old=json.loads(inventoryfile.read_text(encoding='utf-8')) if inventoryfile.exists() else [];by_path={e['png']:e for e in old}
    renderhash=sha(Path(__file__))+sha(Path(__file__).with_name('anno_stamp_blueprint.py'));manifest=[];thumbs=OUT/'_thumbnails';thumbs.mkdir(exist_ok=True);used=set();rendered=0
    for i,e in enumerate(entries):
        packs=set();skin_unknown=False
        for b in e['data']['buildings']:
            a=assets.get(b['guid']);packs.update(packids(a))
            if b['skin'] and a is not None:
                choices=[int(n.text) for n in a.findall('Values/Object/Skins/SkinList/Item/SkinAssetGuid') if n.text]
                candidates=[packids(assets.get(choices[j])) for j in {b['skin']-1,b['skin']} if 0<=j<len(choices)]
                if not candidates or any(c!=candidates[0] for c in candidates):skin_unknown=True
                else:packs.update(candidates[0])
        req={'packs':[{'id':p,'name':packnames.get(p,p.upper())} for p in sorted(packs)],'state':'yes' if packs else 'unknown' if skin_unknown else 'no','skin_unknown':skin_unknown,'geometry_unknown':sorted(set(e['unknown_shapes']))}
        req['technology']=analyze_technology(e['data'],assets,labels,templates,defaults)
        output=OUT/safe(e['region'])
        for folder in e['folder'].split('/'):
            if folder:output=output/safe(folder)
        output.mkdir(parents=True,exist_ok=True);path=output/(safe(e['name'])+'.png');assert path not in used;used.add(path)
        rel=path.relative_to((CONFIG.stamp_output)).as_posix();fingerprint=hashlib.sha256((e['stamp_hash']+renderhash+json.dumps(signature)).encode()).hexdigest();previous=by_path.get(rel)
        if previous and previous.get('fingerprint')==fingerprint and path.exists() and previous.get('png_hash')==sha(path):meta={k:previous[k] for k in ['width','height','buildings','reserve']}
        else:
            meta=render(e,path,simple,texts);rendered+=1
            if e['unknown_shapes']:
                from PIL import ImageDraw,ImageFont
                with Image.open(path) as im:
                    im.load();d=ImageDraw.Draw(im);f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
                    d.rectangle((0,im.height-55,im.width,im.height),fill='#fff1df');d.text((32,im.height-38),f'Hinweis: {len(e["unknown_shapes"])} Objekte nur als 1x1-Symbol; Grundflaeche unbekannt. GUIDs siehe Galerie.',font=f,fill='#883f24');im.save(path)
        thumb=thumbs/(hashlib.sha256(rel.encode()).hexdigest()[:16]+'.jpg')
        if rendered and (not previous or previous.get('fingerprint')!=fingerprint) or not thumb.exists():
            with Image.open(path) as im:im.thumbnail((640,500));im.convert('RGB').save(thumb,quality=86)
        row={k:e[k] for k in ['name','region','folder','source']};row.update(meta);row.update({'png':rel,'thumb':thumb.relative_to((CONFIG.stamp_output)).as_posix(),'fingerprint':fingerprint,'png_hash':sha(path),'requirements':req,'streets':e['data']['street_tiles'],'rail_points':e['data']['rail_points']});manifest.append(row)
        if (i+1)%75==0:print(f'{i+1}/{len(entries)} Plaene fertig.',flush=True)
    assert {p:sha(p) for p in LIB.rglob('*') if p.is_file()}==snapshot,'Stempelbibliothek wurde waehrend des Lesens geaendert.'
    archive_old(old,manifest);write_gallery(manifest)
    inventoryfile.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (CACHE/'source-checksums.json').write_text(json.dumps({str(p.relative_to(LIB)):v for p,v in snapshot.items()},ensure_ascii=False,indent=2),encoding='utf-8')
    for p in used:
        with Image.open(p) as im:im.verify()
    report={'stamps':len(manifest),'rendered':rendered,'reused':len(manifest)-rendered,'regions':dict(collections.Counter(e['region'] for e in manifest)),'unknown_geometry':unresolved,'library_unchanged':True}
    (CACHE/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True),flush=True)
    for name in ['assets.xml','texts_german.xml','templates.xml']:
        f=CACHE/name
        if f.exists():f.unlink()

# GALLERY

def write_gallery(entries):
    esc=html.escape;cards=[]
    for e in entries:
        r=e['requirements'];packs=' '.join(p['id'] for p in r['packs']);png=quote(e['png'],safe='/');thumb=quote(e['thumb'],safe='/')
        badge='Keine DLC-Objekte erkannt' if r['state']=='no' else 'DLC-Zuordnung prüfen' if r['state']=='unknown' else ', '.join(p['name'] for p in r['packs'])
        details=[]
        if r['skin_unknown']:details.append('Nicht alle gespeicherten Skins sind eindeutig einem Paket zuordenbar.')
        if r['geometry_unknown']:details.append('Grundfläche unbekannt; im Plan als 1×1-Symbol: '+', '.join(map(str,r['geometry_unknown'])))
        tech=r['technology']
        for title,key in [('Rathäuser','townhalls'),('Handelskammern','tradeunions'),('Traktormodule','tractors'),('Silos','silos'),('Strom erforderlich','required'),('Strombonus möglich','optional'),('Kraftwerke','powerplants')]:
            if tech[key]:details.append(title+': '+', '.join(f'{x["name"]} ({x["count"]}×)' for x in tech[key]))
        if tech['unknown_guids']:details.append('Technik unbekannter Objekte prüfen: '+', '.join(map(str,tech['unknown_guids'])))
        tractor_label=f'Traktormodule: {tech["tractor_count"]}' if tech['tractor']=='yes' else 'Traktoren: prüfen' if tech['tractor']=='unknown' else 'Ohne Traktormodule'
        silo_label=f'Silos: {tech["silo_count"]}' if tech['silo']=='yes' else 'Silos: prüfen' if tech['silo']=='unknown' else 'Ohne Silos'
        power_label={'required':'Strom erforderlich','optional':'Strombonus möglich','none':'Keine Stromgebäude erkannt','unknown':'Strom: prüfen'}[tech['electricity']]
        tech_badges='<div class="badges tech-badges">'+''.join('<span class="badge">'+esc(x)+'</span>' for x in [tractor_label,silo_label,power_label])+('<span class="badge">Kraftwerk vorhanden</span>' if tech['powerplant_count'] else '')+'</div>'
        civic_labels=[]
        for key,title in [('townhall','Rathaus'),('tradeunion','Handelskammer')]:
            if tech[key]=='yes':civic_labels.append(f'{title}: {tech[key+"_count"]}')
            elif tech[key]=='unknown':civic_labels.append(title+': prüfen')
        if civic_labels:tech_badges+='<div class="badges civic-badges">'+''.join('<span class="badge">'+esc(x)+'</span>' for x in civic_labels)+'</div>'
        detail=('<details><summary>Hinweise zum Plan</summary><ul>'+''.join('<li>'+esc(d)+'</li>' for d in details)+'</ul></details>') if details else ''
        search=esc((e['name']+' '+e['region']+' '+e['folder']+' '+badge).casefold(),quote=True)
        cards.append(f'''<article class="card" data-region="{esc(e['region'])}" data-folder="{esc(e['folder'],quote=True)}" data-search="{search}" data-dlc="{r['state']}" data-packs="{packs}" data-geometry="{int(bool(r['geometry_unknown']))}" data-townhall="{tech['townhall']}" data-tradeunion="{tech['tradeunion']}" data-tractor="{tech['tractor']}" data-silo="{tech['silo']}" data-electricity="{tech['electricity']}" data-powerplant="{int(bool(tech['powerplant_count']))}"><button class="preview" data-full="{png}" data-name="{esc(e['name'],quote=True)}" aria-label="Bauplan {esc(e['name'],quote=True)} öffnen"><img src="{thumb}" loading="lazy" alt="Bauplan {esc(e['name'],quote=True)}"></button><div class="body"><p class="crumb">{esc(e['region'])} / {esc(e['folder'] or 'Direkt in der Region')}</p><h2>{esc(e['name'])}</h2><div class="badges"><span class="badge {r['state']}">{esc(badge)}</span>{'<span class="badge">Grundflächen prüfen</span>' if r['geometry_unknown'] else ''}</div>{tech_badges}<p>{e['width']} × {e['height']} Kacheln · {e['buildings']} Gebäude/Module · {e['streets']} Strassenkacheln</p>{detail}<a href="{png}" download="{esc(e['name'],quote=True)}.png">PNG herunterladen ↗</a></div></article>''')
    packmap={p['id']:p for e in entries for p in e['requirements']['packs']}
    packoptions=''.join(f'<option value="{esc(k)}">{esc(v["name"])}</option>' for k,v in sorted(packmap.items()))
    regions=''.join(f'<option>{esc(r)}</option>' for r in ['Alte Welt','Neue Welt','Enbesa','Arktis'] if any(e['region']==r for e in entries))
    payload=json.dumps([{'region':e['region'],'folder':e['folder']} for e in entries],ensure_ascii=False).replace('<','\u003c')
    page=(HERE/'stamp_gallery_template.html').read_text(encoding='utf-8')
    for marker,value in {'__CSS__':(HERE/'stamp_gallery.css').read_text(encoding='utf-8'),'__COUNT__':str(len(entries)),'__REGIONS__':regions,'__PACKS__':packoptions,'__CARDS__':''.join(cards),'__DATE__':datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),'__INVENTORY__':payload}.items():page=page.replace(marker,value)
    target=(CONFIG.stamp_output)/'stamp-gallery.html';tmp=target.with_suffix('.tmp');tmp.write_text(render_gallery(page, 'anno1800', 'stamp'),encoding='utf-8');os.replace(tmp,target)

if __name__=='__main__':main()
