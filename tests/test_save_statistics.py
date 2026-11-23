"""Regression checks for latest-save selection and conservative statistic extraction."""
import importlib.util
from itertools import chain
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'templates' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stats = load('anno_save_statistics')
summary = load('anno_save_summary')


def u(value, size=4):
    return value.to_bytes(size, 'little')


def fl(value):
    return struct.pack('<f', value)


def assets():
    return stats.AssetIndex(b'''<Assets>
      <Asset><Values><Standard><GUID>1499</GUID></Standard><PopulationLevel><PopulationToWorkforceFactor>0.5</PopulationToWorkforceFactor></PopulationLevel></Values></Asset>
      <Asset><Values><Standard><GUID>10</GUID></Standard><Residence7><PopulationLevel>1499</PopulationLevel></Residence7><AttributeProvider><Population>1499</Population></AttributeProvider></Values></Asset>
      <Asset><Values><Standard><GUID>20</GUID></Standard><AttributeProvider><Population>1499</Population></AttributeProvider></Values></Asset>
      <Asset><Template>TradeShip</Template><Values><Standard><GUID>30</GUID><Name>Real ship</Name></Standard><ShipMaintenance/></Values></Asset>
      <Asset><BaseAssetGUID>30</BaseAssetGUID><Values><Standard><GUID>31</GUID><Name>Regional ship</Name></Standard></Values></Asset>
      <Asset><Template>OrnamentalBuilding</Template><Values><Standard><GUID>40</GUID><Name>Ship decoration</Name></Standard></Values></Asset>
      <Asset><Values><Standard><GUID>50</GUID></Standard><AssetPool><AssetList><Item><Asset>31</Asset></Item></AssetList></AssetPool></Values></Asset>
    </Assets>''')


def object_fields(guid, identity, owner=41, **values):
    prefix = ('GameSessionManager', 'AreaManagers', 'AreaManager_1', 'AreaObjectManager', 'GameObject', 'objects', '[]')
    rows = [(prefix + ('guid',), u(guid)), (prefix + ('ID',), u(identity, 8))]
    if owner != 41:
        rows.append((prefix + ('OwnerProfile',), u(owner)))
    for path, value in values.items():
        rows.append((prefix + tuple(path.split('/')), value))
    return rows


def reader_fixture(game='anno117', extra_outer=()):
    reader = stats.FileDBStatistics.__new__(stats.FileDBStatistics)
    reader.game = game
    reader.load_assets = assets
    inner = [(('GameSessionManager', 'AreaInfo', '[]'), u(1, 2)),
             (('GameSessionManager', 'AreaInfo', '[]', 'OwnerProfile'), u(41)),
             (('GameSessionManager', 'AreaManagers', 'AreaManager_1', 'AreaNeedAttributeManager', 'NeedAttributes', '[]'), fl(7))]
    inner += object_fields(10, 1, **{'Residence7/ResidentCount': fl(4), 'AttributeProvider/LastRegisteredWorkforceAmount': fl(9)})
    inner += object_fields(20, 2, **{'AttributeProvider/LastRegisteredWorkforceAmount': fl(1.5)})
    inner += object_fields(10, 3, **{'StateBits': u(0x66)})
    inner += object_fields(10, 4, owner=77, **{'Residence7/ResidentCount': fl(200)})
    inner += object_fields(31, 5, **{'MetaPersistent/MetaID': u(55, 8)})
    # A duplicate persistent ID and a named decoration must not inflate the fleet.
    inner += object_fields(31, 6, **{'MetaPersistent/MetaID': u(55, 8)})
    inner += object_fields(40, 7)
    outer = [(('MetaGameManager', 'GameSessions', '[]', 'SessionDesc', 'SessionGUID'), u(3245)),
             (('MetaGameManager', 'GameSessions', '[]', 'SessionData', 'BinaryData'), b'inner'), *extra_outer]
    reader.formats = SimpleNamespace(fields=lambda data: iter(outer if data == b'outer' else inner))
    return reader


