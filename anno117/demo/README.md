# Anno 117: Pax Romana: demo files

[English](README.md) · [Deutsch](README.de.md)

These examples were selected from the project owner's files for the bundled tool demo. Save files are unchanged binary copies. Anno 117 packages contain selected stamp records without layout changes; Anno 1800 stamps are unchanged copies. `manifest.json` lists paths, sizes and SHA-256 checksums. No game resources, account databases or extracted assets are included.

## Saves

The saves include settled islands with stored population and residence counts.

- `saves/Demo-01/demo-01.a8s` – Seed 31031979
- `saves/Demo-02/demo-02.a8s` – Seed 3087
- `saves/Demo-03/demo-03.a8s` – Seed 8163

## Stamps

- Startstadt – Liberti und Plebejer
- Baelo Claudia
- Pompeji – Cinis
- Lavendel ohne CDLC
- Lavendel ohne Ceres

Run **Launch.cmd** in the parent folder and choose **Demo**, or use `python launch.py --action demo`. The demo reads only the bundled inputs and writes to the configured output directory under `demo/`. It does not install the samples into the game or alter personal libraries. The files demonstrate analysis; loading saves in the game may depend on the corresponding game version and content.
