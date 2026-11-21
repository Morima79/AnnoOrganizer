from PIL import Image,ImageDraw,ImageFont
import math,collections

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
        color=('#bdab91' if 'stein' in name.lower() or 'pflaster' in name.lower() else '#cfb68f') if road else ('#35603b' if typ=='Hedge' else '#666f77' if typ=='Railway' else '#799fac')
        draw.line((*xy(*e['PosMin']),*xy(*e['PosMax'])),fill=color,width=max(1,round(scale if road else scale*.25)))
    def bcolor(g):
        a=assets[g];typ=a.findtext('Template','');n=a.findtext('Values/Standard/Name','')
        if typ in ['OrnamentalBuilding','Hedge']:return '#4d773f'
        if typ=='Farmfield':return '#d4bc7f'
        if 'Module' in typ:return '#c5b995'
        if 'Residence' in typ:return '#d6c99c'
        if any(k in typ for k in ['Institution','PublicService','Warehouse','GuestHouse','Governor'] ) or 'Warehouse' in n:return '#8aa8ba'
        return '#b47d59'
    for b in buildings:
        g=b['guid'];shape=[xy(*p) for p in b['points']];draw.polygon(shape,fill=bcolor(g),outline='#494b3b')
        if assets[g].findtext('Template') in ['OrnamentalBuilding','Hedge','Farmfield']:continue
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
