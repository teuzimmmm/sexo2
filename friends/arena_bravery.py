"""One controlled reconnect for Arena's explicitly marked Bravery pick."""

import json, secrets, threading, time
from pathlib import Path
import requests
from utils.core.atomic_file import atomic_write
from utils.core.logging import get_logger
from utils.core.paths import get_user_data_dir
from friends.lottery import eligible, draw

log = get_logger()
ACTIVE = {"GameStart", "InProgress", "Reconnect"}


def bravery_selected(session, detail=None):
    if not isinstance(session, dict):
        return False
    cell = session.get("localPlayerCellId")
    if type(cell) is not int:
        return False
    own = next((p for p in session.get("myTeam", []) if isinstance(p, dict) and p.get("cellId") == cell), {})
    # Confirmed in the installed LoL frontend: BRAVERY_CHAMP.championId == -3.
    # -2 is the ordinary random button, -1/0 are not evidence of Bravery.
    return own.get("championId") == -3 and any(
        a.get("actorCellId") == cell
        and a.get("type") == "pick"
        and a.get("completed") is True
        and a.get("championId") == -3
        for group in session.get("actions", [])
        if isinstance(group, list)
        for a in group
        if isinstance(a, dict)
    )


class ArenaBravery:
    def __init__(self, lcu, state, manager, directory=None):
        self.lcu, self.state, self.manager = lcu, state, manager
        self.marker = Path(directory or get_user_data_dir()) / "arena-bravery-match.json"
        self.armed = False
        self.running = False
        self.started = None
        self.last_poll = 0
        self.seen = set()

    def tick(self, phase):
        if not self.manager or self.running or time.monotonic() - self.last_poll < 1:
            return
        self.last_poll = time.monotonic()
        if phase == "ChampSelect":
            self.started = None
            if str(getattr(self.state, "current_game_mode", "")).upper() != "CHERRY":
                self.armed = False
                return
            session = self.lcu.get("/lol-champ-select/v1/session")
            if not isinstance(session, dict):
                return
            self.observe(session)
            return
        if phase not in ACTIVE:
            if phase is not None:
                self.armed = False
                self.started = None
            return
        if not self.armed:
            return
        self.started = self.started or time.monotonic()
        if time.monotonic() - self.started > 75:
            self.armed = False
            return
        self.running = True
        threading.Thread(target=self._attempt, daemon=True, name="SEXO2-Arena-Bravura").start()

    def observe(self, session):
        if self.running:
            return
        self.armed = str(getattr(self.state, "current_game_mode", "")).upper() == "CHERRY" and bravery_selected(session)

    def _attempt(self):
        try:
            self._prepare()
        except requests.RequestException:
            pass  # The game API is normally unavailable during the loading screen.
        except Exception:
            log.exception("[Arena] Bravura preparation failed; no repeated restart")
            self.armed = False
        finally:
            self.running = False

    def _prepare(self):
        if self.state.stop or self.manager.recovery.cancelled.is_set():
            self.armed = False
            return
        session = self.lcu.get("/lol-gameflow/v1/session")
        data = session.get("gameData", {}) if isinstance(session, dict) else {}
        if data.get("queue", {}).get("gameMode") != "CHERRY":
            return
        game_id = data.get("gameId", session.get("gameId"))
        if type(game_id) is not int or game_id <= 0:
            return
        key = str(game_id)
        if key in self.seen:
            self.armed = False
            return
        try:
            if json.loads(self.marker.read_text(encoding="utf-8")).get("gameId") == key:
                self.armed = False
                return
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            self.armed = False  # A damaged guard must never authorize a repeated restart.
            return
        me = self.lcu.get("/lol-summoner/v1/current-summoner")
        if not isinstance(me, dict) or not me.get("puuid"):
            return
        players = data.get("teamOne", []) + data.get("teamTwo", [])
        own = next((p for p in players if p.get("puuid") == me["puuid"]), {})
        cid = own.get("championId")
        from friends.service import FriendsService

        service = getattr(self.state, "friends_service", None) or FriendsService(self.state, self.lcu, self.manager)
        roster = service.load_library()
        if type(cid) is not int or not any(c["championId"] == cid for c in roster):
            # Only the active player's row is accepted from Riot's local game API.
            with requests.Session() as http:
                http.trust_env = False
                with http.get(
                    "https://127.0.0.1:2999/liveclientdata/allgamedata", verify=False, timeout=1.5
                ) as response:
                    response.raise_for_status()
                    live = response.json()
            identity = live.get("activePlayer", {}).get("riotId")
            if not identity:
                return
            rows = [p for p in live.get("allPlayers", []) if p.get("riotId") == identity]
            if len(rows) != 1:
                return
            raw = str(rows[0].get("rawChampionName", "")).removeprefix("game_character_displayname_")
            summary = self.lcu.get("/lol-game-data/assets/v1/champion-summary.json")
            matches = [
                c["id"] for c in summary or [] if c.get("alias", "").casefold() == raw.casefold() and c.get("id", 0) > 0
            ]
            if len(matches) != 1:
                return
            cid = matches[0]
        prefs = service.preferences.snapshot()
        if service.preferences.error:
            self.armed = False
            return
        candidates = eligible(
            service.catalogs.catalog(cid)["skins"],
            "Qualquer",
            prefs["excluded"],
            lambda sid: service.archive(cid, sid, verify=False),
        )
        favorites = [s for s in candidates if s["skinId"] in prefs["favorites"].get(str(cid), [])]
        if prefs.get("automatic") in ("favorite", "favorites") and favorites:
            candidates = favorites
        if not candidates:
            self.armed = False
            return
        pick = draw(candidates, secrets.token_hex(16), 0, cid)
        if not service.archive(cid, pick["skinId"], verify=True):
            self.armed = False
            return
        from injection.game.match_recovery import game_pids
        import psutil

        pids = game_pids()
        if len(pids) != 1 or self.manager._injection_in_progress:
            return
        process = psutil.Process(next(iter(pids)))
        self.manager._ensure_initialized()
        if not self.manager._initialized:
            self.armed = False
            return
        from injection.tools.patcher import check_ltk_patcher

        status = check_ltk_patcher(Path(self.manager.injector.tools_dir))
        if status.missing or status.expired_for(self.manager.injector.game_dir):
            self.armed = False
            self.manager.report_match_issue(
                "ARENA_PATCHER",
                "Bravura: partida mantida aberta",
                "O aplicador está ausente ou incompatível; nenhum reinício foi feito.",
            )
            return
        expected = (Path(self.manager.injector.game_dir) / "League of Legends.exe").resolve()
        if Path(process.exe()).resolve() != expected:
            self.armed = False
            return
        # Stable process identity: psutil also checks PID reuse before terminate.
        birth = process.create_time()
        if time.monotonic() - self.started > 75 or self.lcu.phase not in ACTIVE:
            self.armed = False
            return
        killed = False
        reconnected = False

        def reconnect():
            nonlocal reconnected
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if self.state.stop or self.lcu.phase not in ACTIVE:
                    return False
                try:
                    accepted = self.lcu.reconnect_game()
                except requests.RequestException:
                    accepted = False
                if accepted:
                    reconnected = True
                    return True
                time.sleep(0.5)
            self.manager.report_match_issue(
                "ARENA_RECONNECT",
                "Clique em Reconectar no LoL",
                "A reconexão automática não foi confirmada pelo cliente.",
            )
            return False

        def cancelled():
            return self.state.stop or self.manager.recovery.cancelled.is_set() or self.lcu.phase not in ACTIVE

        def inject(extra):
            nonlocal killed
            if cancelled() or process.create_time() != birth:
                return False
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            with atomic_write(self.marker) as out:
                json.dump({"gameId": key, "championId": cid, "skinId": pick["skinId"]}, out)
            self.seen.add(key)
            self.armed = False
            self.manager.stop_monitor()
            process.terminate()
            killed = True
            process.wait(timeout=6)
            self.manager.start_monitor()
            self.manager.arena_overlay_ready = reconnect
            return self.manager.injector.inject_skin(
                f"skin_{pick['skinId']}",
                timeout=45,
                stop_callback=cancelled,
                injection_manager=self.manager,
                champion_id=cid,
                extra_mods_callback=extra,
            )

        try:
            self.manager._run_injection("Arena Bravura", inject)
        finally:
            self.manager.arena_overlay_ready = None
            if killed and not reconnected:
                self.manager.stop_monitor()
                reconnect()
