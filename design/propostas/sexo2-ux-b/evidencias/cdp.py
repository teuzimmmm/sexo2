"""Cliente CDP mínimo (somente stdlib) para testar index.html por file:// no Chromium headless.
Uso: importado por qa_b.py. Não instala nada."""

import base64, json, os, socket, struct, subprocess, time, urllib.request, tempfile, shutil

CHROME = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell"
)


class WS:
    def __init__(self, url):
        host, rest = url[5:].split("/", 1)
        h, p = host.split(":")
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(
            (
                "GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
                % (rest, host, key)
            ).encode()
        )
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(1)
        self.i = 0

    def send(self, obj):
        data = json.dumps(obj).encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        hdr += mask
        self.s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        b = b""
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c:
                raise EOFError
            b += c
        return b

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            op = b1 & 0x0F
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            if op == 8:
                raise EOFError
            msg += payload
            if b1 & 0x80:
                return json.loads(msg.decode())


class Page:
    def __init__(self, port=None):
        if port is None:
            _s = socket.socket()
            _s.bind(("127.0.0.1", 0))
            port = _s.getsockname()[1]
            _s.close()
        self.tmp = tempfile.mkdtemp()
        self.proc = subprocess.Popen(
            [
                CHROME,
                "--remote-debugging-port=%d" % port,
                "--remote-debugging-address=127.0.0.1",
                "--no-sandbox",
                "--hide-scrollbars",
                "--user-data-dir=" + self.tmp,
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=open(os.environ.get("CDP_LOG", os.devnull), "w"),
        )
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % port))
                ws = [t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"]
                break
            except Exception:
                time.sleep(0.25)
        self.ws = WS(ws)
        self.id = 0
        self.events = []
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")
        self.cmd("Log.enable")

    def cmd(self, method, **params):
        self.id += 1
        i = self.id
        self.ws.send({"id": i, "method": method, "params": params})
        while True:
            m = self.ws.recv()
            if m.get("id") == i:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})
            self.events.append(m)

    def size(self, w, h):
        self.cmd("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)

    def goto(self, url, wait=0.8):
        self.cmd("Page.navigate", url=url)
        time.sleep(wait)

    def js(self, expr):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:400])
        return r["result"].get("value")

    def key(self, key, shift=False, code=None, vk=0):
        mod = 8 if shift else 0
        kw = {"text": "\r", "unmodifiedText": "\r"} if key == "Enter" else {}
        self.cmd(
            "Input.dispatchKeyEvent",
            type="keyDown",
            key=key,
            code=code or key,
            windowsVirtualKeyCode=vk,
            modifiers=mod,
            **kw,
        )
        self.cmd(
            "Input.dispatchKeyEvent", type="keyUp", key=key, code=code or key, windowsVirtualKeyCode=vk, modifiers=mod
        )

    def tab(self, shift=False):
        self.key("Tab", shift=shift, vk=9)

    def esc(self):
        self.key("Escape", vk=27)

    def type(self, text):
        for ch in text:
            self.cmd("Input.dispatchKeyEvent", type="char", text=ch)

    def shot(self, path):
        d = self.cmd("Page.captureScreenshot", format="png")["data"]
        open(path, "wb").write(base64.b64decode(d))

    def errors(self):
        out = []
        for e in self.events:
            if e.get("method") == "Runtime.exceptionThrown":
                out.append(json.dumps(e["params"]["exceptionDetails"])[:300])
            if e.get("method") == "Runtime.consoleAPICalled" and e["params"]["type"] in ("error",):
                out.append("console.error " + json.dumps(e["params"]["args"])[:200])
            if e.get("method") == "Log.entryAdded" and e["params"]["entry"]["level"] == "error":
                out.append("log " + e["params"]["entry"]["text"] + " " + e["params"]["entry"].get("url", ""))
        return out

    def close(self):
        self.proc.terminate()
        shutil.rmtree(self.tmp, ignore_errors=True)
