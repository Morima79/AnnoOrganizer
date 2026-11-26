"""Extract the two verified desktop release files from a raw Actions artifact."""
import argparse
import hashlib
from pathlib import Path
import re
import zipfile


def extract_desktop_artifact(directory, version, output):
    """Accept only the expected desktop ZIP and its matching checksum file."""
    if not re.fullmatch(r'v[0-9]+[.][0-9]+[.][0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Use a version such as v0.1.16')
    downloads = list(Path(directory).iterdir())
    if len(downloads) != 1 or not downloads[0].is_file():
        raise ValueError('Expected exactly one downloaded artifact archive')
    archive_name = f'AnnoOrganizer-{version}-windows-x64.zip'
    checksum_name = str(Path(archive_name).with_suffix('.sha256'))
    with zipfile.ZipFile(downloads[0]) as artifact:
        if sorted(artifact.namelist()) != sorted((archive_name, checksum_name)):
            raise ValueError('Unexpected desktop artifact contents')
        archive = artifact.read(archive_name)
        checksum = artifact.read(checksum_name)
    digest = hashlib.sha256(archive).hexdigest()
    if checksum.decode('ascii').split() != [digest, archive_name]:
        raise ValueError('Desktop archive checksum mismatch')
    output = Path(output)
    targets = [output / archive_name, output / checksum_name]
    if any(target.exists() or target.is_symlink() for target in targets):
        raise ValueError('Desktop release files already exist')
    output.mkdir(parents=True, exist_ok=True)
    for target, content in zip(targets, (archive, checksum)):
        target.write_bytes(content)
    print(f'Extracted {archive_name}; SHA-256 {digest}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    extract_desktop_artifact(args.directory, args.version, args.output)
