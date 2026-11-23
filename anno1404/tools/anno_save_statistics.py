"""Read conservative, read-only campaign statistics from the supported save formats."""
from collections import Counter, defaultdict
import io
import math
from pathlib import Path
import struct
from xml.etree import ElementTree as ET

STATISTICS_VERSION = 1
LEVELS_1404 = {'Outlaw', 'Beggar_on_street', 'Beggar_in_hospice', 'Ruin_of_ambassador',
               'Ruin_of_peasant', 'Nomad', 'Ambassador', 'Peasant', 'Citizen', 'Patrician', 'Nobleman'}
LEVELS = {
    'anno117': (1499, 1496, 1497, 1498, 1500, 1503, 1501, 1504, 1502,
                149681, 150510, 150534, 150511, 150542),
    'anno1800': (15000000, 15000001, 15000002, 15000003, 15000004, 15000005,
                 15000006, 5403, 112642, 112643, 114329, 114330, 118745),
}


def empty_statistics():
    return dict.fromkeys(('population', 'money', 'balance', 'income', 'expenses', 'houses',
                          'blueprints', 'ships', 'airships', 'islands', 'population_levels',
                          'house_levels', 'ship_types'))


def integer(raw):
    if len(raw) not in (1, 2, 4, 8):
        raise ValueError('Ungültige Ganzzahlgrösse')
    return int.from_bytes(raw, 'little')


def floating(raw):
    if len(raw) != 4:
        raise ValueError('Ungültige Float32-Grösse')
    value = struct.unpack('<f', raw)[0]
    if not math.isfinite(value):
        raise ValueError('Ungültiger Zahlenwert in den Kennzahlen')
    return value


def whole(value):
    """Remove only Float32 inversion noise before flooring UI population values."""
    nearest = round(value)
    return nearest if abs(value - nearest) < 0.0001 else math.floor(value)


def single_header_value(raw, slots):
    if raw is None or len(raw) != slots * 4:
        return None
    values = struct.unpack('<' + 'i' * slots, raw)
    # The investigated single-player format uses -1 for all unused peer slots.
    if any(value != -1 for value in values[1:]) or values[0] == -1:
        return None
    return values[0]


class AssetIndex:
    def __init__(self, data, texts=None):
        self.assets, self.factors = {}, {}
        self.has_texts = bool(texts)
        texts = texts or {}
        for _, asset in ET.iterparse(io.BytesIO(data), events=('end',)):
            # Asset pools also contain <Asset>GUID</Asset> references: retain them.
            if asset.tag != 'Asset' or asset.find('Values') is None:
                continue
            guid = asset.findtext('Values/Standard/GUID')
            if guid:
                residence = asset.find('Values/Residence7')
                template = asset.findtext('Template', '')
                level = (residence.findtext('PopulationLevel') or residence.findtext('PopulationLevel7')) if residence is not None else None
                provider = asset.findtext('Values/AttributeProvider/Population')
                text_id = asset.findtext('Values/Text/OasisId') or guid
                display_name = texts.get(text_id)
                self.assets[int(guid)] = {
                    'name': display_name or asset.findtext('Values/Standard/Name', guid),
                    'localized': bool(display_name),
                    'base': int(asset.findtext('BaseAssetGUID', '0')),
                    'residence': residence is not None,
                    'level': int(level) if level else None,
                    'provider': int(provider) if provider else None,
                    'ship': asset.find('Values/ShipMaintenance') is not None or asset.find('Values/ShipModuleOwner') is not None,
                    'airship': 'airship' in template.lower(),
                }
                factor = asset.findtext('Values/PopulationLevel/PopulationToWorkforceFactor')
                if factor is not None and float(factor) > 0:
                    self.factors[int(guid)] = float(factor)
            asset.clear()
        self.resolved = {}

    def get(self, guid, visiting=None):
        if guid in self.resolved:
            return self.resolved[guid]
        source = self.assets.get(guid)
        if source is None:
            return None
        visiting = (visiting or set()) | {guid}
        parent = self.get(source['base'], visiting) if source['base'] and source['base'] not in visiting else None
        result = dict(source)
        if parent:
            if self.has_texts and not result['localized']:
                result['name'] = parent['name']
            for key in ('residence', 'ship', 'airship'):
                result[key] = result[key] or parent[key]
            for key in ('level', 'provider'):
                if result[key] is None:
                    result[key] = parent[key]
        self.resolved[guid] = result
        return result

    def rows(self, counts, game):
        rows = []
        order = {level: index for index, level in enumerate(LEVELS[game])}
        for level, count in sorted(counts.items(), key=lambda item: (order.get(item[0], len(order)), item[0])):
            if not count:
                continue
            if level in LEVELS[game]:
                rows.append({'key': f'stats.level.{game}.{level}', 'count': whole(count)})
            else:
                asset = self.get(level)
                rows.append({'name': asset['name'] if asset else str(level), 'count': whole(count)})
        return rows


