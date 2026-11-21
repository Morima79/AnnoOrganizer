# Automated publishing

[English](publishing.md) · [Deutsch](publishing.de.md) · [Back to README](../README.md)

Repository maintenance guide: create releases, publish GitHub Pages and refresh the demo galleries.

- **Release ZIP:** Pushing a version tag such as `v0.1.1` starts `.github/workflows/release.yml`. After the Windows tests pass on Python 3.11 and 3.14, it builds `AnnoTools-<version>.zip` and its SHA-256 file from that exact Git snapshot and publishes a GitHub release. Existing releases are not overwritten. `Actions → Release ZIP → Run workflow` creates a downloadable test artifact only, without publishing a release.
- **Website:** Changes to `site/` on `main` are automatically deployed through GitHub Pages after link and local-path validation. The repository needs **GitHub Actions** selected once under `Settings → Pages → Source`.
- **Refreshing demos:** Generate fresh output locally using only the bundled demo inputs. Replace the five `index.html` pages under `site/<game>/maps/` or `stamps/` and only their referenced images. Keep relative image paths, remove absolute local paths, and preserve the links back to the demo landing page. Run `python scripts/validate_site.py` before publishing. Original galleries and personal settings remain unchanged. GitHub does not regenerate these snapshots because some exporters require installed game data.

`site/` contains only HTML and required preview/blueprint images, without game resource archives, caches or private configurations. `scripts/build_release.py` packages tracked files only; local settings and output directories remain excluded.
