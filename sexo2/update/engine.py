"""Verify a signed delta and update only declared application files."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_TOTAL = 1024 * 1024 * 1024
PROTECTED = {'config.ini', 'hashes.game.txt', 'friends-preferences.json', 'sexo2-startup-ready.json'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda: file.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def target(root, name):
    p = PurePosixPath(name)
    if (not name or '\\' in name or ':' in name or p.is_absolute()
            or any(part in ('', '.', '..') or part.endswith(('.', ' ')) for part in name.split('/'))
            or p.parts[0].lower() == '.sexo2-update'
            or p.name.lower() in PROTECTED
            or p.parts[0].lower() in {'skins', 'classic', 'logs', 'diagnosticos'}
            or p.parts[0].lower().startswith('unins')):
        raise ValueError('O pacote contém um caminho não permitido.')
    path = root.joinpath(*p.parts)
    for ancestor in (path, *path.parents):
        if ancestor == root.parent:
            break
        if ancestor.exists() and (ancestor.is_symlink() or ancestor.is_junction()):
            raise ValueError('A instalação contém um link ou junção nesse caminho.')
    path.resolve().relative_to(root.resolve())
    return path


def verify(raw, signature, public_key):
    if len(raw) > 4*1024*1024:
        raise ValueError('Manifesto excede o limite.')
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, raw)
        data = json.loads(raw)
    except Exception:
        raise ValueError('A assinatura da atualização é inválida.') from None
    if data.get('schema') != 1 or data.get('app') != 'SEXO2' or not isinstance(data.get('files'), dict):
        raise ValueError('Pacote incompatível com SEXO2.')
    if not data['files'] or len(data['files']) > 10000:
        raise ValueError('Lista de arquivos inválida.')
    return data


def remove_owned(path, root):
    path.resolve().relative_to(root.resolve())
    if path == root or path.is_symlink() or path.is_junction():
        raise ValueError('Pasta de recuperação inválida.')
    if path.exists():
        shutil.rmtree(path)


def restore(root, transaction, public_key):
    data = verify((transaction/'manifest.json').read_bytes(), (transaction/'manifest.sig').read_bytes(), public_key)
    for name, entry in data['files'].items():
        dest = target(root, name)
        old = entry['old']
        if old is None:
            # Only remove a newly introduced file if it still matches the patch.
            if dest.exists() and digest(dest) == entry['new']:
                dest.unlink()
        else:
            backup = target(transaction/'files', name)
            if not backup.is_file() or digest(backup) != old:
                raise ValueError('Backup incompleto. A recuperação foi mantida para inspeção.')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, dest)


def apply_patch(package, installation, public_key, ensure_closed=lambda: None):
    original_root = Path(installation).absolute()
    if original_root.is_junction() or original_root.is_symlink():
        raise ValueError('Selecione uma pasta local normal.')
    root = original_root.resolve()
    if not root.is_dir() or not (root/'SEXO2.exe').is_file():
        raise ValueError('Selecione a pasta da instalação existente do SEXO2.')
    if root.is_junction() or root.is_symlink():
        raise ValueError('Selecione uma pasta local normal.')
    ensure_closed()
    work = root/'.sexo2-update'
    if work.exists() and (work.is_symlink() or work.is_junction()):
        raise ValueError('Pasta de recuperação inválida.')
    work.mkdir(exist_ok=True)
    # One helper may own the transaction at a time. OS closes this handle after
    # a crash; recovery below handles the unfinished signed transaction.
    from sexo2.update.lock import UpdateLock
    with UpdateLock(work/'lock'):
        transaction = work/'transaction'
        if (transaction/'journal.json').exists():
            restore(root, transaction, public_key)
            remove_owned(transaction, work)
        elif transaction.exists():
            remove_owned(transaction, work)
        with zipfile.ZipFile(package) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)) or sum(i.file_size for i in infos) > MAX_TOTAL:
                raise ValueError('Pacote excede os limites ou contém nomes duplicados.')
            if z.getinfo('manifest.json').file_size>4*1024*1024 or z.getinfo('manifest.sig').file_size!=64:
                raise ValueError('Manifesto inválido.')
            raw = z.read('manifest.json'); signature = z.read('manifest.sig')
            data = verify(raw, signature, public_key)
            expected = {'manifest.json','manifest.sig'} | {'payload/'+n for n in data['files']}
            if set(names) != expected:
                raise ValueError('O pacote contém arquivos não declarados.')
            destinations = set()
            for name, entry in data['files'].items():
                dest = target(root, name)
                key = str(dest).casefold()
                if key in destinations:
                    raise ValueError('O pacote contém caminhos equivalentes.')
                destinations.add(key)
                current = digest(dest) if dest.is_file() else None
                if current != entry['old']:
                    raise ValueError('Esta atualização não corresponde à versão instalada. Nenhum arquivo foi substituído.')
                info = z.getinfo('payload/'+name)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError('Links não são permitidos no pacote.')
                with z.open(info) as file:
                    h = hashlib.sha256()
                    for block in iter(lambda: file.read(1024*1024), b''):
                        h.update(block)
                    if h.hexdigest() != entry['new']:
                        raise ValueError('Arquivo de atualização corrompido.')
            required = sum(i.file_size for i in infos)*2 + 50*1024*1024
            if shutil.disk_usage(root).free < required:
                raise ValueError('Falta espaço para aplicar e recuperar a atualização.')
            transaction.mkdir()
            (transaction/'manifest.json').write_bytes(raw)
            (transaction/'manifest.sig').write_bytes(signature)
            for name, entry in data['files'].items():
                if entry['old'] is not None:
                    backup = target(transaction/'files', name)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target(root, name), backup)
            # Journal is written only after every original is safely backed up.
            (transaction/'journal.json').write_text('{}',encoding='utf-8')
            try:
                ensure_closed()
                for name, entry in data['files'].items():
                    dest = target(root, name)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    temp = dest.with_name(dest.name+'.sexo2-tmp')
                    created = False
                    if temp.exists():raise ValueError('Arquivo temporário já existe. Nenhum arquivo alheio foi removido.')
                    try:
                        with z.open('payload/'+name) as source, temp.open('xb') as output:
                            created = True
                            shutil.copyfileobj(source, output)
                            output.flush(); os.fsync(output.fileno())
                        os.replace(temp, dest)
                    finally:
                        if created and temp.exists(): temp.unlink()
                    if digest(dest) != entry['new']:
                        raise ValueError('Não foi possível confirmar o arquivo atualizado.')
            except Exception:
                restore(root, transaction, public_key)
                remove_owned(transaction, work)
                raise
        rollback = work/'rollback'
        remove_owned(rollback, work)
        (transaction/'journal.json').unlink()
        transaction.rename(rollback)
        return data['version']
