"""Small, bounded HTTP transport for the public LoLalytics page data."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
import math
import threading
import time
from urllib.parse import urlsplit

import requests

from .errors import HTTPStatusError, ResponseTooLarge, TransportError


_ALLOWED_HOSTS = {"lolalytics.com", "a1.lolalytics.com"}
_RETRY_STATUSES = {429, 502, 503, 504}
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def _validate_url(url: str) -> None:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except (TypeError, ValueError):
        raise TransportError("Invalid LoLalytics URL") from None
    allowed_path = (host == "lolalytics.com" and parts.path.endswith("/q-data.json")) or (
        host == "a1.lolalytics.com" and parts.path == "/mega/"
    )
    if (
        parts.scheme != "https"
        or host not in _ALLOWED_HOSTS
        or port not in (None, 443)
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
        or not allowed_path
    ):
        raise TransportError("URL is outside the supported LoLalytics endpoints")


def _retry_after(value: str | None, now: float) -> float | None:
    if not value:
        return None
    try:
        delay = float(value.strip())
    except (TypeError, ValueError):
        delay = None
    if delay is not None:
        if not math.isfinite(delay):
            return math.inf
        return max(0.0, delay)
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            from datetime import timezone

            dt = dt.replace(tzinfo=timezone.utc)
        delay = dt.timestamp() - now
        return max(0.0, delay) if math.isfinite(delay) else math.inf
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _finite_number(value, name, *, positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be a finite number") from None
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be finite and {qualifier}")
    return number


class HTTPTransport:
    """Serialized requests session with bounded retries and response size."""

    validate_url = staticmethod(_validate_url)

    def __init__(
        self,
        session=None,
        *,
        timeout=(5, 20),
        max_bytes=_MAX_RESPONSE_BYTES,
        max_wait=30.0,
        min_interval=1.0,
        attempts=3,
        clock=time.monotonic,
        wall_clock=time.time,
        sleep=time.sleep,
    ):
        try:
            if len(timeout) != 2:
                raise ValueError
            self._timeout = tuple(_finite_number(part, "timeout", positive=True) for part in timeout)
        except (TypeError, ValueError):
            raise ValueError("timeout must contain two finite positive numbers") from None
        try:
            self._max_bytes = int(max_bytes)
            if self._max_bytes <= 0:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError("max_bytes must be a positive integer") from None
        self._max_bytes = min(self._max_bytes, _MAX_RESPONSE_BYTES)
        self._max_wait = _finite_number(max_wait, "max_wait")
        self._min_interval = _finite_number(min_interval, "min_interval")
        try:
            self._attempts = int(attempts)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("attempts must be a positive integer") from None
        if self._attempts <= 0:
            raise ValueError("attempts must be a positive integer")
        self._attempts = min(3, self._attempts)
        self._session = session if session is not None else requests.Session()
        self._clock = clock
        self._wall_clock = wall_clock
        self._sleep = sleep
        self._lock = threading.RLock()
        self._last_request = None
        self._closed = False

    def _pace(self):
        if self._last_request is not None:
            remaining = self._min_interval - (self._clock() - self._last_request)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request = self._clock()

    def get(self, url: str) -> bytes:
        self.validate_url(url)
        with self._lock:
            if self._closed:
                raise TransportError("HTTP transport is closed")
            last_error = None
            for attempt in range(self._attempts):
                self._pace()
                response = None
                retry_wait = None
                retry_error = None
                result = None
                try:
                    response = self._session.get(
                        url,
                        timeout=self._timeout,
                        stream=True,
                        allow_redirects=False,
                        headers={"Accept": "application/json,text/html;q=0.9"},
                    )
                    status = int(response.status_code)
                    if 300 <= status < 400:
                        raise HTTPStatusError(status)
                    if status in _RETRY_STATUSES:
                        delay = _retry_after(response.headers.get("Retry-After"), self._wall_clock())
                        retry_error = HTTPStatusError(status, delay)
                        if attempt + 1 >= self._attempts or (delay is not None and delay > self._max_wait):
                            raise retry_error
                        retry_wait = delay if delay is not None else min(2**attempt, self._max_wait)
                    elif status < 200 or status >= 300:
                        raise HTTPStatusError(status)
                    else:
                        chunks = []
                        size = 0
                        for chunk in response.iter_content(chunk_size=64 * 1024):
                            if not chunk:
                                continue
                            size += len(chunk)
                            if size > self._max_bytes:
                                raise ResponseTooLarge("LoLalytics response exceeds the configured size limit")
                            chunks.append(chunk)
                        result = b"".join(chunks)
                except (requests.Timeout, requests.ConnectionError, requests.RequestException):
                    retry_error = TransportError("LoLalytics request failed")
                    if attempt + 1 >= self._attempts:
                        raise retry_error from None
                    retry_wait = min(2**attempt, self._max_wait)
                except (HTTPStatusError, ResponseTooLarge):
                    raise
                except Exception:
                    raise TransportError("LoLalytics response could not be read") from None
                finally:
                    if response is not None:
                        try:
                            response.close()
                        except Exception:
                            pass
                if retry_error is not None:
                    last_error = retry_error
                    if retry_wait is not None and retry_wait > 0:
                        self._sleep(retry_wait)
                    continue
                return result
            raise last_error or TransportError("LoLalytics request failed")

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                self._session.close()

    def __enter__(self):
        if self._closed:
            raise TransportError("HTTP transport is closed")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
