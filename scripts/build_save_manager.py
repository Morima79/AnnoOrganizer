"""Build the standalone development save manager using disposable local storage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'anno117/tools'))
from anno_save_editor import temporary_root
from build_desktop import notices


def build(output):
    if os.name != 'nt':
        raise ValueError('Build the Windows application on Windows.')
    subprocess.run([sys.executable, str(ROOT / 'scripts/sync_save_manager.py'), '--check'],
                   cwd=ROOT, check=True)
    output = output.resolve()
    application = output / 'AnnoSaveManager'
    archive_path = output / 'AnnoSaveManager-dev-windows-x64.zip'
    if application.exists() or archive_path.exists():
        raise ValueError('Choose a new output directory; existing builds are preserved.')
    with tempfile.TemporaryDirectory(prefix='anno-save-build-', dir=temporary_root()) as directory:
        work = Path(directory)
        env = dict(os.environ, TEMP=str(work), TMP=str(work), PYTHONDONTWRITEBYTECODE='1',
                   PYINSTALLER_CONFIG_DIR=str(work / 'cache'))
        command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
                   '--windowed', '--name', 'AnnoSaveManager', '--distpath', str(work / 'dist'),
                   '--workpath', str(work / 'build'), '--specpath', str(work),
                   '--icon', str(ROOT / 'desktop/assets/annoorganizer.ico'),
                   '--add-data', str(ROOT / 'anno117/tools/assets/annoorganizer.ico') + os.pathsep + 'assets',
                   str(ROOT / 'anno117/tools/manage_saves.py')]
        subprocess.run(command, cwd=work, env=env, check=True)
        built = work / 'dist/AnnoSaveManager'
        shutil.copy2(ROOT / 'LICENSE', built / 'LICENSE')
        for suffix in ('', '.de'):
            shutil.copy2(ROOT / ('docs/save-manager' + suffix + '.md'), built / ('README' + suffix + '.md'))
        notices(built / 'licenses')
        inputs = ['anno117/tools/' + name for name in ('manage_saves.py', 'anno_save_editor.py',
                  'anno_file_formats.py', 'anno_settings.py', 'anno_installation.py', 'anno_save_ui.py')]
        inputs.append('anno117/tools/assets/annoorganizer.ico')
        (built / 'BUILD.json').write_text(json.dumps(dict(development=True, python=sys.version,
            base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            inputs={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs}),
            indent=2), encoding='utf-8')
        for game, sample in (('anno117', 'Demo-03/demo-03.a8s'), ('anno1800', 'Demo-01/demo-01.a7s')):
            subprocess.run([str(built / 'AnnoSaveManager.exe'), '--self-test', '--game', game,
                            '--sample-save', str(ROOT / game / 'demo/saves' / sample)],
                           check=True, timeout=90, env=env)
        output.mkdir(parents=True, exist_ok=True)
        shutil.copytree(built, application)
    with zipfile.ZipFile(archive_path, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in application.rglob('*'):
            if path.is_file():
                archive.write(path, 'AnnoSaveManager/' + path.relative_to(application).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip():
            raise ValueError('ZIP verification failed.')
    archive_path.with_suffix('.sha256').write_text(
        hashlib.sha256(archive_path.read_bytes()).hexdigest() + '  ' + archive_path.name + '\n', encoding='ascii')
    print(application / 'AnnoSaveManager.exe')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/save-manager-dev')
    build(parser.parse_args().output)
