"""Lazy, supervised display child. No GPU libraries loaded in the application."""
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import json
import queue
from .worker_wire import encode


class IsolatedOverlay:
    def __init__(self,frame,*,command=None,popen=None,clock=time.monotonic):
        self.frame=frame;self.clock=clock;self.popen=popen or subprocess.Popen
        self.command=command or ([sys.executable,'--overlay-worker'] if getattr(sys,'frozen',False)
            else [sys.executable,str(Path(__file__).resolve().parents[2]/'main.py'),'--overlay-worker'])
        self._stop=threading.Event();self._thread=None;self._child=None;self._writer=None
        self._write_done=threading.Event();self._write_done.set();self._write_at=0
        self._attempts=0;self._key=None;self._context=self._sequence=0;self._action=None
        self._next=0;self._status={'code':'waiting-game','engine':'isolated-layered-cpu','windowShown':False}

    def diagnostic(self):
        messages={'waiting-game':'Aguardando a partida começar.',
                  'waiting-tab':'Segure TAB para comparar o valor dos itens.',
                  'not-game-foreground':'O jogo precisa estar em primeiro plano.',
                  'visible':'A janela CPU foi desenhada; confira a exibição sobre o jogo.',
                  'worker-failed':'O auxiliar do overlay falhou e foi isolado do aplicativo.',
                  'window-error':'O Windows recusou criar ou desenhar a janela.',
                  'show-failed':'O Windows recusou exibir a janela.',
                  'process-unavailable':'Não foi possível identificar a janela do jogo.',
                  'inactive':'Aguardando dados atuais da partida.'}
        return dict(self._status,attempts=self._attempts,message=messages.get(self._status['code'],'Iniciando o auxiliar do overlay.'))
    def set_opponent_action(self,action):self._action=action
    def start(self):
        if self._thread is None:
            self._thread=threading.Thread(target=self._run,name='SEXO2-display-supervisor',daemon=True);self._thread.start()

    def _events(self,child):
        try:
            while not self._stop.is_set() and self._child is child:
                raw=child.stdout.readline(4097)
                if not raw or len(raw)>4096:break
                event=json.loads(raw)
                if not isinstance(event,dict):break
                if event.get('event')=='cycle-opponent' and self._action:self._action()
                elif event.get('event')=='status' and event.get('engine')=='isolated-layered-cpu':
                    allowed={'not-started','inactive','waiting-tab','not-game-foreground','visible','window-error','show-failed','process-unavailable'}
                    code=event.get('code')
                    if code not in allowed:continue
                    self._status={'code':code,'engine':'isolated-layered-cpu','windowShown':event.get('windowShown') is True}
        except (OSError,ValueError,AttributeError):pass

    def _end(self):
        child=self._child;self._child=None
        if child is None:return
        try:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=.3)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=.3)
        except (OSError,subprocess.TimeoutExpired):pass
        # A stalled pipe writer must unblock after process termination. Never
        # acquire its stream lock from the application's shutdown thread.
        if self._write_done.wait(.2):
            for stream in (child.stdin,child.stdout):
                try:stream.close()
                except (OSError,AttributeError):pass

    def _write_loop(self,child,pending):
        while not self._stop.is_set() and self._child is child:
            try:raw=pending.get(timeout=.2)
            except queue.Empty:continue
            self._send(child,raw)

    def _send(self,child,raw):
        try:
            remaining=memoryview(raw)
            while remaining:
                count=child.stdin.write(remaining)
                if not count:raise OSError('Closed pipe')
                remaining=remaining[count:]
            child.stdin.flush()
        except (OSError,ValueError):pass
        finally:self._write_done.set()

    def tick(self):
        frame=self.frame();now=self.clock()
        key=frame.view.key
        if frame.active and re.fullmatch('[a-f0-9]{24}',key or '') and key!=self._key:
            self._key=key;self._attempts=0;self._context+=1
        if self._child is not None and (self._child.poll() is not None or
                (not self._write_done.is_set() and now-self._write_at>1)):
            self._end();self._next=now+2
            self._status={'code':'worker-failed','engine':'isolated-layered-cpu','windowShown':False}
        if not frame.active:
            if self._child is not None and self._child.poll() is None:
                self._attempts=max(0,self._attempts-1)
            self._end()
            self._status={'code':'waiting-game','engine':'isolated-layered-cpu','windowShown':False}
            return
        if self._child is None:
            if self._attempts>=2 or now<self._next or not self._write_done.is_set():return
            self._attempts+=1;self._sequence=0
            try:
                child=self.popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                 bufsize=0,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self._child=child
                self._pending=queue.Queue(maxsize=1)
                self._writer=threading.Thread(target=self._write_loop,args=(child,self._pending),name='SEXO2-display-write',daemon=True)
                self._writer.start()
                threading.Thread(target=self._events,args=(child,),name='SEXO2-display-status',daemon=True).start()
            except OSError:
                self._next=now+2;self._status={'code':'worker-failed','engine':'isolated-layered-cpu','windowShown':False};return
        if self._write_done.is_set():
            self._sequence+=1;raw=encode(frame,self._sequence,self._context)
            self._write_done.clear();self._write_at=now
            self._pending.put_nowait(raw)

    def _run(self):
        try:
            while not self._stop.is_set():
                try:self.tick()
                except Exception:
                    self._end();self._status={'code':'worker-failed','engine':'isolated-layered-cpu','windowShown':False}
                self._stop.wait(.2)
        finally:self._end()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():self._thread.join(timeout=1)
        elif self._thread is None:self._end()
