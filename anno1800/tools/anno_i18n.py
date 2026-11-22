"""Bind gallery UI text to portable, embedded language resources.

The HTML adapter covers the original exporters and existing snapshots. It binds
only known interface messages, never scripts, stored filter values or identities.
New markup can use data-i18n keys directly, with German text as its offline fallback.
"""
from html import escape, unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from string import Formatter


def load_resources(folder):
    resources = {lang: json.loads((Path(folder) / (lang + '.json')).read_text(encoding='utf-8'))
                 for lang in ('de', 'en')}
    if resources['de'].keys() != resources['en'].keys():
        raise ValueError('Gallery language resources have different keys')
    for key, source in resources['de'].items():
        fields = lambda text: {name for _, name, _, _ in Formatter().parse(text) if name}
        if fields(source) != fields(resources['en'][key]):
            raise ValueError('Different translation placeholders: ' + key)
    return resources


def script_json(value):
    # User names and paths can be parameters. Never allow a closing script tag.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


class Messages:
    def __init__(self, resources):
        self.de = resources['de']
        self.exact = {value: key for key, value in self.de.items() if '{' not in value}
        self.patterns = []
        for key, value in self.de.items():
            if '{' not in value:
                continue
            parts = []
            for literal, field, _, _ in Formatter().parse(value):
                parts.append(re.escape(literal))
                if field:
                    numeric = field in {'game', 'seeds', 'variants', 'saves', 'count', 'shown', 'total',
                                        'seed', 'variant', 'width', 'height', 'streets', 'actual', 'normal', 'chapter'}
                    parts.append('(?P<' + field + '>' + (r'[0-9.,’]+' if numeric else r'.+?') + ')')
            self.patterns.append((key, re.compile(''.join(parts))))

    def match(self, text):
        if text in self.exact:
            return self.exact[text], {}
        for key, pattern in self.patterns:
            match = pattern.fullmatch(text)
            if match:
                return key, match.groupdict()
        return None

    @staticmethod
    def attributes(key, params, suffix=''):
        attrs = f' data-i18n{suffix}="{escape(key, quote=True)}"'
        if params:
            attrs += f' data-i18n{suffix}-params="{escape(json.dumps(params, ensure_ascii=False, separators=(",", ":")), quote=True)}"'
        return attrs

    def text(self, raw):
        text = unescape(raw)
        stripped = text.strip()
        found = self.match(stripped)
        if found:
            key, params = found
            left = text[:len(text) - len(text.lstrip())]
            right = text[len(text.rstrip()):]
            return left + '<span' + self.attributes(key, params) + '>' + escape(stripped) + '</span>' + right
        # Separators delimit semantic values (mode, region, DLC list), not words.
        parts = re.split(r'( · |, )', raw)
        if len(parts) > 1:
            return ''.join(part if i % 2 else self.text(part) for i, part in enumerate(parts))
        return raw


class GalleryText(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, resources, kind):
        super().__init__(convert_charrefs=True)
        self.messages = Messages(resources)
        self.kind = kind
        self.stack = []
        self.output = []

    def protected(self):
        return any(skip for _, _, skip in self.stack)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get('class', '').split())
        # Profiles, stamp names, paths and user folder names are identities.
        identity = (bool(classes & {'profiles', 'source'}) or 'data-i18n-ignore' in attributes
                    or any(key in attributes for key in ('data-profile', 'data-profile-filter'))
                    or (tag == 'h2' and self.kind == 'stamp')
                    or attributes.get('id') == 'modalname')
        skip = identity or tag in {'script', 'style'} or 'data-i18n' in attributes
        raw = self.get_starttag_text()
        extra = ''
        if not self.protected() and not identity:
            for name in ('placeholder', 'aria-label', 'title', 'alt'):
                if name in attributes and 'data-i18n-' + name not in attributes:
                    found = self.messages.match(attributes[name])
                    if found:
                        extra += self.messages.attributes(*found, suffix='-' + name)
        if extra:
            ending = '/>' if raw.endswith('/>') else '>'
            raw = raw[:-len(ending)] + extra + ending
        self.output.append(raw)
        if tag not in self.VOID:
            self.stack.append((tag, attributes, skip))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        self.output.append('</' + tag + '>')
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        if any(tag in {'script', 'style'} for tag, _, _ in self.stack):
            self.output.append(data)
            return
        # Decode entity-split names as one parameter, then escape text on output.
        data = escape(data)
        if self.protected():
            self.output.append(data)
        elif self.stack and self.stack[-1][0] in {'option', 'title'}:
            # These elements cannot contain spans. Bind the whole text instead.
            tag, attrs, _ = self.stack[-1]
            found = self.messages.match(unescape(data).strip())
            if found:
                extra = self.messages.attributes(*found)
                if tag == 'option' and 'value' not in attrs:
                    extra += ' value="' + escape(unescape(data), quote=True) + '"'
                self.output[-1] = self.output[-1][:-1] + extra + '>'
            self.output.append(data)
        elif self.stack and 'crumb' in self.stack[-1][1].get('class', '').split():
            region, sep, folder = data.partition(' / ')
            article = next((attrs for tag, attrs, _ in reversed(self.stack) if tag == 'article'), {})
            if sep and not article.get('data-folder'):
                folder = self.messages.text(folder)
            self.output.append(self.messages.text(region) + sep + folder)
        else:
            self.output.append(self.messages.text(data))

    def handle_entityref(self, name):
        self.output.append('&' + name + ';')

    def handle_charref(self, name):
        self.output.append('&#' + name + ';')

    def handle_comment(self, data):
        self.output.append('<!--' + data + '-->')

    def handle_decl(self, data):
        self.output.append('<!' + data + '>')


def bind_messages(page, resources, kind):
    parser = GalleryText(resources, kind)
    parser.feed(page)
    return ''.join(parser.output)
