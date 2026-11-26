"""Stage stamp outputs and roll back failed publication across output trees."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


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
        self.root = Path(tempfile.mkdtemp(prefix='.annotools-stage-', dir=self.target.parent)).resolve()
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
            if self.root.parent != self.target.parent or self.root.is_symlink():
                raise ValueError('Temporärer Ausgabeordner ist nicht mehr sicher erreichbar.')
            def retry_readonly(function, path, exc_info):
                if not isinstance(exc_info[1], PermissionError):
                    raise exc_info[1]
                self.make_writable(path)
                function(path)
            shutil.rmtree(self.root, onerror=retry_readonly)


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
            os.replace(tree.stage / name, target)
            journal.append((tree, target, backup))
        for tree, name in removals:
            target, backup = tree.target / name, tree.root / 'rollback' / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
            journal.append((tree, target, backup))
    except BaseException as original:
        failures = []
        recovery = []
        for tree, target, backup in reversed(journal):
            try:
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(backup, target)
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