class FileDBStatistics:
    def __init__(self, game, game_data, asset_index=None):
        import anno_file_formats as formats
        self.formats, self.game = formats, game
        self.game_data = Path(game_data)
        self.asset_index = asset_index
        archives = ([self.game_data / 'config.rda'] if game == 'anno117'
                    else sorted(self.game_data.glob('data*.rda'), key=lambda p: int(p.stem[4:])))
        self.archives = archives
        self.signature = [[p.name, p.stat().st_size, p.stat().st_mtime_ns] for p in archives if p.is_file()]
        self.assets = None

    def load_assets(self):
        if self.assets is not None:
            return self.assets
        records = self.asset_index() if self.asset_index else {
            name: rec for path in self.archives for name, rec in self.formats.rda_index(path)
            if name.endswith(('/assets.xml', '/texts_german.xml'))}
        main_path = ('data/base/config/export/assets.xml' if self.game == 'anno117'
                     else 'data/config/export/main/asset/assets.xml')
        matches = [rec for name, rec in records.items() if name == main_path]
        if not matches:
            raise ValueError('Spielasset-Definitionen fehlen')
        text_path = ('data/base/config/gui/texts_german.xml' if self.game == 'anno117'
                     else 'data/config/gui/texts_german.xml')
        texts = {}
        if text_path in records:
            tree = ET.fromstring(self.formats.read_asset(records[text_path]))
            texts = {t.findtext('LineId'): t.findtext('Text') for t in tree.findall('./Texts/Text')}
        self.assets = AssetIndex(self.formats.read_asset(matches[-1]), texts)
        return self.assets

    def __call__(self, path):
        result = empty_statistics()
        parts = dict(self.formats.members(path, {'header.a7s', 'data.a7s'}))
        header = {p: bytes(v) for p, v in self.formats.fields(parts['header.a7s'])}
        slots = 5 if self.game == 'anno117' else 4
        for name, key in (('TotalPopulation', 'population'), ('TotalMoney', 'money')):
            result[key] = single_header_value(header.get(('CorporationProfile', name)), slots)
        if result['population'] is not None and result['population'] < 0:
            result['population'] = None
        peers = header.get(('CorporationProfile', 'UsedPeerCount'))
        if self.game == 'anno117':
            if (peers is not None and integer(peers) != 1) or (
                peers is None and (result['population'] is None or result['money'] is None)
            ):
                return result
            owner = 41
        else:
            identity = header.get(('CorporationProfile', 'ParticipantID', 'id'))
            if identity is None:
                return result
            owner = integer(identity)
            if owner != 0:
                result['population'] = result['money'] = None
        try:
            self.read_world(parts['data.a7s'], owner, result)
        except (ValueError, KeyError, IndexError, struct.error, ET.ParseError) as error:
            print(f'Erweiterte Kennzahlen nicht verfügbar: {Path(path).name}: {error}')
        return result

    def read_world(self, data, owner, result):
        objects, areas, transfers, expeditions = [], [], [], []
        area_population = {}
        session = None
        money_owner = None
        expedition_owner = 0
        finance = {}
        for path, raw in self.formats.fields(data):
            if path[-2:] == ('SessionDesc', 'SessionGUID'):
                session = integer(raw)
            if self.game == 'anno117' and path[:3] == ('MetaGameManager', 'MetaMoneyManager', 'MoneyDataPerParticipant'):
                if path[3:] == ('[]',):
                    money_owner = integer(raw)
                if money_owner == owner and path[-1] in ('TotalMoneyIncomePerMinute', 'TotalMoneyOutgoingsPerMinute', 'TotalAmountOfMoneyPerMinuteNew'):
                    finance[path[-1]] = floating(raw)
            if 'MetaUnitManager' in path and path[-1] == 'TargetGameObject':
                transfers.append(integer(raw))
            if path[-4:] == ('MetaExpeditionUser', 'expeditions', '[]', 'guid'):
                expedition_owner = 0
            if 'MetaExpeditionUser' in path and path[-3:] == ('owner', 'value', 'id'):
                expedition_owner = integer(raw)
            if 'MetaExpeditionUser' in path and path[-1] == 'expeditionShip':
                if integer(raw) and expedition_owner == owner:
                    expeditions.append(integer(raw))
            if path[-2:] != ('SessionData', 'BinaryData'):
                continue
            current, area = None, None
            for p, value in self.formats.fields(bytes(raw)):
                if len(p) == 6 and p[1] == 'AreaManagers' and p[3:] == ('AreaNeedAttributeManager', 'NeedAttributes', '[]'):
                    area_key = session, int(p[2].split('_')[-1])
                    if area_key not in area_population:
                        area_population[area_key] = floating(value)
                if p == ('GameSessionManager', 'AreaInfo', '[]'):
                    area = {'id': integer(value), 'session': session, 'owner': None}
                    areas.append(area)
                elif area and p == ('GameSessionManager', 'AreaInfo', '[]', 'OwnerProfile'):
                    area['owner'] = integer(value)
                elif area and p == ('GameSessionManager', 'AreaInfo', '[]', 'Owner', 'id'):
                    area['owner'] = integer(value)
                if len(p) == 8 and p[3:] == ('AreaObjectManager', 'GameObject', 'objects', '[]', 'guid'):
                    current = {'guid': integer(value), 'owner': owner if self.game == 'anno117' else 0,
                               'flags': 0, 'residents': 0, 'workforce': 0, 'residence': False,
                               'session': session, 'area': int(p[2].split('_')[-1])}
                    objects.append(current)
                elif current and p[3:7] == ('AreaObjectManager', 'GameObject', 'objects', '[]'):
                    tail = p[7:]
                    if tail and tail[0] == 'Residence7':
                        current['residence'] = True
                    if tail == ('OwnerProfile',) or tail == ('ParticipantID', 'id'):
                        current['owner'] = integer(value)
                    elif tail == ('ID',):
                        current['id'] = integer(value)
                    elif tail == ('MetaPersistent', 'MetaID'):
                        current['meta_id'] = integer(value)
                    elif tail == ('StateBits',):
                        current['flags'] = integer(value)
                    elif tail == ('Residence7', 'ResidentCount'):
                        current['residents'] = floating(value) if self.game == 'anno117' else integer(value)
                        current['residence'] = True
                    elif tail == ('AttributeProvider', 'LastRegisteredWorkforceAmount'):
                        current['workforce'] = floating(value)
        if len(finance) == 3:
            income, expenses, balance = (finance[k] for k in ('TotalMoneyIncomePerMinute', 'TotalMoneyOutgoingsPerMinute', 'TotalAmountOfMoneyPerMinuteNew'))
            if income >= 0 and expenses >= 0 and math.isclose(income - expenses, balance, abs_tol=0.05):
                result.update(income=income, expenses=expenses, balance=balance)
        if areas:
            # Aegyptus sectors are not separate islands; never count them as such.
            owned = [a for a in areas if a['owner'] == owner]
            if self.game != 'anno117' or not any(a['session'] == 149679 for a in owned):
                result['islands'] = len(owned)
        if not objects:
            return
        assets = self.load_assets()
        own = [o for o in objects if o['owner'] == owner]
        houses, blueprints, population = Counter(), Counter(), Counter()
        reconstructed_areas = Counter()
        ships, types, airships = {}, Counter(), 0
        houses_valid = population_valid = ships_valid = True
        for obj in own:
            asset = assets.get(obj['guid'])
            if asset is None:
                if obj['residence'] or obj['workforce']:
                    houses_valid = population_valid = False
                if 'meta_id' in obj:
                    ships_valid = False
                continue
            residence = asset['residence'] or obj['residence']
            level = asset['level'] if residence else asset['provider']
            if residence:
                blueprint = obj['flags'] == 0x66 if self.game == 'anno117' else obj['flags'] != 0
                if self.game == 'anno117' and obj['flags'] not in (0, 0x66):
                    houses_valid = False
                (blueprints if blueprint else houses)[level] += 1
                if not blueprint:
                    if level is None or obj['residents'] < 0:
                        population_valid = False
                    else:
                        population[level] += obj['residents']
                        reconstructed_areas[obj['session'], obj['area']] += obj['residents']
            elif self.game == 'anno117' and obj['workforce']:
                factor = assets.factors.get(level)
                if not factor or obj['workforce'] < 0:
                    population_valid = False
                else:
                    contribution = obj['workforce'] / factor
                    nearest = round(contribution)
                    contribution = nearest if abs(contribution - nearest) < 0.0001 else contribution
                    population[level] += contribution
                    reconstructed_areas[obj['session'], obj['area']] += contribution
            if asset['ship']:
                identity = obj.get('meta_id')
                if not identity:
                    ships_valid = False
                elif identity not in ships:
                    ships[identity] = obj
                    types[asset['name']] += 1
                    airships += asset['airship']
        if houses_valid:
            result.update(houses=sum(houses.values()), blueprints=sum(blueprints.values()))
            if None not in houses:
                result['house_levels'] = assets.rows(houses, self.game)
        total = math.fsum(population.values())
        if self.game == 'anno117':
            for area in areas:
                if area['owner'] != owner:
                    continue
                key = area['session'], area['id']
                if key not in area_population or abs(reconstructed_areas[key] - area_population[key]) > 0.05:
                    population_valid = False
        if population_valid and result['population'] is not None and abs(total - result['population']) < 1:
            # Preserve fractional values until the final UI floor operation.
            if whole(total) == result['population']:
                result['population_levels'] = assets.rows(population, self.game)
        all_ship_ids = {obj.get('meta_id') for obj in objects
                        if (asset := assets.get(obj['guid'])) and asset['ship']}
        if ships_valid and not (set(expeditions) - ships.keys()) and not (set(transfers) - all_ship_ids if self.game == 'anno117' else False):
            result.update(ships=len(ships), ship_types=[{'name': name, 'count': n} for name, n in sorted(types.items())])
            if self.game == 'anno1800':
                result['airships'] = airships


