// Exercise the actual manual runtime, including language links from the app.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../templates/user_guide.js'), 'utf8');

function openGuide(language, search) {
  const sections = ['de', 'en'].map(value => ({dataset: {guideLanguage: value}, hidden: value === 'en'}));
  const events = {};
  const document = {
    querySelectorAll(selector) { assert.equal(selector, '[data-guide-language]'); return sections; },
    addEventListener(name, handler) { events[name] = handler; }
  };
  const galleryI18n = {
    language,
    setLanguage(value) { this.language = value; events.gallerylanguagechange(); }
  };
  vm.runInNewContext(source, {document, galleryI18n, URLSearchParams, location: {search}});
  return {sections, galleryI18n};
}

test('app language overrides the browser choice and selects matching screenshots', () => {
  for (const [stored, requested] of [['de', 'en'], ['en', 'de']]) {
    const guide = openGuide(stored, '?lang=' + requested);
    assert.equal(guide.galleryI18n.language, requested);
    assert.equal(guide.sections.find(s => !s.hidden).dataset.guideLanguage, requested);
  }
});

test('switching language retains exactly one visible guide without navigation', () => {
  const guide = openGuide('de', '');
  for (const language of ['en', 'de', 'en']) {
    guide.galleryI18n.setLanguage(language);
    assert.equal(guide.sections.filter(s => !s.hidden).length, 1);
    assert.equal(guide.sections.find(s => !s.hidden).dataset.guideLanguage, language);
  }
});

test('absent or invalid language parameters preserve the normal gallery choice', () => {
  for (const search of ['', '?lang=fr', '?lang=', '?lang=__proto__']) {
    const guide = openGuide('en', search);
    assert.equal(guide.galleryI18n.language, 'en');
    assert.equal(guide.sections[1].hidden, false);
  }
});
