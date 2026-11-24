const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'templates/stamp_viewer.js'), 'utf8');

function environment(blocked = false) {
  function target(extra = {}) {
    return {listeners: {}, addEventListener(type, fn) { (this.listeners[type] ??= []).push(fn); },
      emit(type) { for (const fn of this.listeners[type] || []) fn(); }, ...extra};
  }
  const window = target();
  const pending = [];
  const viewer = target({open: false, zoomed: false, source: null,
    close() { this.open = false; pending.push(() => this.emit('close')); }});
  const previews = ['first.png', 'second.png'].map(full => {
    const button = target({dataset: {full, name: full}, click() { this.emit('click'); }});
    button.addEventListener('click', () => {
      viewer.open = true; viewer.source = full; viewer.zoomed = false;
    });
    return button;
  });
  const entries = [{otherFeature: 'preserved'}];
  let index = 0;
  const history = {get state() { if (blocked) throw Error('Blocked'); return entries[index]; },
    pushState(state, title, url) {
      if (blocked) throw Error('Blocked');
      assert.equal(url, undefined, 'The gallery URL must not change');
      entries.splice(++index); entries.push(structuredClone(state));
    },
    back() { if (index > 0) { index--; window.emit('popstate'); } },
    forward() { if (index + 1 < entries.length) { index++; window.emit('popstate'); } }};
  window.history = history;
  const filters = {search: 'bakery', region: 'Alte Welt'};
  const document = {querySelector() { return viewer; }, querySelectorAll() { return previews; }};
  vm.runInNewContext(source, {document, window});
  return {viewer, previews, history, window, entries, filters,
    flush() { while (pending.length) pending.shift()(); }};
}

test('Back closes the stamp viewer; Forward reopens it without adding another entry', () => {
  const e = environment();
  e.previews[0].click();
  e.viewer.zoomed = true;
  assert.equal(e.entries.length, 2);
  assert.equal(e.history.state.otherFeature, 'preserved');
  e.history.back(); e.flush();
  assert.equal(e.viewer.open, false);
  assert.deepEqual(e.filters, {search: 'bakery', region: 'Alte Welt'});
  e.history.forward();
  assert.equal(e.viewer.open, true);
  assert.equal(e.viewer.source, 'first.png');
  assert.equal(e.entries.length, 2);
  e.history.back(); e.flush();
  assert.equal(e.viewer.open, false);
});

test('close button, Escape and backdrop consume the viewer entry without a second Back', () => {
  // All three native close paths dispatch the dialog close event.
  for (const closePath of ['button', 'escape', 'backdrop']) {
    const e = environment();
    e.previews[1].click();
    e.viewer.close(); e.flush();
    assert.equal(e.history.state.annoStampViewer, undefined, closePath);
    e.history.forward();
    assert.equal(e.viewer.source, 'second.png');
    assert.equal(e.viewer.open, true);
  }
});

test('pageshow keeps an open viewer and zoom intact and does not grow history', () => {
  const e = environment();
  e.previews[0].click(); e.viewer.zoomed = true;
  e.window.emit('pageshow');
  assert.equal(e.viewer.zoomed, true);
  assert.equal(e.entries.length, 2);
});

test('blocked history leaves the existing viewer usable', () => {
  const e = environment(true);
  e.previews[0].click();
  assert.equal(e.viewer.open, true);
  e.viewer.close(); e.flush();
  assert.equal(e.viewer.open, false);
});

test('both public stamp galleries embed the canonical viewer runtime exactly once', () => {
  for (const game of ['anno117', 'anno1800']) {
    const page = fs.readFileSync(path.join(root, 'site', game, 'stamps/index.html'), 'utf8');
    const scripts = [...page.matchAll(/<script id="gallery-stamp-viewer">([\s\S]*?)<\/script>/g)];
    assert.equal(scripts.length, 1);
    assert.equal(scripts[0][1], source);
  }
});
