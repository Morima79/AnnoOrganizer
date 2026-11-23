'Assign each campaign to the profile containing its longest saved playtime.'
from collections import defaultdict
from html import escape
from pathlib import Path


def profile_name(source, path):
    folder = Path(path).parent.name or 'Spielkonto'
    return folder if source != 'Archiv' else f'{folder} (Archiv)'


def profile_playtime(entries):
    """Entries: seed, row, source, relative path, milliseconds, active counter."""
    best = {}
    for seed, row, source, path, milliseconds, active in entries:
        profile = profile_name(source, path)
        key = (seed, row['campaign_id'])
        # On ties prefer the live account, then the newest save and a deterministic path.
        priority = (active, milliseconds, source != 'Archiv', row['stamp'], path)
        if key not in best or priority > best[key][0]:
            best[key] = priority, profile

    totals = defaultdict(int)
    counts = defaultdict(int)
    for (_, milliseconds, *_), profile in best.values():
        totals[profile] += milliseconds
        counts[profile] += 1
    return [(profile, counts[profile], milliseconds) for profile, milliseconds in
            sorted(totals.items(), key=lambda item: (-item[1], item[0].casefold()))]


def ranking_html(profiles, format_duration):
    rows = ''.join(f'<tr><th scope="row">{index}</th><td>'
                   f'<a href="#variant-filters" data-profile-filter="{escape(name)}">{escape(name)}</a></td>'
                   f'<td>{count}</td><td>{format_duration(ms // 1000)}</td></tr>'
                   for index, (name, count, ms) in enumerate(profiles, 1))
    return (
        '<details id="profile-ranking" class="profile-ranking" open><summary>Spielzeit pro Profil</summary>'
        '<p>Jede Partie zählt beim Profil ihres längsten gespeicherten Stands. '
        'Bei gleicher Spielzeit hat das Spielkonto Vorrang vor Archivkopien.</p>'
        '<table><thead><tr><th scope="col">Rang</th><th scope="col">Profil</th>'
        '<th scope="col">Partien</th><th scope="col">Spielzeit (h:mm:ss)</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></details>'
    )
