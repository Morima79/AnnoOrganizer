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


def prepare_all(store, documents):
    """Use loaded drafts where available and reject invalid or overlapping targets."""
    jobs, views, errors = [], {}, []
    for game in GAMES:
        try:
            document = documents.get(game) or store.open_game(game)
            view = document.validate()
            actions = ('analyze',) if game == 'anno1404' else ('analyze', 'stamps')
            for action in actions:
                view.validate(action)
                jobs.append(GalleryJob(game, action, document))
            views[game] = view
        except Exception as exc:
            errors.append(game + ': ' + str(exc))
    for game, view in views.items():
        targets = [view.output, view.report_output, view.log_output]
        if game != 'anno1404':
            targets.append(view.stamp_output)
        for other, other_view in views.items():
            if game == other:
                continue
            other_targets = [other_view.output, other_view.report_output, other_view.log_output]
            if other != 'anno1404':
                other_targets.append(other_view.stamp_output)
            for target in targets:
                if any(target.is_relative_to(path) or path.is_relative_to(target)
                       for path in [*other_targets, *other_view.all_sources()]):
                    errors.append(f'{game} / {other}: overlapping paths: {target}')
    if errors:
        raise BatchError('\n'.join(dict.fromkeys(errors)))
    return jobs
