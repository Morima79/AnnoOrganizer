"""Build the Windows onedir GUI from tracked inputs and write a portable ZIP."""
import argparse
import ast
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GAMES = ('anno117', 'anno1800', 'anno1404')


def payload_files(root, tracked):
    """Allow only source resources and approved demo inputs, never local output."""
    selected = []
    for name in tracked:
        path = Path(name)
        parts = path.parts
        allowed = name in ('LICENSE', 'CHANGELOG.md', 'README.md', 'README.de.md')
        allowed |= len(parts) >= 2 and parts[0] == 'desktop' and path.suffix in ('.py', '.json', '.ico')
        allowed |= len(parts) >= 2 and parts[0] == 'docs' and path.suffix in ('.md', '.html', '.png', '.jpg', '.svg')
        if parts and parts[0] in GAMES:
            allowed |= len(parts) >= 3 and parts[1] == 'tools' and path.suffix in ('.py', '.json', '.html', '.js', '.css')
            allowed |= len(parts) >= 3 and parts[1] == 'demo'
            allowed |= len(parts) == 4 and parts[1:3] == ('docs', 'images') and path.suffix in ('.png', '.jpg')
            allowed |= len(parts) == 2 and parts[1] in ('settings.example.json', 'LICENSE')
        if not allowed:
            continue
        if (path.is_absolute() or '..' in parts or path.name in ('settings.json', 'gui.json')
                or (path.name.startswith('settings.') and path.name.endswith('.local.json'))
                or any(p in ('local-data', '.venv', '__pycache__', 'logs', 'backups', '.annoorganizer') for p in parts)
                or (path.suffix.lower() in ('.rda', '.db', '.log', '.zip', '.xlsx') )):
            raise ValueError('Private or generated build input: ' + name)
        source = root / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing or linked build input: ' + name)
        selected.append(name)
    for game in GAMES:
        manifest = json.loads((root / game / 'demo/manifest.json').read_text(encoding='utf-8'))
        approved = {game + '/demo/' + item['file'] for item in manifest['saves'] + manifest['stamps']}
        approved.update(game + '/demo/' + name for name in ('manifest.json', 'README.md', 'README.de.md'))
        if any(name.startswith(game + '/demo/') and name not in approved for name in selected):
            raise ValueError('Unapproved demo input in desktop payload')
    required = ['desktop/app.py', 'desktop/locales/de.json', 'desktop/locales/en.json',
                'desktop/assets/annoorganizer.ico', 'LICENSE']
    required += [game + '/tools/anno_worker.py' for game in GAMES]
    if any(name not in selected for name in required):
        raise ValueError('Desktop resources are incomplete')
    return sorted(selected)


def hidden_imports(root, names):
    local = {Path(name).stem for name in names if '/tools/' in name and name.endswith('.py')}
    imports = set()
    for name in names:
        if not name.endswith('.py'):
            continue
        for node in ast.walk(ast.parse((root / name).read_text(encoding='utf-8'))):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else [])
            imports.update(module for module in modules if module.split('.')[0] not in local)
    return sorted(imports)


def pyinstaller_command(source_root, work, payload):
    """Use the runtime window icon for the executable's Windows resources too."""
    return [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--windowed',
            '--name', 'AnnoOrganizer', '--icon', str(source_root / 'desktop/assets/annoorganizer.ico'),
            '--distpath', str(work / 'dist'), '--workpath', str(work / 'build'), '--specpath', str(work),
            '--add-data', str(payload) + os.pathsep + '.',
            '--collect-all', 'PIL', '--collect-all', 'xlsxwriter', '--collect-all', 'tzdata']


