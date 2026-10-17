"""Foreground-game-only GDI title crops; no full-desktop capture or disk images."""
import ctypes as C
from contextlib import contextmanager
from ctypes import wintypes as W
from dataclasses import dataclass
import os

from .processes import ProcessCatalog


@dataclass(frozen=True)
class Target:
    hwnd: int
    pid: int
    x: int
    y: int
    width: int
    height: int


def title_rects(width, height):
    if not 640 <= width <= 7680 or not 480 <= height <= 4320:
        raise ValueError('Unsupported capture dimensions.')
    rects = []
    for center in (-.3346, .0062, .3470):
        x = round(width / 2 + (center - .125) * height)
        y, w, h = round(.348 * height), round(.25 * height), round(.079 * height)
        if x < 0 or x + w > width or y + h > height:
            raise ValueError('Title crop is outside the game window.')
        rects.append((x, y, w, h))
    return tuple(rects)


class Screen:
    def __init__(self, *, process_catalog=None):
        if os.name != 'nt':
            raise OSError('Screen capture requires Windows.')
        self.processes = process_catalog or ProcessCatalog()
        self.u = C.WinDLL('user32', use_last_error=True)
        self.g = C.WinDLL('gdi32', use_last_error=True)
        def bind(dll, name, result, *args):
            fn = getattr(dll, name); fn.restype = result; fn.argtypes = args
        bind(self.u, 'GetForegroundWindow', W.HWND)
        bind(self.u, 'SetThreadDpiAwarenessContext', W.HANDLE, W.HANDLE)
        bind(self.u, 'IsWindowVisible', W.BOOL, W.HWND)
        bind(self.u, 'IsIconic', W.BOOL, W.HWND)
        bind(self.u, 'GetWindowThreadProcessId', W.DWORD, W.HWND, C.POINTER(W.DWORD))
        bind(self.u, 'GetClientRect', W.BOOL, W.HWND, C.POINTER(W.RECT))
        bind(self.u, 'ClientToScreen', W.BOOL, W.HWND, C.POINTER(W.POINT))
        bind(self.u, 'GetDC', W.HDC, W.HWND)
        bind(self.u, 'ReleaseDC', C.c_int, W.HWND, W.HDC)
        bind(self.g, 'CreateCompatibleDC', W.HDC, W.HDC)
        bind(self.g, 'DeleteDC', W.BOOL, W.HDC)
        bind(self.g, 'DeleteObject', W.BOOL, W.HANDLE)
        bind(self.g, 'SelectObject', W.HANDLE, W.HDC, W.HANDLE)
        bind(self.g, 'CreateDIBSection', W.HBITMAP, W.HDC, W.LPVOID, W.UINT,
             C.POINTER(W.LPVOID), W.HANDLE, W.DWORD)
        bind(self.g, 'BitBlt', W.BOOL, W.HDC, C.c_int, C.c_int, C.c_int, C.c_int,
             W.HDC, C.c_int, C.c_int, W.DWORD)

    @contextmanager
    def _physical_pixels(self):
        # A thread-local context avoids changing Pengu/skins UI behavior. Logical
        # coordinates on a scaled monitor must never select pixels outside LoL.
        previous = self.u.SetThreadDpiAwarenessContext(C.c_void_p(-4))
        if not previous:
            raise OSError('Physical capture coordinates unavailable.')
        try:
            yield
        finally:
            self.u.SetThreadDpiAwarenessContext(previous)

    def target(self):
        with self._physical_pixels():
            return self._target()

    def _target(self):
        hwnd = self.u.GetForegroundWindow()
        if not hwnd or not self.u.IsWindowVisible(hwnd) or self.u.IsIconic(hwnd):
            return None
        pid = W.DWORD()
        if not self.u.GetWindowThreadProcessId(hwnd, C.byref(pid)) or not self.processes.contains(pid.value):
            return None
        rect, point = W.RECT(), W.POINT()
        if not self.u.GetClientRect(hwnd, C.byref(rect)) or not self.u.ClientToScreen(hwnd, C.byref(point)):
            return None
        return Target(hwnd, pid.value, point.x, point.y, rect.right, rect.bottom)

    def valid(self, target):
        return target is not None and self.target() == target

    def capture(self):
        with self._physical_pixels():
            return self._capture()

    def _capture(self):
        from PIL import Image, ImageOps
        target = self.target()
        if target is None:
            raise OSError('Game is not in foreground.')
        images = []
        for x, y, width, height in title_rects(target.width, target.height):
            if not self.valid(target):
                raise OSError('Game window changed.')
            pixels = self._pixels(target.x + x, target.y + y, width, height)
            image = Image.frombytes('RGB', (width, height), pixels, 'raw', 'BGRX')
            # Light card text becomes dark on a light background for Windows OCR.
            image = image.convert('L')
            if image.resize((1, 1)).getpixel((0, 0)) < 128:
                image = ImageOps.invert(image)
            image = ImageOps.autocontrast(image)
            scale = min(3, 768 / width, 240 / height)
            image = image.resize((round(width * scale), round(height * scale)))
            images.append(image.convert('RGBA'))
        if not self.valid(target):
            raise OSError('Game window changed.')
        return target, tuple(images)

    def _pixels(self, x, y, width, height):
        class Header(C.Structure):
            _fields_ = [('size', W.DWORD), ('width', W.LONG), ('height', W.LONG),
                        ('planes', W.WORD), ('bits', W.WORD), ('compression', W.DWORD),
                        ('imageSize', W.DWORD), ('xppm', W.LONG), ('yppm', W.LONG),
                        ('colors', W.DWORD), ('important', W.DWORD)]
        class Info(C.Structure):
            _fields_ = [('header', Header), ('colors', W.DWORD * 3)]
        screen = self.u.GetDC(None)
        if not screen:
            raise OSError('Capture DC unavailable.')
        memory = bitmap = previous = None
        try:
            memory = self.g.CreateCompatibleDC(screen)
            if not memory:
                raise OSError('Capture DC unavailable.')
            info = Info(Header(C.sizeof(Header), width, -height, 1, 32, 0, 0, 0, 0, 0, 0))
            bits = W.LPVOID()
            bitmap = self.g.CreateDIBSection(memory, C.byref(info), 0, C.byref(bits), None, 0)
            if not bitmap or not bits:
                raise OSError('Capture bitmap unavailable.')
            previous = self.g.SelectObject(memory, bitmap)
            if previous in (None, C.c_void_p(-1).value):
                raise OSError('Capture bitmap unavailable.')
            # SRCCOPY deliberately excludes layered windows, including our overlay.
            if not self.g.BitBlt(memory, 0, 0, width, height, screen, x, y, 0xCC0020):
                raise OSError('Capture failed.')
            return C.string_at(bits, width * height * 4)
        finally:
            if previous not in (None, C.c_void_p(-1).value):
                self.g.SelectObject(memory, previous)
            if bitmap:
                self.g.DeleteObject(bitmap)
            if memory:
                self.g.DeleteDC(memory)
            self.u.ReleaseDC(None, screen)