class Statistics1404:
    """Use existing validated RDA/BIN readers without importing the exporter."""
    signature = []

    def __init__(self, read_archive, unpack, binary_fields, metadata_tree):
        self.read_archive, self.unpack = read_archive, unpack
        self.binary_fields, self.metadata_tree = binary_fields, metadata_tree

    def __call__(self, path):
        files = self.read_archive(path)
        stats = self.metadata_tree(files['stats.xml'])
        result = empty_statistics()
        for tag, key in (('Inhabitants', 'population'), ('GoldAmount', 'money')):
            text = stats.findtext('.//' + tag, '').strip()
            if text.lstrip('-').isdigit():
                result[key] = int(text)
        try:
            self.read_world(self.unpack(files['save.sww']), result)
        except (ValueError, KeyError, IndexError, struct.error) as error:
            print(f'Erweiterte Kennzahlen nicht verfügbar: {Path(path).name}: {error}')
        return result

    def read_world(self, data, result):
        owner, player = None, None
        population, ship_lists, objects, kontors = {}, {}, [], set()
        house = None
        for parents, key, raw, is_text in self.binary_fields(data):
            path = (*parents, key)
            text = bytes(raw).decode('utf-8', 'replace') if is_text else None
            if path == ('WorldConfig', 'm_GameEngine', 'm_CurPlayerID'):
                owner = int(text)
            if path == ('WorldConfig', 'm_GameEngine', 'm_Players', 'i', 'm_PlayerID'):
                player = int(text)
            if path == ('WorldConfig', 'm_GameEngine', 'm_Players', 'i', 'm_Ships') and len(raw) % 4 == 0:
                ship_lists[player] = set(struct.unpack('<' + 'I' * (len(raw) // 4), raw))
            if parents == ['WorldConfig', 'm_GameEngine', 'm_WorldManager', 'ResidentLevels'] and key.startswith('m_ResidentCountPerLevel') and len(raw) == 32:
                population[key.removeprefix('m_ResidentCountPerLevel')] = struct.unpack('<8i', raw)
            if len(parents) == 5 and parents[:3] == ['WorldConfig', 'm_GameEngine', 'm_WorldManager'] and parents[4].startswith('Warehouse') and key == 'm_KontorModuleStarted' and text == '1':
                kontors.add((parents[3], int(parents[4].removeprefix('Warehouse'))))
            if path == ('WorldConfig', 'Objects', 'Handle', 'Objects', 'Object'):
                house = {'owner': 0, 'ship': False, 'residence': False, 'level': None, 'residents': 0}
                objects.append(house)
            elif house and parents[:5] == ['WorldConfig', 'Objects', 'Handle', 'Objects', 'Object']:
                tail = (*parents[5:], key)
                if tail == ('m_PlayerID',):
                    house['owner'] = int(text)
                elif tail == ('m_ID',):
                    house['id'] = int(text)
                elif tail == ('Ship',):
                    house['ship'] = True
                elif tail == ('ResidenceBuilding',):
                    house['residence'] = True
                elif tail == ('ResidenceBuilding', 'm_ResidentCount'):
                    house['residents'] = int(text)
                elif tail[-1] == 'ResidentLevel' and 'ResidenceBuilding' in tail:
                    house['level'] = text
        if owner is None or not 0 <= owner < 8:
            result['population'] = result['money'] = None
            return
        if owner != 0:
            result['population'] = result['money'] = None
        rows = [{'key': 'stats.level.anno1404.' + name, 'count': values[owner]}
                for name, values in population.items() if values[owner]]
        if population and population.keys() <= LEVELS_1404 and all(values[owner] >= 0 for values in population.values()) and sum(r['count'] for r in rows) == result['population']:
            result['population_levels'] = rows
        own_houses = [o for o in objects if o['owner'] == owner and o['residence']]
        if objects:
            result['houses'] = len(own_houses)
            levels = Counter(o['level'] for o in own_houses)
            if None not in levels and levels.keys() <= LEVELS_1404:
                result['house_levels'] = [{'key': 'stats.level.anno1404.' + name, 'count': n} for name, n in sorted(levels.items())]
            result['islands'] = sum(player == owner for _, player in kontors)
        listed = ship_lists.get(owner)
        actual = {o.get('id') for o in objects if o['owner'] == owner and o['ship']}
        if listed is not None and None not in actual and listed == actual:
            result['ships'] = len(listed)
