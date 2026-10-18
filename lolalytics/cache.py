"""Private, bounded on-disk cache for validated response bytes."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import time


_MAX_ENTRY_BYTES = 4 * 1024 * 1024
_CACHE_NAME = re.compile(r"[0-9a-f]{64}\.json\Z")


def _finite(value, name, *, positive=False):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError(f"{name} must be finite and positive")
    return result


def _is_finite(value):
    try:
        return math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        return False


class FileCache:
    def __init__(self, directory, ttl=900, max_bytes=_MAX_ENTRY_BYTES, *, max_entries=32, clock=time.time):
        self.directory = Path(directory)
        self.ttl = _finite(ttl, "ttl")  # Expiration is decided by the caller.
        try:
            self.max_bytes = min(int(max_bytes), _MAX_ENTRY_BYTES)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("max_bytes must be a positive integer") from None
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        try:
            self.max_entries = int(max_entries)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("max_entries must be a positive integer") from None
        if self.max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")
        self.max_entries = min(32, self.max_entries)
        self._clock = clock
        self._lock = threading.RLock()
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            self.directory.chmod(0o700)
        except OSError:
            pass

    @staticmethod
    def _name(key):
        if not isinstance(key, str):
            key = str(key)
        return hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json"

    def _path(self, key):
        return self.directory / self._name(key)

    @property
    def _max_envelope_bytes(self):
        # Base64 is at most 4/3 of the payload; allowance covers JSON and timestamp.
        return 4 * ((self.max_bytes + 2) // 3) + 1024

    def get(self, key):
        path = self._path(key)
        with self._lock:
            try:
                if path.stat().st_size > self._max_envelope_bytes:
                    return None
                with path.open("rb") as stream:
                    raw = stream.read(self._max_envelope_bytes + 1)
                if len(raw) > self._max_envelope_bytes:
                    return None
                item = json.loads(raw)
                stored_at = item["stored_at"]
                if isinstance(stored_at, bool) or not isinstance(stored_at, (float, int)) or not _is_finite(stored_at):
                    return None
                value = base64.b64decode(item["value"], validate=True)
                if len(value) > self.max_bytes:
                    return None
                try:
                    os.utime(path, None)
                except (AttributeError, OSError):
                    pass
                return {"stored_at": stored_at, "value": value}
            except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
                return None

    def put(self, key, value):
        if not isinstance(value, bytes):
            raise TypeError("cache values must be bytes")
        if len(value) > self.max_bytes:
            raise ValueError("cache value exceeds the configured size limit")
        path = self._path(key)
        stored_at = self._clock()
        if isinstance(stored_at, bool) or not isinstance(stored_at, (int, float)) or not _is_finite(stored_at):
            raise ValueError("cache clock must return a finite timestamp")
        envelope = json.dumps(
            {"stored_at": stored_at, "value": base64.b64encode(value).decode("ascii")},
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        with self._lock:
            fd, temp_name = tempfile.mkstemp(prefix=".lolalytics-", dir=self.directory)
            try:
                try:
                    os.fchmod(fd, 0o600)
                except (AttributeError, OSError):
                    pass
                with os.fdopen(fd, "wb") as stream:
                    stream.write(envelope)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_name, path)
                try:
                    path.chmod(0o600)
                except OSError:
                    pass
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                raise
            self._trim()

    def _trim(self):
        files = []
        try:
            candidates = self.directory.iterdir()
        except OSError:
            return
        for path in candidates:
            if not _CACHE_NAME.fullmatch(path.name):
                continue
            try:
                stat = path.stat()
                if path.is_file():
                    files.append((stat.st_mtime, path))
            except OSError:
                continue
        files.sort(key=lambda item: (item[0], item[1].name))
        while len(files) > self.max_entries:
            _, victim = files.pop(0)
            try:
                victim.unlink()
            except OSError:
                pass
