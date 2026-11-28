"""Sync shared save-manager sources into independently usable game directories."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('anno_save_editor.py', 'anno_save_ui.py', 'anno_save_language.py', 'manage_saves.py')


def sync(check=False):
    changed = []
    for game in ('anno117', 'anno1800'):
        pairs = [(ROOT / 'templates/save_manager' / name, ROOT / game / 'tools' / name)
                 for name in MODULES]
        pairs.append((ROOT / 'desktop/assets/annoorganizer.ico',
                      ROOT / game / 'tools/assets/annoorganizer.ico'))
        pairs += [(ROOT / 'docs' / ('save-manager' + suffix + '.md'),
                   ROOT / game / 'docs' / ('save-manager' + suffix + '.md')) for suffix in ('', '.de')]
        for name in ('save-manager-guide.html', 'save-manager-guide.md', 'save-manager-guide.de.md'):
            pairs.append((ROOT / 'docs' / name, ROOT / game / 'docs' / name))
        pairs += [(source, ROOT / game / 'docs/images' / source.name)
                  for source in (ROOT / 'docs/images').glob('save-manager-*.jpg')]
        for source, target in pairs:
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                changed.append(str(target.relative_to(ROOT)))
                if not check:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    if check and changed:
        raise ValueError('Save-manager copies differ: ' + ', '.join(changed))
    print('Save-manager copies verified.' if check else f'Synchronised {len(changed)} save-manager files.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    sync(parser.parse_args().check)
