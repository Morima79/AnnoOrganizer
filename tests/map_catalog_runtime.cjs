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

function environment(source = runtime, history = {state: null}) {
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
  history.replaceState ??= function(state) { this.state = structuredClone(state); };
  const window = {history, listeners: {},
    addEventListener(type, listener) { this.listeners[type] = listener; }};
  vm.runInNewContext(source, {document, galleryI18n, window});
  return {nodes, cards, links, backs, chips, history, window,
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

test('image navigation and back restore exact profile, mode and sort on a fresh page', () => {
  const before = environment();
  before.links[0].click();
  before.nodes.mode.value = 'Kampagne'; before.nodes.mode.listeners.change();
  before.nodes.sort.value = 'variant'; before.nodes.sort.listeners.change();
  const after = environment(runtime, before.history);
  assert.equal(after.nodes.query.value, 'Mori');
  assert.equal(after.nodes.mode.value, 'Kampagne');
  assert.equal(after.nodes.sort.value, 'variant');
  assert.deepEqual(after.cards.map(card => card.hidden), [true, true, false]);
  assert.ok(after.backs.every(button => !button.hidden));
  after.backs[0].click();
  assert.equal(after.links[0].focused, true);
});

test('back restores search and zero results, including browser-restored controls on pageshow', () => {
  const before = environment();
  before.search('unknown');
  const after = environment(runtime, before.history);
  assert.equal(after.nodes.count.textContent, '0 von 3 Varianten');
  after.nodes.query.value = '';
  after.window.listeners.pageshow();
  assert.equal(after.nodes.query.value, 'unknown');
  assert.equal(after.nodes.count.textContent, '0 von 3 Varianten');
});

test('history state remains entry-local, preserves other state and tolerates blocked history', () => {
  const first = environment(runtime, {state: {otherFeature: 7}});
  first.search('20');
  assert.equal(first.history.state.otherFeature, 7);
  assert.equal(environment().nodes.query.value, '');
  const blocked = environment(runtime, {
    get state() { throw Error('Blocked'); }, replaceState() { throw Error('Blocked'); }
  });
  blocked.search('7');
  blocked.window.listeners.pageshow();
  assert.equal(blocked.nodes.count.textContent, '1 von 3 Varianten');
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

function environment1404(history = {state: null}) {
  const source = fs.readFileSync(path.join(root, 'anno1404/tools/map_gallery_template.html'), 'utf8')
    .match(/<script>([\s\S]*?)<\/script>/)[1];
  const nodes = Object.fromEntries(['cards', 'query', 'edition', 'sort', 'count', 'filter', 'rangliste']
    .map(id => [id, element()]));
  nodes.sort.value = 'timestamp';
  const rows = ['Mori', 'Mori 2'].map((profile, index) => element({
    profiles: JSON.stringify([profile]), editions: JSON.stringify([index ? 'Venedig' : 'History Edition']),
    seed: index + 1, timestamp: index + 2, oldest: index, time: index + 10
  }));
  const backs = [element(), element()];
  const links = ['Mori', 'Mori 2'].map(profile => element({profile}));
  nodes.cards.querySelectorAll = () => rows;
  nodes.cards.append = () => {};
  const window = {history, listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; }};
  history.replaceState ??= function(state) { this.state = structuredClone(state); };
  const document = {querySelector(selector) { return nodes[selector.slice(1)]; },
    querySelectorAll(selector) { return selector === '.back' ? backs : links; }, addEventListener() {}};
  const galleryI18n = {searchText(row) { return row.dataset.profiles; },
    t(key, {shown, total}) { return `${shown}/${total}`; }};
  vm.runInNewContext(source, {document, galleryI18n, window});
  return {nodes, rows, backs, links, history, window};
}

test('1404 restores exact profile, edition and sort after image navigation and Back', () => {
  const before = environment1404();
  before.links[0].click();
  before.nodes.edition.value = 'Venedig'; before.nodes.edition.listeners.input();
  before.nodes.sort.value = 'seed'; before.nodes.sort.listeners.input();
  const after = environment1404(before.history);
  assert.equal(after.nodes.edition.value, 'Venedig');
  assert.equal(after.nodes.sort.value, 'seed');
  assert.equal(after.nodes.count.textContent, '0/2 · Mori');
  assert.ok(after.backs.every(button => !button.hidden));
  after.nodes.edition.value = '';
  after.window.listeners.pageshow();
  assert.equal(after.nodes.edition.value, 'Venedig');
  after.backs[0].click();
  assert.equal(after.nodes.count.textContent, '2/2');
});

test('1404 restores search and works with blocked history', () => {
  const before = environment1404();
  before.nodes.query.value = 'Mori 2'; before.nodes.query.listeners.input();
  assert.equal(environment1404(before.history).nodes.count.textContent, '1/2');
  const blocked = environment1404({get state() { throw Error('Blocked'); },
    replaceState() { throw Error('Blocked'); }});
  blocked.nodes.query.value = 'missing'; blocked.nodes.query.listeners.input();
  blocked.window.listeners.pageshow();
  assert.equal(blocked.nodes.count.textContent, '0/2');
});
