"""Settings validation and commit owned by SEXO2, independent of panel DOM."""

import math

from sexo2.version import RELEASE_VERSION
from config import get_config_float, get_config_option, set_config_options
from sexo2.overlay import runtime as overlay_runtime
from sexo2.overlay.runtime import enabled as overlay_enabled

OVERLAY_KEYS = {"gold": "goldOverlay", "augments": "augmentsOverlay"}


class SettingsService:
    def __init__(self, *, validate_path, autostart_status, set_autostart, infer_client_path, on_auto_accept=None):
        self.validate_path = validate_path
        self.autostart_status = autostart_status
        self.set_autostart = set_autostart
        self.infer_client_path = infer_client_path
        # Switches the running match acceptance at once (it reads the setting only at start)
        self.on_auto_accept = on_auto_accept

    def snapshot(self):
        path = get_config_option("General", "leaguePath", "") or ""
        return {
            "threshold": get_config_float("General", "injection_threshold", 0.5),
            "monitorAutoResumeTimeout": int(get_config_float("General", "monitor_auto_resume_timeout", 60)),
            "autostart": bool(self.autostart_status()),
            "hideEmptyCategories": (get_config_option("General", "hide_empty_categories", "false") or "").lower()
            == "true",
            "gamePath": path,
            "gamePathValid": bool(path and self.validate_path(path)),
            "goldOverlay": overlay_enabled("gold"),
            "augmentsOverlay": overlay_enabled("augments"),
            "autoAccept": _auto_accept_enabled(),
            "version": RELEASE_VERSION,
        }

    def save(self, payload):
        try:
            threshold = float(payload["threshold"])
            timeout = float(payload["monitorAutoResumeTimeout"])
        except (KeyError, ValueError, TypeError):
            raise ValueError("Confira os tempos de preparação e de pausa.") from None
        if not math.isfinite(threshold) or not 0.3 <= threshold <= 2:
            raise ValueError("O tempo de preparação deve ficar entre 0,30 e 2 segundos.")
        if not math.isfinite(timeout) or not timeout.is_integer() or not 20 <= timeout <= 180:
            raise ValueError("O limite de pausa deve ficar entre 20 e 180 segundos.")
        for key in ("autostart", "hideEmptyCategories"):
            if type(payload.get(key)) is not bool:
                raise ValueError("Confira as opções das configurações.")
        # Overlay switches (D-117); a panel from an older build does not send them.
        overlays = {kind: payload.get(key, overlay_enabled(kind)) for kind, key in OVERLAY_KEYS.items()}
        if any(type(value) is not bool for value in overlays.values()):
            raise ValueError("Confira as opções das configurações.")
        # Moved here from Suporte; a panel from an older build does not send it.
        auto_accept = payload.get("autoAccept", _auto_accept_enabled())
        if type(auto_accept) is not bool:
            raise ValueError("Confira as opções das configurações.")
        path = payload.get("gamePath")
        if not isinstance(path, str):
            raise ValueError("Confira a pasta do League of Legends.")
        path = path.strip()
        if path and not self.validate_path(path):
            raise ValueError("Selecione uma pasta local válida do League of Legends (Game).")
        client_path = (self.infer_client_path(path) or "") if path else ""
        previous_autostart = bool(self.autostart_status())
        changed_autostart = payload["autostart"] != previous_autostart
        changes = {
            "General": {
                "injection_threshold": f"{threshold:.2f}",
                "monitor_auto_resume_timeout": str(int(timeout)),
                "hide_empty_categories": "true" if payload["hideEmptyCategories"] else "false",
                "leaguePath": path,
                "clientPath": client_path,
                "autoaccept": "true" if auto_accept else "false",
            },
            "Overlay": {f"{kind}_enabled": "true" if value else "false" for kind, value in overlays.items()},
        }
        if changed_autostart:
            self.set_autostart(payload["autostart"])
        try:
            set_config_options(changes, strict=True, atomic_only=True)
        except Exception as error:
            if changed_autostart:
                try:
                    self.set_autostart(previous_autostart)
                except Exception:
                    raise ValueError(
                        "A gravação falhou e a inicialização com Windows pode ter mudado. Confira essa opção ao reconectar."
                    ) from error
            raise
        overlay_runtime.apply()
        if self.on_auto_accept is not None:
            self.on_auto_accept(auto_accept)
        return {
            "threshold": threshold,
            "monitorAutoResumeTimeout": int(timeout),
            "autostart": payload["autostart"],
            "hideEmptyCategories": payload["hideEmptyCategories"],
            "gamePath": path,
            "gamePathValid": bool(path),
            "goldOverlay": overlays["gold"],
            "augmentsOverlay": overlays["augments"],
            "autoAccept": auto_accept,
            "version": RELEASE_VERSION,
        }


def _auto_accept_enabled():
    return (get_config_option("General", "autoaccept", "false") or "").lower() == "true"
