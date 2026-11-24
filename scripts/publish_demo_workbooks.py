"""Copy approved demo reports and package their referenced map images for offline use."""
import argparse
from pathlib import Path, PurePosixPath
import re
import shutil
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
GAMES = ('anno117', 'anno1800', 'anno1404')


def workbook_images(workbook):
    """Accept only relative map-image links, never arbitrary files or machine paths."""
    images = set()
    with ZipFile(workbook) as package:
        if package.testzip() is not None:
            raise ValueError('Invalid workbook ZIP: ' + str(workbook))
        for name in package.namelist():
            if not name.endswith(('.xml', '.rels')):
                continue
            text = package.read(name).decode('utf-8')
            if re.search(r'(?:(?<![A-Za-z])[A-Za-z]:[\\/]|file:/{2,}|OneDrive)', text):
                raise ValueError('Local machine path in demo workbook: ' + str(workbook))
            if not name.endswith('.rels'):
                continue
            for link in ET.fromstring(text):
                if link.get('TargetMode') != 'External':
                    continue
                target = unquote(link.get('Target', '')).replace('\\', '/')
                path = PurePosixPath(target)
                if (len(path.parts) != 2 or path.parts[0] != 'map-images'
                        or path.suffix.lower() != '.png' or '..' in path.parts):
                    raise ValueError('Unexpected workbook link: ' + target)
                images.add(path.as_posix())
    if not images:
        raise ValueError('Demo workbook has no map-image links: ' + str(workbook))
    return sorted(images)


def publish(reports_root, output):
    output = Path(output)
    # Validate every input before updating the public snapshots.
    reports = []
    for game in GAMES:
        report = Path(reports_root) / game / 'reports' / f'{game}-map-seeds.xlsx'
        images = workbook_images(report)
        for image in images:
            if not (report.parent / image).is_file():
                raise ValueError('Missing map image: ' + image)
        reports.append((game, report, images))
    output.mkdir(parents=True, exist_ok=True)
    for game, report, images in reports:
        target = output / f'{game}-map-demo.xlsx'
        shutil.copyfile(report, target)
        with ZipFile(output / f'{game}-map-demo.zip', 'w', ZIP_DEFLATED) as package:
            package.write(target, target.name)
            for image in images:
                package.write(report.parent / image, image)
        print(f'{game}: demo workbook and offline ZIP with {len(images)} map images')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports-root', type=Path, default=ROOT / 'local-data/statistics-demo')
    parser.add_argument('--output', type=Path, default=ROOT / 'site/downloads')
    args = parser.parse_args()
    publish(args.reports_root, args.output)
