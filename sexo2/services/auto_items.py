"""Prepare item sets independently of any draft panel. No rune writes here."""
from copy import deepcopy
from dataclasses import dataclass
import math
import threading
import time

from lolalytics import Client, Query
from lolalytics.builds import build_page
from lolalytics.errors import CollectorError
from sexo2.overlay.arena import own_champion
from .draft import BuildError, DraftReader, game_key, lane, positive
from .loadouts import LoadoutImporter
from .session import play_mode
from .work_queue import SerialWorker


class ItemPlans:
    """Exact non-personal pages prepared by the user's SR queries, in memory only."""
    def __init__(self):
        self._lock=threading.Lock();self._data=None;self.version=0

    def prepare(self, context, pages):
        if context.get('mode')!='ranked' or not context.get('game_key') or not pages:return
        with self._lock:
            self._data=(context['game_key'],context['champion_id'],deepcopy(pages))
            self.version+=1

    def get(self, key, cid):
        with self._lock:
            if self._data and self._data[:2]==(key,cid):return deepcopy(self._data[2])
        return None

    def clear(self):
        with self._lock:
            if self._data is not None:self.version+=1
            self._data=None


@dataclass(frozen=True)
class Intent:
    mode: str
    groups: tuple
    key: str | None
    plan_version: int


