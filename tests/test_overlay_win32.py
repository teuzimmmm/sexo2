"""Opt-in native window smoke on disposable Windows, without League installed."""
import ctypes as C
from ctypes import wintypes as W
import os
import time
import threading
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
        self.assertTrue(window._expanded)  # First match opens without a hidden-only bar.
        u.SendMessageW(window.hwnd, 0x312, 1, 0)
        self.assertFalse(window._expanded)
        u.SendMessageW(window.hwnd, 0x312, 1, 0)
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

    def test_composited_pixels_recover_z_order_without_new_data_and_pass_clicks(self):
        # Unlike the old HWND-only smoke, inspect actual desktop pixels in memory.
        # No screenshot is saved. The target/competitor are disposable own windows.
        gate, paused = threading.Event(), threading.Event()
        gate.set()
        def foreground():
            if not gate.is_set():
                paused.set()
                gate.wait(2)
            return (0, 0, 1000, 700)
        window = NativeOverlay(lambda: Frame(True, View('pixel-test',
            (Card('Composição nativa', ('Conteúdo sintético, sem partida.',)),))),
            foreground=foreground)
        self.addCleanup(window.stop)
        self.addCleanup(gate.set)
        window.start(); self.assertTrue(window.ready.wait(8)); self.assertIsNone(window.error)
        self.until(lambda: window._visible)
        u, g = window.u, window.g
        u.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
        u.GetWindowRect.restype = W.BOOL
        u.GetDC.argtypes = [W.HWND]; u.GetDC.restype = W.HDC
        u.ReleaseDC.argtypes = [W.HWND, W.HDC]; u.ReleaseDC.restype = C.c_int
        u.WindowFromPoint.argtypes = [W.POINT]; u.WindowFromPoint.restype = W.HWND
        g.GetPixel.argtypes = [W.HDC, C.c_int, C.c_int]; g.GetPixel.restype = W.DWORD
        previous = u.SetThreadDpiAwarenessContext(C.c_void_p(-4))
        self.addCleanup(lambda: u.SetThreadDpiAwarenessContext(previous))
        rect = W.RECT()
        self.assertTrue(u.GetWindowRect(window.hwnd, C.byref(rect)))
        px, py = rect.left + 4, rect.top + 4
        def pixel():
            dc = u.GetDC(None)
            try:
                value = g.GetPixel(dc, px, py)
                return (value & 255, (value >> 8) & 255, (value >> 16) & 255)
            finally:
                u.ReleaseDC(None, dc)
        def drawn():
            color = pixel()
            return 0 < min(color) and max(color) < 60
        self.until(drawn)
        self.assertEqual(window.diagnostic()['engine'], 'directcomposition-d3d11')
        self.assertIn(window.diagnostic()['driver'], ('hardware', 'warp'))
        self.assertGreater(window.diagnostic()['renders'], 0)
        self.assertNotEqual(u.WindowFromPoint(W.POINT(px, py)), window.hwnd)
        renders, raises = window._renders, window._raises
        # Hold the injectable foreground seam briefly, avoiding a race between
        # our occlusion setup and the 200 ms production repair timer.
        gate.clear()
        self.assertTrue(paused.wait(1))
        # An opaque white TOPMOST deliberately occludes the exact same rectangle.
        competitor = u.CreateWindowExW(0x08000008, 'STATIC', 'synthetic-occluder',
            0x90000006, rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top,
            None, None, window.k.GetModuleHandleW(None), None)
        self.assertTrue(competitor)
        self.addCleanup(lambda: u.DestroyWindow(competitor))
        self.assertTrue(u.SetWindowPos(competitor, W.HWND(-1), 0, 0, 0, 0, 0x10 | 0x40 | 0x1 | 0x2))
        # Verify actual z-order loss; periodic positioning must repair it despite
        # unchanged frame/geometry (the old implementation never did this).
        u.UpdateWindow.argtypes = [W.HWND]; u.UpdateWindow.restype = W.BOOL
        u.UpdateWindow(competitor)
        C.WinDLL('dwmapi').DwmFlush()
        self.assertGreater(min(pixel()), 200)
        gate.set()
        self.until(lambda: window._raises > raises and drawn())
        self.assertEqual(window._renders, renders)
        self.assertNotEqual(u.WindowFromPoint(W.POINT(px, py)), window.hwnd)
        self.assertNotEqual(u.GetForegroundWindow(), window.hwnd)

    def test_three_offer_strips_have_visible_pixels_and_transparent_clickthrough_gaps(self):
        from sexo2.overlay.screen import offer_band
        values=[Frame(True,View('offers',tuple(Card(name,('PR 12% · 345 jogos','Fonte sintética'))
            for name in ('Esquerda','Centro','Direita'))),offer_layout=True)]
        window=NativeOverlay(lambda:values[0],foreground=lambda:(0,0,1000,700))
        self.addCleanup(window.stop);window.start()
        self.assertTrue(window.ready.wait(8));self.assertIsNone(window.error)
        self.until(lambda:window._visible)
        u,g=window.u,window.g
        host=u.CreateWindowExW(0x08000008,'STATIC','offer-pixel-fixture',0x90000006,
            0,0,1000,700,None,None,window.k.GetModuleHandleW(None),None)
        self.assertTrue(host);self.addCleanup(lambda:u.DestroyWindow(host))
        u.UpdateWindow.argtypes=[W.HWND];u.UpdateWindow.restype=W.BOOL;u.UpdateWindow(host)
        u.GetDC.argtypes=[W.HWND];u.GetDC.restype=W.HDC
        u.ReleaseDC.argtypes=[W.HWND,W.HDC];u.ReleaseDC.restype=C.c_int
        g.GetPixel.argtypes=[W.HDC,C.c_int,C.c_int];g.GetPixel.restype=W.DWORD
        u.WindowFromPoint.argtypes=[W.POINT];u.WindowFromPoint.restype=W.HWND
        previous=u.SetThreadDpiAwarenessContext(C.c_void_p(-4))
        self.addCleanup(lambda:u.SetThreadDpiAwarenessContext(previous))
        (x,y,w,h),regions=offer_band(1000,700)
        def pixel(px,py):
            dc=u.GetDC(None)
            try:
                value=g.GetPixel(dc,px,py)
                return value&255,(value>>8)&255,(value>>16)&255
            finally:u.ReleaseDC(None,dc)
        def all_drawn():
            return all(0<min(pixel(x+rx+4,y+3)) and max(pixel(x+rx+4,y+3))<60 for rx,rw in regions)
        self.until(all_drawn)
        gapx=x+(regions[0][0]+regions[0][1]+regions[1][0])//2
        self.until(lambda:min(pixel(gapx,y+3))>200)
        self.assertEqual(window._registered,{1})
        self.assertNotEqual(u.WindowFromPoint(W.POINT(gapx,y+3)),window.hwnd)
        self.assertNotEqual(u.GetForegroundWindow(),window.hwnd)
        values[0]=Frame();self.until(lambda:not window._visible and not window._registered)
        self.assertIsNone(window.error)

    def test_f7_opponent_switch_and_live_gold_do_not_reset_build_navigation(self):
        values=[Frame(True, View('match', (Card('Ouro em itens', ('+600 G',)),
            Card('Build preparada', tuple('Item '+str(i) for i in range(50))))), opponent_switch=True)]
        switched=[]
        window=NativeOverlay(lambda:values[0], foreground=lambda:(0,0,1280,720))
        window.set_opponent_action(lambda:switched.append(True))
        self.addCleanup(window.stop)
        window.start();self.assertTrue(window.ready.wait(8));self.assertIsNone(window.error)
        self.until(lambda:window._visible and 4 in window._registered)
        u=window.u
        u.SendMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.SendMessageW.restype=C.c_ssize_t
        u.SendMessageW(window.hwnd,0x312,4,0)
        self.assertEqual(switched,[True])
        u.SendMessageW(window.hwnd,0x312,2,0)
        u.SendMessageW(window.hwnd,0x312,3,0)
        self.assertEqual((window._index,window._page),(1,1))
        values[0]=Frame(True,View('match',(Card('Ouro em itens',('+900 G',)),values[0].view.cards[1])),opponent_switch=True)
        self.until(lambda:window._view==values[0].view)
        self.assertEqual((window._index,window._page),(1,1))
        values[0]=Frame(True,values[0].view)
        self.until(lambda:4 not in window._registered)
        u.SendMessageW(window.hwnd,0x312,4,0)
        self.assertEqual(switched,[True])

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
