"""Bundle canonical gallery templates with each independently usable Anno project."""
import argparse
import importlib.util
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sync(check=False):
    mismatches = []
    for game in ('anno117', 'anno1800', 'anno1404'):
        for name in ('anno_gallery.py', 'map_gallery.html', 'map_gallery.css', 'stamp_gallery.html', 'stamp_gallery.css'):
            source = ROOT / 'templates' / name
            target = ROOT / game / 'tools' / (name if name == 'anno_gallery.py' else 'gallery_templates/' + name)
            if not target.is_file() or source.read_bytes() != target.read_bytes():
                mismatches.append(str(target.relative_to(ROOT)))
                if not check:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    if check and mismatches:
        raise ValueError('Gallery template copies differ: ' + ', '.join(mismatches))
    print('Gallery template copies verified.' if check else f'Synchronised {len(mismatches)} gallery files.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument('--check', action='store_true')
    options.add_argument('--refresh-site', action='store_true',
                         help='Also update the frames of the five existing public demo snapshots')
    args = parser.parse_args()
    sync(args.check)
    if args.refresh_site:
        for game in ('anno117', 'anno1800', 'anno1404'):
            spec = importlib.util.spec_from_file_location('gallery_' + game,
                                                          ROOT / game / 'tools/anno_gallery.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for kind in (('map',) if game == 'anno1404' else ('map', 'stamp')):
                folder = 'maps' if kind == 'map' else 'stamps'
                page = ROOT / 'site' / game / folder / 'index.html'
                page.write_text(module.render_gallery(page.read_text(encoding='utf-8'), game, kind),
                                encoding='utf-8', newline='\n')
        print('Refreshed the five public demo frames without reading game data.')
