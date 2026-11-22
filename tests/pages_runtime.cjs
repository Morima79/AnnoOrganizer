// Validate the real preload in isolated Node processes without deployment tokens.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');
const runtime = path.join(root, '.github/actions/pages-runtime');
const preload = pathToFileURL(path.join(runtime, 'punycode.mjs')).href;

function run(source, {adapted = true, strict = true} = {}) {
  const env = {...process.env};
  // No inherited flags may hide the warning or affect the baseline.
  delete env.NODE_OPTIONS;
  delete env.NODE_NO_WARNINGS;
  const args = [...(strict ? ['--throw-deprecation'] : []), ...(adapted ? ['--import', preload] : []), '-e', source];
  return spawnSync(process.execPath, args, {env, encoding: 'utf8'});
}

test('vendored implementation and licence match their recorded upstream bytes', () => {
  const provenance = JSON.parse(fs.readFileSync(path.join(runtime, 'vendor/provenance.json'), 'utf8'));
  for (const [name, metadata] of Object.entries(provenance.files)) {
    const bytes = fs.readFileSync(path.join(runtime, 'vendor', name));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), metadata.sha256, name);
  }
});

test('baseline reproduces DEP0040 under the Node 24 runtime', () => {
  const result = run("require('punycode')", {adapted: false});
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /DEP0040/);
});

test('both core import names use userland punycode without deprecation', () => {
  const result = run(`
    const assert = require('node:assert/strict');
    const plain = require('punycode');
    const prefixed = require('node:punycode');
    assert.equal(plain, prefixed);
    assert.equal(plain.version, '2.3.1');
    assert.equal(plain.toASCII('bücher.example'), 'xn--bcher-kva.example');
    assert.equal(plain.toUnicode('xn--bcher-kva.example'), 'bücher.example');
    assert.deepEqual(plain.ucs2.decode('💡'), [0x1F4A1]);
    assert.equal(plain.ucs2.encode([0x1F4A1]), '💡');
    assert.equal(require('fs'), require('node:fs'));
  `);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
});

test('dynamic imports are supported without loading the deprecated core module', () => {
  const result = run("import('node:punycode').then(p => { if(p.default.toASCII('mañana.com') !== 'xn--maana-pta.com') process.exitCode=1; })");
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
});

test('unrelated warnings remain visible and strict deprecation still fails', () => {
  const source = "process.emitWarning('Still visible', {type:'DeprecationWarning', code:'DEP_TEST'})";
  const visible = run(source, {strict: false});
  assert.equal(visible.status, 0);
  assert.match(visible.stderr, /DEP_TEST.*Still visible/);
  const strict = run(source);
  assert.notEqual(strict.status, 0);
  assert.match(strict.stderr, /DEP_TEST/);
});

test('workflow scopes the preload to deploy-pages and retains Pages permissions', () => {
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/pages.yml'), 'utf8');
  assert.match(workflow, /uses: actions\/deploy-pages@v5\s+env:\s+NODE_OPTIONS: --import=\$\{\{ github.workspace \}\}\/\.github\/actions\/pages-runtime\/punycode.mjs/);
  assert.equal((workflow.match(/NODE_OPTIONS:/g) || []).length, 1);
  assert.doesNotMatch(workflow, /NODE_NO_WARNINGS|--no-warnings|--no-deprecation/);
  assert.match(workflow, /pages: write/);
  assert.match(workflow, /id-token: write/);
  assert.match(workflow, /run: node --test tests\/pages_runtime.cjs/);
});
