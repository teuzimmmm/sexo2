"""External DirectComposition window; Win32 owns focus, geometry and hotkeys."""
import ctypes as C
from ctypes import wintypes as W
import logging
import threading
import textwrap
from .processes import ProcessCatalog
from .composition import Composition

log = logging.getLogger(__name__)


class NativeOverlay:
    def __init__(self, frame, *, foreground=None, process_catalog=None, foreground_hwnd=None):
        self.frame = frame
        self.foreground = foreground
        self.processes = process_catalog or ProcessCatalog()
        self.foreground_hwnd = foreground_hwnd
        self.ready = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self.hwnd = None
        self.error = None
        self._expanded = False
        self._index = self._page = 0
        self._renderer = None
        self._renders = self._raises = 0
        self._view = None
        self._registered = set()
        self._hotkey_attempted = False
        self._visible = False
        self._position = None
        self._state = None
        self._diagnostic = {'code': 'not-started', 'message': 'Janela ainda não iniciada.', 'windowShown': False}

    def diagnostic(self):
        return dict(self._diagnostic, engine='directcomposition-d3d11', renders=self._renders,
                    raises=self._raises, driver=getattr(self._renderer, 'driver', None), hotkeys={f'F{i + 7}': i in self._registered for i in (1, 2, 3)})

    def _status(self, code, message):
        self._diagnostic = {'code': code, 'message': message,
                            'windowShown': self._diagnostic['windowShown'] or (code == 'visible' and not self._view.key == 'preview')}

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
        bind(self.u, 'SetThreadDpiAwarenessContext', W.HANDLE, W.HANDLE)
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

    def _foreground_bounds(self, preview=False):
        hwnd = self.foreground_hwnd() if self.foreground_hwnd else self.u.GetForegroundWindow()
        if not hwnd or self.u.IsIconic(hwnd) or not self.u.IsWindowVisible(hwnd):
            return None
        if not preview:
            pid = W.DWORD()
            self.u.GetWindowThreadProcessId(hwnd, C.byref(pid))
            if not self.processes.contains(pid.value):
                return None
        rect, origin = W.RECT(), W.POINT()
        if not self.u.GetClientRect(hwnd, C.byref(rect)) or not self.u.ClientToScreen(hwnd, C.byref(origin)):
            return None
        return (origin.x, origin.y, rect.right, rect.bottom)

    def _foreground_game(self):
        return self._foreground_bounds()

    def _hotkeys(self, active):
        if active and not self._hotkey_attempted:
            self._hotkey_attempted = True
            for identifier, key in ((1, 0x77), (2, 0x78), (3, 0x79)):  # F8/F9/F10, MOD_NOREPEAT
                if self.u.RegisterHotKey(self.hwnd, identifier, 0x4000, key):
                    self._registered.add(identifier)
            if 1 not in self._registered:
                log.warning('F8 já está em uso; overlay expandido sem esse atalho.')
                self._expanded = True
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
        bounds = None
        if frame.active:
            try:
                bounds = self.foreground() if self.foreground else self._foreground_bounds(frame.preview)
            except OSError:
                self._hotkeys(False)
                self.u.ShowWindow(self.hwnd, 0)
                self._visible = False
                self._status('process-unavailable', 'Não foi possível enumerar os processos; tentando novamente.')
                return
        active = bounds is not None
        self._hotkeys(active)
        if not active:
            if self._visible:
                self.u.ShowWindow(self.hwnd, 0)
                self._visible = False
            self._status('not-game-foreground' if frame.active else 'inactive',
                         'Jogo não detectado em primeiro plano.' if frame.active else 'Aguardando contexto da partida ou uma prévia.')
            return
        if self._view != frame.view:
            new_match = self._view is None or self._view.key != frame.view.key
            self._view = frame.view
            self._index, self._page = frame.view.selected, 0
            if new_match:
                self._expanded = True
        x, y, width, height = bounds
        width = min(420, width - 24)
        height = min(570, height - 160) if self._expanded else 40
        if width < 240 or height < 40:
            self.u.ShowWindow(self.hwnd, 0); self._visible = False
            return
        state = (x, y, width, height, frame.view, self._expanded, self._index, self._page)
        if state != self._state or not self._visible:
            self._paint(width, height)
            self._state = state
        # Another topmost application (including the game) can change z-order
        # without changing our data. Reassert every 200 ms, never activate/focus.
        position = (x + bounds[2] - width - 12, y + 110, width, height)
        flags = 0x10 | 0x40
        if position == self._position:
            flags |= 0x1 | 0x2  # SWP_NOSIZE | SWP_NOMOVE; z-order still repaired.
        if not self.u.SetWindowPos(self.hwnd, W.HWND(-1), *position, flags):
            self.u.ShowWindow(self.hwnd, 0)
            self._visible = False
            self._status('show-failed', 'O Windows recusou exibir a janela do overlay.')
            return
        self._position = position
        self._raises += 1
        self._visible = True
        self._status('preview' if frame.preview else 'visible',
                     'Prévia desenhada por DirectComposition.' if frame.preview else
                     'DirectComposition desenhou o painel; exibição no LoL ainda requer confirmação visual.')

    def _paint(self, width, height):
        # Only presentation strings enter the DLL. No LCU/game context or raw data.
        columns = max(20, (width - 28) // 8)
        header = 'SEXO2 · F8 expandir/recolher' if 1 in self._registered else 'SEXO2 · F8 ocupado'
        body, footer = '', ''
        if self._expanded:
            cards = self._view.cards if self._view else ()
            if cards:
                self._index %= len(cards)
                card = cards[self._index]
                rows = []
                for line in (card.title, '', *card.lines):
                    rows.extend(textwrap.wrap(line, width=columns, break_long_words=True) or [''])
                capacity = max(1, (height - 90) // 20)
                count = max(1, (len(rows) + capacity - 1) // capacity)
                self._page %= count
                body = '\n'.join(rows[self._page * capacity:(self._page + 1) * capacity])
                footer = (f"{'F9' if 2 in self._registered else 'F9 ocupado'} {self._index + 1}/{len(cards)} · "
                          f"{'F10' if 3 in self._registered else 'F10 ocupado'} {self._page + 1}/{count}")
            else:
                body = 'Nenhuma sugestão preparada.\nConsulte SEXO2 · Builds na seleção\nda próxima partida.'
                footer = 'Somente leitura · cliques passam ao jogo'
        self._renderer.draw(width, height, header, body, footer)
        self._renders += 1

    def _procedure(self, hwnd, message, wparam, lparam):
        try:
            if message == 0x113:  # WM_TIMER
                self._tick(); return 0
            if message == 0x312 and int(wparam) in self._registered:  # WM_HOTKEY
                frame = self.frame()
                try:
                    foreground = self.foreground() if self.foreground else self._foreground_bounds(frame.preview)
                except OSError:
                    self._tick(); return 0
                if not frame.active or not foreground:
                    self._tick(); return 0
                if int(wparam) == 1:
                    self._expanded = not self._expanded
                elif int(wparam) == 2:
                    self._index += 1; self._page = 0
                else:
                    self._page += 1
                self._tick(); return 0
            if message == 0xF:  # Validate the update region; DComp draws its own surface.
                paint = self.Paint()
                self.u.BeginPaint(hwnd, C.byref(paint))
                self.u.EndPaint(hwnd, C.byref(paint))
                return 0
            if message == 0x14:  # WM_ERASEBKGND: no GDI redirection bitmap.
                return 1
            if message == 0x84:  # WM_NCHITTEST: never consume mouse input
                return -1
            if message == 0x21:  # WM_MOUSEACTIVATE
                return 3
            if message == 2:  # WM_DESTROY
                self._hotkeys(False)
                self.u.PostQuitMessage(0); return 0
        except Exception as error:
            self.error = ('Falha no desenho DirectComposition.' +
                          (' ' + str(error) if isinstance(error, OSError) and str(error).startswith('DirectComposition HRESULT') else ''))
            self._status('window-error', self.error)
            self._stop.set()
            log.warning(self.error)
        return self.u.DefWindowProcW(hwnd, message, wparam, lparam)

    def _run(self):
        registered = False
        dpi = None
        try:
            self._api()
            dpi = self.u.SetThreadDpiAwarenessContext(C.c_void_p(-4))
            if not dpi:
                raise OSError('DPI context unavailable')
            instance = self.k.GetModuleHandleW(None)
            class_name = 'SEXO2Overlay_' + str(id(self))
            self._callback = self.proc_type(self._procedure)
            window_class = self.WindowClass(0, self._callback, 0, 0, instance, None, None, None, None, class_name)
            if not self.u.RegisterClassW(C.byref(window_class)):
                raise OSError('RegisterClass')
            registered = True
            # Layered transparent hit-testing + no redirection bitmap. Content
            # is supplied exclusively by the DirectComposition visual tree.
            self.hwnd = self.u.CreateWindowExW(0x082800A8, class_name, 'SEXO2 · Builds', 0x80000000,
                                               0, 0, 420, 40, None, None, instance, None)
            if not self.hwnd:
                raise OSError('CreateWindow')
            self._renderer = Composition(self.hwnd)
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
        except Exception as error:
            self.error = ('Não foi possível iniciar DirectComposition.' +
                          (' ' + str(error) if isinstance(error, OSError) and str(error).startswith('DirectComposition HRESULT') else ''))
            self._status('window-error', self.error)
            log.warning(self.error)
        finally:
            self._visible = False
            if self._renderer is not None:
                self._renderer.close()
                self._renderer = None
            if self.hwnd:
                self._hotkeys(False)
                self.u.KillTimer(self.hwnd, 1)
                self.u.DestroyWindow(self.hwnd)
                self.hwnd = None
            if registered:
                self.u.UnregisterClassW(class_name, instance)
            if dpi:
                self.u.SetThreadDpiAwarenessContext(dpi)
            self.ready.set()
