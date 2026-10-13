"""Outbound tunnel controller, independent of the GUI and Rose preferences."""
import asyncio
import queue
import logging
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path
from .friends_relay import FriendsRelay

class HostController:
    def __init__(self,binary=None):
        base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[2]))
        self.binary=Path(binary) if binary else base/'hosting-tools/cloudflared.exe'
        self.events=queue.Queue()
        self.thread=None;self.loop=None;self.stop_event=None;self.process=None
        self.link=None;self.started=False;self._cancel=threading.Event();self.last_logs=[];self.last_check_error=None

    def start(self):
        if self.thread and self.thread.is_alive():return
        self._cancel.clear();self.thread=threading.Thread(target=self._run,daemon=True,name='RoseFriendsHost');self.thread.start()

    def _run(self):
        try:asyncio.run(self._serve())
        except Exception as e:self.events.put(('error',str(e)))
        finally:self.started=False;self.link=None;self.events.put(('stopped',None))

    async def _serve(self):
        if not self.binary.is_file():raise RuntimeError('Falta cloudflared.exe na pasta de ferramentas do módulo Sala.')
        self.loop=asyncio.get_running_loop();self.stop_event=asyncio.Event()
        token=secrets.token_urlsafe(32)
        relay=FriendsRelay(token)
        process=None
        try:
            port=await relay.start()
            flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
            # TCP transport avoids requiring UDP egress. No Windows service or firewall rule.
            process=subprocess.Popen([str(self.binary),'tunnel','--no-autoupdate','--protocol','http2','--url',f'http://127.0.0.1:{port}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=flags)
            self.process=process
            discovered=queue.Queue()
            logs=[]
            self.last_logs=logs
            def read():
                for line in process.stdout:
                    logs.append(line.rstrip());del logs[:-30]
                    match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
                    if match:discovered.put(match.group(0))
            reader=threading.Thread(target=read,daemon=True);reader.start()
            self.events.put(('status','Abrindo conexão segura...'))
            deadline=time.monotonic()+90;url=None
            while not url:
                if self._cancel.is_set():return
                if process.poll() is not None:raise RuntimeError('O túnel encerrou antes de abrir a sala. Verifique a internet e tente novamente.')
                if time.monotonic()>deadline:raise RuntimeError('Não foi possível abrir o túnel em 90 segundos. Verifique a internet e tente novamente.')
                try:url=discovered.get_nowait()
                except queue.Empty:await asyncio.sleep(.2)
            # Wait until the public WebSocket really works; a printed URL isn't sufficient.
            from ..network.tunnel_connection import secure_connection
            import ssl,certifi
            from urllib.parse import urlencode
            check_url=url.replace('https://','wss://')+'/room?'+urlencode({'key':'rose-host-readiness','access':token,'v':'1.4.7'})
            transport_logger = logging.getLogger("rose.tunnel.check")
            transport_logger.setLevel(logging.WARNING)
            ready=False
            for attempt in range(35):
                if self._cancel.is_set():return
                try:
                    async with secure_connection(check_url,ssl=ssl.create_default_context(cafile=certifi.where()),open_timeout=5,close_timeout=2,proxy=None,logger=transport_logger) as ws:
                        await ws.send('ping')
                        for _ in range(3):
                            response=await asyncio.wait_for(ws.recv(),5)
                            if response=='pong':ready=True;break
                    if ready:break
                except Exception as error:
                    self.last_check_error = str(getattr(getattr(error,"response",None),"status_code",None) or type(error).__name__) 
                await asyncio.sleep(1)
            if not ready:raise RuntimeError('O túnel abriu, mas a sala ainda não respondeu. Tente hospedar novamente.')
            self.link=url+'/#rose='+token;self.started=True
            self.events.put(('ready',self.link))
            while not self._cancel.is_set() and not self.stop_event.is_set():
                if process.poll()is not None:raise RuntimeError('A conexão da sala caiu. Clique em Hospedar para criar outro endereço.')
                await asyncio.sleep(.2)
        finally:
            if process and process.poll()is None:
                process.terminate()
                try:await asyncio.to_thread(process.wait,5)
                except subprocess.TimeoutExpired:process.kill();await asyncio.to_thread(process.wait,5)
            if process and process.stdout:process.stdout.close()
            self.process=None
            await relay.close()
            self.loop=None;self.stop_event=None

    def stop(self,wait=False):
        self._cancel.set()
        process=self.process
        if process and process.poll()is None:
            try:process.terminate()
            except OSError:pass
        if self.loop and self.stop_event:
            try:self.loop.call_soon_threadsafe(self.stop_event.set)
            except RuntimeError:pass
        if wait and self.thread:self.thread.join(timeout=12)
