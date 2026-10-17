"""Opt-in native window smoke on disposable Windows, without League installed."""
import ctypes as C
from ctypes import wintypes as W
import os
import time
import unittest

from sexo2.overlay.model import Card, View
from sexo2.overlay.runtime import Frame
from sexo2.overlay.win32 import NativeOverlay
from sexo2.overlay.processes import ProcessCatalog, game_pids


@unittest.skipUnless(os.name == 'nt' and os.environ.get('SEXO2_TEST_NATIVE_OVERLAY') == '1',
                     'Opt-in isolated Windows desktop smoke')
class NativeWindowTests(unittest.TestCase):
    def until(self, predicate):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.03)
        self.fail('Native overlay did not reach expected state')

    def test_native_flags_paint_hotkeys_pagination_hide_and_cleanup(self):
        active = [True]
        view = View('synthetic-match', (Card('Ahri · WR', tuple('Item / runa ' + str(i) for i in range(45))),
                                        Card('Ahri · Common', ('Somente dados preparados',))))
        foreground = [True]
        window = NativeOverlay(lambda: Frame(active[0], view),
                               foreground=lambda: (0, 0, 1280, 720) if foreground[0] else None)
        self.addCleanup(window.stop)
        window.start()
        self.assertTrue(window.ready.wait(5))
        self.assertIsNone(window.error)
        self.assertTrue(window.hwnd)
        self.until(lambda: window._visible)
        self.assertEqual(window._registered, {1, 2, 3})
        u = C.WinDLL('user32', use_last_error=True)
        u.GetWindowLongPtrW.argtypes = [W.HWND, C.c_int]
        u.GetWindowLongPtrW.restype = C.c_ssize_t
        u.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
        u.SendMessageW.restype = C.c_ssize_t
        u.UpdateWindow.argtypes = [W.HWND]
        u.UpdateWindow.restype = W.BOOL
        u.GetForegroundWindow.restype = W.HWND
        u.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
        flags = u.GetWindowLongPtrW(window.hwnd, -20)
        self.assertEqual(flags & 0x080800A8, 0x080800A8)
        self.assertEqual(u.SendMessageW(window.hwnd, 0x84, 0, 0), -1)
        self.assertEqual(u.SendMessageW(window.hwnd, 0x21, 0, 0), 3)
        self.assertNotEqual(u.GetForegroundWindow(), window.hwnd)
        u.SendMessageW(window.hwnd, 0x312, 1, 0)  # F8, owning thread handles event
        self.assertTrue(window._expanded)
        u.UpdateWindow(window.hwnd)
        rect = W.RECT()
        u.GetWindowRect(window.hwnd, C.byref(rect))
        self.assertGreater(rect.bottom - rect.top, 40)
        u.SendMessageW(window.hwnd, 0x312, 3, 0)  # F10 text page
        u.UpdateWindow(window.hwnd)
        self.assertEqual(window._page, 1)
        u.SendMessageW(window.hwnd, 0x312, 2, 0)  # F9 suggestion
        u.UpdateWindow(window.hwnd)
        self.assertEqual(window._index, 1)
        self.assertIsNone(window.error)
        foreground[0] = False
        self.until(lambda: not window._visible and not window._registered)
        foreground[0] = True
        self.until(lambda: window._visible)
        active[0] = False
        self.until(lambda: not window._visible and not window._registered)
        window.stop()
        self.assertFalse(window._thread.is_alive())
        self.assertIsNone(window.hwnd)

    def test_stop_during_creation_and_repeated_shutdown(self):
        window = NativeOverlay(lambda: Frame(), foreground=lambda: None)
        window.start()
        window.stop(); window.stop()
        self.until(lambda: not window._thread.is_alive())
        self.assertIsNone(window.error)
        self.assertIsNone(window.hwnd)

    def test_real_process_enumeration_pid_and_window_geometry_without_openprocess(self):
        import sys
        from pathlib import Path
        active = [False]
        window = NativeOverlay(lambda: Frame(active[0], View('real-window', (Card('Arena · teste', ('PR 10% · 20 jogos',)),))))
        self.addCleanup(window.stop)
        window.start(); self.assertTrue(window.ready.wait(5)); self.assertIsNone(window.error)
        # Real Win32 target owned by this disposable test. Only the foreground
        # HWND and allowed executable name are controlled, not PID/geometry APIs.
        target = window.u.CreateWindowExW(0x08000000, 'STATIC', 'SEXO2 isolated target', 0x10CF0000,
                                          40, 50, 1280, 720, None, None, window.k.GetModuleHandleW(None), None)
        self.assertTrue(target)
        self.addCleanup(lambda: window.u.DestroyWindow(target))
        executable = Path(sys.executable).name.casefold()
        self.assertIn(os.getpid(), game_pids(frozenset({executable})))
        window.foreground_hwnd = lambda: target
        # Production names must reject this Python test process.
        self.assertIsNone(window._foreground_game())
        self.assertIsNotNone(window._foreground_bounds(preview=True))
        window.processes = ProcessCatalog(enumerate_pids=lambda: game_pids(frozenset({executable})))
        self.assertIsNotNone(window._foreground_game())
        active[0] = True
        self.until(lambda: window._visible)
        self.assertTrue(window.u.IsWindowVisible(window.hwnd))
        self.assertEqual(window.diagnostic()['code'], 'visible')
        active[0] = False
        self.until(lambda: not window._visible)

    def test_f8_conflict_does_not_hide_window(self):
        window = NativeOverlay(lambda: Frame(True, View('arena', (Card('Arena', ('PR sem WR',)),))),
                               foreground=lambda: (0, 0, 1280, 720))
        window._api()
        self.assertTrue(window.u.RegisterHotKey(None, 99, 0x4000, 0x77))
        self.addCleanup(lambda: window.u.UnregisterHotKey(None, 99))
        self.addCleanup(window.stop)
        window.start(); self.assertTrue(window.ready.wait(5))
        self.until(lambda: window._visible)
        self.assertTrue(window._expanded)
        self.assertNotIn(1, window._registered)
        self.assertIsNone(window.error)
        self.assertFalse(window.diagnostic()['hotkeys']['F8'])


if __name__ == '__main__':
    unittest.main()
