# Automated publishing

[English](publishing.md) · [Deutsch](publishing.de.md) · [Back to README](../README.md)

Repository maintenance guide: create releases, publish GitHub Pages and refresh the demo galleries.

- **Release ZIPs:** Pushing a version tag such as `v0.1.21` starts `.github/workflows/release.yml`. After the Windows tests pass on Python 3.11 and 3.14, it builds `AnnoOrganizer-<version>-windows-x64.zip` and `AnnoSaveManager-<version>-windows-x64.zip`, each with a SHA-256 file, from the tested commit and publishes a GitHub release. Existing releases are not overwritten. `Actions → Release ZIP → Run workflow` creates a downloadable test artifact only, without publishing a release.
- **Release description:** Before tagging, add and commit a section such as `## [v0.1.2] - 2026-11-21` to [CHANGELOG.md](../CHANGELOG.md), with English and German notes. The workflow uses that version section as the GitHub release description. Missing, empty or duplicate entries prevent release publication. A manual ZIP test build also requires an entry for its selected version.
- **Website:** Changes to `site/` on `main` are automatically deployed through GitHub Pages after link and local-path validation. The repository needs **GitHub Actions** selected once under `Settings → Pages → Source`.
- **Refreshing demos:** Generate fresh output locally using only the bundled demo inputs. Replace the five `index.html` pages under `site/<game>/maps/` or `stamps/` and only their referenced images. Keep relative image paths, remove absolute local paths, and preserve the links back to the demo landing page. Run `python scripts/validate_site.py` before publishing. Original galleries and personal settings remain unchanged. GitHub does not regenerate these snapshots because some exporters require installed game data.

`site/` contains HTML, required preview/blueprint images and the six approved demo workbook/ZIP downloads, without game resource archives, caches or private configurations. The release workflow uploads only the two executable packages and their checksums. GitHub automatically provides source ZIP/tar.gz links for each release; a duplicate custom source ZIP is no longer uploaded. The optional `scripts/build_release.py` remains available for local Git-snapshot archives. Local settings and output directories remain excluded.

## Project rename

