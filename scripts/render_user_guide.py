"""Render the illustrated Markdown guides as one portable bilingual HTML page."""
from html import escape, unescape
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def guide_content(language, *, online=False):
    """Support the small, explicit Markdown subset used by our beginner guides."""
    source = ROOT / 'docs' / ('desktop.de.md' if language == 'de' else 'desktop.md')

    def href(target):
        if online and not urlsplit(target).scheme and not target.startswith(('images/', '#')):
            relative = (source.parent / target).resolve().relative_to(ROOT).as_posix()
            return 'https://github.com/Morima79/AnnoOrganizer/blob/main/' + relative
        return target

    def inline(text):
        text = escape(text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return re.sub(r'\[([^]]+)\]\(([^)]+)\)',
                      lambda m: '<a href="' + escape(href(unescape(m[2])), quote=True) + '">' + m[1] + '</a>', text)

    # The shared HTML header supplies the title and language navigation.
    blocks = source.read_text(encoding='utf-8').split('\n\n')[2:]
    result = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        picture = re.fullmatch(r'\[<img src="([^"]+)" alt="([^"]+)" width="(\d+)">\]\(([^)]+)\)', block)
        if picture:
            src, alt, width, target = picture.groups()
            if src != target or not src.startswith('images/user-guide-117-'):
                raise ValueError('Unexpected guide screenshot link')
            result.append(f'<figure style="max-width:{width}px"><a href="{escape(src, quote=True)}" '
                          f'target="_blank" rel="noopener"><img src="{escape(src, quote=True)}" '
                          f'alt="{escape(alt, quote=True)}" loading="lazy"></a></figure>')
        elif block.startswith('## '):
            result.append('<h2>' + inline(block[3:]) + '</h2>')
        elif block.startswith('- '):
            lines = block.splitlines()
            if not all(line.startswith('- ') for line in lines):
                raise ValueError('Unsupported mixed guide list')
            result.append('<ul>' + ''.join('<li>' + inline(line[2:]) + '</li>' for line in lines) + '</ul>')
        elif block.startswith('|'):
            rows = [line.strip('|').split('|') for line in block.splitlines()]
            headers = ''.join('<th scope="col">' + inline(cell.strip()) + '</th>' for cell in rows[0])
            body = ''.join('<tr>' + ''.join('<td>' + inline(cell.strip()) + '</td>' for cell in row) + '</tr>'
                           for row in rows[2:])
            result.append('<div class="table-scroll"><table><thead><tr>' + headers + '</tr></thead><tbody>'
                          + body + '</tbody></table></div>')
        else:
            if block.startswith(('#', '```', '<')):
                raise ValueError('Unsupported guide Markdown block')
            result.append('<p>' + inline(block.replace('\n', ' ')) + '</p>')
    return '\n'.join(result)


def render_user_guide(render_page, *, online=False):
    sections = '\n'.join('<article class="guide-content" lang="' + language + '" data-guide-language="'
                         + language + '"' + (' hidden' if language == 'en' else '') + '>\n'
                         + guide_content(language, online=online) + '\n</article>' for language in ('de', 'en'))
    return render_page('user_guide.html', {
        'GUIDE_CONTENT': sections,
        'GUIDE_RUNTIME': (ROOT / 'templates/user_guide.js').read_text(encoding='utf-8'),
        'HOME_URL': '../' if online else 'https://morima79.github.io/AnnoOrganizer/',
    })
