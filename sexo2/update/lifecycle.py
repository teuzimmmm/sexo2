"""Scoped app shutdown/relaunch. League and other installs are never targets."""
import ctypes, hashlib, os, subprocess, sys, threading
from pathlib import Path
import psutil

NAMES = {'sexo2.exe', 'rose.exe'}

def event_name(executable, pid):
    key = str(Path(executable).resolve()).casefold().encode('utf-8')
    return 'Local\\SEXO2-Update-' + hashlib.sha256(key).hexdigest()[:24] + '-' + str(pid)


def kernel():
    from ctypes import wintypes
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateEventW.restype = wintypes.HANDLE
    api.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    api.OpenEventW.restype = wintypes.HANDLE
    api.SetEvent.argtypes = [wintypes.HANDLE]; api.SetEvent.restype = wintypes.BOOL
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.CloseHandle.argtypes = [wintypes.HANDLE]; api.CloseHandle.restype = wintypes.BOOL
    return api


def start_shutdown_listener(callback, executable=None):
    if os.name != 'nt': return None
    api = kernel()
    handle = api.CreateEventW(None, False, False, event_name(executable or sys.executable, os.getpid()))
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    def wait():
        try:
            if api.WaitForSingleObject(handle, 0xFFFFFFFF) == 0:
                callback()
        finally: api.CloseHandle(handle)
    thread = threading.Thread(target=wait, name='SEXO2-Update-stop', daemon=True)
    thread.start()
    return thread


def request_shutdown(process):
    if os.name != 'nt': return False
    api = kernel()
    handle = api.OpenEventW(2, False, event_name(process.exe(), process.pid))
    if not handle: return False
    try: return bool(api.SetEvent(handle))
    finally: api.CloseHandle(handle)


def processes_for(installation):
    root = Path(installation).resolve()
    allowed = {str(root/name).casefold() for name in ('SEXO2.exe', 'Rose.exe')}
    matches = []
    for process in psutil.process_iter(['name']):
        if (process.info.get('name') or '').casefold() not in NAMES: continue
        try:
            if str(Path(process.exe()).resolve()).casefold() in allowed:
                matches.append(process)
        except psutil.NoSuchProcess: continue
        except psutil.AccessDenied as exc:
            raise ValueError('Não foi possível verificar o caminho do aplicativo. Feche o SEXO2 manualmente e tente novamente.') from exc
    return matches


def stop_owned_tools(process, installation):
    root = Path(installation).resolve()
    owned = []
    try: children = process.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied): return
    for child in children:
        try:
            if child.name().casefold() not in {'mod-tools.exe', 'ltk_patcher_host.exe', 'cloudflared.exe'}:
                continue
            if not Path(child.exe()).resolve().is_relative_to(root): continue
            child.terminate(); owned.append(child)
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    if owned:
        _, alive = psutil.wait_procs(owned, timeout=3)
        for child in alive:
            try: child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass


def stop_installed_app(installation):
    forced = False
    for process in processes_for(installation):
        try:
            graceful = request_shutdown(process)
            if graceful:
                try:
                    process.wait(timeout=8)
                    continue
                except psutil.TimeoutExpired: pass
            stop_owned_tools(process, installation)
            forced = True
            process.terminate()
            try: process.wait(timeout=4)
            except psutil.TimeoutExpired:
                process.kill(); process.wait(timeout=4)
        except psutil.NoSuchProcess: pass
    # Old versions have no graceful update signal; release an orphaned pause
    # after forced exit. This resumes a game, never terminates or restarts it.
    for game in (psutil.process_iter(['name']) if forced else []):
        if (game.info.get('name') or '').casefold() not in {'league of legends.exe', 'league of legends (tm) client.exe'}:
            continue
        try:
            if game.status() == psutil.STATUS_STOPPED:
                game.resume()
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    if processes_for(installation):
        raise ValueError('O SEXO2 ainda está em uso; nenhum arquivo foi substituído.')


def reopen_app(installation):
    root = Path(installation).resolve()
    if processes_for(root): return
    app = root/'SEXO2.exe'
    if not app.is_file(): raise ValueError('Executável atualizado não encontrado.')
    subprocess.Popen([str(app)], cwd=str(root), close_fds=True,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
