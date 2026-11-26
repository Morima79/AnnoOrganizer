"""Stage gallery outputs outside OneDrive and retain failed-publication recovery."""
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


class RecoveryError(OSError):
    """Publication left recovery files that must survive context cleanup."""


def outside_onedrive(path):
    """Reject configured and recognisable OneDrive locations after resolution."""
    path = Path(path).resolve()
    roots = [Path(os.environ[key]).resolve() for key in
             ('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial') if os.environ.get(key)]
    return not any(path.is_relative_to(root) for root in roots) and not any(
        part.lower() == 'onedrive' or part.lower().startswith('onedrive - ') for part in path.parts)


def staging_directory(prefix='.annoorganizer-stage-'):
    """Allocate an owned working directory outside synchronised output folders."""
    configured = os.environ.get('ANNOORGANIZER_TEMP_DIR', '').strip()
    candidates = [Path(os.path.expandvars(configured)).expanduser()] if configured else []
    candidates.append(Path(tempfile.gettempdir()))
    for candidate in candidates:
        if not candidate.is_absolute() or not candidate.is_dir() or not outside_onedrive(candidate):
            continue
        try:
            return Path(tempfile.mkdtemp(prefix=prefix, dir=candidate)).resolve()
        except OSError:
            continue
    raise OSError('Kein beschreibbarer temporärer Ordner ausserhalb von OneDrive verfügbar.')


def cleanup_directory(root):
    """Remove only an owned working tree, retrying copied read-only attributes."""
    if root.is_symlink() or root.resolve() != root or getattr(root.lstat(), 'st_file_attributes', 0) & 0x400:
        raise ValueError('Temporärer Ausgabeordner ist nicht mehr sicher erreichbar.')
    def retry_readonly(function, path, exc_info):
        if not isinstance(exc_info[1], PermissionError):
            raise exc_info[1]
        path = Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Arbeitskopie ist nicht mehr sicher erreichbar: ' + str(path))
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
        function(path)
    shutil.rmtree(root, onerror=retry_readonly)


@contextmanager
def temporary_directory(prefix):
    """Retain rollback files if publication could not restore an output."""
    root = staging_directory(prefix)
    keep = False
    try:
        yield str(root)
    except RecoveryError:
        keep = True
        raise
    finally:
        if not keep and not (root / 'RECOVERY.json').exists():
            cleanup_directory(root)


def replace_file(source, target):
    """Support different temporary/output volumes without masking other errors."""
    try:
        os.replace(source, target)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        # The caller journals before copying so a partially written file rolls back.
        shutil.copyfile(source, target)
        Path(source).unlink()


def restore_files(journal):
    """Return unresolved rollback records; unchanged locked files need no restore."""
    failures = []
    for target, backup in reversed(journal):
        try:
            if backup is None:
                target.unlink(missing_ok=True)
            elif not target.is_file() or fingerprint(target) != fingerprint(backup):
                replace_file(backup, target)
        except OSError:
            failures.append(dict(target=str(target), backup=str(backup) if backup else None))
    return failures


def publish_files(pairs, backup_root):
    """Publish map files with recovery data kept outside the final output tree."""
    backup_root.mkdir(parents=True)
    journal = []
    try:
        for index, (source, target) in enumerate(pairs):
            backup = backup_root / str(index) if target.is_file() else None
            if backup is not None:
                shutil.copy2(target, backup)
            journal.append((target, backup))
            replace_file(source, target)
    except BaseException as original:
        failures = restore_files(journal)
        if failures:
            manifest = backup_root.parent / 'RECOVERY.json'
            try:
                manifest.write_text(json.dumps(failures, indent=2), encoding='utf-8')
            except OSError:
                pass
            raise RecoveryError('Wiederherstellung unvollständig. Sicherungsdaten bleiben erhalten: '
                                + str(backup_root.parent)) from original
        raise


