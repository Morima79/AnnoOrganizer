// Exercise the actual embedded runtime without a server or third-party packages.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const resources = Object.fromEntries(['de', 'en'].map(lang => [lang, JSON.parse(fs.readFileSync(path.join(root, 'templates/locales', lang + '.json'), 'utf8'))]));
const runtime = fs.readFileSync(path.join(root, 'templates/gallery_i18n.js'), 'utf8');

function element(attributes = {}, text = '') {
  return {attributes, textContent: text, dataset: {}, listeners: {},
    getAttribute(name) { return this.attributes[name] ?? null; },
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(event, handler) { this.listeners[event] = handler; }};
}

function environment({stored = null, blocked = false, missingEnglish = false} = {}) {
  const messages = structuredClone(resources);
  if (missingEnglish) delete messages.en['stamp.download'];
  const heading = element({'data-i18n': 'stamp.heading'});
  const option = element({'data-i18n': 'mode.sandbox'});
  option.value = 'Sandkasten';
  const userName = element({}, 'Klein <script>alert(1)</script>');
  const input = element({'data-i18n-placeholder': 'filters.stampPlaceholder117'});
  input.value = 'Lavendel';
  const preview = element({'data-i18n-alt': 'stamp.alt', 'data-i18n-alt-params': JSON.stringify({name: userName.textContent})});
  const de = element(), en = element();
  de.dataset.galleryLanguage = 'de'; en.dataset.galleryLanguage = 'en';
  const events = [];
  const document = {documentElement: {lang: ''},
    getElementById(id) { assert.equal(id, 'gallery-language-resources'); return {textContent: JSON.stringify(messages)}; },
    querySelectorAll(selector) {
      return ({'[data-i18n]': [heading, option], '[data-i18n-placeholder]': [input],
        '[data-i18n-alt]': [preview], '[data-gallery-language]': [de, en]})[selector] || [];
    },
    dispatchEvent(event) { events.push(event); }};
  const storage = new Map(stored ? [['annotools.gallery.language', stored]] : []);
  const localStorage = {getItem(key) { if (blocked) throw Error('Storage unavailable'); return storage.get(key) ?? null; },
    setItem(key, value) { if (blocked) throw Error('Storage unavailable'); storage.set(key, value); }};
  const window = {};
  vm.runInNewContext(runtime, {document, window, localStorage, CustomEvent: class {constructor(type, init) { this.type = type; this.detail = init.detail; }}});
  return {document, i18n: window.galleryI18n, heading, option, userName, input, preview, de, en, storage, events};
}

test('DE/EN switching preserves inputs, option values and identity text', () => {
  const e = environment();
  assert.equal(e.document.documentElement.lang, 'de-CH');
  e.en.listeners.click();
  assert.equal(e.heading.textContent, 'Your blueprints, all in one place.');
  assert.equal(e.document.documentElement.lang, 'en');
  assert.equal(e.en.attributes['aria-pressed'], 'true');
  assert.equal(e.de.attributes['aria-pressed'], 'false');
  assert.equal(e.option.textContent, 'Sandbox');
  assert.equal(e.option.value, 'Sandkasten');
  assert.equal(e.input.value, 'Lavendel');
  assert.equal(e.input.attributes.placeholder, 'Name, production or town …');
  assert.equal(e.preview.attributes.alt, 'Blueprint ' + e.userName.textContent);
  assert.equal(e.i18n.t('stamp.count', {shown: 2, total: 5}), '2 of 5 stamps');
  assert.equal(e.i18n.t('map.visible', {count: 1}), '1 variant visible');
  assert.equal(e.i18n.t('map.summary', {seeds: 1, variants: 2, saves: 1}), '1 seed · 2 map variants · 1 save');
  assert.equal(e.events[0].type, 'gallerylanguagechange');
  assert.equal(e.storage.get('annotools.gallery.language'), 'en');
  e.de.listeners.click();
  assert.equal(e.option.textContent, 'Sandkasten');
  assert.equal(e.input.value, 'Lavendel');
});

test('saved English choice restores without a network request', () => {
  const e = environment({stored: 'en'});
  assert.equal(e.heading.textContent, resources.en['stamp.heading']);
  assert.equal(e.i18n.language, 'en');
});

test('blocked or invalid storage keeps both languages usable', () => {
  for (const settings of [{blocked: true}, {stored: 'invalid'}]) {
    const e = environment(settings);
    assert.equal(e.i18n.language, 'de');
    e.en.listeners.click();
    assert.equal(e.i18n.language, 'en');
    e.i18n.setLanguage('invalid');
    assert.equal(e.i18n.language, 'en');
  }
});

test('missing English message falls back to German', () => {
  const e = environment({stored: 'en', missingEnglish: true});
  assert.equal(e.i18n.t('stamp.download'), resources.de['stamp.download']);
});

test('search index includes both languages and survives switching', () => {
  const e = environment();
  const label = element({'data-i18n': 'region.oldWorld'}, 'Alte Welt');
  const card = {textContent: 'Mein Bauplan · Alte Welt', querySelectorAll() { return [label]; }};
  const before = e.i18n.searchText(card);
  assert.ok(before.includes('Alte Welt'));
  assert.ok(before.includes('Old World'));
  assert.ok(before.includes('Mein Bauplan'));
  e.en.listeners.click();
  assert.equal(e.i18n.searchText(card), before);
});