def notices(destination):
    lines = ['Third-party components', '', 'ANNO - Organizer: Morima79, MIT; see LICENSE.',
             'Python ' + platform.python_version() + ': https://www.python.org/',
             'Tcl/Tk: https://www.tcl.tk/ (notices included in the Python distribution license)', '']
    for package in ('Pillow', 'XlsxWriter', 'tzdata', 'PyInstaller'):
        distribution = metadata.distribution(package)
        lines += [package + ' ' + distribution.version, 'Source: https://pypi.org/project/' + package + '/', '']
        count = 0
        for file in distribution.files or []:
            if any(word in str(file).lower() for word in ('license', 'copying', 'notice')):
                source = Path(distribution.locate_file(file))
                if source.is_file() and source.suffix.lower() not in ('.py', '.pyc'):
                    target = destination / package / str(file).replace('..', '_')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    count += 1
        if not count:
            raise ValueError('Missing license text for ' + package)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise ValueError('Missing Python distribution license')
    for source in [python_license,
                   *Path(sys.base_prefix).glob('tcl/*/license.terms')]:
        if source.is_file():
            target = destination / 'Python' / source.parent.name / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (destination.parent / 'THIRD-PARTY-NOTICES.txt').write_text('\n'.join(lines), encoding='utf-8')


def build(version, output, development=False):
    if os.name != 'nt':
        raise ValueError('Build the Windows package on Windows')
    if platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('Use an x64 Python environment for the x64 package')
    for line in (ROOT / 'requirements-build.txt').read_text(encoding='utf-8').splitlines():
        if '==' in line and not line.startswith('#'):
            name, expected = line.split('==', 1)
            if metadata.version(name) != expected:
                raise ValueError('Install the pinned build dependencies: ' + name)
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Use a semantic version starting with v')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT))
    if dirty and not development:
        raise ValueError('Commit tracked changes before a release build, or use --development')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').rstrip('\0').split('\0')
    required_build = ('desktop_entry.py', 'requirements-build.txt', 'packaging/README.md', 'packaging/README.de.md')
    if any(name not in tracked for name in required_build) and not development:
        raise ValueError('The desktop entry point and build resources must be committed')
    with tempfile.TemporaryDirectory(prefix='anno-desktop-', dir=output) as directory:
        work = Path(directory)
        source_root = ROOT
        if not development:
            snapshot = work / 'snapshot.zip'
            subprocess.run(['git', 'archive', '--format=zip', '-o', str(snapshot), 'HEAD'], cwd=ROOT, check=True)
            source_root = work / 'source'
            with zipfile.ZipFile(snapshot) as package:
                package.extractall(source_root)
        names = payload_files(source_root, tracked)
        payload = work / 'payload'
        manifest = {}
        for name in names:
            target = payload / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_root / name, target)
            manifest[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        command = pyinstaller_command(source_root, work, payload)
        for module in hidden_imports(source_root, names):
            command += ['--hidden-import', module]
        command.append(str(source_root / 'desktop_entry.py'))
        epoch = subprocess.check_output(['git', 'show', '-s', '--format=%ct', 'HEAD'], cwd=ROOT, text=True).strip()
        subprocess.run(command, cwd=source_root, env=dict(os.environ, SOURCE_DATE_EPOCH=epoch), check=True)
        application = work / 'dist/AnnoOrganizer'
        shutil.copy2(source_root / 'LICENSE', application / 'LICENSE')
        for language in ('', '.de'):
            shutil.copy2(source_root / ('packaging/README' + language + '.md'), application / ('README' + language + '.md'))
        notices(application / 'licenses')
        (application / 'BUILD.json').write_text(json.dumps(dict(version=version, commit=commit,
            development=development, python=sys.version, inputs=manifest,
            entry_sha256=hashlib.sha256((source_root / 'desktop_entry.py').read_bytes()).hexdigest(),
            packages={name: metadata.version(name) for name in ('PyInstaller', 'Pillow', 'XlsxWriter', 'tzdata')}),
            indent=2), encoding='utf-8')
        archive = output / ('AnnoOrganizer-' + version + '-windows-x64' + ('-dev' if development else '') + '.zip')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
            for path in sorted(application.rglob('*')):
                if path.is_file():
                    package.write(path, 'AnnoOrganizer/' + path.relative_to(application).as_posix())
        with zipfile.ZipFile(archive) as package:
            if package.testzip() is not None:
                raise ValueError('Desktop ZIP integrity check failed')
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix('.sha256').write_text(digest + '  ' + archive.name + '\n', encoding='ascii')
        print(str(archive))
        return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--development', action='store_true')
    options = parser.parse_args()
    build(options.version, options.output, options.development)
