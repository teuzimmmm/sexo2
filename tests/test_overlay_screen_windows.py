"""Windows integration with synthetic text, never with the user's game or desktop."""
import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import time
import unittest

from sexo2.overlay.offers import normalized
from sexo2.overlay.reader import OcrProcess


@unittest.skipUnless(os.name == 'nt' and os.getenv('SEXO2_TEST_SCREEN_OCR') == '1',
                     'Explicit Windows screen/OCR integration only')
class WindowsScreenTests(unittest.TestCase):
    def test_actual_windows_ocr_reuses_process_on_synthetic_crops(self):
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.truetype('arial.ttf', 40)
        images = []
        expected = ['Critical Rhythm', 'Fire Power', 'Ice Shield']
        for name in expected:
            image = Image.new('RGBA', (600, 120), 'white')
            ImageDraw.Draw(image).text((20, 30), name, font=font, fill='black')
            images.append(image)
        ocr = OcrProcess(timeout=8)
        self.addCleanup(ocr.close)
        for _ in range(2):
            result = ocr.recognize(images)
            self.assertEqual([normalized(x) for x in result], [normalized(x) for x in expected])
        child = ocr._child
        ocr.close()
        self.assertIsNotNone(child.poll())

    def test_game_guard_and_real_gdi_crops_on_own_test_window(self):
        from sexo2.overlay.processes import ProcessCatalog
        from sexo2.overlay.screen import Screen, title_rects
        u = C.WinDLL('user32', use_last_error=True)
        g = C.WinDLL('gdi32', use_last_error=True)
        u.CreateWindowExW.restype = W.HWND
        u.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD,
            C.c_int, C.c_int, C.c_int, C.c_int, W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID]
        u.DestroyWindow.argtypes = [W.HWND]
        u.SetForegroundWindow.argtypes = [W.HWND]
        u.UpdateWindow.argtypes = [W.HWND]
        u.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
        u.SendMessageW.restype = W.LPARAM
        g.GetStockObject.argtypes = [C.c_int]
        g.GetStockObject.restype = W.HANDLE
        hwnd = u.CreateWindowExW(0, 'STATIC', 'SEXO2 synthetic offer test', 0x10CF0000,
                                30, 30, 800, 600, None, None, None, None)
        self.assertTrue(hwnd)
        self.addCleanup(u.DestroyWindow, hwnd)
        u.SetForegroundWindow(hwnd)
        screen = Screen(process_catalog=ProcessCatalog(enumerate_pids=lambda: frozenset({os.getpid()})))
        target = screen.target()
        self.assertIsNotNone(target)
        for rect, name in zip(title_rects(target.width, target.height), ('Fire Power', 'Ice Shield', 'Quick Feet')):
            x, y, w, h = rect
            child = u.CreateWindowExW(0, 'STATIC', name, 0x50000001,
                                     x, y, w, h, hwnd, None, None, None)
            self.assertTrue(child)
            u.SendMessageW(child, 0x30, g.GetStockObject(17), 1)  # WM_SETFONT
            u.UpdateWindow(child)
        u.UpdateWindow(hwnd)
        time.sleep(.1)
        observed, images = screen.capture()
        self.assertEqual(observed, target)
        self.assertEqual(len(images), 3)
        for image in images:
            self.assertLessEqual(image.width, 768)
            self.assertLessEqual(image.height, 240)
        # Production guard must reject this process, even though test capture works.
        self.assertIsNone(Screen().target())
        ocr = OcrProcess(timeout=8)
        self.addCleanup(ocr.close)
        self.assertEqual([normalized(x) for x in ocr.recognize(images)],
                         [normalized(x) for x in ('Fire Power', 'Ice Shield', 'Quick Feet')])


if __name__ == '__main__':
    unittest.main()
