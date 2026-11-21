"""Create a reproducible Git snapshot ZIP and its SHA-256 checksum."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import zipfile


def build_release(version, output):
    if not re.fullmatch(r'v[0-9]+[.][0-9]+[.][0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Use a version such as v0.1.1 or v0.2.0-beta.1')
    root = Path(__file__).resolve().parents[1]
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    prefix = f'AnnoTools-{version}/'
    archive = output / f'AnnoTools-{version}.zip'
    subprocess.run(['git', 'archive', '--format=zip', '--prefix=' + prefix,
                    '-o', str(archive), 'HEAD'], cwd=root, check=True)
    names = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', 'HEAD'], cwd=root)
    tracked = names.decode('utf-8').rstrip('\0').split('\0')
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        files = [name.removeprefix(prefix) for name in package.namelist() if not name.endswith('/')]
        if sorted(files) != sorted(tracked):
            raise ValueError('ZIP does not match the tracked Git snapshot')
        for name in files:
            if (Path(name).name == 'settings.json'
                    or any(part in ('LokaleDaten', 'local-data', '.venv', '__pycache__') for part in Path(name).parts)):
                raise ValueError('Private/generated file in release: ' + name)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.sha256').write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
    print(f'{archive.name}: {len(files)} files; SHA-256 {checksum}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    args = parser.parse_args()
    build_release(args.version, args.output)
