"""Persistent, champion-keyed Swiftplay preferences; independent of UI hover events."""
import json
import os
import threading
from pathlib import Path
from utils.core.paths import get_user_data_dir


class SwiftplayPins:
    def __init__(self, path=None):
        self.path = Path(path) if path else get_user_data_dir() / "swiftplay-pins.json"
        self.lock = threading.RLock()
        self.error = None
        self._pins = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") != 1 or not isinstance(data.get("pins"), dict):
                raise ValueError("Formato de preferências inválido")
            for key, value in data["pins"].items():
                cid, sid = int(key), value["skinId"]
                if cid > 0 and type(sid) is int and sid // 1000 == cid:
                    self._pins[cid] = {"skinId": sid, "name": str(value.get("name", sid))}
        except FileNotFoundError:
            pass
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            self.error = f"Não foi possível ler as preferências: {exc}"

    def snapshot(self):
        with self.lock:
            return {cid: dict(pin) for cid, pin in self._pins.items()}

    def save(self, changes):
        with self.lock:
            if self.error:
                raise ValueError(self.error)
            updated = self.snapshot()
            for cid, pin in changes.items():
                if pin is None:
                    updated.pop(cid, None)
                else:
                    if type(cid) is not int or type(pin["skinId"]) is not int or pin["skinId"] // 1000 != cid:
                        raise ValueError("A skin não pertence ao campeão")
                    updated[cid] = dict(pin)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps({"version": 1, "pins": updated}, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self.path)
            self._pins = updated


def get_pins(state):
    # SharedState owns the service so preparation and the bridge use the same lock/cache.
    with state.swiftplay_lock:
        if getattr(state, "swiftplay_pins", None) is None:
            state.swiftplay_pins = SwiftplayPins()
        return state.swiftplay_pins


def read_lobby(lcu):
    """Confirm queue and local slots together from one fresh lobby response."""
    if not lcu or not lcu.ok:
        return None
    lobby = lcu.get("/lol-lobby/v2/lobby")
    if not isinstance(lobby, dict):
        return None
    config = lobby.get("gameConfig") or {}
    # BRAWL is grouped with Swiftplay by upstream; it must NOT enable this panel.
    if config.get("queueId") != 480:
        return None
    local = lobby.get("localMember") or {}
    slots = local.get("playerSlots")
    if not isinstance(slots, list) or len(slots) != 2:
        return None
    ids = []
    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            return None
        cid = slot.get("championId") or local.get("primaryChampionId" if i == 0 else "secondaryChampionId")
        if type(cid) is not int or cid <= 0:
            return None
        ids.append(cid)
    if len(set(ids)) != 2:
        return None
    return ids


def base_slots_ready(lcu, ids, pins):
    """Confirm the base-skin reset took effect before preparing pinned mods."""
    if not ids or not any(cid in pins for cid in ids):
        return True
    lobby = lcu.get("/lol-lobby/v2/lobby")
    if not isinstance(lobby, dict) or (lobby.get("gameConfig") or {}).get("queueId") != 480:
        return False
    local = lobby.get("localMember") or {}
    slots = local.get("playerSlots") or []
    if len(slots) != 2:
        return False
    for i, cid in enumerate(ids):
        slot = slots[i]
        if not isinstance(slot, dict):
            return False
        actual = slot.get("championId") or local.get("primaryChampionId" if i == 0 else "secondaryChampionId")
        if actual != cid or (cid in pins and slot.get("skinId") != cid * 1000):
            return False
    return True


class SwiftplayPanelService:
    def __init__(self, state, lcu):
        self.state, self.lcu = state, lcu
        self.pins = get_pins(state)
        self.catalogs = {}

    def catalog(self, cid):
        if cid not in self.catalogs:
            data = self.lcu.get(f"/lol-game-data/assets/v1/champions/{cid}.json")
            if not isinstance(data, dict) or not isinstance(data.get("skins"), list):
                raise ValueError("Catálogo indisponível; tente novamente")
            skins = []
            for skin in data["skins"]:
                sid = skin.get("id")
                if type(sid) is int and sid // 1000 == cid:
                    skins.append({"skinId": sid, "name": str(skin.get("name") or sid), "tilePath": skin.get("tilePath")})
                    for chroma in skin.get("chromas", []) or []:
                        if not isinstance(chroma, dict) or chroma.get("disabled"): continue
                        chroma_id = chroma.get("id")
                        if type(chroma_id) is int and chroma_id // 1000 == cid:
                            skins.append({"skinId": chroma_id, "name": str(skin.get("name") or sid) + " · " + str(chroma.get("name") or "Croma " + str(chroma_id)), "tilePath": chroma.get("chromaPath") or skin.get("tilePath"), "chroma": True, "baseSkinId": sid})
            if not skins:
                raise ValueError("Catálogo de skins vazio; tente novamente")
            self.catalogs[cid] = {"championId": cid, "name": str(data.get("name") or cid),
                                  "portrait": data.get("squarePortraitPath"), "skins": skins}
        return self.catalogs[cid]

    def snapshot(self):
        ids = read_lobby(self.lcu)
        phase = self.lcu.get("/lol-gameflow/v1/gameflow-phase") if ids else None
        active = bool(ids and phase in ("Lobby", "Matchmaking", "ReadyCheck"))
        result = {"type": "swiftplay-pins-state", "active": active, "editable": active and phase == "Lobby",
                  "championIds": ids or [], "champions": [], "error": self.pins.error}
        if active:
            pins = self.pins.snapshot()
            for cid in ids:
                row = dict(self.catalog(cid))
                row["pin"] = pins.get(cid)
                with self.state.swiftplay_lock:
                    row["status"] = dict(getattr(self.state, "swiftplay_pin_status", {}).get(cid, {}))
                result["champions"].append(row)
        return result

    def save(self, payload):
        ids = read_lobby(self.lcu)
        if not ids or self.lcu.get("/lol-gameflow/v1/gameflow-phase") != "Lobby":
            raise ValueError("Volte ao lobby de Swiftplay para alterar as skins")
        if payload.get("championIds") != ids:
            raise ValueError("Os campeões mudaram. Confira as escolhas novamente")
        selections = payload.get("selections")
        if not isinstance(selections, list) or len(selections) != 2:
            raise ValueError("Confirme as escolhas dos dois campeões")
        changes = {}
        for cid, choice in zip(ids, selections):
            if not isinstance(choice, dict) or choice.get("championId") != cid:
                raise ValueError("Seleção de campeão inválida")
            sid = choice.get("skinId")
            if sid is None:
                changes[cid] = None
            else:
                entry = next((s for s in self.catalog(cid)["skins"] if type(sid) is int and s["skinId"] == sid), None)
                if not entry:
                    raise ValueError("A skin não pertence ao catálogo deste campeão")
                changes[cid] = {"skinId": sid, "name": entry["name"]}
        # Recheck after fetching catalog: the user may have changed slots while it loaded.
        if read_lobby(self.lcu) != ids or self.lcu.get("/lol-gameflow/v1/gameflow-phase") != "Lobby":
            raise ValueError("O lobby mudou durante a confirmação; tente novamente")
        self.pins.save(changes)
        with self.state.swiftplay_lock:
            for cid, pin in changes.items():
                self.state.swiftplay_skin_tracking.pop(cid, None)
                if pin:
                    self.state.swiftplay_skin_tracking[cid] = pin["skinId"]
            self.state.swiftplay_pin_status = {}
        handler = getattr(self.state, "swiftplay_handler", None)
        if handler:
            for cid in ids:
                handler.mark_champion_changed(cid)
            handler.force_base_skins_if_needed()
        return self.snapshot()
