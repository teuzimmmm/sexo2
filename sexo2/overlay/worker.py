"""Renderer-only entry; never imports the application's initialization or skins."""
import json
import os
import sys
import threading
import time
from .wire import MAX_BYTES,ProtocolError
from .worker_wire import Inbox


def main():
    if os.name!='nt':return 2
    # PyInstaller --windowed sets Python stdio to None even with inherited pipes.
    # Restore only our private standard handles; never attach a user console.
    if sys.stdin is None or sys.stdout is None:
        import ctypes as C
        from ctypes import wintypes as W
        import msvcrt,io
        api=C.WinDLL('kernel32',use_last_error=True)
        api.GetStdHandle.argtypes=[W.DWORD];api.GetStdHandle.restype=W.HANDLE
        for name,identifier,flags,mode in [('stdin',-10,os.O_RDONLY,'rb'),('stdout',-11,os.O_WRONLY,'wb')]:
            if getattr(sys,name) is not None:continue
            handle=api.GetStdHandle(identifier & 0xffffffff)
            if handle in (None,C.c_void_p(-1).value):return 2
            fd=msvcrt.open_osfhandle(handle,flags|os.O_BINARY)
            setattr(sys,name,io.TextIOWrapper(os.fdopen(fd,mode,buffering=0),encoding='utf-8'))
    from .software import SoftwareOverlay
    inbox=Inbox();lock=threading.Lock()
    def emit(value):
        with lock:
            try:sys.stdout.buffer.write((json.dumps(value)+'\n').encode());sys.stdout.buffer.flush()
            except (OSError,AttributeError):inbox.close()
    window=SoftwareOverlay(inbox.frame)
    window.set_opponent_action(lambda:emit({'event':'cycle-opponent'}))
    def read():
        try:
            while True:
                raw=sys.stdin.buffer.readline(MAX_BYTES+1)
                if not raw:break
                inbox.accept(raw)
        except (OSError,ProtocolError):pass
        finally:inbox.close()
    threading.Thread(target=read,name='SEXO2-display-inbox',daemon=True).start()
    window.start();last=None
    try:
        while not inbox.closed:
            state=window.diagnostic()
            value={'event':'status','code':state['code'],'renders':state['renders'],
                   'windowShown':bool(state['windowShown']),'engine':'isolated-layered-cpu'}
            if value!=last:emit(value);last=value
            if window.ready.is_set() and window.error:break
            if window.error:break
            time.sleep(.1)
    finally:inbox.close();window.stop()
    return 1 if window.error else 0
