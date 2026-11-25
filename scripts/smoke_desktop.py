"""Extract and run the portable worker without access to a Python installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile


def extract(archive, destination):
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Extract into a new or empty directory')
    destination.mkdir(parents=True, exist_ok=True)
    checksum = archive.with_suffix('.sha256').read_text(encoding='ascii').split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != checksum:
        raise ValueError('Desktop archive checksum mismatch')
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError('Invalid desktop ZIP')
        for name in package.namelist():
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or '\\' in name:
                raise ValueError('Unsafe archive entry: ' + name)
        package.extractall(destination)
    application = destination / 'AnnoOrganizer'
    manifest = json.loads((application / 'BUILD.json').read_text(encoding='utf-8'))
    resources = application / '_internal'
    for name, expected in manifest['inputs'].items():
        source = (resources / name).resolve()
        if not source.is_relative_to(resources.resolve()):
            raise ValueError('Unsafe resource manifest entry: ' + name)
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Bundled resource mismatch: ' + name)
    if not (application / 'THIRD-PARTY-NOTICES.txt').is_file():
        raise ValueError('Missing third-party notices')
    return application


def run(application, workspace, games):
    before = {p.relative_to(application).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in application.rglob('*') if p.is_file()}
    environment = dict(os.environ)
    environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    environment['PYTHONHOME'] = str(workspace / 'no-python-here')
    environment['PYTHONPATH'] = str(workspace / 'no-python-packages')
    environment.pop('VIRTUAL_ENV', None)
    results = {}
    for game in games:
        config = workspace / (game + '.json')
        config.write_text(json.dumps(dict(version=1, game=game, output=str(workspace / (game + '-output')))),
                          encoding='utf-8')
        completed = subprocess.run([str(application / 'AnnoOrganizer.exe'), '--worker', '--game', game,
                                    '--action', 'demo', '--config', str(config)], cwd=workspace, env=environment,
                                   capture_output=True, text=True, encoding='utf-8', timeout=300)
        events = [json.loads(line) for line in completed.stdout.splitlines()]
        if completed.returncode or not events or events[-1]['payload'].get('status') != 'success':
            raise ValueError('Portable demo failed for ' + game + ': ' + completed.stdout + completed.stderr)
        result = events[-1]['payload']
        expected = 1 if game == 'anno1404' else 2
        if len(result['galleries']) != expected or not all(Path(p).is_file() for p in result['galleries']):
            raise ValueError('Portable galleries missing for ' + game)
        results[game] = result
    report = workspace / 'gui-smoke.json'
    completed = subprocess.run([str(application / 'AnnoOrganizer.exe'), '--ui-smoke', str(report),
                                '--gui-data-dir', str(workspace / 'gui-state')], cwd=workspace,
                               env=environment, capture_output=True, timeout=90)
    if completed.returncode or not report.is_file() or json.loads(report.read_text(encoding='utf-8'))['status'] != 'success':
        raise ValueError('Portable GUI first-launch/worker smoke failed: ' +
                         (report.read_text(encoding='utf-8') if report.is_file() else completed.stderr.decode('utf-8', 'replace')))
    after = {p.relative_to(application).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in application.rglob('*') if p.is_file()}
    if after != before:
        raise ValueError('Portable execution modified its program/resources directory')
    (workspace / 'smoke-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--extract-to', type=Path)
    parser.add_argument('--all-games', action='store_true', help='Require installed 117/1800 game resources too')
    args = parser.parse_args()
    games = ('anno117', 'anno1800', 'anno1404') if args.all_games else ('anno1404',)
    if args.extract_to:
        application = extract(args.archive.resolve(), args.extract_to)
        run(application, args.extract_to.resolve(), games)
    else:
        with tempfile.TemporaryDirectory(prefix='anno-portable-smoke-') as directory:
            workspace = Path(directory)
            application = extract(args.archive.resolve(), workspace)
            run(application, workspace, games)
