"""Mayhem-specific pooled champion popularity, outside the window/OCR threads."""
import threading
import time
from sexo2.services.work_queue import SerialWorker
from .model import View
from .offers import offer_view


class MayhemFeed:
    def __init__(self, *, client_factory=None, clock=time.monotonic):
        self._factory=client_factory or self._default_client
        self._client=None;self._clock=clock
        self._lock=threading.RLock();self._worker=SerialWorker('SEXO2-Overlay-Mayhem',capacity=1)
        self._desired=self._attempted=self._complete=None
        self._busy=self._closed=False
        self._metrics={};self._source=None
        self._retry_at=float('-inf');self._attempts=0

    @staticmethod
    def _default_client():
        from sexo2.sources.mayhem import MayhemClient
        from utils.core.paths import get_user_data_dir
        return MayhemClient(cache_dir=get_user_data_dir()/'mayhem-cache')

    def ensure(self,key,cid):
        signature=(key,cid)
        with self._lock:
            if self._closed:return
            if signature!=self._desired:
                self._desired=signature;self._attempts=0;self._retry_at=float('-inf')
            if self._busy or self._complete==signature or self._attempts>=2 or self._clock()<self._retry_at:return
            self._busy=True;self._attempts+=1
        def work():
            try:
                if self._client is None:self._client=self._factory()
                pools=self._client.pools(cid)
                source=f'aramkit · Mayhem · {pools.patch} · {pools.data_date}'+(' · cache' if pools.cache_hit else '')
                with self._lock:
                    if not self._closed and self._desired==signature:
                        self._metrics,self._source,self._complete=pools.metrics,source,signature
            except Exception as error:
                # Public source transport bounds retries; only one later observer attempt.
                delay=getattr(error,'retry_after',30)
                if type(delay) not in (int,float) or delay!=delay:delay=30
                with self._lock:self._retry_at=self._clock()+max(30,delay)
            finally:
                with self._lock:
                    self._busy=False;closed=self._closed
                if closed and self._client is not None:self._client.close()
        if not self._worker.submit(work,lambda error:None):
            with self._lock:self._busy=False

    def offered_view(self,key,cid,offer,*,positioned=False):
        with self._lock:
            if offer.context!=(key,cid,'mayhem') or self._desired!=(key,cid):return View(key,())
            ready=self._complete==(key,cid)
            metrics=self._metrics if ready else {}
            source=self._source if ready else 'Mayhem · estatísticas indisponíveis.'
        return offer_view(key,offer,metrics,mode='mayhem',source=source,positioned=positioned)

    def clear(self):
        with self._lock:
            self._desired=self._complete=None;self._metrics={};self._source=None

    def close(self):
        with self._lock:self._closed=True;self.clear();busy=self._busy
        self._worker.close(timeout=.1)
        if not busy and self._client is not None:self._client.close()
