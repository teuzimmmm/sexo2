#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fronteira declarada entre o OverlayManager e o InjectionManager.

POR QUE ESTE ARQUIVO EXISTE (ver A4 em ROSE_0_3_DECISOES.md):

O `mk_run_overlay` precisa de seis coisas do InjectionManager: a recuperação,
a fase atual, o aviso de liberação de segurança, o canal de diagnóstico e o
controle do monitor. Antes, buscava cada uma com `getattr(..., None)` no meio
do fluxo. Isso tem dois problemas:

1. Se um nome mudar do outro lado, `getattr` devolve `None` em silêncio e o
   Rose passa a agir como se o recurso não existisse — sem erro, sem log.
   Uma proteção que some sozinha é pior do que proteção nenhuma, porque você
   continua confiando nela.
2. A dependência real entre os dois módulos fica invisível: não dá para ler o
   OverlayManager e saber o que ele exige do InjectionManager.

`MatchContext` resolve os dois: é o contrato escrito, aceita `None` (há
caminhos legítimos que injetam sem manager) e, quando um manager existe mas
não tem o atributo esperado, **avisa uma vez no log** em vez de fingir que
está tudo bem.
"""

from utils.core.logging import get_logger
from utils.core.match_report import MatchReport

log = get_logger()

_ACTIVE_PHASES = ("GameStart", "InProgress", "Reconnect")


class MatchContext:
    """Tudo o que o overlay precisa saber sobre a partida em curso."""

    def __init__(self, injection_manager, skins=None):
        self._manager = injection_manager
        self._warned = set()
        #: Linha do tempo desta tentativa. Vive aqui porque o contexto já
        #: circula por todas as partes do fluxo — assim o registro não exige
        #: mudar a assinatura de nenhuma função.
        self.report = MatchReport(skins)

    # -- acesso interno ----------------------------------------------------

    def _get(self, name, default=None):
        """Lê um atributo do manager avisando (uma vez) se ele não existir."""
        if self._manager is None:
            return default
        try:
            return getattr(self._manager, name)
        except AttributeError:
            if name not in self._warned:
                self._warned.add(name)
                log.warning(
                    "[INJECT] InjectionManager sem '%s'; o overlay vai seguir sem esse "
                    "recurso. Se isso não for intencional, a interface quebrou.",
                    name,
                )
            return default

    # -- estado da partida -------------------------------------------------

    @property
    def manager(self):
        """O InjectionManager cru, para o que ainda não passa por aqui."""
        return self._manager

    @property
    def recovery(self):
        """MatchRecovery da partida, ou None se não houver."""
        return self._get("recovery")

    @property
    def phase(self):
        """Fase atual do cliente ('GameStart', 'InProgress', ...) ou None."""
        state = self._get("shared_state")
        return getattr(state, "phase", None) if state is not None else None

    @property
    def in_active_phase(self) -> bool:
        """True quando a partida está em andamento de alguma forma."""
        return self.phase in _ACTIVE_PHASES

    @property
    def safety_released(self) -> bool:
        """True quando o limite de pausa já liberou o LoL nesta injeção."""
        return bool(self._get("safety_resume_triggered", False))

    @property
    def cancelled(self) -> bool:
        """True quando o usuário pediu parada de emergência nesta partida."""
        recovery = self.recovery
        return bool(recovery and recovery.cancelled.is_set())

    # -- ações -------------------------------------------------------------

    def report_issue(self, code: str, summary: str, detail: str) -> None:
        """Mostra um problema observado na bandeja, sem afirmar a causa."""
        self.report.aviso(code)
        callback = self._get("report_match_issue")
        if not callback:
            return
        try:
            callback(code, summary, detail)
        except Exception as exc:
            log.debug("[INJECT] Could not report match issue %s: %s", code, exc)

    def resume_game(self) -> None:
        if self._manager is not None:
            self._manager.resume_game()

    def start_monitor(self) -> None:
        manager = self._manager
        if manager is None:
            return
        starter = getattr(manager, "start_monitor", None) or getattr(manager, "_start_monitor", None)
        if starter:
            starter()

    def stop_monitor(self) -> None:
        manager = self._manager
        if manager is None:
            return
        stopper = getattr(manager, "stop_monitor", None) or getattr(manager, "_stop_monitor", None)
        if stopper:
            stopper()
