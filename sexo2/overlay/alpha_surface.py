"""Small, reusable per-pixel-alpha bitmap for a Windows overlay window."""

import ctypes
from ctypes import wintypes as w


class _BitmapInfo(ctypes.Structure):
    _fields_ = [
        ("size", w.DWORD),
        ("width", w.LONG),
        ("height", w.LONG),
        ("planes", w.WORD),
        ("bits", w.WORD),
        ("compression", w.DWORD),
        ("image_size", w.DWORD),
        ("xppm", w.LONG),
        ("yppm", w.LONG),
        ("used", w.DWORD),
        ("important", w.DWORD),
    ]


class _Blend(ctypes.Structure):
    _fields_ = [
        ("op", ctypes.c_ubyte),
        ("flags", ctypes.c_ubyte),
        ("opacity", ctypes.c_ubyte),
        ("alpha", ctypes.c_ubyte),
    ]


class AlphaSurface:
    def __init__(self, hwnd: int, width: int, height: int) -> None:
        self.hwnd, self.width, self.height = hwnd, width, height
        self._gdi = ctypes.WinDLL("gdi32", use_last_error=True)
        self._user = ctypes.WinDLL("user32", use_last_error=True)
        signatures = [
            (self._gdi.CreateCompatibleDC, [w.HDC], w.HDC),
            (
                self._gdi.CreateDIBSection,
                [w.HDC, ctypes.POINTER(_BitmapInfo), w.UINT, ctypes.POINTER(ctypes.c_void_p), w.HANDLE, w.DWORD],
                w.HANDLE,
            ),
            (self._gdi.SelectObject, [w.HDC, w.HANDLE], w.HANDLE),
            (self._gdi.DeleteObject, [w.HANDLE], w.BOOL),
            (self._gdi.DeleteDC, [w.HDC], w.BOOL),
            (
                self._user.UpdateLayeredWindow,
                [
                    w.HWND,
                    w.HDC,
                    ctypes.POINTER(w.POINT),
                    ctypes.POINTER(w.SIZE),
                    w.HDC,
                    ctypes.POINTER(w.POINT),
                    w.DWORD,
                    ctypes.POINTER(_Blend),
                    w.DWORD,
                ],
                w.BOOL,
            ),
        ]
        for function, arguments, result in signatures:
            function.argtypes, function.restype = arguments, result
        self._dc = self._gdi.CreateCompatibleDC(None)
        self._bitmap = self._old = None
        self._bits = ctypes.c_void_p()
        try:
            if not self._dc:
                raise ctypes.WinError(ctypes.get_last_error())
            info = _BitmapInfo(size=ctypes.sizeof(_BitmapInfo), width=width, height=-height, planes=1, bits=32)
            self._bitmap = self._gdi.CreateDIBSection(
                self._dc, ctypes.byref(info), 0, ctypes.byref(self._bits), None, 0
            )
            if not self._bitmap:
                raise ctypes.WinError(ctypes.get_last_error())
            self._old = self._gdi.SelectObject(self._dc, self._bitmap)
            if not self._old:
                raise ctypes.WinError(ctypes.get_last_error())
        except Exception:
            self.close()
            raise

    def update(self, image, left: int, top: int) -> None:
        if image.mode != "RGBA" or image.size != (self.width, self.height):
            raise ValueError("Overlay bitmap must be RGBA and match the surface size")
        # Windows requires premultiplied BGRA, including partially covered glyph edges.
        pixels = image.convert("RGBa").tobytes("raw", "BGRa")
        ctypes.memmove(self._bits, pixels, len(pixels))
        destination, source = w.POINT(left, top), w.POINT(0, 0)
        size, blend = w.SIZE(self.width, self.height), _Blend(0, 0, 255, 1)
        if not self._user.UpdateLayeredWindow(
            self.hwnd,
            None,
            ctypes.byref(destination),
            ctypes.byref(size),
            self._dc,
            ctypes.byref(source),
            0,
            ctypes.byref(blend),
            2,
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self._old:
            self._gdi.SelectObject(self._dc, self._old)
            self._old = None
        if self._bitmap:
            self._gdi.DeleteObject(self._bitmap)
            self._bitmap = None
        if self._dc:
            self._gdi.DeleteDC(self._dc)
            self._dc = None
