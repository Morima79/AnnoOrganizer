const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const runtime = fs.readFileSync(path.join(root, 'templates/map_viewer.js'), 'utf8');
const historyRuntime = fs.readFileSync(path.join(root, 'templates/stamp_viewer.js'), 'utf8');

function environment() {
  const element = (extra = {}) => ({listeners: {}, dataset: {}, attributes: {},
    addEventListener(type, fn) { (this.listeners[type] ??= []).push(fn); },
    emit(type, event = {}) { for (const fn of this.listeners[type] || []) fn(event); },
    setAttribute(key, value) { this.attributes[key] = value; },
    getAttribute(key) { return this.attributes[key]; },
    click(event = {}) { this.emit('click', {button: 0, preventDefault() { this.prevented = true; }, ...event}); }, ...extra});
  const nodes = Object.fromEntries(['viewer', 'full', 'modalname', 'download', 'zoom', 'close'].map(id => [id, element()]));
  const pending = [];
  nodes.viewer.dataset.historyKey = 'annoMapViewer';
  nodes.viewer.open = false;
  nodes.viewer.showModal = function() { this.open = true; };
  nodes.viewer.close = function() { this.open = false; pending.push(() => this.emit('close')); };
  const classes = new Set();
  nodes.full.classList = {contains(c) { return classes.has(c); }, remove(c) { classes.delete(c); },
    toggle(c) { if (classes.has(c)) classes.delete(c); else classes.add(c); }};
  nodes.full.parentElement = {scrollTop: 50, scrollLeft: 75};
  const image = {alt: 'Inselkarte Seed 1234'};
  const link = element({attributes: {href: 'map-images/map.png'}, querySelector() { return image; }});
  const topLink = element({querySelector() { return null; }});
  const document = element({querySelector(selector) { return nodes[selector.slice(1)]; },
    querySelectorAll(selector) { return selector === 'article a[href]' ? [link, topLink] : [link]; }});
  const window = element();
  const entries = [{annoMapCatalog: {query: '1234', mode: 'Kampagne'}}];
  let index = 0;
  window.history = {get state() { return entries[index]; },
    pushState(state, title, url) { assert.equal(url, undefined); entries.splice(++index); entries.push(structuredClone(state)); },
    back() { if (index) { index--; window.emit('popstate'); } },
    forward() { if (index + 1 < entries.length) { index++; window.emit('popstate'); } }};
  const galleryI18n = {t(key) { return key; }};
  const context = vm.createContext({document, window, galleryI18n});
  vm.runInContext(runtime, context);
  vm.runInContext(historyRuntime, context);
  return {nodes, link, topLink, image, entries, window, document,
    flush() { while (pending.length) pending.shift()(); }};
}

test('map links open a labelled dialog with download, fit/original zoom and scroll reset', () => {
  const e = environment();
  const event = {button: 0, prevented: false, preventDefault() { this.prevented = true; }};
  e.link.emit('click', event);
  assert.equal(event.prevented, true);
  assert.equal(e.nodes.viewer.open, true);
  assert.equal(e.nodes.full.src, 'map-images/map.png');
  assert.equal(e.nodes.modalname.textContent, 'Inselkarte Seed 1234');
  assert.equal(e.nodes.download.href, 'map-images/map.png');
  assert.equal(e.nodes.download.download, 'map.png');
  assert.equal(e.nodes.full.parentElement.scrollTop, 0);
  assert.equal(e.nodes.full.parentElement.scrollLeft, 0);
  e.nodes.zoom.click();
  assert.equal(e.nodes.full.classList.contains('zoomed'), true);
  assert.equal(e.nodes.zoom.attributes['aria-pressed'], 'true');
  e.nodes.full.click();
  assert.equal(e.nodes.full.classList.contains('zoomed'), false);
});

test('map Back/Forward and explicit close share the stamp navigation without losing filters', () => {
  const e = environment();
  e.link.click();
  assert.equal(e.entries.length, 2);
  assert.equal(e.window.history.state.annoMapCatalog.query, '1234');
  e.window.history.back(); e.flush();
  assert.equal(e.nodes.viewer.open, false);
  assert.equal(e.window.history.state.annoMapCatalog.query, '1234');
  e.window.history.forward();
  assert.equal(e.nodes.viewer.open, true);
  assert.equal(e.entries.length, 2);
  e.nodes.close.click(); e.flush();
  assert.equal(e.window.history.state.annoMapViewer, undefined);
});

test('language switching retains zoom and uses the translated source image label', () => {
  const e = environment();
  e.link.click(); e.nodes.zoom.click();
  e.image.alt = 'Island map Seed 1234';
  e.document.emit('gallerylanguagechange');
  assert.equal(e.nodes.full.alt, 'Island map Seed 1234');
  assert.equal(e.nodes.modalname.textContent, 'Island map Seed 1234');
  assert.equal(e.nodes.full.classList.contains('zoomed'), true);
  assert.equal(e.nodes.zoom.dataset.i18n, 'viewer.fit');
});

test('modified clicks retain native navigation and ordinary non-image links are untouched', () => {
  for (const event of [{ctrlKey: true}, {metaKey: true}, {shiftKey: true}, {altKey: true}, {button: 1}]) {
    const e = environment(); e.link.click(event);
    assert.equal(e.nodes.viewer.open, false);
    assert.equal(e.entries.length, 1);
    assert.equal(e.topLink.listeners.click, undefined);
  }
});

test('all three public map galleries embed the same dialog and runtimes once', () => {
  for (const game of ['anno117', 'anno1800', 'anno1404']) {
    const page = fs.readFileSync(path.join(root, 'site', game, 'maps/index.html'), 'utf8');
    assert.equal((page.match(/<dialog id="viewer"/g) || []).length, 1);
    assert.equal(page.match(/<script id="gallery-map-viewer">([\s\S]*?)<\/script>/)[1], runtime);
    assert.equal(page.match(/<script id="gallery-stamp-viewer">([\s\S]*?)<\/script>/)[1], historyRuntime);
  }
});
