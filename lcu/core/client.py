#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
League Client API client
Main orchestrator for LCU API interactions
"""

from typing import Optional

from .lcu_connection import LCUConnection
from .lcu_api import LCUAPI
from ..features.lcu_properties import LCUProperties
from ..features.lcu_skin_selection import LCUSkinSelection
from ..features.lcu_game_mode import LCUGameMode
from ..features.lcu_swiftplay import LCUSwiftplay


class LCU:
    """League Client API client - main orchestrator"""
    
    def __init__(self, lockfile_path: Optional[str] = None):
        """Initialize LCU client
        
        Args:
            lockfile_path: Optional explicit path to lockfile
        """
        # Initialize connection
        self._connection = LCUConnection(lockfile_path)
        
        # Initialize API handler
        self._api = LCUAPI(self._connection)
        
        # Initialize property handlers
        self._properties = LCUProperties(self._api)
        self._skin_selection = LCUSkinSelection(self._api, self._connection)
        self._game_mode = LCUGameMode(self._properties)
        self._swiftplay = LCUSwiftplay(self._api, self._game_mode)
    
    # Connection properties (delegated to connection)
    @property
    def ok(self) -> bool:
        """Check if LCU connection is active"""
        return self._connection.ok
    
    @property
    def port(self) -> Optional[int]:
        """Get LCU port"""
        return self._connection.port
    
    @property
    def pw(self) -> Optional[str]:
        """Get LCU password"""
        return self._connection.pw
    
    @property
    def base(self) -> Optional[str]:
        """Get LCU base URL"""
        return self._connection.base
    
    @property
    def s(self):
        """Get requests session (for backward compatibility)"""
        return self._connection.session
    
    def refresh_if_needed(self, force: bool = False):
        """Refresh connection if needed"""
        self._connection.refresh_if_needed(force)

    def websocket_credentials(self):
        """Return a consistent port/password snapshot for the LCU WebSocket."""
        return self._connection.websocket_credentials()
    
    def get(self, path: str, timeout: float = 1.0, *, use_cache: bool = True):
        """Make GET request to LCU API"""
        return self._api.get(path, timeout, use_cache=use_cache)

    def accept_ready_check(self) -> bool:
        if not self.ok:return False
        if self._api.get('/lol-gameflow/v1/gameflow-phase',use_cache=False)!='ReadyCheck':return False
        ready=self._api.get('/lol-matchmaking/v1/ready-check',use_cache=False)
        if not isinstance(ready,dict)or ready.get('state')!='InProgress'or ready.get('playerResponse')not in ('None','Pending',None):return False
        response=self._connection.session.post(
            (self._connection.base or '')+'/lol-matchmaking/v1/ready-check/accept',timeout=2)
        try:return 200<=response.status_code<300
        finally:response.close()

    def loadout_request(self, method, path, payload=None):
        """Strict, bounded requests for explicit loadout actions; never retry writes."""
        import re
        allowed_reads = {'/lol-summoner/v1/current-summoner', '/lol-perks/v1/pages',
                         '/lol-game-data/assets/v1/perkstyles.json',
                         '/lol-game-data/assets/v1/cherry-augments.json',
                         '/lol-game-data/assets/v1/perks.json', '/lol-game-data/assets/v1/items.json'}
        item_sets = re.fullmatch(r'/lol-item-sets/v1/item-sets/[1-9][0-9]*/sets', path)
        permitted = (method == 'GET' and (path in allowed_reads or item_sets)
                     or method == 'POST' and path == '/lol-perks/v1/pages'
                     or method == 'PUT' and (item_sets or re.fullmatch(r'/lol-perks/v1/pages/[1-9][0-9]*', path)))
        if not permitted:
            raise ValueError('Operação de páginas não permitida.')
        return self._build_request(method, path, payload, timeout=(2, 5))

    def draft_request(self, path):
        """Fresh, bounded reads for builds, independent of the legacy GET cache."""
        if path not in {'/lol-lobby/v2/lobby', '/lol-gameflow/v1/gameflow-phase', '/lol-gameflow/v1/session',
                        '/lol-champ-select/v1/session',
                        '/lol-game-data/assets/v1/champion-summary.json'}:
            raise ValueError('Leitura de seleção não permitida.')
        return self._build_request('GET', path, None, timeout=(1, 2))

    def _build_request(self, method, path, payload, *, timeout):
        import json
        import re
        # Capture the connection once: concurrent reconnects must not combine a
        # session from one local client with the endpoint of another.
        connection = self._connection
        with connection._lock:
            session, base, connected = connection.session, connection.base, connection.ok
        if not connected or not re.fullmatch(r'https://127\.0\.0\.1:[0-9]{1,5}', base or ''):
            raise ValueError('O cliente LoL não está conectado localmente.')
        try:
            with session.request(method, base + path, json=payload, timeout=timeout,
                                stream=True, allow_redirects=False) as response:
                if not 200 <= response.status_code < 300:
                    raise ValueError(f'O cliente recusou a operação (HTTP {response.status_code}).')
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > 4 * 1024 * 1024:
                        raise ValueError('Resposta de páginas excedeu o limite permitido.')
                def invalid_constant(_):
                    raise ValueError('Resposta de páginas contém número inválido.')
                result = json.loads(body, parse_constant=invalid_constant) if body else None
            self._api.invalidate(path)
            return result
        except ValueError:
            raise
        except Exception:
            # Never expose credentials, account IDs, URLs or response bodies.
            raise ValueError('Falha de comunicação com as páginas do cliente. Confira o resultado antes de repetir.') from None
    
    def reconnect_game(self) -> bool:
        """Ask the still-running client to reopen its current game."""
        if not self.ok or self.phase not in ('Reconnect', 'InProgress', 'GameStart'):
            return False
        response = self._connection.session.post(
            (self._connection.base or '') + '/lol-gameflow/v1/reconnect', timeout=2)
        try:
            return 200 <= response.status_code < 300
        finally:
            response.close()

    # Properties (delegated to properties handler)
    @property
    def phase(self) -> Optional[str]:
        """Get current gameflow phase"""
        return self._properties.phase
    
    @property
    def session(self) -> Optional[dict]:
        """Get current session"""
        return self._properties.session
    
    @property
    def hovered_champion_id(self) -> Optional[int]:
        """Get hovered champion ID"""
        return self._properties.hovered_champion_id
    
    @property
    def my_selection(self) -> Optional[dict]:
        """Get my selection"""
        return self._properties.my_selection
    
    @property
    def unlocked_skins(self) -> Optional[dict]:
        """Get unlocked skins"""
        return self._properties.unlocked_skins
    
    def owned_skins(self) -> Optional[list[int]]:
        """Get owned skins (returns list of skin IDs)"""
        return self._properties.owned_skins()
    
    @property
    def current_summoner(self) -> Optional[dict]:
        """Get current summoner info"""
        return self._properties.current_summoner
    
    @property
    def region_locale(self) -> Optional[dict]:
        """Get client region and locale information"""
        return self._properties.region_locale
    
    @property
    def client_language(self) -> Optional[str]:
        """Get client language from LCU API"""
        return self._properties.client_language
    
    # Skin selection methods (delegated to skin selection handler)
    def set_selected_skin(self, action_id: int, skin_id: int) -> bool:
        """Set the selected skin for a champion select action"""
        return self._skin_selection.set_selected_skin(action_id, skin_id)
    
    def set_my_selection_skin(self, skin_id: int) -> bool:
        """Set the selected skin using my-selection endpoint"""
        return self._skin_selection.set_my_selection_skin(skin_id)
    
    # Game mode properties (delegated to game mode handler)
    @property
    def game_session(self) -> Optional[dict]:
        """Get current game session with mode and map info"""
        return self._properties.game_session
    
    @property
    def game_mode(self) -> Optional[str]:
        """Get current game mode (e.g., 'ARAM', 'CLASSIC')"""
        return self._game_mode.game_mode
    
    @property
    def map_id(self) -> Optional[int]:
        """Get current map ID (12 = Howling Abyss, 11 = Summoner's Rift)"""
        return self._game_mode.map_id
    
    @property
    def is_aram(self) -> bool:
        """Check if currently in ARAM (Howling Abyss)"""
        return self._game_mode.is_aram
    
    @property
    def is_sr(self) -> bool:
        """Check if currently in Summoner's Rift"""
        return self._game_mode.is_sr
    
    @property
    def is_swiftplay(self) -> bool:
        """Check if currently in Swiftplay mode"""
        return self._game_mode.is_swiftplay
    
    # Swiftplay methods (delegated to swiftplay handler)
    def get_swiftplay_lobby_data(self) -> Optional[dict]:
        """Get Swiftplay lobby data with champion selection"""
        return self._swiftplay.get_swiftplay_lobby_data()
    
    def get_swiftplay_champion_selection(self) -> Optional[dict]:
        """Get champion selection data from Swiftplay lobby (single champion)"""
        return self._swiftplay.get_swiftplay_champion_selection()
    
    def get_swiftplay_dual_champion_selection(self) -> Optional[dict]:
        """Get both champion selections from Swiftplay lobby"""
        return self._swiftplay.get_swiftplay_dual_champion_selection()

    def force_swiftplay_base_skins(self, skin_tracking: dict, owned_skin_ids: set = None) -> bool:
        """Force base skins on swiftplay player slots for tracked champions"""
        return self._swiftplay.force_base_skin_slots(skin_tracking, owned_skin_ids)
    
    # Champion name lookup (delegated to properties handler)
    def get_champion_name_by_id(self, champion_id: int) -> Optional[str]:
        """Get champion name by champion ID"""
        return self._properties.get_champion_name_by_id(champion_id)
