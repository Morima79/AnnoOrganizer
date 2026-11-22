"""CDLC provenance regression cases; synthetic XML, no private stamps or game assets."""
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'anno117_stamp_requirements', ROOT / 'anno117/tools/anno_stamp_requirements.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def asset(guid, name, extra=''):
    return (f'<Asset><Values><Standard><GUID>{guid}</GUID><Name>{name}</Name></Standard>'
            f'{extra}</Values></Asset>')


class StampRequirementsTests(unittest.TestCase):
    def setUp(self):
        floors = ''.join(asset(g, f'Garden Plaza {i}',
                    '<Polygon><Path>data/base/forest/</Path></Polygon>')
                    for i, g in enumerate((158417, 158418), 1))
        skins = ''.join(asset(g, 'Skin with base graphics') for g in (91001, 91002))
        base = asset(82636, 'Grass') + asset(81091, 'Pavement') + asset(80574, 'Flowers',
                    '<Object><Skins><SkinList><Item><SkinAssetGuid>91001</SkinAssetGuid></Item>'
                    '<Item><SkinAssetGuid>91002</SkinAssetGuid></Item></SkinList></Skins></Object>')
        self.root = ET.fromstring(
            '<AssetList><Groups><Group><Assets>' + base + '</Assets></Group>'
            '<Group><GUID>-417418295</GUID><Groups><Group><Assets>' + floors + skins
            + '</Assets></Group></Groups></Group></Groups></AssetList>')
        self.assets = {int(a.findtext('Values/Standard/GUID')): a for a in self.root.iter('Asset')}
        self.sources = module.asset_cdlc_sources(self.root)

    def classify(self, buildings=(), polygons=(), edges=()):
        return module.requirements({'buildings': list(buildings), 'polygons': list(polygons),
                                    'edges': list(edges)}, self.assets, {}, {}, self.sources)

    def test_both_forest_floors_with_base_paths_require_cdlc02(self):
        for guid in (158417, 158418):
            with self.subTest(guid=guid):
                result = self.classify(polygons=[{'guid': guid}])
                self.assertEqual(result['cdlc'], 'yes')
                self.assertEqual([p['id'] for p in result['cdlc_packs']], ['cdlc02'])
                self.assertEqual(len(result['cdlc_details']), 1)

    def test_base_replacements_do_not_require_cdlc(self):
        result = self.classify(polygons=[{'guid': 82636}, {'guid': 81091}])
        self.assertEqual(result['cdlc'], 'no')
        self.assertEqual(result['cdlc_packs'], [])

    def test_optional_skin_does_not_mark_default_building(self):
        self.assertEqual(self.classify(buildings=[{'guid': 80574}])['cdlc'], 'no')

    def test_used_skin_uses_group_provenance(self):
        result = self.classify(buildings=[{'guid': 80574, 'skin': 1}])
        self.assertEqual(result['cdlc'], 'yes')
        self.assertEqual([p['id'] for p in result['cdlc_packs']], ['cdlc02'])

    def test_ambiguous_skin_remains_unknown(self):
        self.sources.pop(91002)
        self.assertEqual(self.classify(buildings=[{'guid': 80574, 'skin': 1}])['cdlc'], 'unknown')

    def test_all_known_cosmetic_groups_propagate_to_nested_assets(self):
        for group, pack in module.CDLC_ASSET_GROUPS.items():
            with self.subTest(group=group):
                root = ET.fromstring('<AssetList><Groups><Group><GUID>' + group + '</GUID>'
                    '<Groups><Group><Assets>' + asset(12345, 'Neutral name')
                    + '</Assets></Group></Groups></Group></Groups></AssetList>')
                self.assertEqual(module.asset_cdlc_sources(root), {12345: {pack}})

    def test_path_fallback_and_unknown_object_are_preserved(self):
        self.assets[999] = ET.fromstring(asset(999, 'cdlc03 decoration'))
        self.assertEqual(self.classify(edges=[{'guid': 999}])['cdlc_packs'][0]['id'], 'cdlc03')
        self.assertEqual(self.classify(polygons=[{'guid': 888}])['cdlc'], 'unknown')

    def test_non_cosmetic_group_is_not_a_cosmetic_dependency(self):
        root = ET.fromstring('<AssetList><Groups><Group><GUID>542901794</GUID><Assets>'
                            + asset(12345, 'Expansion asset') + '</Assets></Group></Groups></AssetList>')
        self.assertEqual(module.asset_cdlc_sources(root), {})


if __name__ == '__main__':
    unittest.main()