def fingerprint(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def files_in(root):
    """Reject output-tree links instead of following them into unrelated data."""
    files = {}
    if not root.exists():
        return files
    pending = [root]
    while pending:
        folder = pending.pop()
        for path in folder.iterdir():
            stat = path.lstat()
            if path.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Verknüpfungen innerhalb der Ausgabe werden nicht unterstützt: ' + str(path))
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                files[path.relative_to(root).as_posix()] = fingerprint(path)
            else:
                raise ValueError('Unbekannter Dateityp in der Ausgabe: ' + str(path))
    return files


class StagedTree:
    def __init__(self, target, subfolder):
        self.target = Path(target).resolve()
        self.before = files_in(self.target)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.root = staging_directory()
        self._owned_root = self.root
        self.stage = self.root / subfolder
        self.stage.mkdir(parents=True)
        self.keep = False
        try:
            if self.target.exists():
                shutil.copytree(self.target, self.stage, dirs_exist_ok=True)
                # OneDrive and Windows directory metadata may copy read-only flags.
                # Change attributes only inside our owned working copy.
                for folder, directories, filenames in os.walk(self.stage):
                    for path in [Path(folder), *(Path(folder) / name for name in filenames)]:
                        self.make_writable(path)
        except BaseException:
            self.cleanup()
            raise

    def make_writable(self, path):
        path = Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError('Arbeitskopie ist nicht mehr sicher erreichbar: ' + str(path))
        path.chmod(path.stat().st_mode | stat.S_IWRITE)

    def cleanup(self):
        if not self.keep:
            if self.root != self._owned_root or self.root.is_symlink() or getattr(self.root.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('Temporärer Ausgabeordner ist nicht mehr sicher erreichbar.')
            cleanup_directory(self.root)


def publish(trees, checkpoint):
    changes, removals = [], []
    for tree in trees:
        if files_in(tree.target) != tree.before:
            raise ValueError('Die Ausgabe wurde während der Verarbeitung extern geändert: ' + str(tree.target))
        after = files_in(tree.stage)
        changes.extend((tree, name) for name, digest in after.items() if tree.before.get(name) != digest)
        removals.extend((tree, name) for name in tree.before.keys() - after.keys())
    checkpoint()
    journal = []
    try:
        # Publish resources first, HTML entry points last, obsolete resources after HTML.
        for tree, name in sorted(changes, key=lambda item: (item[1].lower().endswith('.html'), item[1])):
            target = tree.target / name
            target.parent.mkdir(parents=True, exist_ok=True)
            backup = tree.root / 'rollback' / name if name in tree.before else None
            if backup is not None:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            journal.append((tree, target, backup))
            replace_file(tree.stage / name, target)
        for tree, name in removals:
            target, backup = tree.target / name, tree.root / 'rollback' / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            journal.append((tree, target, backup))
            target.unlink()
    except BaseException as original:
        failures = []
        recovery = []
        for tree, target, backup in reversed(journal):
            try:
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    if not target.is_file() or fingerprint(target) != fingerprint(backup):
                        replace_file(backup, target)
            except OSError as exc:
                tree.keep = True
                failures.append(str(exc))
                recovery.append((tree, dict(target=str(target), backup=str(backup) if backup else None)))
        if failures:
            # Never delete the only remaining copy if a viewer/editor blocks rollback.
            roots = ', '.join(str(tree.root) for tree in trees if tree.keep)
            for tree in trees:
                if tree.keep:
                    try:
                        (tree.root / 'RECOVERY.json').write_text(json.dumps(
                            [record for owner, record in recovery if owner is tree], indent=2), encoding='utf-8')
                    except OSError:
                        pass
            raise OSError('Wiederherstellung unvollständig. Sicherungsdaten bleiben erhalten: ' + roots) from original
        raise


@contextmanager
def stamp_transaction(settings, checkpoint):
    """Preserve references/caches and publish only after complete generation."""
    checkpoint()
    stamp_target = settings.stamp_output.resolve()
    cache_target = (settings.report_output / 'stamp-gallery').resolve()
    if stamp_target.is_relative_to(cache_target) or cache_target.is_relative_to(stamp_target):
        raise ValueError('Stempelausgabe und Ressourcen-Cache dürfen sich nicht überschneiden.')
    trees = []
    try:
        stamps = StagedTree(settings.stamp_output, 'stamps')
        trees.append(stamps)
        cache = StagedTree(settings.report_output / 'stamp-gallery', 'reports/stamp-gallery')
        trees.append(cache)
        data = dict(settings.data, stamp_output=str(stamps.stage), report_output=str(cache.stage.parent))
        staged = type(settings).from_data(settings.game, settings.filename, data)
        yield staged
        publish(trees, checkpoint)
    finally:
        for tree in reversed(trees):
            tree.cleanup()
