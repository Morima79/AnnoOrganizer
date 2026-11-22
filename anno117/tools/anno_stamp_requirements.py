'Infer requirements from object GUIDs and saved field areas.'
import collections,math,re

# Top-level content groups in the exported Anno 117 assets.xml. Some members
# (notably both forest floors) retain base-game names and graphics paths.
CDLC_ASSET_GROUPS = {
    '-1574124720': 'cdlc01',
    '-417418295': 'cdlc02',
    '385980937': 'cdlc03',
}


def asset_cdlc_sources(root):
    """Preserve cosmetic-pack provenance before flattening the asset tree."""
    sources = {}
    for group in root.findall('./Groups/Group'):
        pack = CDLC_ASSET_GROUPS.get(group.findtext('GUID'))
        if pack is None:
            continue
        for asset in group.iter('Asset'):
            guid = asset.findtext('Values/Standard/GUID')
            if guid:
                sources.setdefault(int(guid), set()).add(pack)
    return sources


def requirements(data,assets,texts,templates,cdlc_sources=None):
    def name(g):
        a=assets[g]
        return texts.get(a.findtext('Values/Text/OasisId')) or a.findtext('Values/Standard/Name') or str(g)
    def packs_for(g):
        a=assets.get(g)
        if a is None:return None
        found=set((cdlc_sources or {}).get(g, ()))
        # Optional skin configurations belong to the base object as well, but
        # do not make its default appearance DLC-dependent.
        values=[a.findtext('Values/Standard/Name',''),a.findtext('Values/Standard/IconFilename',''),a.findtext('Values/Polygon/Path','')]
        values.extend(e.text or '' for e in a.findall('Values/Object/Variations/Item/Filename'))
        base=a.find('Values/MeshGraphStyle/PerSkinConfig/Item')
        if base is not None:values.extend(e.text or '' for e in base.iter())
        for value in values:
            for n in re.findall(r'cdlc0*(\d+)',value,re.I):found.add('cdlc'+str(int(n)).zfill(2))
        return found
    packnames={}
    for g,a in assets.items():
        standard=a.findtext('Values/Standard/Name','')
        if 'Source Container' in standard:
            for pack in packs_for(g) or []:
                if a.findtext('Values/Text/OasisId') in texts:packnames.setdefault(pack,name(g))
    refs=collections.Counter(o['guid'] for key in ('buildings','polygons','edges') for o in data[key])
    packs=set();cdlc_details=[];cdlc_unknown=[]
    for g,count in sorted(refs.items()):
        found=packs_for(g)
        if found is None:cdlc_unknown.append(f'Unbekanntes Objekt {g}');continue
        if found:
            packs.update(found);cdlc_details.append(f'{name(g)} ({count}×)')
    for b in data['buildings']:
        skin=b.get('skin',0)
        if not skin:continue
        a=assets.get(b['guid'])
        choices=[] if a is None else [int(e.text) for e in a.findall('Values/Object/Skins/SkinList/Item/SkinAssetGuid') if e.text]
        # Skin is an index, not an asset GUID. Check both index conventions. A
        # mixed/unresolvable selection is labelled unknown, never declared free.
        candidates=[packs_for(choices[i]) for i in {skin-1,skin} if 0<=i<len(choices)]
        if not candidates or any(c is None for c in candidates) or any(c!=candidates[0] for c in candidates):
            cdlc_unknown.append(f'Skin von {name(b["guid"])} nicht eindeutig zuordenbar')
        elif candidates[0]:
            packs.update(candidates[0]);cdlc_details.append(f'Skin von {name(b["guid"])}')
    cdlc='yes' if packs else ('unknown' if cdlc_unknown else 'no')
    if packs and cdlc_unknown:cdlc_details.extend(cdlc_unknown)

    limits={};farmowners={};ceres_unknown=[]
    for b in data['buildings']:
        a=assets.get(b['guid'])
        if a is None:continue
        template=templates.get(a.findtext('Template'))
        farmtype=a.findtext('Values/ModuleOwner/FarmType')
        if farmtype is None and template is not None:farmtype=template.findtext('Properties/ModuleOwner/FarmType')
        if farmtype!='PlantFarm':continue
        raw=a.findtext('Values/ModuleOwner/ModuleLimits/Main/Limit')
        if raw is None and template is not None:raw=template.findtext('Properties/ModuleOwner/ModuleLimits/Main/Limit')
        if raw is None or not b.get('owner'):
            ceres_unknown.append(f'Grundbedarf von {name(b["guid"])} nicht auslesbar');continue
        limits[b['owner']]=int(raw);farmowners[b['owner']]=b['guid']
    counts=collections.Counter()
    for p in data['polygons']:
        if p.get('owner') in limits:
            counts[p['owner']]+=sum(n.bit_count()/4 for n in p['cells'].values())
    buff=assets.get(43610)
    percent=None if buff is None else buff.findtext('Values/ModuleOwnerUpgrade/ModuleLimitPercent')
    checks=[];oversized=[]
    for owner,normal in limits.items():
        actual=counts[owner]
        check={'farm':name(farmowners[owner]),'guid':farmowners[owner],'normal':normal,'stored':actual}
        checks.append(check)
        if actual>normal:
            oversized.append(check)
            # Existing hand-painted fields can exceed the nominal limit by
            # two cells (e.g. 92 hemp cells instead of 90).
            if percent is None or actual>math.ceil(normal*(1+float(percent)/100))+2:
                ceres_unknown.append(f'{check["farm"]}: {actual:g} statt {normal} Feldkacheln; Ursache nicht eindeutig')
    ceres='unknown' if ceres_unknown else ('yes' if oversized else 'no')
    details=[f'{c["farm"]}: {c["stored"]:g} statt {c["normal"]} Feldkacheln' for c in oversized]
    return {'ceres':ceres,'ceres_details':details+ceres_unknown,'field_checks':checks,
            'cdlc':cdlc,'cdlc_packs':[{'id':p,'name':packnames.get(p,p.upper())} for p in sorted(packs)],
            'cdlc_details':cdlc_details+(cdlc_unknown if not packs else [])}
