"""Regressions for patch-stable variants and unique current-campaign placement."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('map_variants', ROOT/'templates/anno_map_variants.py')
variants = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variants)


def entry(campaign, stamp, setup, seed=7):
    return dict(seed=seed, campaign=campaign, order=(stamp,), setup=setup, item=(campaign, stamp))


def filed_rows(**values):
    return [[[key, 'value', 'id'], value] for key, value in values.items()]


class MapVariantTests(unittest.TestCase):
    def test_patch_flags_dlc_lists_and_option_changes_never_split_one_campaign(self):
        entries = [
            entry('a', 1, dict(SetupMapTemplateType=[1], SetupStartSessionIslandSize=[0])),
            entry('a', 2, dict(SetupMapTemplateType=[1], SetupStartSessionIslandSize=[1],
                               ActiveDLCs=[99], SetupContinentalIslandStart=[0])),
            entry('a', 3, dict(SetupMapTemplateType=[1], ActiveDLCs=[99, 100], ActiveMods=['patch-v2']))]
        groups = variants.campaign_variants('anno117', entries)
        self.assertEqual(groups, [(7, [('a', 1), ('a', 2), ('a', 3)])])
        # Missing newest values inherit known older menu values, not guessed zeroes.
        known = variants.latest_known_values(e['setup'] for e in reversed(entries))
        self.assertEqual(known['SetupStartSessionIslandSize'], (1,))
        self.assertNotIn('SetupStartSession', known)

    def test_different_campaigns_compare_menu_values_without_technical_noise(self):
        entries = [entry('a', 1, dict(SetupMapTemplateType=[1])),
                   entry('b', 2, dict(SetupMapTemplateType=[1], EnableCampaign=[0], ActiveDLCs=[99],
                                       SetupContinentalIslandAllowRivalSettling=[0])),
                   entry('c', 3, dict(SetupMapTemplateType=[2])),
                   entry('d', 4, dict(SetupMapTemplateType=[1], DefaultStartProvince=[44]))]
        groups = variants.campaign_variants('anno117', entries)
        self.assertEqual(len(groups), 3)
        self.assertIn((7, [('a', 1), ('b', 2)]), groups)

    def test_1800_normalises_filedb_paths_and_ignores_patch_session_and_party_drift(self):
        entries = [entry('a', 1, filed_rows(SetupMapType=1, SetupStartSession=1)),
                   entry('a', 2, filed_rows(SetupMapType=1, SetupStartSession=1, SetupStartWithKontor=1)
                         + [[['ActiveDLCs', 'DLC'], 99], [['Maps', 'Asset'], 180025]]),
                   entry('b', 3, [[['SetupMapType'], 1], [['SetupStartSession'], 1],
                                  [['SecondParties', 'Profile'], 77]])]
        self.assertEqual(variants.campaign_variants('anno1800', entries),
                         [(7, [('a', 1), ('a', 2), ('b', 3)])])

    def test_actual_options_modes_scenarios_and_seeds_still_distinguish_variants(self):
        entries = [entry('a', 1, filed_rows(SetupMapType=1)),
                   entry('b', 2, filed_rows(SetupMapType=2)),
                   entry('c', 3, filed_rows(SetupMapType=1, EnableCampaign=1)),
                   entry('d', 4, filed_rows(SetupMapType=1, EnableScenario=1) + [[['Maps', 'Asset'], 123]]),
                   entry('e', 5, filed_rows(SetupMapType=1, EnableScenario=1) + [[['Maps', 'Asset'], 456]]),
                   entry('f', 6, filed_rows(SetupMapType=1), seed=8)]
        self.assertEqual(len(variants.campaign_variants('anno1800', entries)), 6)

    def test_missing_options_are_not_assumed_to_be_equal_between_unrelated_campaigns(self):
        self.assertEqual(len(variants.campaign_variants('anno117', [entry('a', 1, {}), entry('b', 2, {})])), 2)


if __name__ == '__main__':
    unittest.main()
