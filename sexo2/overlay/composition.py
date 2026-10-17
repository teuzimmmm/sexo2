"""Own-process DirectComposition renderer. No game DLL or injection interface."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import sys


class Composition:
    def __init__(self, hwnd):
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
        path = root / 'sexo2/overlay/bin/sexo2-overlay-renderer.dll'
        # LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32.
        self.api = C.CDLL(str(path), winmode=0x100 | 0x800)
        self.api.s2_create.argtypes = [W.HWND, C.POINTER(C.c_void_p)]
        self.api.s2_create.restype = C.c_int32
        self.api.s2_draw.argtypes = [C.c_void_p, W.UINT, W.UINT, W.LPCWSTR, W.LPCWSTR, W.LPCWSTR]
        self.api.s2_draw.restype = C.c_int32
        self.api.s2_destroy.argtypes = [C.c_void_p]
        self.api.s2_destroy.restype = None
        self.api.s2_driver.argtypes = [C.c_void_p]
        self.api.s2_driver.restype = C.c_int
        self.handle = C.c_void_p()
        self._check(self.api.s2_create(hwnd, C.byref(self.handle)))
        self.driver = 'warp' if self.api.s2_driver(self.handle) == 2 else 'hardware'

    @staticmethod
    def _check(result):
        if result < 0:
            # HRESULT is useful diagnostics, with no paths, text or account data.
            raise OSError('DirectComposition HRESULT 0x%08X' % (result & 0xffffffff))

    def draw(self, width, height, header, body, footer):
        if any(not isinstance(s, str) or len(s.encode('utf-16-le')) // 2 > 8192 or '\0' in s
               for s in (header, body, footer)):
            raise ValueError('Composition text exceeds limits.')
        self._check(self.api.s2_draw(self.handle, width, height, header, body, footer))

    def close(self):
        if self.handle:
            self.api.s2_destroy(self.handle)
            self.handle = C.c_void_p()
