import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('technology', ROOT / 'anno1800/tools/anno_stamp_technology.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def asset(guid, template='', base=None, values=''):
    return ET.fromstring(f'<Asset><Template>{template}</Template>'
                         + (f'<BaseAssetGUID>{base}</BaseAssetGUID>' if base else '')
                         + f'<Values><Standard><GUID>{guid}</GUID></Standard>{values}</Values></Asset>')


class BuildingDetectionTests(unittest.TestCase):
    def test_building_counts_include_regional_variants_but_not_named_decorations(self):
        assets = {100415: asset(100415, 'Guildhouse'), 1010516: asset(1010516, 'Guildhouse'),
                  101285: asset(101285, base=100415),
                  900: asset(900, 'OrnamentalBuilding', values='<Text><Name>Town Hall</Name></Text>')}
        data = {'buildings': [{'guid': g} for g in [100415, 101285, 1010516, 900]]}
        result = module.analyze_technology(data, assets, {}, {}, {})
        self.assertEqual(result['townhall_count'], 2)
        self.assertEqual(result['tradeunion_count'], 1)

    def test_unknown_building_is_not_reported_as_absent(self):
        result = module.analyze_technology({'buildings': [{'guid': 999}]}, {}, {}, {}, {})
        self.assertEqual(result['townhall'], 'unknown')
        self.assertEqual(result['tradeunion'], 'unknown')

    def test_electricity_bonus_does_not_mean_mandatory_operation(self):
        assets = {1: asset(1, values='<Electrifiable><ElectricityBoost>100</ElectricityBoost></Electrifiable>'),
                  2: asset(2, values='<Industrializable><MandatoryIndustrialization>1</MandatoryIndustrialization></Industrializable>')}
        bonus = module.analyze_technology({'buildings': [{'guid': 1}]}, assets, {}, {}, {})
        self.assertEqual(bonus['electricity'], 'optional')
        both = module.analyze_technology({'buildings': [{'guid': 1}, {'guid': 2}]}, assets, {}, {}, {})
        self.assertEqual(both['electricity'], 'required')
        self.assertEqual(len(both['optional']), 1)


if __name__ == '__main__':
    unittest.main()
