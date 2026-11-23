// Execute the shipped catalogue runtime with statistics cards lacking .profiles.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const runtime = fs.readFileSync(path.join(root, 'templates/map_catalog.js'), 'utf8');

function element(dataset = {}) {
  return {dataset, value: '', hidden: false, open: false, listeners: {},
    addEventListener(type, listener) { this.listeners[type] = listener; },
    focus() { this.focused = true; }, scrollIntoView() { this.scrolled = true; },
    click() { this.listeners.click({preventDefault() {}}); }};
}

function environment(source = runtime) {
  const nodes = Object.fromEntries(['query', 'mode', 'sort', 'count', 'variants', 'profile-ranking', 'variant-filters']
    .map(id => [id, element()]));
  nodes.sort.value = 'latest';
  const cards = [
    ['20', '1', ['Mori', 'Zweitprofil'], 'Sandkasten', 10, 100],
    ['7', '2', ['Mori 2'], 'Kampagne', 20, 50],
    ['20', '3', ['Mori'], 'Kampagne', 30, 200]
  ].map(([seed, variant, profiles, mode, latest, totalTime]) => Object.assign(element({
    seed, variant, profiles: JSON.stringify(profiles), mode, latest, first: latest - 5,
    recordDate: latest + 1, totalTime, latestTime: totalTime - 1}), {
    // Reading an optional paragraph is the regression we are preventing.
    querySelector() { throw Error('Card text must not be used for profile filtering'); },
    groups: [{open: true}, {open: false}]
  }));
  nodes.variants.querySelectorAll = () => cards;
  nodes.variants.append = (...ordered) => { nodes.variants.ordered = ordered; };
  const links = ['Mori', 'Mori 2'].map(profileFilter => element({profileFilter}));
  const backs = [element(), element()];
  const chips = [element({filter: '20'})];
  const document = {listeners: {}, querySelector(selector) { return nodes[selector.slice(1)]; },
    querySelectorAll(selector) {
      return {'[data-profile-filter]': links, '[data-back-to-profiles]': backs, '[data-filter]': chips}[selector];
    }, addEventListener(type, listener) { this.listeners[type] = listener; }};
  let language = 'de';
  const galleryI18n = {t(key, {shown, total}) {
    assert.equal(key, 'map.count');
    return language === 'de' ? `${shown} von ${total} Varianten` : `${shown} of ${total} variants`;
  }};
  vm.runInNewContext(source, {document, galleryI18n});
  return {nodes, cards, links, backs, chips,
    search(text) { nodes.query.value = text; nodes.query.listeners.input(); },
    language() { language = 'en'; document.listeners.gallerylanguagechange(); }};
}

test('search and mode filters work without visible profile paragraphs, including zero results', () => {
  const e = environment();
  assert.equal(e.nodes.count.textContent, '3 von 3 Varianten');
  e.search(' MORI ');
  assert.equal(e.nodes.count.textContent, '3 von 3 Varianten');
  e.search('ZWEITPROFIL');
  assert.deepEqual(e.cards.map(card => card.hidden), [false, true, true]);
  e.nodes.mode.value = 'Kampagne'; e.nodes.mode.listeners.change();
  assert.equal(e.nodes.count.textContent, '0 von 3 Varianten');
  e.nodes.mode.value = ''; e.search('7');
  assert.deepEqual(e.cards.map(card => card.hidden), [true, false, true]);
  e.search('unknown');
  assert.equal(e.nodes.count.textContent, '0 von 3 Varianten');
});

test('profile links filter exact names, focus search and scroll down; either back button returns', () => {
  for (const backIndex of [0, 1]) {
    const e = environment();
    e.links[0].click();
    assert.deepEqual(e.cards.map(card => card.hidden), [false, true, false]);
    assert.equal(e.nodes.query.value, 'Mori');
    assert.equal(e.nodes.query.focused, true);
    assert.equal(e.nodes['variant-filters'].scrolled, true);
    assert.ok(e.backs.every(button => !button.hidden));
    e.nodes.mode.value = 'Kampagne'; e.nodes.mode.listeners.change();
    e.backs[backIndex].click();
    assert.equal(e.nodes['profile-ranking'].open, true);
    assert.equal(e.nodes['profile-ranking'].scrolled, true);
    assert.equal(e.links[0].focused, true);
    assert.equal(e.nodes.count.textContent, '3 von 3 Varianten');
    assert.equal(e.nodes.query.value, '');
    assert.equal(e.nodes.mode.value, '');
    assert.ok(e.backs.every(button => button.hidden));
  }
});

test('seed chips reset profile/mode and scroll to filtered results', () => {
  const e = environment();
  e.links[1].click();
  e.nodes.mode.value = 'Kampagne';
  e.chips[0].click();
  assert.equal(e.nodes.query.value, '20');
  assert.equal(e.nodes.mode.value, '');
  assert.deepEqual(e.cards.map(card => card.hidden), [false, true, false]);
  assert.ok(e.backs.every(button => button.hidden));
  assert.equal(e.nodes['variant-filters'].scrolled, true);
});

test('sorting reorders existing cards and language switching preserves filters and details', () => {
  const e = environment();
  assert.deepEqual(e.nodes.variants.ordered.map(card => card.dataset.variant), ['3', '2', '1']);
  e.nodes.sort.value = 'variant'; e.nodes.sort.listeners.change();
  assert.deepEqual(e.nodes.variants.ordered.map(card => card.dataset.variant), ['2', '1', '3']);
  e.nodes.sort.value = 'totalTime'; e.nodes.sort.listeners.change();
  assert.deepEqual(e.nodes.variants.ordered.map(card => card.dataset.variant), ['3', '1', '2']);
  e.links[0].click();
  e.nodes.mode.value = 'Kampagne'; e.nodes.mode.listeners.change();
  e.language();
  assert.equal(e.nodes.count.textContent, '1 of 3 variants');
  assert.equal(e.nodes.query.value, 'Mori');
  assert.equal(e.nodes.mode.value, 'Kampagne');
  assert.equal(e.nodes.sort.value, 'totalTime');
  assert.deepEqual(e.cards.map(card => card.hidden), [true, true, false]);
  assert.deepEqual(e.cards[0].groups.map(group => group.open), [true, false]);
  assert.ok(e.backs.every(button => !button.hidden));
  e.search('Mori 2');
  assert.ok(e.backs.every(button => button.hidden));
});

test('public 117 and 1800 exports embed the identical canonical runtime and shared controls', () => {
  for (const game of ['anno117', 'anno1800']) {
    const page = fs.readFileSync(path.join(root, 'site', game, 'maps/index.html'), 'utf8');
    const script = page.match(/<script id="map-catalog-runtime">([\s\S]*?)<\/script>/);
    assert.ok(script, `${game} must use the shared runtime`);
    assert.equal(script[1], runtime);
    assert.match(page, /class="seed-list"/);
    assert.match(page, /id="variant-filters" class="catalog-controls"/);
    assert.equal((page.match(/data-back-to-profiles/g) || []).length, 3); // Two buttons and script selector.
    environment(script[1]);
  }
});