class StatisticsTests(unittest.TestCase):
    def test_unused_peer_slots_and_missing_headers_are_not_zero(self):
        self.assertIsNone(stats.single_header_value(None, 5))
        self.assertIsNone(stats.single_header_value(struct.pack('<5i', 10, 20, -1, -1, -1), 5))
        self.assertEqual(stats.single_header_value(struct.pack('<5i', 0, -1, -1, -1, -1), 5), 0)
        self.assertEqual(stats.single_header_value(struct.pack('<4i', -25, -1, -1, -1), 4), -25)

    def test_117_includes_nonresidential_population_but_not_residential_workforce_bonuses(self):
        result = stats.empty_statistics()
        result['population'] = 7
        reader_fixture().read_world(b'outer', 41, result)
        self.assertEqual(result['population_levels'], [{'key': 'stats.level.anno117.1499', 'count': 7}])
        self.assertEqual((result['houses'], result['blueprints']), (1, 1))
        self.assertEqual(result['ships'], 1)
        self.assertEqual(result['islands'], 1)

    def test_population_disagreement_retains_total_but_hides_unreliable_breakdown(self):
        result = stats.empty_statistics()
        result['population'] = 10
        reader_fixture().read_world(b'outer', 41, result)
        self.assertEqual(result['population'], 10)
        self.assertIsNone(result['population_levels'])

    def test_117_checks_individual_island_population_not_only_the_grand_total(self):
        reader = reader_fixture()
        fields = reader.formats.fields
        reader.formats.fields = lambda data: ((p, fl(8) if p[-3:] == ('AreaNeedAttributeManager', 'NeedAttributes', '[]') else value)
                                             for p, value in fields(data))
        result = stats.empty_statistics()
        result['population'] = 7
        reader.read_world(b'outer', 41, result)
        self.assertEqual(result['population'], 7)
        self.assertIsNone(result['population_levels'])

    def test_financial_values_require_player_match_and_consistent_minute_balance(self):
        prefix = ('MetaGameManager', 'MetaMoneyManager', 'MoneyDataPerParticipant', '[]')
        for owner, balance in ((41, 3), (41, 99), (77, 3)):
            reader = reader_fixture(extra_outer=[(prefix, u(owner)),
                (prefix + ('TotalMoneyIncomePerMinute',), fl(8)),
                (prefix + ('TotalMoneyOutgoingsPerMinute',), fl(5)),
                (prefix + ('TotalAmountOfMoneyPerMinuteNew',), fl(balance))])
            result = stats.empty_statistics()
            reader.read_world(b'outer', 41, result)
            self.assertEqual(result['balance'], 3 if owner == 41 and balance == 3 else None)

    def test_inherited_ship_asset_is_detected_without_installed_module_fields(self):
        index = assets()
        self.assertTrue(index.get(31)['ship'])
        self.assertFalse(index.get(40)['ship'])
        # Nested Asset references must not corrupt real asset definitions.
        self.assertIsNotNone(index.get(50))

    def test_asset_loader_uses_each_games_main_export_not_empty_secondary_assets(self):
        for game, path in [('anno117', 'data/base/config/export/assets.xml'),
                           ('anno1800', 'data/config/export/main/asset/assets.xml')]:
            reader = stats.FileDBStatistics.__new__(stats.FileDBStatistics)
            reader.game, reader.assets = game, None
            reader.asset_index = lambda: {path: 'main', 'data/unused/assets.xml': 'empty'}
            requested = []
            def read_asset(record):
                requested.append(record)
                return b'<Assets/>' if record == 'main' else b''
            reader.formats = SimpleNamespace(read_asset=read_asset)
            reader.load_assets()
            self.assertEqual(requested, ['main'])

    def test_unresolved_1800_expedition_prevents_partial_ship_total(self):
        reader = reader_fixture(game='anno1800', extra_outer=[
            (('MetaGameManager', 'MetaGameObjectManager', 'MetaExpeditionUser', 'expeditionShip'), u(999, 8))])
        result = stats.empty_statistics()
        reader.read_world(b'outer', 0, result)
        self.assertIsNone(result['ships'])
        self.assertIsNone(result['balance'])

    def test_npc_transfers_do_not_hide_the_players_fleet(self):
        reader = reader_fixture(extra_outer=[
            (('MetaGameManager', 'MetaUnitManager', 'QueuedTransfers', '[]', 'TargetGameObject'), u(66, 8))])
        fields = reader.formats.fields
        reader.formats.fields = lambda data: chain(fields(data), object_fields(
            31, 8, owner=77, **{'MetaPersistent/MetaID': u(66, 8)})) if data == b'inner' else fields(data)
        result = stats.empty_statistics()
        reader.read_world(b'outer', 41, result)
        self.assertEqual(result['ships'], 1)

    def test_1404_ship_reference_list_is_checked_against_owned_objects(self):
        rows = []
        def add(path, value, text=True):
            rows.append((list(path[:-1]), path[-1], str(value).encode() if text else value, text))
        base = ('WorldConfig', 'm_GameEngine')
        add(base + ('m_CurPlayerID',), 0)
        add(base + ('m_Players', 'i', 'm_PlayerID'), 0)
        add(base + ('m_Players', 'i', 'm_Ships'), u(12), False)
        add(base + ('m_WorldManager', 'ResidentLevels', 'm_ResidentCountPerLevelPeasant'), struct.pack('<8i', 5, 0, 0, 0, 0, 0, 0, 0), False)
        ob = ('WorldConfig', 'Objects', 'Handle', 'Objects', 'Object')
        add(ob, b'', False)
        add(ob + ('m_ID',), 12)
        add(ob + ('Ship',), b'', False)
        reader = stats.Statistics1404(None, None, lambda data: iter(rows), None)
        result = stats.empty_statistics()
        result['population'] = 5
        reader.read_world(b'', result)
        self.assertEqual(result['ships'], 1)
        self.assertEqual(result['population_levels'][0]['count'], 5)
        rows[2] = (list(base + ('m_Players', 'i')), 'm_Ships', u(999), False)
        result = stats.empty_statistics()
        reader.read_world(b'', result)
        self.assertIsNone(result['ships'])


