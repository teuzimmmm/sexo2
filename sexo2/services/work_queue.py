"""Bounded serial execution for synchronous panel services."""

import logging
import queue
import threading
import time

log = logging.getLogger(__name__)


class SerialWorker:
    """One application-lifetime worker; accepted actions retain submission order.

    submit() never waits for a slow service. A full/closed queue returns False,
    allowing the caller to answer the original request with its existing error
    protocol. close() drains accepted work; it cannot interrupt an active HTTP
    request, which must have its own timeout.
    """

    def __init__(self, name, capacity=16):
        self.name = name
        self._queue = queue.Queue(maxsize=capacity)
        self._lock = threading.Lock()
        self._closed = threading.Event()
        self._thread = None

    def submit(self, work, on_error):
        with self._lock:
            if self._closed.is_set():
                return False
            try:
                self._queue.put_nowait((work, on_error, time.monotonic()))
            except queue.Full:
                return False
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name=self.name, daemon=True)
                self._thread.start()
            return True

    def close(self, timeout=1):
        with self._lock:
            self._closed.set()
            thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        return thread is None or not thread.is_alive()

    def _run(self):
        if self.name == "SEXO2-Mod-library":
            try:
                import sys, ctypes

                if sys.platform == "win32":
                    api = ctypes.WinDLL("kernel32", use_last_error=True)
                    api.GetCurrentThread.restype = ctypes.c_void_p
                    api.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
                    api.SetThreadPriority(api.GetCurrentThread(), 0x10000)
            except Exception:
                log.debug("[MOD_LIBRARY] Background scheduling unavailable")
        while not self._closed.is_set() or not self._queue.empty():
            try:
                work, on_error, queued_at = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            started = time.monotonic()
            try:
                work()
            except Exception as error:
                try:
                    on_error(error)
                except Exception:
                    # Neither a failed action nor its error response kills
                    # subsequent actions. Do not log request content.
                    log.error("[SEXO2] Service error response failed: %s", self.name)
            finally:
                finished = time.monotonic()
                if started - queued_at >= 0.5 or finished - started >= 0.5:
                    log.warning(
                        "[PERFORMANCE] service=%s queue_s=%.3f work_s=%.3f pending=%d",
                        self.name,
                        started - queued_at,
                        finished - started,
                        self._queue.qsize(),
                    )
                self._queue.task_done()
