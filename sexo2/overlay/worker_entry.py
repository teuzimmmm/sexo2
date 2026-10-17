"""Minimal windowed entry: report safe failures without a bootloader dialog."""
import os
import re


def report_error(error):
    if os.name!='nt':return
    import ctypes as C
    from ctypes import wintypes as W
    api=C.WinDLL('kernel32',use_last_error=True)
    api.GetStdHandle.argtypes=[W.DWORD];api.GetStdHandle.restype=W.HANDLE
    api.WriteFile.argtypes=[W.HANDLE,W.LPCVOID,W.DWORD,C.POINTER(W.DWORD),W.LPVOID]
    api.WriteFile.restype=W.BOOL
    label=type(error).__name__
    name=getattr(error,'name',None)
    if isinstance(error,ModuleNotFoundError) and isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_.]{1,120}',name):label+=':'+name
    value=('display-worker-error:'+label+'\n').encode()
    count=W.DWORD();api.WriteFile(api.GetStdHandle(0xfffffff4),value,len(value),C.byref(count),None)


def entry():
    try:
        from .worker import main
        return main()
    except Exception as error:
        report_error(error)
        return 3