The repository is [Morima79/AnnoOrganizer](https://github.com/Morima79/AnnoOrganizer), and the demo site is [https://morima79.github.io/AnnoOrganizer/](https://morima79.github.io/AnnoOrganizer/). Existing releases and tags keep their original names and assets; future releases use the new archive name. Do not rebuild or replace published releases for the rename.

Pages uses relative navigation and embedded CSS, JavaScript and language resources, so all five galleries work under the new repository path and when opened locally. The workflow obtains the deployment URL from GitHub Pages rather than hard-coding the repository name. Keep **Settings → Pages → Source → GitHub Actions** selected; pushing the updated `site/` to `main` publishes the renamed content. Check any manually configured repository homepage or external links separately; the old Pages URL may return 404 rather than redirect.

Runtime identifiers consistently use the current project name: `ANNOORGANIZER_SETTINGS`, `.annoorganizer-game.json`, `.annoorganizer.lock`, `.annoorganizer/` output folders and `annoorganizer.gallery.language`. Only these names are supported; there are no aliases or automatic imports for obsolete identifiers. Update local configurations and administrative filenames together before using the renamed tools. Browser language preferences start with the German default until selected again.

## Pages action Node.js warning

The current official `actions/deploy-pages@v5` still bundles a dependency that loads Node's deprecated built-in `punycode`. The workflow therefore uses a [local compatibility adapter](../.github/actions/pages-runtime/README.md) only for that deployment step. It loads the unchanged userland implementation, recorded with its MIT licence and checksums, instead of suppressing warnings. Other warnings, permissions and the OIDC deployment flow are unaffected.

Before deployment, `node --test tests/pages_runtime.cjs` verifies the correction on Node 24. Remove the adapter as described in its guide once an official release fixes the dependency. The correction takes effect on GitHub after committing and pushing the workflow.

## Demo Excel downloads

After exporting only the bundled demo inputs for all three games, run `python scripts/publish_demo_workbooks.py --reports-root local-data/statistics-demo`. Each game must have its report in `<reports-root>/<game>/reports/<game>-map-seeds.xlsx`. The script checks for machine paths and only accepts relative `map-images/*.png` links, then writes the three approved workbooks and ZIPs with their referenced images to `site/downloads/`. ZIPs preserve the relative links for offline use. Personal reports must never be used as publishing inputs. The landing page and both README languages link these snapshots; Pages publishes them with the next authorised site push.

## Portable Windows x64 package

The existing release workflow builds `AnnoOrganizer-<version>-windows-x64.zip` and its SHA-256 file on Windows using Python 3.11 and pinned versions from `requirements-build.txt`. Before publication, the extracted executable must generate the 1404 demo with unusable Python search paths. The existing publishing job then takes both executable ZIPs and their checksums; manual workflow runs remain test artifacts without a release.

Local build from a clean committed state (choose a version label for local testing; never replace existing release assets):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts/build_desktop.py --version v0.1.13-desktop-preview --output dist
.\.venv\Scripts\python.exe scripts/smoke_desktop.py --archive dist/AnnoOrganizer-v0.1.13-desktop-preview-windows-x64.zip
```

`--development` explicitly allows uncommitted changes and marks the ZIP `-dev`; do not present those packages as exact release snapshots. Smoke-test `--all-games` requires installed 117/1800 game resources and checks all five galleries. `--extract-to` retains the package and outputs in a new or empty directory. Altering Python search paths does not replace independent acceptance on a fresh Windows installation.

The builder excludes normal local settings, caches and game resource archives. `BUILD.json` records the commit, runtime versions and resource hashes. Third-party notices include Python and its dependency notices, Pillow, XlsxWriter, tzdata and the PyInstaller bootloader with its built-application exception. For maintenance and constraints, see official [PyInstaller runtime information](https://pyinstaller.org/en/stable/runtime-information.html) and [windowed-mode guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html). Binary identity across different Python versions and Windows toolchains is not promised. The package is unsigned; bundled DE/EN READMEs explain this. Signing remains separate.

The demo landing page links directly to the published Windows ZIP and its versioned release page. When releasing a new desktop version, update both application download URLs in the shared landing-page template and the main/game READMEs, plus `demo.downloadDetails` in the shared locales, then refresh `site/`. Publish the version tag through the existing release workflow and verify the asset before announcing the download.

## Artifact download Node.js warning

`actions/download-artifact@v8` still uses a ZIP extractor that emits `DEP0005` through a deprecated Buffer constructor ([upstream fix](https://github.com/actions/download-artifact/pull/490)). The release workflow keeps the official action and its digest mismatch failure, uses `skip-decompress: true` to save the raw artifact under `runner.temp`, then runs `scripts/extract_desktop_artifact.py`. Python accepts exactly the desktop ZIP and checksum for the requested version, verifies SHA-256 and writes only those two files into `dist/`. Unrelated existing output files are preserved; unexpected members, corrupt archives, mismatched checksums and existing desktop files fail the job. The download step uses `--throw-deprecation` so a new Node deprecation fails the test/build. No Node warning suppression or action bundle patches are used.

Run `python -m unittest discover -s tests -p test_release_artifact.py -v`. After changing the workflow, dispatch a manual `Release ZIP` test build on `main` with a version already documented in the changelog and inspect the download/extraction logs through completion. This creates test artifacts without replacing the published release. Once the official action fixes its extractor, verify normal extraction before removing the raw-download setting and helper.

## Standalone Save Manager release

The same release workflow also builds `AnnoSaveManager-<version>-windows-x64.zip` and `AnnoSaveManager-<version>-windows-x64.sha256` on Windows with pinned dependencies. `scripts/build_save_manager.py --version vX.Y.Z --output dist` requires a clean committed checkout and records the release version, commit and source hashes in `BUILD.json`. Without `--version`, it remains a development build. Before packaging, the frozen executable tests both Anno 117 and Anno 1800 against isolated approved demo copies. The complete application folder, offline DE/EN guides and licence notices are included; private saves and settings are excluded.

Publication waits for both Windows packages. The Save Manager artifact uses the same raw download, digest validation and strict Python extraction as the desktop artifact, with `--package save-manager`. A manual workflow run produces both executable ZIPs and their checksums without publishing a release.
