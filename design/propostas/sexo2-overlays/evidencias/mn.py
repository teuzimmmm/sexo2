import socket, json, time, subprocess, base64, sys, os


class M:
    def __init__(s, port=2828):
        s.sock = None
        for _ in range(60):
            try:
                s.sock = socket.create_connection(("127.0.0.1", port), timeout=60)
                break
            except OSError:
                time.sleep(0.5)
        s.id = 0
        s._read()

    def _read(s):
        n = b""
        while True:
            c = s.sock.recv(1)
            if c == b":":
                break
            n += c
        n = int(n)
        d = b""
        while len(d) < n:
            d += s.sock.recv(n - len(d))
        return json.loads(d)

    def cmd(s, name, params=None):
        s.id += 1
        m = json.dumps([0, s.id, name, params or {}])
        s.sock.sendall(f"{len(m.encode())}:{m}".encode())
        while True:
            r = s._read()
            if r[0] == 1 and r[1] == s.id:
                if r[2]:
                    raise Exception(r[2])
                return r[3]

    def js(s, script, args=None):
        return s.cmd("WebDriver:ExecuteScript", {"script": script, "args": args or []}).get("value")

    def shot(s, path):
        v = s.cmd("WebDriver:TakeScreenshot", {"full": False})["value"]
        open(path, "wb").write(base64.b64decode(v))

    def keys(s, *ks):
        acts = []
        for k in ks:
            acts += [{"type": "keyDown", "value": k}, {"type": "keyUp", "value": k}]
        s.cmd("WebDriver:PerformActions", {"actions": [{"type": "key", "id": "kb", "actions": acts}]})


def start(prof="/private/tmp/ffm"):
    os.system(f"rm -rf {prof}; mkdir -p {prof}")
    p = subprocess.Popen(
        [
            "/Applications/Firefox.app/Contents/MacOS/firefox",
            "--headless",
            "--marionette",
            "--profile",
            prof,
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    m = M()
    m.cmd("WebDriver:NewSession", {"capabilities": {}})
    return p, m
