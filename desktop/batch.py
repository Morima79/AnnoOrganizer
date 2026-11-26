"""Preflight all configured games before starting a sequence of gallery jobs."""
from dataclasses import dataclass

from desktop.settings_store import GAMES


class BatchError(ValueError):
    """A combined update could not be prepared or started."""


@dataclass(frozen=True)
class GalleryJob:
    game: str
    action: str
    document: object


@dataclass(frozen=True)
class GalleryPlan:
    jobs: tuple
    skipped: tuple


def prepare_all(store, documents):
    """Use loaded drafts where available and reject invalid or overlapping targets."""
    jobs, views, errors, skipped = [], {}, [], []
    for game in GAMES:
        try:
            document = documents.get(game) or store.open_game(game)
            view = document.validate()
            views[game] = view
            if game == 'anno1404':
                reason = 'missing_saves' if not any(path.is_dir() for path in view.saves()) else None
            else:
                installation = view.path('game_data')
                marker = 'config.rda' if game == 'anno117' else 'data0.rda'
                reason = 'missing_installation' if installation is None or not (installation / marker).is_file() else None
                if reason is None and not any(view.path(key) and view.path(key).is_dir() for key in ('account', 'stamps')):
                    reason = 'missing_inputs'
            if reason:
                skipped.append(dict(game=game, reason=reason))
                continue
            actions = ('analyze',) if game == 'anno1404' else ('analyze', 'stamps')
            for action in actions:
                if game != 'anno1404':
                    source = view.path('account' if action == 'analyze' else 'stamps')
                    if source is None or not source.is_dir():
                        skipped.append(dict(game=game, action=action,
                                            reason='missing_saves' if action == 'analyze' else 'missing_stamps'))
                        continue
                view.validate(action)
                jobs.append(GalleryJob(game, action, document))
        except Exception as exc:
            errors.append(game + ': ' + str(exc))
    active = {job.game for job in jobs}
    for game, view in views.items():
        if game not in active:
            continue
        targets = [view.output, view.report_output, view.log_output]
        if game != 'anno1404':
            targets.append(view.stamp_output)
        for other, other_view in views.items():
            if game == other:
                continue
            other_targets = [other_view.output, other_view.report_output, other_view.log_output]
            if other != 'anno1404':
                other_targets.append(other_view.stamp_output)
            if other not in active:
                other_targets = []
            for target in targets:
                if any(target.is_relative_to(path) or path.is_relative_to(target)
                       for path in [*other_targets, *other_view.all_sources()]):
                    errors.append(f'{game} / {other}: overlapping paths: {target}')
    if errors:
        raise BatchError('\n'.join(dict.fromkeys(errors)))
    return GalleryPlan(tuple(jobs), tuple(skipped))
