"""One reusable local OCR process and one bounded observer for live offers."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from sexo2.services.loadouts import GameCatalog
from .offers import Matcher, OfferState


class OcrProcess:
    def __init__(self, executable=None, *, timeout=2):
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
        self.path = Path(executable) if executable else root / 'sexo2/overlay/bin/sexo2-offer-reader.exe'
        if not executable and not hasattr(sys, '_MEIPASS') and not self.path.is_file():
            self.path = root / 'native/overlay-host/target/release/sexo2-offer-reader.exe'
        self.timeout = timeout
        self._child = self._io = None
        self._lock = threading.Lock()
        self._closed = False
        self._seq = 0

    def recognize(self, images):
        if len(images) != 3:
            raise OSError('Three title crops required.')
        rows = []
        for image in images:
            w, h = image.size
            if not 0 < w <= 768 or not 0 < h <= 240:
                raise OSError('OCR crop outside limits.')
            rows.append({'width': w, 'height': h,
                         'bgra': base64.b64encode(image.tobytes('raw', 'BGRA')).decode('ascii')})
        with self._lock:
            if self._closed or (self._io is not None and self._io.is_alive()):
                raise OSError('OCR reader unavailable.')
            cold = self._child is None
            if cold:
                if os.name != 'nt' or not self.path.is_file():
                    raise OSError('Local OCR helper unavailable.')
                self._child = subprocess.Popen([str(self.path)], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            child = self._child
            self._seq += 1
            sequence = self._seq
            payload = (json.dumps({'v': 1, 'seq': sequence, 'images': rows}, separators=(',', ':')) + '\n').encode()
            if len(payload) > 4 * 1024 * 1024:
                raise OSError('OCR message outside limits.')
            done, result = threading.Event(), []
            def exchange():
                try:
                    child.stdin.write(payload); child.stdin.flush()
                    line = child.stdout.readline(8193)
                    if len(line) > 8192 or not line.endswith(b'\n'):
                        raise ValueError('Invalid OCR response.')
                    result.append(json.loads(line))
                except (OSError, ValueError):
                    pass
                finally:
                    done.set()
            self._io = threading.Thread(target=exchange, name='SEXO2-OCR-pipe', daemon=True)
            self._io.start()
        if not done.wait(max(self.timeout, 8) if cold else self.timeout) or not result:
            self.close()
            raise OSError('Local OCR timed out or failed.')
        row = result[0]
        titles = row.get('titles') if isinstance(row, dict) else None
        if (not isinstance(row, dict) or row.get('v') != 1 or row.get('seq') != sequence or row.get('status') != 'ok'
                or not isinstance(titles, list) or len(titles) != 3
                or any(not isinstance(s, str) or len(s) > 256 for s in titles)):
            self.close()
            raise OSError('Local OCR schema changed.')
        return titles

    def close(self):
        with self._lock:
            self._closed = True
            child, io = self._child, self._io
            self._child = None
        if child:
            try:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=.5)
            except (OSError, subprocess.SubprocessError):
                pass
            if io is not None and io is not threading.current_thread():
                io.join(timeout=.5)
            if io is None or not io.is_alive():
                for stream in (child.stdin, child.stdout):
                    try:
                        stream.close()
                    except OSError:
                        pass


class OfferReader:
    def __init__(self, lcu, *, screen_factory=None, ocr_factory=OcrProcess, clock=time.monotonic):
        self.catalog = GameCatalog(lcu)
        self._screen_factory, self._ocr_factory, self._clock = screen_factory, ocr_factory, clock
        self._lock = threading.Lock()
        self._state = OfferState()
        self._context = None
        self._generation = 0
        self._renewed = float('-inf')
        self._stop = threading.Event()
        self._thread = None
        self._ocr = None
        self._status = 'waiting'

    def ensure(self, context):
        with self._lock:
            if self._stop.is_set():
                return
            if context != self._context:
                self._context = context
                self._generation += 1
                self._state.clear()
            self._renewed = self._clock()
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name='SEXO2-offers', daemon=True)
                self._thread.start()

    def current(self, context):
        with self._lock:
            return self._state.current(context, self._clock())

    def clear(self):
        with self._lock:
            self._context = None
            self._generation += 1
            self._state.clear()

    def diagnostic(self):
        with self._lock:
            return self._status

    def _run(self):
        from .screen import Screen
        screen = None
        matcher = None
        generation = None
        blocked_until = 0
        while not self._stop.is_set():
            started = self._clock()
            images = None
            with self._lock:
                if self._context is not None and self._clock() - self._renewed > 8:
                    self._context = None
                    self._generation += 1
                    self._state.clear()
                context, current_generation = self._context, self._generation
            try:
                if context is None:
                    if self._ocr:
                        self._ocr.close(); self._ocr = None
                elif self._clock() >= blocked_until:
                    if current_generation != generation:
                        self.catalog.bind_revision(context[0])
                        # Shared official ID/name catalog, not statistics. Mode
                        # separation is enforced when looking up the metrics.
                        matcher = Matcher(self.catalog.names('cherry-augments'))
                        generation = current_generation
                    if screen is None:
                        screen = self._screen_factory() if self._screen_factory else Screen()
                    captured_at = self._clock()
                    target, images = screen.capture()
                    if self._ocr is None:
                        self._ocr = self._ocr_factory()
                    titles = self._ocr.recognize(images)
                    images = None
                    choices = tuple(matcher.match(s) for s in titles)
                    if not screen.valid(target):
                        raise OSError('Window changed during OCR.')
                    with self._lock:
                        if (self._context == context and self._generation == current_generation
                                and self._clock() - self._renewed <= 8 and not self._stop.is_set()):
                            if self._clock() - captured_at >= 2:
                                self._state.clear()
                                self._status = 'slow'
                            else:
                                self._state.observe(context, choices, captured_at)
                                self._status = 'reading'
            except Exception:
                # No image, OCR text, names, account fields, paths or exception repr in logs.
                with self._lock:
                    self._state.clear()
                    self._status = 'unavailable'
                if self._ocr:
                    self._ocr.close(); self._ocr = None
                blocked_until = self._clock() + 5
            images = None  # Never retain pixels while paused or between iterations.
            self._stop.wait(max(.05, 1 - (self._clock() - started)))
        ocr = self._ocr
        if ocr:
            ocr.close()

    def close(self):
        self._stop.set()
        self.clear()
        ocr = self._ocr
        if ocr:
            ocr.close()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=.2)
