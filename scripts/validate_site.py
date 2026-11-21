"""Validate the portable, static public demo snapshots without installed games."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        self.references.extend(value for key, value in attrs
                               if key in ('href', 'src', 'data-full') and value)


def validate_site(folder):
    folder = Path(folder).resolve()
    expected = ['index.html', 'anno117/maps/index.html', 'anno117/stamps/index.html',
                'anno1800/maps/index.html', 'anno1800/stamps/index.html', 'anno1404/maps/index.html']
    for name in expected:
        if not (folder / name).is_file():
            raise ValueError('Missing demo page: ' + name)
    pages = list(folder.rglob('*.html'))
    if len(pages) != len(expected):
        raise ValueError('Expected one landing page and five galleries')
    for page in pages:
        text = page.read_text(encoding='utf-8')
        if re.search(r'(?:(?<![A-Za-z])[A-Za-z]:[\\/]|file:/{2,}|OneDrive|LokaleDaten)', text):
            raise ValueError('Local machine path in ' + str(page))
        parser = References()
        parser.feed(text)
        for reference in parser.references:
            url = urlsplit(reference)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (page.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(folder):
                raise ValueError('Reference escapes site: ' + reference)
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                raise ValueError(f'{page}: missing target {reference}')
    allowed = {'.html', '.png', '.jpg', '.jpeg', '.svg', '.webp'}
    for path in folder.rglob('*'):
        if path.is_file() and path.name != '.nojekyll' and path.suffix not in allowed:
            raise ValueError('Unexpected public file: ' + str(path))
    print(f'Validated {len(pages)} pages and all local image/navigation references.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', type=Path, default=Path(__file__).resolve().parents[1] / 'site')
    validate_site(parser.parse_args().folder)
