"""Actual Windows alpha upload, kept hidden throughout the test."""

import ctypes
import sys
import unittest
from ctypes import wintypes as w

from PIL import Image

from sexo2.overlay.alpha_surface import AlphaSurface


@unittest.skipUnless(sys.platform == "win32", "Windows layered window API")
class AlphaSurfaceTests(unittest.TestCase):
    def test_premultiplied_pixels_and_resources_without_showing_a_window(self):
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.CreateWindowExW.argtypes = [
            w.DWORD,
            w.LPCWSTR,
            w.LPCWSTR,
            w.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            w.HWND,
            w.HANDLE,
            w.HANDLE,
            ctypes.c_void_p,
        ]
        user.CreateWindowExW.restype = w.HWND
        user.DestroyWindow.argtypes = [w.HWND]
        user.IsWindowVisible.argtypes = [w.HWND]
        user.GetGuiResources.argtypes = [w.HANDLE, w.DWORD]
        kernel = ctypes.WinDLL("kernel32")
        kernel.GetCurrentProcess.restype = w.HANDLE
        process = kernel.GetCurrentProcess()
        hwnd = user.CreateWindowExW(0x080800A0, "STATIC", "", 0x80000000, 0, 0, 2, 2, None, None, None, None)
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            baseline = user.GetGuiResources(process, 0)
            surface = AlphaSurface(hwnd, 2, 2)
            try:
                image = Image.new("RGBA", (2, 2), (200, 100, 50, 128))
                surface.update(image, 0, 0)
                self.assertEqual(ctypes.string_at(surface._bits, 4), bytes([25, 50, 100, 128]))
                self.assertFalse(user.IsWindowVisible(hwnd))
                with self.assertRaises(ValueError):
                    surface.update(Image.new("RGB", (2, 2)), 0, 0)
            finally:
                surface.close()
                surface.close()
            self.assertEqual(user.GetGuiResources(process, 0), baseline)
        finally:
            user.DestroyWindow(hwnd)
