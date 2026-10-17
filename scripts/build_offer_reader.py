"""Compile the local OCR helper from pinned source; never download an executable."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def build(source):
    source = Path(source).resolve()
    manifest = source / 'native/overlay-host/Cargo.toml'
    target = manifest.parent / 'target'
    command = ['cargo', 'build', '--manifest-path', str(manifest), '--locked',
               '--release', '--bin', 'sexo2-offer-reader', '--target-dir', str(target)]
    subprocess.run(command, cwd=source, check=True)
    executable = target / 'release/sexo2-offer-reader.exe'
    body = executable.read_bytes()
    if not body.startswith(b'MZ') or not 1024 < len(body) < 32 * 1024 * 1024:
        raise ValueError('Invalid OCR helper output.')
    dest = source / 'sexo2/overlay/bin'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(executable, dest / executable.name)
    # Keep complete dependency notices with any private packaged helper too.
    licenses = source / 'sexo2/overlay/licenses'
    licenses.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(subprocess.run(['cargo', 'metadata', '--manifest-path', str(manifest),
        '--locked', '--format-version', '1'], cwd=source, check=True, capture_output=True, text=True).stdout)
    for package in metadata['packages']:
        parent = Path(package['manifest_path']).parent
        for notice in parent.iterdir():
            if notice.is_file() and notice.name.upper().startswith(('LICENSE', 'COPYING')):
                if notice.stat().st_size > 512 * 1024:
                    raise ValueError('Dependency notice exceeds limit.')
                name = package['name'] + '-' + package['version'] + '-' + notice.name
                shutil.copyfile(notice, licenses / name)
    shutil.copyfile(source / 'native/overlay-host/licenses/sygnano.txt', licenses / 'Sygnano-MIT.txt')
    return hashlib.sha256(body).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print('Local OCR helper SHA-256: ' + build(args.source))
