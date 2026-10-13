"""In-process hosting. UI reads sanitized status; secrets never enter diagnostics."""
import atexit
import asyncio
import queue
from pathlib import Path
import sys
from party.hosting.controller import HostController
from party.network.private_server_config import save_server_link

class RoomService:
    def __init__(self, state, host=None):
        self.state = state
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
        self.host = host or HostController(base/'hosting-tools/cloudflared.exe')
        self.status = 'idle'; self.message = ''; self.link = None
        atexit.register(self.shutdown)
        from main.core.state import get_app_state
        get_app_state().room_service=self

    def shutdown(self):
        self.host.stop(wait=True)

    def reconnect(self):
        party = getattr(self.state, 'party_manager', None)
        loop = getattr(self.state, 'friends_event_loop', None)
        if party and loop and loop.is_running():
            async def connect():
                try:
                    if party.enabled: await party.force_reconnect()
                    else: await party.enable()
                except Exception:
                    self.message = 'A conexão falhou. Tente novamente ou confira o endereço.'
            asyncio.run_coroutine_threadsafe(connect(), loop)

    def poll(self):
        while True:
            try: event, value = self.host.events.get_nowait()
            except queue.Empty: break
            if event == 'ready':
                try:
                    save_server_link(value)
                    self.link = value; self.status = 'hosting'; self.message = 'Sala disponível.'
                    self.reconnect()
                except Exception:
                    self.host.stop(); self.status = 'error'; self.message = 'Não foi possível salvar o endereço. Suas configurações anteriores foram preservadas.'
            elif event == 'error':
                self.status = 'error'; self.link = None
                self.message = 'A sala não pôde ser aberta ou a conexão caiu. Tente criar novamente.'
            elif event == 'stopped':
                self.link = None
                if self.status != 'error': self.status = 'idle'
            elif event == 'status': self.message = str(value)
        party = getattr(self.state, 'party_manager', None)
        p = party.get_state_dict() if party else {}
        return {'hosting': self.status == 'hosting', 'status': self.status,
                'message': self.message, 'link': self.link,
                'connected': bool(p.get('relay_connected')),
                'connection': p.get('connection', 'offline')}

    def handle(self, action, payload):
        self.poll()
        if action == 'room-host':
            if self.host.thread and self.host.thread.is_alive():
                raise ValueError('A sala já está ativa ou iniciando. Encerre antes de criar outra.')
            self.link = None; self.status = 'starting'; self.message = 'Abrindo conexão segura…'
            self.host.start()
        elif action == 'room-stop':
            self.host.stop(); self.link = None; self.status = 'stopping'
            self.message = 'Encerrando hospedagem…'
        elif action == 'room-join':
            link = payload.get('link')
            if not isinstance(link, str) or not link.strip(): raise ValueError('Cole o endereço completo da sala.')
            if self.host.thread and self.host.thread.is_alive(): raise ValueError('Encerre sua hospedagem antes de entrar em outra sala.')
            save_server_link(link); self.message = 'Reconectando ao endereço informado…'; self.reconnect()
        elif action == 'room-reconnect': self.message = 'Reconectando…'; self.reconnect()
        elif action == 'room-leave':
            party = getattr(self.state, 'party_manager', None)
            loop = getattr(self.state, 'friends_event_loop', None)
            self.state.party_user_disconnected = True
            if party and loop and loop.is_running(): asyncio.run_coroutine_threadsafe(party.disable(), loop)
            self.message = 'Conexão encerrada. Suas escolhas locais foram mantidas.'
        else: raise ValueError('Operação de sala desconhecida.')
        if action in ('room-join', 'room-host', 'room-reconnect'): self.state.party_user_disconnected = False
