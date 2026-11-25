"""Choose the GUI language from Windows display preferences or a saved override."""
import ctypes
import json
import os
from pathlib import Path


def windows_display_language():
    if os.name != 'nt':
        return ''
    try:
        kernel = ctypes.windll.kernel32
        count, size = ctypes.c_ulong(), ctypes.c_ulong()
        if kernel.GetUserPreferredUILanguages(8, ctypes.byref(count), None, ctypes.byref(size)):
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel.GetUserPreferredUILanguages(8, ctypes.byref(count), buffer, ctypes.byref(size)):
                return buffer.value
        buffer = ctypes.create_unicode_buffer(85)
        if kernel.LCIDToLocaleName(kernel.GetUserDefaultUILanguage(), buffer, len(buffer), 0):
            return buffer.value
    except (OSError, AttributeError, ValueError):
        pass
    return ''


def choose_language(saved=None, display_language=None):
    if saved in ('de', 'en'):
        return saved
    name = windows_display_language() if display_language is None else display_language
    return 'de' if (name or '').replace('_', '-').split('-')[0].lower() == 'de' else 'en'


def resources(language):
    path = Path(__file__).resolve().parent / 'locales' / (language + '.json')
    return json.loads(path.read_text(encoding='utf-8'))