class SelectionAndPresentationTests(unittest.TestCase):
    def test_statistics_cache_reuses_only_unchanged_saves_and_game_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            path, cache_path = Path(directory)/'save', Path(directory)/'cache'
            path.write_bytes(b'save')
            candidates = [dict(path=path, campaign='1:a', stamp=1, profile='Name', source=path.name)]
            class Reader:
                signature = ['assets-v1']
                calls = 0
                def __call__(self, path):
                    self.calls += 1
                    return stats.empty_statistics()
            reader = Reader()
            _, cache = summary.collect_statistics(candidates, reader, cache_path, ZoneInfo('Europe/Zurich'))
            cache_path.write_text(json.dumps(cache), encoding='utf-8')
            summary.collect_statistics(candidates, reader, cache_path, ZoneInfo('Europe/Zurich'))
            self.assertEqual(reader.calls, 1)
            reader.signature = ['assets-v2']
            summary.collect_statistics(candidates, reader, cache_path, ZoneInfo('Europe/Zurich'))
            self.assertEqual(reader.calls, 2)
            reader.signature = ['assets-v1']
            path.write_bytes(b'changed save')
            summary.collect_statistics(candidates, reader, cache_path, ZoneInfo('Europe/Zurich'))
            self.assertEqual(reader.calls, 3)
            summary.collect_statistics(candidates, reader, cache_path, ZoneInfo('Europe/Zurich'), cache_only=True)
            self.assertEqual(reader.calls, 3)

    def test_latest_save_only_and_campaign_ids_keep_same_seed_parties_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('old', 'new', 'other')]
            for path in paths:
                path.write_bytes(b'save')
            candidates = [dict(path=p, campaign=campaign, stamp=stamp, profile='Name', source=p.name, seed=1)
                          for p, campaign, stamp in zip(paths, ('1:a', '1:a', '1:b'), (1, 2, 1))]
            calls = []
            class Reader:
                signature = []
                def __call__(self, path):
                    calls.append(path.name)
                    if path.name == 'new':
                        raise ValueError('Unsupported latest save')
                    return stats.empty_statistics()
            entries, cache = summary.collect_statistics(candidates, Reader(), Path(directory)/'cache', ZoneInfo('Europe/Zurich'))
            self.assertEqual(calls, ['new', 'other'])
            self.assertEqual(len(entries), 2)
            self.assertIsNone(entries['1:a']['values']['population'])
            self.assertNotIn(str(paths[0]), cache['files'])

    def test_statistics_groups_start_closed_and_escape_names_and_sources(self):
        values = stats.empty_statistics()
        values.update(population=7, money=500, houses=1, ships=1,
                      ship_types=[{'name': '<script>private</script>', 'count': 1}])
        page = summary.render_statistics([dict(profile='A < B', date='23.11.2026',
                                                source='<private>', values=values)])
        self.assertEqual(page.count('class="stat-group"'), 4)
        self.assertNotIn(' open', page)
        self.assertIn('stats.unavailable', page)
        self.assertIn('&lt;script&gt;private&lt;/script&gt;', page)
        self.assertNotIn('<private>', page)
        self.assertIn('stats.lastPlayed', page)
        self.assertEqual(summary.number(-0.4, signed=True), '-0.4')


if __name__ == '__main__':
    unittest.main()
