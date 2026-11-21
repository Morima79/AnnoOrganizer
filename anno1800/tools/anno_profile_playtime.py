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


RANKING_CSS = """
.profile-ranking { margin: 0 0 20px; }
.profile-back { font: inherit; color: #d7f1f3; background: #253f46; border: 1px solid #6b858d;
                border-radius: 5px; padding: 8px 12px; margin: 0 0 10px; cursor: pointer; }
.profile-back:hover { background: #32535c; }
.profile-back:focus-visible { outline: 2px solid #a8dde0; outline-offset: 3px; }
.profile-ranking summary { font-weight: 650; }
.profile-ranking a { color: #a8dde0; text-underline-offset: 3px; }
.profile-ranking table { border-collapse: collapse; margin: 10px 0; }
.profile-ranking th, .profile-ranking td { padding: 4px 12px; border-bottom: 1px solid #49626b; }
.profile-ranking thead th, .profile-ranking td:nth-child(2) { text-align: left; }
.profile-ranking td:nth-child(n+3) { text-align: right; font-variant-numeric: tabular-nums; }
"""
