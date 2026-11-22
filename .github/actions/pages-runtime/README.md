# Pages runtime compatibility

`actions/deploy-pages@v5` (including v5.0.1) bundles `@actions/artifact` 2.x, which imports Node's deprecated built-in `punycode`. This emits `DEP0040` even on Node 24. The upstream problem is tracked in [actions/deploy-pages#413](https://github.com/actions/deploy-pages/issues/413) and [#434](https://github.com/actions/deploy-pages/issues/434).

The Pages workflow preloads `punycode.mjs` **only for the deploy-pages step**. A synchronous Node module-resolution hook redirects `punycode` and `node:punycode` to the unchanged userland implementation in `vendor/punycode.cjs`. All other modules use normal resolution. The official deployment action, its artifact handling, permissions and OIDC flow remain in place. No warning filters, dependency installation or modifications to the downloaded action bundle are used.

The vendor file is upstream `punycode.js` 2.3.1, renamed to `.cjs` so its CommonJS format is explicit. `vendor/provenance.json` records the immutable upstream commit, filenames and SHA-256 checksums. `vendor/LICENSE-MIT.txt` retains its original licence. The scoped Git attributes preserve those exact LF bytes on Windows as well as Linux.

Run with Node 24:

```sh
node --test tests/pages_runtime.cjs
```

The tests verify the recorded bytes, reproduce `DEP0040` without the preload, test CommonJS and dynamic imports with it, verify Unicode conversions and confirm that unrelated warnings still appear. The workflow runs these tests before deployment; Python's test discovery also runs them when Node 24 or newer is available. Python application users do not need Node.js for the Anno tools themselves.

The unmodified official deploy-pages v5.0.1 bundle was also started locally with and without the preload and **without GitHub/OIDC credentials**. Its normal startup emitted `DEP0040`; the preloaded startup did not. Both stopped at the missing OIDC credential check, before any deployment. Actual publication must still be checked in Actions after committing and pushing the workflow change.

Once an official deploy-pages release upgrades the affected dependency and rebuilds its bundle, verify it without this preload. Then remove the step-local `NODE_OPTIONS`, this directory, its Git attribute and the compatibility tests. Do not replace this correction with `NODE_NO_WARNINGS`, `--no-warnings` or `--no-deprecation`.
