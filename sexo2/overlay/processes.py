"""Public Windows process enumeration; never open the protected game process."""
import ctypes as C
from ctypes import wintypes as W
import time

GAME_NAMES = frozenset(('league of legends.exe', 'league of legends (tm) client.exe'))


def game_pids(names=GAME_NAMES):
    class Entry(C.Structure):
        _fields_ = [('size', W.DWORD), ('usage', W.DWORD), ('pid', W.DWORD),
                    ('heap', C.c_size_t), ('module', W.DWORD), ('threads', W.DWORD),
                    ('parent', W.DWORD), ('priority', W.LONG), ('flags', W.DWORD),
                    ('exe', W.WCHAR * 260)]
    api = C.WinDLL('kernel32', use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    api.CreateToolhelp32Snapshot.restype = W.HANDLE
    for name in ('Process32FirstW', 'Process32NextW'):
        getattr(api, name).argtypes = [W.HANDLE, C.POINTER(Entry)]
        getattr(api, name).restype = W.BOOL
    api.CloseHandle.argtypes = [W.HANDLE]
    api.CloseHandle.restype = W.BOOL
    handle = api.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS, no process access handle
    if handle in (None, C.c_void_p(-1).value):
        raise OSError('Process enumeration unavailable')
    try:
        entry = Entry()
        entry.size = C.sizeof(Entry)
        found = set()
        more = api.Process32FirstW(handle, C.byref(entry))
        for _ in range(65536):
            if not more:
                if C.get_last_error() not in (0, 18):  # ERROR_NO_MORE_FILES
                    raise OSError('Process enumeration interrupted')
                return frozenset(found)
            if entry.exe.casefold() in names:
                found.add(entry.pid)
            more = api.Process32NextW(handle, C.byref(entry))
        raise OSError('Process enumeration exceeds limit')
    finally:
        api.CloseHandle(handle)


class ProcessCatalog:
    def __init__(self, *, enumerate_pids=game_pids, clock=time.monotonic):
        self._enumerate = enumerate_pids
        self._clock = clock
        self._until = float('-inf')
        self._pids = frozenset()

    def contains(self, pid):
        if self._clock() >= self._until:
            # Do not keep a stale catalog after an enumeration error.
            self._pids = frozenset()
            self._pids = self._enumerate()
            self._until = self._clock() + 1
        return pid in self._pids
