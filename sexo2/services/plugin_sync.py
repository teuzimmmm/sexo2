"""Upgrade only hash-recognized project scripts in a separately owned Pengu.

Never copies a loader, config, datastore, credentials, or arbitrary plugin trees.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from utils.core.atomic_file import atomic_write

NAMES=('SEXO2-Builds','SEXO2-Settings','ROSE-SkinMonitor','ROSE-UI','ROSE-I18n','ROSE-CustomWheel','ROSE-Hub')

class PluginSyncError(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__('Não foi possível atualizar com segurança os plugins do SEXO2 no Pengu externo.')

@dataclass(frozen=True)
class SyncResult:
    changed: bool
    disabled: tuple


def _plain(path):
    for node in (path,*path.parents):
        if node.is_symlink() or getattr(node,'is_junction',lambda:False)():raise PluginSyncError('link')


def _read(path):
    _plain(path)
    if not path.is_file() or path.stat().st_size>2*1024*1024:raise PluginSyncError('file')
    return path.read_bytes()


def sync_project_plugins(source,target,manifest,backups):
    source,target,backups=map(lambda p:Path(p).absolute(),(source,target,backups))
    _plain(source);_plain(target);_plain(backups)
    try:
        raw=_read(Path(manifest).absolute())
        if len(raw)>65536:raise PluginSyncError('manifest')
        data=json.loads(raw)
        if not isinstance(data,dict) or data.get('schema')!=1 or not isinstance(data.get('plugins'),dict) or set(data['plugins'])!=set(NAMES):raise PluginSyncError('manifest')
        known=data['plugins']
        if any(not isinstance(v,list) or not 1<=len(v)<=128 or any(not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h) for h in v) for v in known.values()):raise PluginSyncError('manifest')
        plans=[];disabled=[]
        # Complete preflight: a changed user script prevents any partial update.
        for name in NAMES:
            folder=target/name;dest=folder/'index.js';_plain(folder)
            if (folder/'index.js_').exists():disabled.append(name);continue
            body=_read(source/name/'index.js')
            if hashlib.sha256(body).hexdigest() not in known[name]:raise PluginSyncError('source')
            previous=_read(dest) if dest.exists() else None
            if previous==body:continue
            if previous is not None and hashlib.sha256(previous).hexdigest() not in known[name]:raise PluginSyncError('customized')
            plans.append((name,dest,body,previous))
        applied=[]
        try:
            for name,dest,body,previous in plans:
                if (_read(dest) if dest.exists() else None)!=previous:raise PluginSyncError('changed')
                if previous is not None:
                    backup=backups/name/(hashlib.sha256(previous).hexdigest()+'.js')
                    _plain(backup)
                    if not backup.exists():
                        with atomic_write(backup,'wb') as file:file.write(previous)
                with atomic_write(dest,'wb') as file:file.write(body)
                applied.append((dest,body,previous))
        except Exception:
            # Roll back only our own unchanged writes, never a concurrent user edit.
            for dest,body,previous in reversed(applied):
                try:
                    if _read(dest)!=body:continue
                    if previous is None:dest.unlink()
                    else:
                        with atomic_write(dest,'wb') as file:file.write(previous)
                except (OSError,PluginSyncError):pass
            raise
        return SyncResult(bool(plans),tuple(disabled))
    except PluginSyncError:raise
    except (OSError,ValueError,TypeError,KeyError):raise PluginSyncError('io') from None
