"""Minimal Chrome DevTools Protocol client (stdlib only) with request interception."""

import base64
import glob
import json
import os
import socket
import struct
import subprocess
import time
import urllib.request

CHROME = glob.glob(
    os.path.expanduser("~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/*.app/Contents/MacOS/*")
)


class WS:
    def __init__(self, url):
        host, path = url[5:].split("/", 1)
        h, p = host.split(":")
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.send(
            f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
        )
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(1)
        self.i = 0

    def send(self, msg):
        data = json.dumps(msg).encode()
        mask = os.urandom(4)
        n = len(data)
        head = b"\x81"
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.s.sendall(head + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(data)))

    def _read(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise EOFError
            buf += chunk
        return buf

    def recv(self):
        msg = b""
        while True:
            h = self._read(2)
            fin = h[0] & 128
            n = h[1] & 127
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            msg += self._read(n)
            if fin:
                break
        return json.loads(msg)


class Browser:
    """Full Chromium (the headless shell does not produce frames) on a given debugging port."""

    def __init__(self, profile, port=9334, routes=None):
        self.routes = routes or {}  # url prefix -> (status, content_type, bytes)
        self.proc = subprocess.Popen(
            [
                CHROME[0],
                "--headless=new",
                f"--remote-debugging-port={port}",
                "--no-first-run",
                f"--user-data-dir={profile}",
                "--allow-file-access-from-files",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        tabs = []
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                break
            except OSError:
                time.sleep(0.2)
        page = [t for t in tabs if t["type"] == "page"][0]
        self.ws = WS(page["webSocketDebuggerUrl"])
        for method in ("Page.enable", "Runtime.enable"):
            self.call(method)
        self.call("Fetch.enable", patterns=[{"urlPattern": "https://plugins/*"}])

    def _event(self, r):
        if r.get("method") != "Fetch.requestPaused":
            return
        p = r["params"]
        hit = next((v for k, v in self.routes.items() if p["request"]["url"].startswith(k)), None)
        if hit is None:
            self.call("Fetch.failRequest", requestId=p["requestId"], errorReason="Failed")
            return
        status, ctype, body = hit
        self.call(
            "Fetch.fulfillRequest",
            requestId=p["requestId"],
            responseCode=status,
            responseHeaders=[
                {"name": "Content-Type", "value": ctype},
                {"name": "Access-Control-Allow-Origin", "value": "*"},
            ],
            body=base64.b64encode(body).decode(),
        )

    def call(self, method, **params):
        self.ws.i += 1
        n = self.ws.i
        self.ws.send({"id": n, "method": method, "params": params})
        while True:
            r = self.ws.recv()
            if r.get("id") == n:
                if "error" in r:
                    raise RuntimeError(r["error"])
                return r["result"]
            self._event(r)

    def pump(self, seconds):
        """Serve intercepted requests for a while (real time)."""
        end = time.time() + seconds
        self.ws.s.settimeout(0.05)
        try:
            while time.time() < end:
                try:
                    self._event(self.ws.recv())
                except (TimeoutError, socket.timeout):
                    pass
        finally:
            self.ws.s.settimeout(None)

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")

    def size(self, w, h):
        self.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)

    def shot(self, path):
        with open(path, "wb") as f:
            f.write(base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"]))

    def close(self):
        self.proc.terminate()
