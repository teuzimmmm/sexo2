"""Reuse a confirmed local library; remote probes only schedule later maintenance."""

import json, re, sys, threading
from pathlib import Path
from utils.core.atomic_file import write_text_atomic
from utils.core.logging import get_logger
from config import get_config_file_path

log = get_logger()
_fast_used = False


def state_path():
    return get_config_file_path().parent / "sexo2-startup-ready.json"


def tracked_files():
    from utils.core.paths import get_skins_dir, get_classic_skins_dir

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return {
        "hashes": base / "injection/tools/hashes.game.txt",
        "skins": get_skins_dir() / ".skin_version",
        "classic": get_classic_skins_dir() / ".classic_state.json",
    }


def fingerprints():
    result = {}
    for key, path in tracked_files().items():
        stat = path.stat()
        if stat.st_size <= 0:
            raise ValueError("Missing library data")
        if key == "skins" and not re.fullmatch(r"[0-9a-fA-F]{40}", path.read_text(encoding="utf-8").strip()):
            raise ValueError("Invalid library revision")
        if key == "classic":
            marker = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(marker, dict) or marker.get("synced") is not True:
                raise ValueError("Classic library not synced")
        result[key] = {"path": str(path.resolve()), "size": stat.st_size, "mtime": stat.st_mtime_ns}
    return result


def read_state():
    try:
        result = json.loads(state_path().read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def game_running():
    import psutil

    names = {"league of legends.exe", "league of legends (tm) client.exe"}
    try:
        return any((p.info.get("name") or "").lower() in names for p in psutil.process_iter(["name"]))
    except (psutil.Error, OSError):
        return True


def can_start_fast():
    try:
        data = read_state()
        if data.get("schema") != 1 or data.get("files") != fingerprints():
            return False
        from state import AppStatus

        status = AppStatus()
        if not (status.check_skins_downloaded() and status.check_previews_downloaded()):
            return False
        # Pending maintenance is deferred while a match is running.
        return not data.get("pending") or game_running()
    except (OSError, ValueError):
        return False


def record_ready():
    try:
        write_text_atomic(state_path(), json.dumps({"schema": 1, "files": fingerprints(), "pending": []}))
    except (OSError, ValueError):
        log.debug("[STARTUP] Local library checkpoint unavailable")


def probe_updates(cancelled=lambda: False, notify=lambda: None):
    """Read remote revisions only. Never extract/download/remove library content."""
    try:
        from utils.download.repo_downloader import RepoDownloader
        from utils.download.hash_updater import check_for_updates

        saved = read_state()
        if saved.get("files") != fingerprints():
            return
        downloader = RepoDownloader()
        try:
            remote = downloader.fetch_remote_sha()
        finally:
            downloader.session.close()
        pending = set(saved.get("pending", []))
        if remote and remote != downloader.get_local_sha():
            pending.add("skins")
        if cancelled():
            return
        if check_for_updates(parallel=False, cancelled=cancelled):
            pending.add("hashes")
        if cancelled() or saved.get("files") != fingerprints():
            return
        saved["pending"] = sorted(pending)
        write_text_atomic(state_path(), json.dumps(saved))
        if pending:
            notify()
    except Exception:
        log.debug("[STARTUP] Remote library probe unavailable; local data retained")


def start_probe(state, tray=None):
    if not _fast_used:
        return

    def notify():
        if tray and tray.icon:
            tray.icon.notify(
                "Novos arquivos de skins serão preparados na próxima abertura fora de uma partida.", "SEXO2"
            )

    threading.Thread(
        target=lambda: probe_updates(lambda: state.stop, notify), name="SEXO2-Library-probe", daemon=True
    ).start()
