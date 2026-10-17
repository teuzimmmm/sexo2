"""Small, testable staging helpers for a Windows-only native build."""
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import zipfile

from .identity import MANIFEST

MAX_NATIVE_FILE = 128 * 1024 * 1024
MAX_NATIVE_TOTAL = 512 * 1024 * 1024
REQUIRED_NATIVE = {
    'Pengu Loader/Pengu Loader.exe', 'Pengu Loader/core.dll',
    'injection/tools/mod-tools.exe', 'injection/tools/cslol-dll.dll',
    'injection/tools/ltk_patcher_host.exe', 'injection/tools/ltk_patcher_dll.dll',
    'hosting-tools/cloudflared.exe',
}
_OMIT_ROOTS = {'release-secrets', '.git', '.github', 'ui-test-runtime', 'node_modules', 'tests', 'docs'}
_PRIVATE_SUFFIXES = {'.key', '.pem', '.pfx', '.p12', '.snk', '.ini', '.log'}


def validate_version(value):
    if not isinstance(value, str) or not re.fullmatch(r'2\.0\.0\.[1-9][0-9]{0,4}', value):
        raise ValueError('Use uma versão de teste como 2.0.0.1.')
    if int(value.rsplit('.', 1)[1]) > 65535:
        raise ValueError('O número da edição deve ser menor ou igual a 65535.')
    return value


def member_path(value):
    if '\\' in value or ':' in value or value.startswith('/'):
        raise ValueError('Caminho inválido no pacote de origem.')
    path = PurePosixPath(value)
    if not path.parts or any(p in {'', '.', '..'} for p in value.rstrip('/').split('/')):
        raise ValueError('Caminho inválido no pacote de origem.')
    return path


def source_allowed(path):
    return (path.parts[0] not in _OMIT_ROOTS and path.suffix.lower() not in _PRIVATE_SUFFIXES
            and path.name.lower() not in {'update-access.json', '.env', 'config', 'datastore', MANIFEST}
            and not any(p.lower() in {'__pycache__', 'node_modules', 'release-secrets'} for p in path.parts))


def reject_links(path, root):
    current = path
    while current != root:
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise ValueError('Links e junctions não são aceitos no staging.')
        if current == current.parent:
            raise ValueError('Caminho fora da raiz de origem.')
        current = current.parent
    if root.is_symlink() or getattr(root, 'is_junction', lambda: False)():
        raise ValueError('A raiz de origem não pode ser um link.')


def snapshot_source(root, destination, files=None):
    root, destination = Path(root).absolute(), Path(destination)
    if files is None:
        result = subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True, capture_output=True)
        files = result.stdout.decode('utf-8').rstrip('\0').split('\0')
    for name in files:
        path = member_path(name)
        if not source_allowed(path):
            continue
        source = root.joinpath(*path.parts)
        reject_links(source, root)
        if not source.is_file():
            raise ValueError('Arquivo rastreado ausente no snapshot de build.')
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def native_target(member):
    parts = member.parts
    if not parts or parts[0] != '_internal':
        return None
    path = PurePosixPath(*parts[1:])
    if path.as_posix() in REQUIRED_NATIVE or path.as_posix() == 'injection/tools/cslol-dll.stub':
        return path
    if (len(path.parts) == 2 and path.parts[0] == 'Pengu Loader'
            and path.suffix.lower() in {'.exe', '.dll'}):
        return path
    return None


def is_pe(body):
    if len(body) < 64 or body[:2] != b'MZ':
        return False
    offset = int.from_bytes(body[60:64], 'little')
    return 64 <= offset <= len(body) - 4 and body[offset:offset + 4] == b'PE\0\0'


def restore_native(base, destination):
    """Copy only allowlisted binaries, never configs, tokens, or old plugins."""
    base, destination = Path(base).absolute(), Path(destination)
    report, seen, total = [], set(), 0

    def save(member, size, opener):
        nonlocal total
        path = native_target(member)
        if path is None:
            return
        name = path.as_posix()
        if name.casefold() in seen or not 0 < size <= MAX_NATIVE_FILE or total + size > MAX_NATIVE_TOTAL:
            raise ValueError('Binários duplicados ou limite da baseline excedido.')
        with opener() as stream:
            body = stream.read(MAX_NATIVE_FILE + 1)
        if len(body) != size or not is_pe(body):
            raise ValueError('A baseline contém um binário Windows inválido.')
        seen.add(name.casefold())
        total += size
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        report.append({'file': name, 'bytes': size, 'sha256': hashlib.sha256(body).hexdigest()})

    if base.is_dir():
        for path in (base / '_internal').rglob('*'):
            relative = PurePosixPath(path.relative_to(base).as_posix())
            if native_target(relative) is not None:
                reject_links(path, base)
                if path.is_file():
                    save(relative, path.stat().st_size, lambda p=path: p.open('rb'))
    else:
        reject_links(base, base.parent)
        if base.stat().st_size > 1024 * 1024 * 1024:
            raise ValueError('A baseline excede o limite de 1 GiB.')
        with zipfile.ZipFile(base) as archive:
            for info in archive.infolist():
                member = member_path(info.filename)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError('Links não são aceitos na baseline.')
                if not info.is_dir():
                    save(member, info.file_size, lambda i=info: archive.open(i))
    if not REQUIRED_NATIVE.issubset({r['file'] for r in report}):
        raise ValueError('Baseline incompleta: faltam componentes Pengu, LTK, mod-tools ou cloudflared.')
    return sorted(report, key=lambda row: row['file'])
