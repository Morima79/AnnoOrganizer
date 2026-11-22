"""Render shared gallery frames with game-specific colours and embedded logos."""
import base64
import importlib.util
from html import escape
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('_gallery_i18n', HERE / 'anno_i18n.py')
_i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_i18n)
THEMES = {
    'anno117': {'label': 'Anno 117: Pax Romana', 'scheme': 'light', 'background': '#f1e5cc',
                'ink': '#263b37', 'muted': '#5d6657', 'heading': '#62461c', 'surface': '#fffaf0',
                'inset': '#e8dcc1', 'border': '#baa475', 'link': '#79551e'},
    'anno1800': {'label': 'Anno 1800', 'scheme': 'dark', 'background': '#173345',
                 'ink': '#edf3ee', 'muted': '#bdd0d6', 'heading': '#f3d9a4', 'surface': '#203f51',
                 'inset': '#284b5d', 'border': '#587580', 'link': '#a7dde5'},
    'anno1404': {'label': 'Anno 1404 History Edition', 'scheme': 'light', 'background': '#f3ead8',
                 'ink': '#4a3927', 'muted': '#75644c', 'heading': '#72501e', 'surface': '#fffaf0',
                 'inset': '#e8dbc0', 'border': '#c5ae7b', 'link': '#805b22'},
}


def marker(page, name):
    match = re.search(r'<!-- gallery-' + name + r':start -->(.*?)<!-- gallery-' + name + r':end -->',
                      page, flags=re.DOTALL)
    if match is None:
        raise ValueError('Missing shared gallery section: ' + name)
    return match[1]


def render_gallery(page, game, kind):
    if kind not in ('map', 'stamp'):
        raise ValueError('Unknown gallery kind: ' + str(kind))
    theme = THEMES[game]
    title_match = re.search(r'<title\b[^>]*>(.*?)</title>', page, flags=re.DOTALL | re.IGNORECASE)
    title = title_match[1] if title_match else escape(theme['label'])
    styles = []
    for match in re.finditer(r'<style\b([^>]*)>(.*?)</style>', page, flags=re.DOTALL | re.IGNORECASE):
        if not re.search(r'id=["\']gallery-theme["\']', match[1]):
            styles.append(match[2])
    scripts = '\n'.join(match[0] for match in re.finditer(r'<script\b([^>]*)>.*?</script>', page, flags=re.DOTALL | re.IGNORECASE)
                        if not re.search(r'id=["\']gallery-(?:language-resources|i18n)["\']', match[1]))
    if '<!-- gallery-content:start -->' in page:
        header, content, navigation, footer = (marker(page, name) for name in ('header', 'content', 'navigation', 'footer'))
    else:
        body = re.sub(r'<(?:style|script)\b[^>]*>.*?</(?:style|script)>', '', page,
                      flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<head\b[^>]*>.*?</head>', '', body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<title>.*?</title>', '', body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<!doctype[^>]*>|</?(?:html|body|main)\b[^>]*>|<meta\b[^>]*>', '', body,
                      flags=re.IGNORECASE)
        match = re.search(r'<header\b[^>]*>(.*?)</header>', body, flags=re.DOTALL | re.IGNORECASE)
        if match is None:
            raise ValueError('Gallery header missing')
        header = match[1]
        body = body[:match.start()] + body[match.end():]
        navigation_match = re.search(r'<nav\b[^>]*>.*?</nav>', body, flags=re.DOTALL | re.IGNORECASE)
        navigation = navigation_match[0] if navigation_match else ''
        if navigation_match:
            body = body[:navigation_match.start()] + body[navigation_match.end():]
        footer_match = re.search(r'<footer\b[^>]*>(.*?)</footer>', body, flags=re.DOTALL | re.IGNORECASE)
        footer = footer_match[1] if footer_match else ''
        if footer_match:
            body = body[:footer_match.start()] + body[footer_match.end():]
        content = body.strip()
    header = re.sub(r'<img\b[^>]*class=["\'][^"\']*\bgame-logo\b[^"\']*["\'][^>]*>', '', header,
                    flags=re.IGNORECASE).strip()
    if kind == 'stamp':
        date = re.search(r'(?:Stand|Aktualisiert):\s*([^<·]+)', footer)
        if date is None:
            raise ValueError('Stamp gallery update timestamp missing')
        if 'data-i18n=' not in footer:
            footer = 'Stand: ' + date[1].strip()
    # Shared snapshots store footer text rather than a second nested footer element.
    footer = re.sub(r'^<footer[^>]*>(.*?)</footer>$', r'\1', footer.strip(), flags=re.DOTALL)
    image = HERE.parent / 'docs/images/game-logo.png'
    logo_data = base64.b64encode(image.read_bytes()).decode('ascii')
    logo = f'<img class="game-logo" src="data:image/png;base64,{logo_data}" alt="{escape(theme["label"])}">'
    theme_css = ':root{' + ';'.join('--gallery-' + name + ':' + value for name, value in theme.items() if name != 'label') + '}'
    folder = HERE / 'gallery_templates'
    resources = _i18n.load_resources(folder / 'locales')
    language_switch = '<div class="gallery-language" role="group" aria-label="Sprache" data-i18n-aria-label="language.label"><button type="button" data-gallery-language="de" aria-pressed="true" lang="de">DE</button><button type="button" data-gallery-language="en" aria-pressed="false" lang="en">EN</button></div>'
    if kind == 'stamp' and 'data-gallery-language=' not in content:
        # A modal makes the page header inert, so offer the same switch in the viewer.
        content = content.replace('<div class="modalbar">', '<div class="modalbar">' + language_switch)
    template = (folder / (kind + '_gallery.html')).read_text(encoding='utf-8')
    replacements = {'TITLE': title, 'COMPONENT_CSS': '\n'.join(styles),
                    'THEME_CSS': theme_css, 'SHARED_CSS': (folder / (kind + '_gallery.css')).read_text(encoding='utf-8') + '\n' + (folder / 'gallery_i18n.css').read_text(encoding='utf-8'),
                    'GAME': game, 'LOGO': logo, 'HEADER': header, 'CONTENT': content,
                    'NAVIGATION': navigation, 'FOOTER': '<footer class="gallery-footer">' + footer + '</footer>' if footer else '',
                    'LANGUAGE_SWITCH': language_switch,
                    'LOCALIZATION': '<script id="gallery-language-resources" type="application/json">' + _i18n.script_json(resources) + '</script>\n<script id="gallery-i18n">' + (folder / 'gallery_i18n.js').read_text(encoding='utf-8') + '</script>',
                    'SCRIPTS': scripts}
    # Substitute once so marker-looking text inside user data is not interpreted.
    rendered = re.sub(r'@@([A-Z_]+)@@', lambda match: replacements[match[1]], template)
    return _i18n.bind_messages(rendered, resources, kind)
