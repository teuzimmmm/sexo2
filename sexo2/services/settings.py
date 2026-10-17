"""Settings validation and commit owned by SEXO2, independent of panel DOM."""
import math

from config import APP_VERSION, get_config_float, get_config_option, set_config_options
from lolalytics.risk import DEFAULT_RISK_LEVEL, validate_risk_level
from sexo2.install.identity import display_version


def get_risk_level():
    """Return the saved LoLalytics risk level, falling back on corrupt values."""
    value = get_config_option('LoLalytics', 'risk_level', DEFAULT_RISK_LEVEL)
    try:
        return validate_risk_level(value)
    except (TypeError, ValueError):
        return DEFAULT_RISK_LEVEL


def get_overlay_enabled():
    return str(get_config_option('LoLalytics', 'overlay_enabled', 'true')).lower() == 'true'


class SettingsService:
    def __init__(self, *, validate_path, autostart_status, set_autostart, infer_client_path):
        self.validate_path = validate_path
        self.autostart_status = autostart_status
        self.set_autostart = set_autostart
        self.infer_client_path = infer_client_path

    def snapshot(self):
        path = get_config_option('General', 'leaguePath', '') or ''
        return {
            'threshold': get_config_float('General', 'injection_threshold', 0.5),
            'monitorAutoResumeTimeout': int(get_config_float('General', 'monitor_auto_resume_timeout', 60)),
            'autostart': bool(self.autostart_status()),
            'hideEmptyCategories': (get_config_option('General', 'hide_empty_categories', 'false') or '').lower() == 'true',
            'lolalyticsRiskLevel': get_risk_level(),
            'buildOverlayEnabled': get_overlay_enabled(),
            'gamePath': path, 'gamePathValid': bool(path and self.validate_path(path)),
            'version': display_version(APP_VERSION),
        }

    def save(self, payload):
        overlay_enabled = payload.get('buildOverlayEnabled', get_overlay_enabled())
        if type(overlay_enabled) is not bool:
            raise ValueError('Confira a opção do overlay durante a partida.')
        # Older panels do not send this field; retain the saved preference.
        if 'lolalyticsRiskLevel' in payload:
            try:
                risk_level = validate_risk_level(payload['lolalyticsRiskLevel'])
            except (TypeError, ValueError):
                raise ValueError('Escolha um nível de risco válido para as recomendações.') from None
            save_risk_level = True
        else:
            risk_level = get_risk_level()
            save_risk_level = False
        try:
            threshold = float(payload['threshold'])
            timeout = float(payload['monitorAutoResumeTimeout'])
        except (KeyError, ValueError, TypeError):
            raise ValueError('Confira os tempos de preparação e de pausa.') from None
        if not math.isfinite(threshold) or not 0.3 <= threshold <= 2:
            raise ValueError('O tempo de preparação deve ficar entre 0,30 e 2 segundos.')
        if not math.isfinite(timeout) or not timeout.is_integer() or not 20 <= timeout <= 180:
            raise ValueError('O limite de pausa deve ficar entre 20 e 180 segundos.')
        for key in ('autostart', 'hideEmptyCategories'):
            if type(payload.get(key)) is not bool:
                raise ValueError('Confira as opções das configurações.')
        path = payload.get('gamePath')
        if not isinstance(path, str):
            raise ValueError('Confira a pasta do League of Legends.')
        path = path.strip()
        if path and not self.validate_path(path):
            raise ValueError('Selecione uma pasta local válida do League of Legends (Game).')
        client_path = (self.infer_client_path(path) or '') if path else ''
        previous_autostart = bool(self.autostart_status())
        changed_autostart = payload['autostart'] != previous_autostart
        changes = {'General': {
            'injection_threshold': f'{threshold:.2f}',
            'monitor_auto_resume_timeout': str(int(timeout)),
            'hide_empty_categories': 'true' if payload['hideEmptyCategories'] else 'false',
            'leaguePath': path, 'clientPath': client_path,
        }}
        if save_risk_level:
            changes['LoLalytics'] = {'risk_level': risk_level}
        if 'buildOverlayEnabled' in payload:
            changes.setdefault('LoLalytics', {})['overlay_enabled'] = 'true' if overlay_enabled else 'false'
        if changed_autostart:
            self.set_autostart(payload['autostart'])
        try:
            set_config_options(changes, strict=True, atomic_only=True)
        except Exception as error:
            if changed_autostart:
                try:
                    self.set_autostart(previous_autostart)
                except Exception:
                    raise ValueError('A gravação falhou e a inicialização com Windows pode ter mudado. Confira essa opção ao reconectar.') from error
            raise
        return {
            'threshold': threshold, 'monitorAutoResumeTimeout': int(timeout),
            'autostart': payload['autostart'], 'hideEmptyCategories': payload['hideEmptyCategories'],
            'lolalyticsRiskLevel': risk_level,
            'buildOverlayEnabled': overlay_enabled,
            'gamePath': path, 'gamePathValid': bool(path), 'version': display_version(APP_VERSION),
        }
