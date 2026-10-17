"""Serialized local operations. Network callbacks only read a prepared metadata snapshot."""

import asyncio, copy, json, secrets, sys, threading, time, zipfile
from pathlib import Path
from config import get_config_option
from sexo2.version import RELEASE_VERSION
from utils.core.paths import get_user_data_dir, get_skins_dir, get_classic_skins_dir
from utils.core.historic import load_historic_map
from pengu.processing.swiftplay_pins import SwiftplayPanelService, get_pins, read_lobby
from injection.tools.patcher import check_ltk_patcher, read_game_build
from injection.mods.zip_resolver import ZipResolver
from injection.classic import is_classic_game_mode, to_classic_champion_id, to_library_skin_name
from .preferences import Preferences
from .lottery import THEMES, eligible, draw
from .diagnostics import export_report
from .selection_guard import is_manual, release, mark_manual
from .room import RoomService
from .auto_accept import AutoAccept


class FriendsService:
    def __init__(self, state, lcu, injection_manager=None, data_dir=None):
        self.state = state
        self.lcu = lcu
        self.manager = injection_manager
        self.directory = Path(data_dir) if data_dir else get_user_data_dir()
        self.preferences = Preferences(self.directory / "friends-preferences.json")
        self.catalogs = SwiftplayPanelService(state, lcu)
        self.lock = threading.RLock()
        self.network_lock = threading.RLock()
        self._network = {}
        self._applied_profile = None
        self._applied_draw = None
        self._request = None
        self.optin = False
        self.draw_result = None
        self.last_export = None
        self.last_message = ""
        self._file_cache = {}
        self.room = RoomService(state)
        self._automatic_context = None
        self._crc_cache = {}
        self.library = []
        self.browse_id = None
        self.auto_accept = getattr(state, "auto_accept_controller", None) or AutoAccept(lcu)
        state.auto_accept_controller = self.auto_accept
        self.auto_accept.enabled = str(get_config_option("General", "autoaccept", "false")).lower() == "true"

    def party(self):
        return getattr(self.state, "party_manager", None)

    def phase(self):
        if not self.lcu or not self.lcu.ok:
            return None
        return self.lcu.get("/lol-gameflow/v1/gameflow-phase")

    def local_ids(self):
        ids = read_lobby(self.lcu)
        if ids:
            return ids
        if self.phase() != "ChampSelect":
            return []
        session = self.lcu.get("/lol-champ-select/v1/session")
        if not isinstance(session, dict):
            return []
        cell = session.get("localPlayerCellId")
        player = next((p for p in session.get("myTeam", []) if isinstance(p, dict) and p.get("cellId") == cell), {})
        cid = player.get("championId")
        return [cid] if type(cid) is int and cid > 0 else []

    def editable(self):
        phase = self.phase()
        ids = self.local_ids()
        return bool(
            ids
            and (
                phase == "Lobby"
                and read_lobby(self.lcu)
                or phase == "ChampSelect"
                and getattr(self.state, "own_champion_locked", False)
            )
            and not getattr(self.manager, "_injection_in_progress", False)
        )

    def context(self):
        return (self.phase(), tuple(self.local_ids()), getattr(self.state, "champ_select_generation", 0))

    def my_id(self):
        party = self.party()
        sid = party.party_state.my_summoner_id if party else None
        if sid:
            return sid
        data = self.lcu.get("/lol-summoner/v1/current-summoner") if self.lcu and self.lcu.ok else None
        return data.get("summonerId") if isinstance(data, dict) else None

    def lobby_ids(self):
        party = self.party()
        matcher = getattr(party, "_lobby_matcher", None)
        if matcher:
            return {int(x) for x in matcher.get_all_summoner_ids() if x}
        data = self.lcu.get("/lol-lobby/v2/lobby") if self.lcu and self.lcu.ok else None
        return (
            {
                p.get("summonerId")
                for p in data.get("members", [])
                if isinstance(p, dict) and type(p.get("summonerId")) is int
            }
            if isinstance(data, dict)
            else set()
        )

    def owned(self):
        return set(getattr(self.state, "owned_skin_ids", None) or [])

    def load_library(self):
        if not self.library:
            if not self.lcu or not self.lcu.ok:
                raise ValueError("Abra o cliente LoL para carregar o catálogo de campeões.")
            raw = self.lcu.get("/lol-game-data/assets/v1/champion-summary.json")
            if not isinstance(raw, list):
                raise ValueError("Não foi possível carregar os campeões. Tente novamente.")
            self.library = [
                {"championId": c["id"], "name": str(c.get("name") or c["id"]), "portrait": c.get("squarePortraitPath")}
                for c in raw
                if isinstance(c, dict) and type(c.get("id")) is int and c["id"] > 0
            ][:700]
            self.library.sort(key=lambda c: c["name"].casefold())
        return self.library

    def browsed_catalog(self):
        if self.browse_id is None:
            return None
        row = copy.deepcopy(self.catalogs.catalog(self.browse_id))
        for skin in row["skins"]:
            skin["favorite"] = skin["skinId"] in self.preferences.snapshot().get("favorites", {}).get(
                str(self.browse_id), []
            )
        return row

    def selected(self, cid):
        if read_lobby(self.lcu):
            pin = get_pins(self.state).snapshot().get(cid)
            if pin:
                return pin["skinId"]
            return self.state.swiftplay_skin_tracking.get(cid, cid * 1000)
        for active, name in [("historic_mode_active", "historic_skin_id"), ("random_mode_active", "random_skin_id")]:
            sid = getattr(self.state, name, None)
            if getattr(self.state, active, False) and type(sid) is int and sid // 1000 == cid:
                return sid
        for name in ["selected_chroma_id", "last_hovered_skin_id"]:
            sid = getattr(self.state, name, None)
            if type(sid) is int and sid // 1000 == cid:
                return sid
        return cid * 1000

    def archive(self, cid, sid, verify=True):
        if sid == cid * 1000:
            return True
        classic = is_classic_game_mode(getattr(self.state, "current_game_mode", None))
        key = (cid, sid, classic, verify)
        cached = self._file_cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        injector = getattr(self.manager, "injector", None)
        if classic:
            directory = Path(getattr(injector, "classic_dir", None) or get_classic_skins_dir())
            resolver = getattr(injector, "classic_resolver", None) or ZipResolver(directory)
            archive_cid = to_classic_champion_id(cid)
            name = to_library_skin_name(directory / str(archive_cid), f"skin_{sid}")
        else:
            resolver = getattr(injector, "zip_resolver", None) or ZipResolver(get_skins_dir())
            archive_cid = cid
            name = f"skin_{sid}"
        try:
            path = resolver.resolve_zip(name, champion_id=archive_cid)
            available = bool(path and Path(path).is_file() and zipfile.is_zipfile(path))
            if available and verify:
                stat = Path(path).stat()
                signature = (str(path), stat.st_size, stat.st_mtime_ns)
                if signature in self._crc_cache:
                    available = self._crc_cache[signature]
                else:
                    with zipfile.ZipFile(path) as archive:
                        available = bool(archive.infolist()) and archive.testzip() is None
                    if len(self._crc_cache) > 128:
                        self._crc_cache.clear()
                    self._crc_cache[signature] = available
        except Exception:
            available = False
        self._file_cache[key] = (time.monotonic() + 15, available)
        return available

    def available(self, cid, sid):
        return sid == cid * 1000 or sid in self.owned() or self.archive(cid, sid, verify=False)

    def picks(self):
        result = {}
        for cid in self.local_ids():
            sid = self.selected(cid)
            entry = next((s for s in self.catalogs.catalog(cid)["skins"] if s["skinId"] == sid), None)
            result[str(cid)] = {"skinId": sid, "name": entry["name"] if entry else str(sid)}
        return result

    def apply(self, picks, automatic=True):
        self._file_cache.clear()
        if automatic and is_manual(self.state):
            raise ValueError("Escolha manual preservada para este campeão.")
        if not self.editable():
            raise ValueError("Volte ao lobby de Swiftplay ou trave seu campeão na seleção para alterar as skins.")
        context = self.context()
        ids = list(context[1])
        changes = {}
        for cid in ids:
            pick = picks.get(str(cid)) or picks.get(cid)
            if pick is None:
                continue
            sid = pick.get("skinId")
            entry = next(
                (s for s in self.catalogs.catalog(cid)["skins"] if s["skinId"] == sid and type(sid) is int), None
            )
            if not entry:
                raise ValueError("A skin escolhida não está no catálogo atual deste campeão.")
            if sid != cid * 1000 and sid not in self.owned() and not self.archive(cid, sid, verify=True):
                raise ValueError("Arquivo da skin indisponível ou corrompido: " + entry["name"])
            changes[cid] = entry
        if not changes:
            raise ValueError("Este conjunto não tem uma escolha para seus campeões atuais.")
        if self.context() != context:
            raise ValueError("Os campeões mudaram durante a confirmação. Tente novamente.")
        if context[0] == "Lobby":
            current = get_pins(self.state).snapshot()
            selections = [
                {
                    "championId": cid,
                    "skinId": changes[cid]["skinId"] if cid in changes else current.get(cid, {}).get("skinId"),
                }
                for cid in ids
            ]
            self.catalogs.save({"championIds": ids, "selections": selections})
        else:
            cid = ids[0]
            entry = changes[cid]
            sid = entry["skinId"]
            if getattr(self.state, "locked_champ_id", None) != cid:
                raise ValueError("Seu campeão ainda não foi confirmado pelo Rose.")
            target = sid if sid in self.owned() else cid * 1000
            if not self.lcu.set_my_selection_skin(target):
                raise ValueError("O cliente não confirmou a escolha. Tente novamente.")
            if self.context() != context:
                raise ValueError("A seleção mudou durante a confirmação.")
            if automatic and is_manual(self.state):
                raise ValueError("Escolha manual preservada; a seleção automática foi cancelada.")
            self.state.historic_first_detection_done = True
            self.state.random_mode_active = False
            self.state.random_skin_id = None
            self.state.selected_chroma_id = None
            self.state.selected_custom_mod = None
            self.state.historic_mode_active = sid != cid * 1000
            self.state.historic_skin_id = sid if sid != cid * 1000 else None
            self.state.ui_skin_id = sid
            self.state.last_hovered_skin_id = sid
            self.state.last_hovered_skin_key = entry["name"]
            ui = getattr(self.state, "ui_skin_thread", None)
            if ui:
                ui._broadcast_historic_state()
                ui._broadcast_random_mode_state()
        return changes

    def readiness(self):
        ids = self.local_ids()
        phase = self.phase()
        checks = []

        def add(key, title, ok, detail, required=True, waiting=False):
            checks.append(
                {
                    "id": key,
                    "title": title,
                    "status": "waiting" if waiting else "ok" if ok else "error",
                    "detail": detail,
                    "required": required,
                }
            )

        if self.preferences.error:
            add("preferences", "Preferências", False, self.preferences.error)
        connected = bool(self.lcu and self.lcu.ok)
        add("client", "Cliente do LoL", connected, "Conectado" if connected else "Abra o cliente do LoL.")
        add(
            "champions",
            "Campeões e escolhas",
            bool(ids),
            "Escolhas identificadas" if ids else "Escolha os campeões no lobby ou na seleção.",
            waiting=connected and not ids,
        )
        if ids and phase == "ChampSelect":
            add(
                "locked",
                "Campeão confirmado",
                getattr(self.state, "own_champion_locked", False),
                "Trave seu campeão para confirmar o preparo.",
            )
        tools = getattr(getattr(self.manager, "injector", None), "tools_dir", None) or getattr(
            self.manager, "tools_dir", None
        )
        tools = (
            Path(tools)
            if tools
            else Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "injection/tools"
        )
        try:
            patcher = check_ltk_patcher(tools)
            game = getattr(self.manager, "game_dir", None) or get_config_option("General", "leaguepath", None)
            build = read_game_build(Path(game)) if game else None
            supported = (
                not patcher.missing and build is not None and not patcher.expired_for(Path(game) if game else None)
            )
            add(
                "patcher",
                "Aplicador de skins",
                supported,
                "Arquivos presentes e compatíveis com o jogo instalado."
                if supported
                else "Atualize os arquivos do aplicador; arquivos ausentes ou jogo fora do suporte.",
            )
        except Exception:
            add("patcher", "Aplicador de skins", False, "Não foi possível conferir o aplicador.")
        add(
            "tools",
            "Ferramentas do SEXO2",
            (tools / "mod-tools.exe").is_file() and (tools / "cslol-dll.dll").is_file(),
            "Ferramentas presentes"
            if (tools / "mod-tools.exe").is_file() and (tools / "cslol-dll.dll").is_file()
            else "Reinstale o pacote completo do SEXO2.",
        )
        custom = getattr(self.state, "selected_custom_mod", None)
        if isinstance(custom, dict) and custom.get("relative_path"):
            from party.discovery.custom_mods import get_mods_root

            root = get_mods_root().resolve()
            path = (root / str(custom["relative_path"])).resolve()
            inside = path.is_relative_to(root)
            exists = inside and path.exists()
            add(
                "custom-mod",
                "Mod escolhido",
                exists,
                "Arquivo presente" if exists else "O mod escolhido não foi encontrado neste computador.",
            )
        for cid in ids:
            sid = self.selected(cid)
            ok = self.available(cid, sid)
            try:
                label = self.catalogs.catalog(cid)["name"]
            except ValueError:
                label = str(cid)
            add(
                f"skin-{cid}",
                label + " · arquivo da skin",
                ok,
                "Disponível" if ok else f"A skin {sid} não foi encontrada neste computador.",
            )
        for member in self.members():
            if member.get("local") or not member.get("sameLobby"):
                continue
            for pick in member.get("choices", []):
                cid = pick.get("champion_id")
                sid = pick.get("skin_id")
                if type(cid) is not int or type(sid) is not int or cid in ids or sid == cid * 1000:
                    continue
                ok = self.archive(cid, sid)
                add(
                    f"peer-skin-{cid}",
                    "Arquivo da skin de um amigo",
                    ok,
                    "Disponível neste computador"
                    if ok
                    else f"A skin {sid} de um amigo não foi encontrada neste computador.",
                )
        local = bool(ids and all(c["status"] == "ok" for c in checks if c["required"]))
        party = self.party()
        party_state = party.get_state_dict() if party else {}
        relay = bool(party_state.get("relay_connected"))
        add(
            "server",
            "Servidor da sala",
            relay,
            "Conectado" if relay else "Abra Sala neste painel para hospedar, entrar ou reconectar.",
            required=False,
        )
        members = self.members()
        relevant = [m for m in members if not m.get("local") and m.get("sameLobby")]
        group = local and relay and all(m.get("ready") is True and m.get("connected") for m in relevant)
        return {
            "localReady": local,
            "groupReady": group,
            "title": "Tudo pronto para jogar"
            if group
            else "Seu SEXO2 está pronto; confira a sala"
            if local
            else "Ainda falta preparar o SEXO2",
            "checks": checks,
            "note": "Conferência antes da partida. Não confirma que a skin foi aplicada dentro do jogo.",
        }

    def members(self):
        party = self.party()
        if not party:
            return []
        allowed = self.lobby_ids()
        result = []
        myid = self.my_id()
        for relay in list(party._relays.values()):
            for member in relay.members:
                sid = member.get("summoner_id")
                skin = member.get("skin") or {}
                skin = skin if isinstance(skin, dict) else {}
                friends = skin.get("friends") or {}
                friends = friends if isinstance(friends, dict) else {}
                if sid == myid:
                    friends = {"version": 1, **self.network_state()}
                result.append(
                    {
                        "id": sid,
                        "name": str(member.get("summoner_name") or "Participante"),
                        "local": sid == myid,
                        "connected": bool(relay.connected),
                        "sameLobby": sid in allowed,
                        "skinReceived": bool(skin.get("champion_id") and skin.get("skin_id"))
                        or bool(friends.get("choices")),
                        "choices": friends.get("choices")
                        or (
                            [{"champion_id": skin.get("champion_id"), "skin_id": skin.get("skin_id")}]
                            if skin.get("skin_id")
                            else []
                        ),
                        "ready": friends.get("ready") if friends.get("version") == 1 else None,
                        "lotteryOptin": friends.get("lottery_optin", False),
                        "supportsTools": friends.get("version") == 1,
                    }
                )
        return result

    def network_state(self):
        with self.network_lock:
            return copy.deepcopy(self._network)

    def publish(self, ready):
        choices = [
            {
                "champion_id": int(cid),
                "skin_id": p["skinId"],
                "skin_name": p["name"],
                "champion_name": self.catalogs.catalog(int(cid))["name"],
            }
            for cid, p in self.picks().items()
        ]
        data = {"version": 1, "choices": choices, "ready": ready, "lottery_optin": self.optin}
        if self._request:
            data["lottery"] = self._request
        with self.network_lock:
            changed = data != self._network
            self._network = data
        party = self.party()
        if changed and party and party.enabled:
            loop = getattr(self.state, "friends_event_loop", None)
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(party._publish_state(), loop)

    def sync(self):
        self.auto_accept.tick(self.phase())
        data = self.preferences.snapshot()
        ids = self.local_ids()
        context = self.context()
        active = data["active_profile"]
        signature = (active, context, json.dumps(data["profiles"].get(active, {}), sort_keys=True))
        self.room.poll()
        if active and ids and self.editable() and not is_manual(self.state) and signature != self._applied_profile:
            applicable = {cid: pick for cid, pick in data["profiles"][active].items() if int(cid) in ids}
            if applicable:
                try:
                    self.apply(applicable)
                    self._applied_profile = signature
                except ValueError as e:
                    self.last_message = str(e)
        mode = data.get("automatic", "off")
        if (
            mode != "off"
            and ids
            and self.editable()
            and not self.preferences.error
            and not is_manual(self.state)
            and self._automatic_context != context
        ):
            try:
                selected = {}
                for cid in ids:
                    skins = eligible(
                        self.catalogs.catalog(cid)["skins"],
                        "Qualquer",
                        set(data["excluded"]),
                        lambda sid: self.available(cid, sid),
                    )
                    favorites = [
                        s
                        for s in self.catalogs.catalog(cid)["skins"]
                        if s["skinId"] in data.get("favorites", {}).get(str(cid), [])
                        and s["skinId"] not in data["excluded"]
                        and self.available(cid, s["skinId"])
                    ]
                    if mode == "favorite":
                        if not favorites:
                            raise ValueError("Este campeão não tem uma favorita disponível.")
                        selected[str(cid)] = favorites[0]
                    else:
                        selected[str(cid)] = draw(
                            favorites if mode == "favorites" and favorites else skins,
                            secrets.token_hex(16),
                            self.my_id() or 0,
                            cid,
                        )
                self.apply(selected)
                self._automatic_context = context
                self.last_message = "Skin automática escolhida."
            except ValueError as e:
                self.last_message = str(e)
                self._automatic_context = context
        if self.optin and self.editable() and not self.preferences.error and not is_manual(self.state):
            allowed = self.lobby_ids()
            myid = self.my_id()
            requests = []
            if self._request:
                requests.append((myid, self._request))
            party = self.party()
            if party:
                for relay in list(party._relays.values()):
                    if not relay.connected:
                        continue
                    for member in relay.members:
                        sid = member.get("summoner_id")
                        meta = (member.get("skin") or {}).get("friends") or {}
                        request = meta.get("lottery")
                        if sid in allowed and isinstance(request, dict):
                            requests.append((sid, request))
            valid = []
            for sid, r in requests:
                if not isinstance(r, dict) or r.get("theme") not in THEMES:
                    continue
                created = r.get("created")
                seed = r.get("seed")
                targets = r.get("targets")
                if type(created) is not int or not 0 <= time.time() * 1000 - created <= 120000:
                    continue
                if not isinstance(seed, str) or len(seed) != 32 or any(c not in "0123456789abcdef" for c in seed):
                    continue
                if not isinstance(targets, list) or myid not in targets:
                    continue
                valid.append(r)
            if valid:
                r = max(valid, key=lambda x: (x["created"], x["seed"]))
                key = (r["seed"], context)
                if key != self._applied_draw:
                    self._applied_draw = key
                    try:
                        selected = {}
                        for cid in ids:
                            candidates = eligible(
                                self.catalogs.catalog(cid)["skins"],
                                r["theme"],
                                set(data["excluded"]),
                                lambda sid: self.available(cid, sid),
                            )
                            selected[str(cid)] = draw(candidates, r["seed"], myid, cid)
                        self.apply(selected)
                        self.draw_result = {"theme": r["theme"], "choices": selected, "success": True}
                        self.last_message = "Sorteio aplicado aos seus campeões."
                    except ValueError as e:
                        self.draw_result = {"theme": r["theme"], "success": False, "error": str(e)}
                        self.last_message = str(e)
        readiness = self.readiness()
        self.publish(readiness["localReady"])
        return readiness

    def snapshot(self):
        readiness = self.sync()
        data = self.preferences.snapshot()
        champions = []
        for cid in self.local_ids():
            row = copy.deepcopy(self.catalogs.catalog(cid))
            row["selectedSkinId"] = self.selected(cid)
            for skin in row["skins"]:
                skin["excluded"] = skin["skinId"] in data["excluded"]
                skin["available"] = self.available(cid, skin["skinId"])
            champions.append(row)
        return {
            "type": "friends-state",
            "libraryChampions": self.library,
            "browseChampion": self.browsed_catalog(),
            "autoAccept": self.auto_accept.enabled,
            "autoAcceptMessage": self.auto_accept.message,
            "room": self.room.poll(),
            "automatic": data.get("automatic", "off"),
            "favorites": data.get("favorites", {}),
            "manualChoice": is_manual(self.state),
            "version": RELEASE_VERSION,
            "phase": self.phase(),
            "queueId": getattr(self.state, "current_queue_id", None),
            "editable": self.editable(),
            "readiness": readiness,
            "members": self.members(),
            "profiles": data["profiles"],
            "activeProfile": data["active_profile"],
            "excluded": data["excluded"],
            "preferenceError": self.preferences.error,
            "champions": champions,
            "themes": THEMES,
            "lotteryOptin": self.optin,
            "drawResult": self.draw_result,
            "message": self.last_message,
        }

    def handle(self, payload):
        with self.lock:
            action = payload.get("action", "snapshot")
            if (
                self.preferences.error
                and action
                not in (
                    "snapshot",
                    "check",
                    "export-diagnostic",
                    "open-diagnostic",
                    "restore-preferences",
                    "auto-accept",
                    "manual-choice",
                )
                and not action.startswith("room-")
            ):
                raise ValueError(self.preferences.error)
            if action.startswith("room-"):
                self.room.handle(action, payload)
            elif action == "manual-choice":
                mark_manual(self.state)
            elif action == "auto-accept":
                from config import set_config_option

                enabled = payload.get("enabled") is True
                set_config_option("General", "autoaccept", "true" if enabled else "false", strict=True)
                self.auto_accept.enabled = enabled
            elif action == "restore-preferences":
                self.preferences.restore_backup()
                self.last_message = "Backup restaurado; arquivo anterior preservado."
            elif action == "automatic":
                self.preferences.automatic(payload.get("mode"))
                self.optin = False
                self._request = None
                self._automatic_context = None
            elif action == "favorite":
                cid = payload.get("championId")
                sid = payload.get("skinId")
                if (
                    type(cid) is not int
                    or type(sid) is not int
                    or cid <= 0
                    or not any(s["skinId"] == sid for s in self.catalogs.catalog(cid)["skins"])
                ):
                    raise ValueError("Skin fora do catálogo do campeão")
                self.preferences.favorite(cid, sid, payload.get("enabled") is True)
                self.last_message = "Favoritas salvas."
            elif action == "library-list":
                self.load_library()
            elif action == "library-open":
                cid = payload.get("championId")
                if type(cid) is not int or not any(c["championId"] == cid for c in self.load_library()):
                    raise ValueError("Campeão fora do catálogo")
                self.catalogs.catalog(cid)
                self.browse_id = cid
            elif action == "use-skin":
                cid = payload.get("championId")
                sid = payload.get("skinId")
                if type(cid) is not int or type(sid) is not int or cid not in self.local_ids():
                    raise ValueError("Campeão inválido")
                self.apply({str(cid): {"skinId": sid}}, automatic=False)
                mark_manual(self.state)
                self.last_message = "Escolha manual preservada."
            elif action == "random-now":
                self._file_cache.clear()
                selected = {}
                for cid in self.local_ids():
                    skins = eligible(
                        self.catalogs.catalog(cid)["skins"],
                        "Qualquer",
                        set(self.preferences.snapshot()["excluded"]),
                        lambda sid: self.available(cid, sid),
                    )
                    selected[str(cid)] = draw(skins, secrets.token_hex(16), self.my_id() or 0, cid)
                self.apply(selected, automatic=False)
                mark_manual(self.state)
                self.last_message = "Skin sorteada para esta seleção."
            elif action == "save-profile":
                picks = get_pins(self.state).snapshot()
                picks = {str(cid): p for cid, p in picks.items()}
                for cid, sid in load_historic_map().items():
                    if type(sid) is int and sid // 1000 == int(cid):
                        picks.setdefault(str(cid), {"skinId": sid, "name": str(sid)})
                picks.update(self.picks())
                edits = payload.get("selections", {})
                if not isinstance(edits, dict):
                    raise ValueError("Escolhas inválidas")
                for cid, pick in edits.items():
                    if int(cid) not in self.local_ids():
                        raise ValueError("Edite apenas seus campeões atuais")
                    entry = next(
                        (s for s in self.catalogs.catalog(int(cid))["skins"] if s["skinId"] == pick.get("skinId")), None
                    )
                    if not entry:
                        raise ValueError("Skin fora do catálogo")
                    picks[str(cid)] = {"skinId": entry["skinId"], "name": entry["name"]}
                self.preferences.save_profile(payload.get("name"), picks)
                self.last_message = "Perfil salvo."
            elif action == "apply-profile":
                name = payload.get("name")
                data = self.preferences.snapshot()
                if name not in data["profiles"]:
                    raise ValueError("Perfil não encontrado")
                previous = data["active_profile"]
                release(self.state)
                self.preferences.automatic("off")
                self.preferences.activate(name)
                try:
                    if self.editable():
                        self.apply(data["profiles"][name], automatic=False)
                except Exception:
                    self.preferences.activate(previous)
                    raise
                self.optin = False
                self._request = None
                self._applied_profile = (
                    (name, self.context(), json.dumps(data["profiles"][name], sort_keys=True))
                    if self.editable()
                    else None
                )
                self.last_message = "Perfil ativo. Aplicado agora ou quando seu campeão estiver confirmado."
            elif action == "delete-profile":
                self.preferences.delete(payload.get("name"))
                self.last_message = "Perfil removido."
            elif action == "release":
                self.preferences.activate(None)
                self.optin = False
                self._request = None
                self.state.historic_mode_active = False
                self.state.historic_skin_id = None
                self.last_message = "Escolha automática liberada."
            elif action == "exclude":
                sid = payload.get("skinId")
                if type(sid) is not int or not any(
                    sid == s["skinId"] for cid in self.local_ids() for s in self.catalogs.catalog(cid)["skins"]
                ):
                    raise ValueError("Skin fora do catálogo atual")
                ids = set(self.preferences.snapshot()["excluded"])
                if payload.get("excluded") is True:
                    ids.add(sid)
                else:
                    ids.discard(sid)
                self.preferences.exclusions(sorted(ids))
                self.last_message = "Exclusão atualizada."
            elif action == "lottery-optin":
                enabled = payload.get("enabled") is True
                if enabled:
                    self.preferences.activate(None)
                self.optin = enabled
                if not self.optin:
                    self._request = None
                self.last_message = "Você entrou no sorteio do grupo." if self.optin else "Você saiu do sorteio."
            elif action in ("lottery-start", "lottery-local"):
                if not self.editable():
                    raise ValueError("Confirme seus campeões antes de sortear.")
                theme = payload.get("theme", "Qualquer")
                if theme not in THEMES:
                    raise ValueError("Temática desconhecida")
                party = self.party()
                myid = self.my_id()
                if not myid:
                    raise ValueError("Não foi possível confirmar seu jogador.")
                if action == "lottery-start" and not (party and party.get_state_dict().get("relay_connected")):
                    raise ValueError("Conecte a sala para sortear o grupo.")
                targets = sorted(self.lobby_ids() | {myid}) if action == "lottery-start" else [myid]
                self.preferences.activate(None)
                self.optin = True
                self._request = {
                    "seed": secrets.token_hex(16),
                    "created": int(time.time() * 1000),
                    "theme": theme,
                    "targets": targets[:10],
                }
                self.last_message = "Sorteio enviado. Só participantes que entraram no sorteio alteram suas escolhas."
            elif action == "export-diagnostic":
                snapshot = self.snapshot()
                snapshot.pop("room", None)
                from party.core.party_manager import get_party_room

                values = [get_config_option("Party", "relay_access", ""), get_party_room()[1]]
                self.last_export = export_report(
                    self.directory / "diagnosticos", snapshot, self.directory / "logs", values
                )
                self.last_message = "Relatório sanitizado salvo: " + self.last_export.name
            elif action == "check":
                self._file_cache.clear()
                self.last_message = "Verificação atualizada."
            elif action == "open-diagnostic":
                if not self.last_export:
                    raise ValueError("Gere um relatório primeiro.")
                import os

                os.startfile(str(self.last_export.parent))
            elif action != "snapshot":
                raise ValueError("Operação desconhecida")
            result = self.snapshot()
            if self.last_export:
                result["diagnostic"] = {"name": self.last_export.name, "path": str(self.last_export)}
            return result
