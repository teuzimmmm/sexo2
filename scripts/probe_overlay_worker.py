"""Opt-in Windows child-process entry/pipe probe; never opens a game."""
import argparse
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sexo2.overlay.display import Frame
from sexo2.overlay.model import View,Card
from sexo2.overlay.worker_wire import encode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',type=Path,required=True)
    args=parser.parse_args()
    child=subprocess.Popen([str(args.worker.resolve()),'--overlay-worker'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    lines=queue.Queue()
    def read():
        try:
            for raw in child.stdout:lines.put(raw)
        finally:lines.put(None)
    thread=threading.Thread(target=read,daemon=True);thread.start()
    try:
        frame=Frame(True,View('a'*24,(Card('Teste isolado',('Sem LoL; sem dados pessoais.',)),)))
        child.stdin.write(encode(frame,1,1));child.stdin.flush()
        deadline=time.monotonic()+15
        while True:
            raw=lines.get(timeout=max(.01,deadline-time.monotonic()))
            if raw is None:raise RuntimeError('Display child exited before readiness')
            status=json.loads(raw)
            assert status.get('event')=='status' and status.get('engine')=='isolated-layered-cpu','Invalid display status schema'
            if status.get('code')=='not-started':continue
            assert status.get('code') in {'inactive','not-game-foreground','waiting-tab','visible'},'Display window initialization failed'
            break
        child.stdin.close();child.stdin=None
        child.wait(timeout=5)
        assert child.returncode==0,'Worker did not close cleanly on EOF'
        print(json.dumps({'workerEntry':True,'windowInitialized':True,'privatePipes':True,'eofExit':True,'leagueValidated':False}))
    except (queue.Empty,AssertionError,RuntimeError):
        if child.poll() is None:child.kill();child.wait(timeout=3)
        error=child.stderr.read(4096).decode('utf-8',errors='replace')
        # stderr from the display-only entry has no source paths or data.
        safe=re.findall(r'display-worker-error:[A-Za-z0-9_.:]+|ModuleNotFoundError: No module named [\'\"][A-Za-z0-9_.]+[\'\"]',error)
        print('Worker exit:',child.returncode,'status:',safe or 'No private status received')
        raise
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=3)
        for stream in (child.stdin,child.stdout,child.stderr):
            if stream:stream.close()

if __name__=='__main__':main()
