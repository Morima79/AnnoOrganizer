"""Render setting-specific game texts without translating raw values or identities."""
from functools import lru_cache
from html import escape
import json
from pathlib import Path


@lru_cache(maxsize=1)
def resources():
    folder = Path(__file__).parent / 'gallery_templates'
    if not folder.is_dir():
        folder = Path(__file__).parent
    catalog = json.loads((folder / 'game_settings.json').read_text(encoding='utf-8'))
    messages = json.loads((folder / 'locales/de.json').read_text(encoding='utf-8'))
    return catalog['games'], messages


def binding(key):
    return f'<span data-i18n="{escape(key, quote=True)}">{escape(resources()[1][key])}</span>'


def known(game, key):
    return key in resources()[0][game]


def name(game, key, fallback=None, html=False):
    entry = resources()[0][game].get(key)
    if entry:
        return binding(entry['label']) if html else resources()[1][entry['label']]
    raw = fallback or key
    return '<span data-i18n-ignore>' + escape(raw) + '</span>' if html else raw


def value(game, key, values, html=False):
    entry = resources()[0][game].get(key, {})
    result = []
    for raw in values:
        translation = entry.get('values', {}).get(str(raw))
        if translation:
            result.append(binding(translation['key']) if html else resources()[1][translation['key']])
        else:
            text = str(raw)
            result.append(('<code data-i18n-ignore>' + escape(text) + '</code> (' + binding('setting.unknownValue') + ')')
                          if html else text + ' (' + resources()[1]['setting.unknownValue'] + ')')
    if not result:
        return binding('stats.unavailable') if html else resources()[1]['stats.unavailable']
    return ', '.join(result)


def row(game, key, values, fallback=None):
    return '<div><dt>' + name(game, key, fallback, html=True) + '</dt><dd>' + value(game, key, values, html=True) + '</dd></div>'


def description(game, pairs):
    return ' · '.join(name(game, key, html=True) + ': ' + value(game, key, values, html=True)
                      for key, values in pairs)
