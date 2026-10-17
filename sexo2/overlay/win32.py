"""External Win32/GDI window. No hooks, injection, game memory or browser."""
import ctypes as C
from ctypes import wintypes as W
import logging
import threading
import textwrap

log = logging.getLogger(__name__)


class NativeOverlay:
    def __init__(self, frame, *, foreground=None):
        self.frame = frame
        self.foreground = foreground
        self.ready = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self.hwnd = None
        self.error = None
        self._expanded = False
        self._index = self._page = 0
        self._view = None
        self._registered = set()
        self._hotkey_attempted = False
        self._visible = False
        self._state = None

    def start(self):
        if self._thread is None and not self._stop.is_set():
            self._thread = threading.Thread(target=self._run, name='SEXO2-Overlay-window', daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        # Timer drains the stop flag on the owning UI thread, including creation races.
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)

    def _api(self):
        self.u = C.WinDLL('user32', use_last_error=True)
        self.g = C.WinDLL('gdi32', use_last_error=True)
        self.k = C.WinDLL('kernel32', use_last_error=True)
        self.proc_type = C.WINFUNCTYPE(C.c_ssize_t, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
        class WindowClass(C.Structure):
            _fields_ = [('style', W.UINT), ('proc', self.proc_type), ('clsExtra', C.c_int),
                        ('wndExtra', C.c_int), ('instance', W.HINSTANCE), ('icon', W.HICON),
                        ('cursor', W.HANDLE), ('background', W.HBRUSH),
                        ('menu', W.LPCWSTR), ('name', W.LPCWSTR)]
        class Paint(C.Structure):
            _fields_ = [('dc', W.HDC), ('erase', W.BOOL), ('rect', W.RECT),
                        ('restore', W.BOOL), ('update', W.BOOL), ('reserved', C.c_byte * 32)]
        self.WindowClass, self.Paint = WindowClass, Paint
        # Explicit signatures are necessary for handles/pointers on Windows x64.
        def bind(dll, name, result, *args):
            fn = getattr(dll, name); fn.restype = result; fn.argtypes = args
            return fn
        bind(self.k, 'GetModuleHandleW', W.HMODULE, W.LPCWSTR)
        bind(self.k, 'OpenProcess', W.HANDLE, W.DWORD, W.BOOL, W.DWORD)
        bind(self.k, 'QueryFullProcessImageNameW', W.BOOL, W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD))
        bind(self.k, 'CloseHandle', W.BOOL, W.HANDLE)
        bind(self.u, 'RegisterClassW', W.ATOM, C.POINTER(WindowClass))
        bind(self.u, 'UnregisterClassW', W.BOOL, W.LPCWSTR, W.HINSTANCE)
        bind(self.u, 'CreateWindowExW', W.HWND, W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD,
             C.c_int, C.c_int, C.c_int, C.c_int, W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID)
        bind(self.u, 'DefWindowProcW', C.c_ssize_t, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
        bind(self.u, 'DestroyWindow', W.BOOL, W.HWND)
        bind(self.u, 'GetMessageW', W.BOOL, C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT)
        bind(self.u, 'TranslateMessage', W.BOOL, C.POINTER(W.MSG))
        bind(self.u, 'DispatchMessageW', C.c_ssize_t, C.POINTER(W.MSG))
        bind(self.u, 'PostQuitMessage', None, C.c_int)
        bind(self.u, 'SetTimer', C.c_size_t, W.HWND, C.c_size_t, W.UINT, W.LPVOID)
        bind(self.u, 'KillTimer', W.BOOL, W.HWND, C.c_size_t)
        bind(self.u, 'RegisterHotKey', W.BOOL, W.HWND, C.c_int, W.UINT, W.UINT)
        bind(self.u, 'UnregisterHotKey', W.BOOL, W.HWND, C.c_int)
        bind(self.u, 'GetForegroundWindow', W.HWND)
        bind(self.u, 'IsIconic', W.BOOL, W.HWND)
        bind(self.u, 'IsWindowVisible', W.BOOL, W.HWND)
        bind(self.u, 'GetWindowThreadProcessId', W.DWORD, W.HWND, C.POINTER(W.DWORD))
        bind(self.u, 'GetClientRect', W.BOOL, W.HWND, C.POINTER(W.RECT))
        bind(self.u, 'ClientToScreen', W.BOOL, W.HWND, C.POINTER(W.POINT))
        bind(self.u, 'SetWindowPos', W.BOOL, W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT)
        bind(self.u, 'ShowWindow', W.BOOL, W.HWND, C.c_int)
        bind(self.u, 'SetLayeredWindowAttributes', W.BOOL, W.HWND, W.DWORD, W.BYTE, W.DWORD)
        bind(self.u, 'InvalidateRect', W.BOOL, W.HWND, W.LPVOID, W.BOOL)
        bind(self.u, 'BeginPaint', W.HDC, W.HWND, C.POINTER(Paint))
        bind(self.u, 'EndPaint', W.BOOL, W.HWND, C.POINTER(Paint))
        bind(self.u, 'FillRect', C.c_int, W.HDC, C.POINTER(W.RECT), W.HBRUSH)
        bind(self.u, 'DrawTextW', C.c_int, W.HDC, W.LPCWSTR, C.c_int, C.POINTER(W.RECT), W.UINT)
        bind(self.g, 'CreateSolidBrush', W.HBRUSH, W.DWORD)
        bind(self.g, 'CreateFontW', W.HFONT, C.c_int, C.c_int, C.c_int, C.c_int, C.c_int,
             W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.LPCWSTR)
        bind(self.g, 'SelectObject', W.HANDLE, W.HDC, W.HANDLE)
        bind(self.g, 'DeleteObject', W.BOOL, W.HANDLE)
        bind(self.g, 'SetBkMode', C.c_int, W.HDC, C.c_int)
        bind(self.g, 'SetTextColor', W.DWORD, W.HDC, W.DWORD)
        bind(self.g, 'GetTextExtentPoint32W', W.BOOL, W.HDC, W.LPCWSTR, C.c_int, C.POINTER(W.SIZE))

    def _foreground_game(self):
        hwnd = self.u.GetForegroundWindow()
        if not hwnd or self.u.IsIconic(hwnd) or not self.u.IsWindowVisible(hwnd):
            return None
        pid = W.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, C.byref(pid))
        process = self.k.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
        if not process:
            return None
        try:
            path, length = C.create_unicode_buffer(32768), W.DWORD(32768)
            if not self.k.QueryFullProcessImageNameW(process, 0, path, C.byref(length)):
                return None
            if path.value.rsplit('\\', 1)[-1].lower() not in ('league of legends.exe', 'league of legends (tm) client.exe'):
                return None
        finally:
            self.k.CloseHandle(process)
        rect, origin = W.RECT(), W.POINT()
        if not self.u.GetClientRect(hwnd, C.byref(rect)) or not self.u.ClientToScreen(hwnd, C.byref(origin)):
            return None
        return (origin.x, origin.y, rect.right, rect.bottom)

    def _hotkeys(self, active):
        if active and not self._hotkey_attempted:
            self._hotkey_attempted = True
            for identifier, key in ((1, 0x77), (2, 0x78), (3, 0x79)):  # F8/F9/F10, MOD_NOREPEAT
                if self.u.RegisterHotKey(self.hwnd, identifier, 0x4000, key):
                    self._registered.add(identifier)
            if 1 not in self._registered:
                self.error = 'F8 já está em uso; overlay oculto.'
                log.warning(self.error)
                for identifier in self._registered:
                    self.u.UnregisterHotKey(self.hwnd, identifier)
                self._registered.clear()
        elif not active:
            for identifier in self._registered:
                self.u.UnregisterHotKey(self.hwnd, identifier)
            self._registered.clear()
            self._hotkey_attempted = False

    def _tick(self):
        if self._stop.is_set():
            self.u.DestroyWindow(self.hwnd)
            return
        frame = self.frame()
        bounds = (self.foreground or self._foreground_game)() if frame.active else None
        active = bounds is not None
        self._hotkeys(active)
        if not active or 1 not in self._registered:
            if self._visible:
                self.u.ShowWindow(self.hwnd, 0)
                self._visible = False
            return
        if self._view != frame.view:
            new_match = self._view is None or self._view.key != frame.view.key
            self._view = frame.view
            self._index, self._page = frame.view.selected, 0
            if new_match:
                self._expanded = False
        x, y, width, height = bounds
        width = min(420, width - 24)
        height = min(570, height - 160) if self._expanded else 40
        if width < 240 or height < 40:
            self.u.ShowWindow(self.hwnd, 0); self._visible = False
            return
        state = (x, y, width, height, frame.view, self._expanded, self._index, self._page)
        if state != self._state or not self._visible:
            # HWND_TOPMOST, SWP_NOACTIVATE | SWP_SHOWWINDOW
            self.u.SetWindowPos(self.hwnd, W.HWND(-1), x + bounds[2] - width - 12, y + 110,
                                width, height, 0x10 | 0x40)
            self.u.InvalidateRect(self.hwnd, None, True)
            self._state = state
            self._visible = True

    def _paint(self, hwnd):
        paint, rect = self.Paint(), W.RECT()
        dc = self.u.BeginPaint(hwnd, C.byref(paint))
        try:
            self.u.GetClientRect(hwnd, C.byref(rect))
            self.u.FillRect(dc, C.byref(rect), self._brush)
            previous = self.g.SelectObject(dc, self._font)
            self.g.SetBkMode(dc, 1)
            self.g.SetTextColor(dc, 0xAEC1C8)
            size = W.SIZE()
            self.g.GetTextExtentPoint32W(dc, 'M', 1, C.byref(size))
            line_height = max(18, size.cy + 3)
            columns = max(20, (rect.right - 28) // max(8, size.cx))
            def draw(value, y):
                r = W.RECT(14, y, rect.right - 14, y + line_height)
                self.u.DrawTextW(dc, value, -1, C.byref(r), 0x800 | 0x20)  # NOPREFIX | SINGLELINE
            draw('SEXO2 · F8 expandir/recolher', 10)
            if self._expanded:
                cards = self._view.cards if self._view else ()
                if cards:
                    self._index %= len(cards)
                    card = cards[self._index]
                    rows = []
                    for line in (card.title, '', *card.lines):
                        rows.extend(textwrap.wrap(line, width=columns, break_long_words=True) or [''])
                    capacity = max(1, (rect.bottom - 90) // line_height)
                    count = max(1, (len(rows) + capacity - 1) // capacity)
                    self._page %= count
                    for i, line in enumerate(rows[self._page * capacity:(self._page + 1) * capacity]):
                        draw(line, 42 + i * line_height)
                    footer = f'F9 sugestão {self._index + 1}/{len(cards)} · F10 {self._page + 1}/{count}'
                else:
                    for i, line in enumerate(('Nenhuma sugestão preparada.', 'Consulte SEXO2 · Builds na seleção', 'da próxima partida.')):
                        draw(line, 46 + i * line_height)
                    footer = 'Somente leitura · cliques passam ao jogo'
                draw(footer, rect.bottom - 30)
            self.g.SelectObject(dc, previous)
        finally:
            self.u.EndPaint(hwnd, C.byref(paint))

    def _procedure(self, hwnd, message, wparam, lparam):
        try:
            if message == 0x113:  # WM_TIMER
                self._tick(); return 0
            if message == 0x312 and int(wparam) in self._registered:  # WM_HOTKEY
                if not self.frame().active or not (self.foreground or self._foreground_game)():
                    self._tick(); return 0
                if int(wparam) == 1:
                    self._expanded = not self._expanded
                elif int(wparam) == 2:
                    self._index += 1; self._page = 0
                else:
                    self._page += 1
                self._tick(); return 0
            if message == 0xF:  # WM_PAINT
                self._paint(hwnd); return 0
            if message == 0x84:  # WM_NCHITTEST: never consume mouse input
                return -1
            if message == 0x21:  # WM_MOUSEACTIVATE
                return 3
            if message == 2:  # WM_DESTROY
                self._hotkeys(False)
                self.u.PostQuitMessage(0); return 0
        except Exception:
            self.error = 'Falha na janela do overlay.'
            self._stop.set()
            log.warning(self.error)
        return self.u.DefWindowProcW(hwnd, message, wparam, lparam)

    def _run(self):
        registered = False
        try:
            self._api()
            instance = self.k.GetModuleHandleW(None)
            class_name = 'SEXO2Overlay_' + str(id(self))
            self._callback = self.proc_type(self._procedure)
            window_class = self.WindowClass(0, self._callback, 0, 0, instance, None, None, None, None, class_name)
            if not self.u.RegisterClassW(C.byref(window_class)):
                raise OSError('RegisterClass')
            registered = True
            self._brush = self.g.CreateSolidBrush(0x1B1409)
            self._font = self.g.CreateFontW(-14, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 4, 0, 'Consolas')
            # TOPMOST | TRANSPARENT | TOOLWINDOW | LAYERED | NOACTIVATE; WS_POPUP.
            self.hwnd = self.u.CreateWindowExW(0x080800A8, class_name, 'SEXO2 · Builds', 0x80000000,
                                               0, 0, 420, 40, None, None, instance, None)
            if not self.hwnd or not self._brush or not self._font:
                raise OSError('CreateWindow')
            if not self.u.SetLayeredWindowAttributes(self.hwnd, 0, 242, 2):
                raise OSError('LayeredWindow')
            if not self.u.SetTimer(self.hwnd, 1, 200, None):
                raise OSError('Timer')
            self.ready.set()
            message = W.MSG()
            while True:
                code = self.u.GetMessageW(C.byref(message), None, 0, 0)
                if code <= 0:
                    break
                self.u.TranslateMessage(C.byref(message))
                self.u.DispatchMessageW(C.byref(message))
        except Exception:
            self.error = 'Não foi possível iniciar o overlay Windows.'
            log.warning(self.error)
        finally:
            if self.hwnd:
                self._hotkeys(False)
                self.u.KillTimer(self.hwnd, 1)
                self.u.DestroyWindow(self.hwnd)
                self.hwnd = None
            for name in ('_font', '_brush'):
                handle = getattr(self, name, None)
                if handle:
                    self.g.DeleteObject(handle)
            if registered:
                self.u.UnregisterClassW(class_name, instance)
            self.ready.set()
