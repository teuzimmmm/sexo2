"""Exercise only the own-process DX11 host. Does not launch or attach to League."""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sexo2.overlay.model import Card, View
from sexo2.overlay.runtime import Frame
from sexo2.overlay.wire import encode


def probe(host):
    if os.name != 'nt':
        raise RuntimeError('The DX11 host probe requires Windows.')
    path = Path(host).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != '.exe':
        raise RuntimeError('Expected the native host executable.')
    child = subprocess.Popen([str(path), '--seconds', '4'], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    messages = queue.Queue(maxsize=4)
    failed = threading.Event()

    def read():
        try:
            while True:
                line = child.stdout.readline(8193)
                if not line:
                    return
                if len(line) > 8192 or not line.endswith(b'\n'):
                    raise ValueError('Invalid host report')
                messages.put_nowait(json.loads(line))
        except (ValueError, queue.Full, OSError):
            failed.set()

    reader = threading.Thread(target=read, name='SEXO2-native-probe', daemon=True)
    reader.start()
    try:
        ready = messages.get(timeout=12)
        if ready != {'ready': True, 'leagueValidated': False}:
            raise RuntimeError('Native host did not confirm isolated startup.')
        # Synthetic data only; the game key is deliberately not serialized.
        frame = Frame(True, View('synthetic-context', (
            Card('Arena · teste de popularidade', ('Aprimoramento fictício', 'Escolha: 12.4% · 214 jogos')),
            Card('SR · teste de apresentação', ('Runa sugerida: exemplo', 'Sem estatísticas reais nesta prévia.')),
        )), True)
        child.stdin.write(encode(frame, 1, ttl_ms=800))
        child.stdin.flush()
        time.sleep(1.3)
        child.stdin.write(encode(Frame(), 2))
        child.stdin.write(b'{"v":2}\n')  # Invalid schema must hide and disconnect.
        child.stdin.flush()
        child.stdin.close()
        report = messages.get(timeout=8)
        child.wait(timeout=4)
        reader.join(timeout=1)
        if failed.is_set() or child.returncode != 0 or not messages.empty():
            raise RuntimeError('Native host execution failed.')
        if (report.get('protocol') != 1 or report.get('engine') != 'hudhook-dx11'
                or report.get('leagueValidated') is not False
                or report.get('injectionFeature') is not False):
            raise RuntimeError('Unexpected native host report.')
        stats = report.get('stats', {})
        if (stats.get('received') != 2 or stats.get('rejected') != 1
                or not all(type(stats.get(k)) is int and stats[k] > 0 for k in
                           ('drawCallbacks', 'visibleCallbacks', 'hiddenCallbacks', 'expiredCallbacks'))):
            raise RuntimeError('Native draw/expiry checks failed.')
        return report
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)
        for stream in (child.stdin, child.stdout):
            if stream and not stream.closed:
                stream.close()
        reader.join(timeout=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='Path to the compiled isolated host')
    parser.add_argument('--output', type=Path, help='Optional sanitized JSON report')
    args = parser.parse_args()
    try:
        report = probe(args.host)
    except (RuntimeError, OSError, ValueError, queue.Empty, subprocess.SubprocessError):
        print('Native host probe failed. No League validation was performed.', file=sys.stderr)
        return 1
    data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(data, encoding='utf-8')
    print(data, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