class AutoItems:
    def __init__(self,lcu,*,plans=None,importer=None,client_factory=None,mayhem_factory=None,
                 clock=time.monotonic):
        from utils.core.paths import get_user_data_dir
        self.lcu=lcu;self.plans=plans if plans is not None else ItemPlans()
        self.reader=DraftReader(lcu)
        self.importer=importer or LoadoutImporter(lcu,get_user_data_dir()/'sexo2-loadouts.json')
        self._factory=client_factory or (lambda:Client(cache_dir=get_user_data_dir()/'lolalytics-cache'))
        self._mayhem_factory=mayhem_factory
        self._client=self._mayhem=None
        self._clock=clock;self._lock=threading.RLock()
        self._worker=SerialWorker('SEXO2-Auto-items',capacity=1)
        self._desired=self._complete=None
        self._busy=self._closed=False
        self._attempts=0;self._retry_at=float('-inf')
        self._status={'code':'waiting','message':'Itens: aguardando campeão.'}

    def _observe(self):
        phase=self.lcu.draft_request('/lol-gameflow/v1/gameflow-phase')
        if phase in ('Lobby','Matchmaking','ReadyCheck'):
            lobby=self.lcu.draft_request('/lol-lobby/v2/lobby')
            if not isinstance(lobby,dict):return None
            config=lobby.get('gameConfig') if isinstance(lobby.get('gameConfig'),dict) else {}
            qid=config.get('queueId',lobby.get('queueId'))
            if qid not in (480,490):return None
            own=lobby.get('localMember')
            slots=own.get('playerSlots') if isinstance(own,dict) else None
            if not isinstance(slots,list) or not 1<=len(slots)<=2:return None
            groups=[]
            for slot in slots:
                if not isinstance(slot,dict) or not positive(slot.get('championId')):continue
                pair=(slot['championId'],'all' if qid==480 else lane(slot.get('positionPreference')))
                if all(pair[0]!=p[0] for p in groups):groups.append(pair)
            if not groups:return None
            intent=Intent('swiftplay' if qid==480 else 'ranked',tuple(groups),None,self.plans.version)
        elif phase in ('ChampSelect','GameStart','InProgress','Reconnect'):
            game=self.lcu.draft_request('/lol-gameflow/v1/session')
            data=game.get('gameData') if isinstance(game,dict) else None
            mode=play_mode(data)
            if mode not in ('ranked','swiftplay','aram','mayhem'):return None
            if phase=='ChampSelect':
                draft=self.reader.read()
                cid,position=draft.champion_id,draft.lane
            else:
                cid=own_champion(self.lcu,game)
                position='all'
            if not positive(cid):return None
            intent=Intent(mode,((cid,position if mode=='ranked' else 'all'),),
                          game_key(game.get('gameId') or data.get('gameId')),self.plans.version)
        else:return None
        if self.lcu.draft_request('/lol-gameflow/v1/gameflow-phase')!=phase:
            raise BuildError('A fase mudou durante a preparação dos itens.')
        return intent

    def diagnostic(self):
        with self._lock:return dict(self._status)

    def _pages(self,intent,cid,position):
        if intent.mode=='ranked':
            prepared=self.plans.get(intent.key,cid)
            if prepared:return prepared
        champion=self.reader.champion(cid)
        if intent.mode=='mayhem':
            if self._mayhem is None:
                from sexo2.sources.mayhem import MayhemClient
                from utils.core.paths import get_user_data_dir
                self._mayhem=self._mayhem_factory() if self._mayhem_factory else MayhemClient(cache_dir=get_user_data_dir()/'mayhem-cache')
            return self._mayhem.builds(cid,champion['slug'],champion['name'])
        if self._client is None:self._client=self._factory()
        query=Query(champion['slug'],mode='swift' if intent.mode=='swiftplay' else intent.mode,
                    lane=position if intent.mode=='ranked' else 'all',
                    tier='all' if intent.mode=='aram' else 'emerald_plus')
        if intent.mode=='swiftplay':return self._client.collect_builds(query).pages
        from .settings import get_risk_level
        recommendation=self._client.recommend(query,risk_level=get_risk_level())
        common=next((r for r in recommendation.rune_candidates if r['selection']=='pick'),None)
        if recommendation.build_page is None or common is None:raise BuildError('A fonte não retornou itens completos.')
        filtered=Query(query.champion,mode=query.mode,patch=recommendation.resolved['patch'],
                       lane=recommendation.build_page.query['lane'],tier=query.tier,region=query.region,
                       keystone=common['keystone'])
        return [recommendation.build_page,build_page(self._client.collect(filtered),'pick',common['keystone'])]

    def tick(self):
        with self._lock:
            if self._closed:return
        try:intent=self._observe()
        except Exception:
            intent=None
            with self._lock:self._status={'code':'client-unavailable','message':'Itens: não foi possível confirmar a seleção pelo cliente.'}
        with self._lock:
            if self._closed:return
            if intent!=self._desired:
                self._desired=intent;self._complete=None;self._attempts=0;self._retry_at=float('-inf')
            if intent is None:return
            if self._busy or self._complete==intent or self._attempts>=3 or self._clock()<self._retry_at:return
            self._busy=True;self._attempts+=1
            self._status={'code':'preparing','message':'Preparando conjuntos de itens para o modo atual.'}

        def guard():
            with self._lock:
                if self._closed or self._desired!=intent:raise BuildError('A preparação de itens expirou.')
            if self._observe()!=intent:raise BuildError('Campeão, modo ou partida mudou; itens não aplicados.')
            return {'revision':str(intent)}  # Only non-personal intent fields.

        def work():
            writing=False
            try:
                groups=[(cid,self._pages(intent,cid,position)) for cid,position in intent.groups]
                guard();writing=True
                result=self.importer.apply_item_groups(groups,guard=guard)
                with self._lock:
                    if not self._closed and self._desired==intent:
                        self._complete=intent
                        self._status={'code':'imported','message':result['message']}
            except Exception as error:
                with self._lock:
                    if not self._closed and self._desired==intent:
                        delay=getattr(error,'retry_after',None)
                        if not isinstance(delay,(int,float)) or isinstance(delay,bool) or delay<0:delay=0
                        if math.isnan(delay):delay=math.inf
                        self._retry_at=self._clock()+max(delay,10*self._attempts)
                        if writing or not isinstance(error,CollectorError):self._attempts=3
                        self._status={'code':'unavailable','message':'Não foi possível confirmar os itens; conjuntos pessoais preservados.'}
            finally:
                with self._lock:
                    self._busy=False
                    closed=self._closed
                if closed:self._close_clients()
        if not self._worker.submit(work,lambda error:None):
            with self._lock:self._busy=False

    def _close_clients(self):
        for client in (self._client,self._mayhem):
            if client is not None:client.close()

    def close(self):
        with self._lock:self._closed=True;self._desired=None;busy=self._busy
        self._worker.close(timeout=.1)
        if not busy:self._close_clients()
