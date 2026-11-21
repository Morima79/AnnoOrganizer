"""Extract one version's bilingual release notes from CHANGELOG.md."""
import argparse
from pathlib import Path
import re


def extract_release_notes(changelog, version):
    if not re.fullmatch(r'v[0-9]+[.][0-9]+[.][0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Use a version such as v0.1.2 or v0.2.0-beta.1')
    pattern = r'^## \[' + re.escape(version) + r'\][^\n]*\n(.*?)(?=^## |\Z)'
    matches = re.findall(pattern, changelog, flags=re.MULTILINE | re.DOTALL)
    if len(matches) != 1 or not matches[0].strip():
        raise ValueError('Expected exactly one non-empty changelog entry for ' + version)
    return matches[0].strip() + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--changelog', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'CHANGELOG.md')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    notes = extract_release_notes(args.changelog.read_text(encoding='utf-8'), args.version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(notes, encoding='utf-8', newline='\n')
    print('Release notes written for ' + args.version)
