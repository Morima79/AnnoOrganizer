"""Group campaign histories by player-facing map options, without patch drift."""
from collections import defaultdict


MAP_OPTIONS = {
    'anno117': ('SetupMapTemplateType', 'SetupStartSession', 'SetupStartSessionIslandSize',
                'SetupStartSessionIslandDifficulty', 'SetupFertility', 'SetupRawMaterial',
                'SetupStartForestSize', 'DefaultStartProvince'),
    'anno1800': ('SetupMapType', 'SetupStartSession', 'SetupStartSessionIslandSize',
                 'SetupStartSessionIslandDifficulty', 'SetupFertility', 'SetupRawMaterial'),
}
MODE_OPTIONS = ('EnableScenario', 'EnableCampaign', 'CreativeMode')


def setup_values(setup):
    """Normalise dictionary and FileDB path-list representations, keeping list order."""
    if isinstance(setup, dict):
        return {key: tuple(values) for key, values in setup.items()}
    values = defaultdict(list)
    for path, value in setup:
        if path[-1] != 'count':
            values[path[0]].append(value)
    return {key: tuple(items) for key, items in values.items()}


def latest_known_values(setups):
    """Use newest values first and fill missing fields from older saves."""
    values = {}
    for setup in setups:
        for key, value in setup_values(setup).items():
            if value:
                values.setdefault(key, value)
    return values


def campaign_variants(game, entries):
    """Each campaign belongs to exactly one variant, with its full save history.

    Entries contain seed, campaign, order, setup and item. Latest known menu values
    define the campaign's map options; older saves fill missing values. DLC lists,
    internal paths, participants and patch-added flags cannot split a campaign.
    Unknown map options remain unknown rather than being guessed as defaults.
    """
    histories = defaultdict(list)
    for entry in entries:
        histories[entry['seed'], entry['campaign']].append(entry)
    groups = defaultdict(list)
    for (seed, campaign), history in histories.items():
        values = latest_known_values(entry['setup'] for entry in sorted(history, key=lambda entry: entry['order'], reverse=True))
        options = tuple((key, values[key]) for key in MAP_OPTIONS[game] if key in values)
        mode = next((key for key in MODE_OPTIONS if any(values.get(key, (0,)))), 'sandbox')
        # Scenario templates are player-visible maps, unlike normal session lists.
        scenario = values.get('Maps', ()) if game == 'anno1800' and mode == 'EnableScenario' else ()
        unknown = str(campaign) if not options else ''
        key = seed, mode, options, scenario, unknown
        groups[key].extend(entry['item'] for entry in history)
    return [(key[0], items) for key, items in sorted(groups.items(), key=lambda pair: (pair[0][0], repr(pair[0][1:])))]
