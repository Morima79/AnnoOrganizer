'Detect technology from actual modules and electricity properties rather than names.'
import collections

def analyze_technology(data,assets,labels,templates,defaults):
    counts=collections.Counter(b['guid'] for b in data['buildings'])
    tractors={};silos={};required={};optional={};powerplants={};townhalls={};tradeunions={};unknown=[]
    for g,count in counts.items():
        a=assets.get(g)
        if a is None:unknown.append(g);continue
        # Regional variants inherit the original building asset; skins do not
        # change the saved building GUID. Follow lineage rather than names.
        lineage=set();current=g
        while current in assets and current not in lineage:
            lineage.add(current)
            base=assets[current].findtext('BaseAssetGUID')
            if not base:break
            current=int(base)
        if 100415 in lineage:townhalls[g]=count
        if 1010516 in lineage:tradeunions[g]=count
        template=templates.get(a.findtext('Template'))
        def exists(component):
            return a.find('Values/'+component) is not None or (template is not None and template.find('Properties/'+component) is not None)
        def value(component,property,default=None):
            path=component+'/'+property
            v=a.findtext('Values/'+path)
            if v is None and template is not None:v=template.findtext('Properties/'+path)
            if v is None:v=defaults.get(path,default)
            return v
        def on(v):return str(v).lower() in ('1','true')
        if a.findtext('Template')=='BuffFactoryModule':
            buffs={e.text for e in a.findall('Values/BuffFactory/ProductionBuffs/Item/ProductivityBuff')}
            if a.findtext('Values/BuffFactory/BaseBuff')=='269980' or '269979' in buffs:tractors[g]=count
            if '269978' in buffs:silos[g]=count
        if exists('Powerplant'):powerplants[g]=count
        if on(value('Industrializable','MandatoryIndustrialization','0')):required[g]=count
        elif exists('Electrifiable') and on(value('Industrializable','BoostedByIndustrialization','1')):
            boost=value('Electrifiable','ElectricityBoost','100')
            if float(boost)>0:optional[g]=count
    state='required' if required else 'unknown' if unknown else 'optional' if optional else 'none'
    def rows(found):return [{'guid':g,'name':labels.get(g,str(g)),'count':n} for g,n in sorted(found.items(),key=lambda x:labels.get(x[0],str(x[0])))]
    return {'townhall':'yes' if townhalls else 'unknown' if unknown else 'no','townhall_count':sum(townhalls.values()),'townhalls':rows(townhalls),
            'tradeunion':'yes' if tradeunions else 'unknown' if unknown else 'no','tradeunion_count':sum(tradeunions.values()),'tradeunions':rows(tradeunions),
            'tractor':'yes' if tractors else 'unknown' if unknown else 'no','tractor_count':sum(tractors.values()),'tractors':rows(tractors),
            'silo':'yes' if silos else 'unknown' if unknown else 'no','silo_count':sum(silos.values()),'silos':rows(silos),
            'electricity':state,'required':rows(required),'optional':rows(optional),'powerplant_count':sum(powerplants.values()),'powerplants':rows(powerplants),'unknown_guids':unknown}
