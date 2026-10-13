"""Parada de emergência por partida, e observação do processo do jogo.

## O QUE MUDOU NA PORTAGEM PARA O ROSE 1.3.1 (leia antes de "restaurar" algo)

Este módulo era maior. Ele tinha uma máquina de repetição: se o processo do
LoL sumisse cedo, o Rose reiniciava o overlay até três vezes dentro de quatro
minutos (`may_retry`, `wait_for_new_game`, `start_retry_window`, e a opção
"Tentar recuperar após crash do LoL" na bandeja).

**Tudo isso foi removido de propósito, porque o Rose 1.3.1 resolveu o mesmo
problema num nível mais baixo e melhor.** O aplicador LTK (`ltk_patcher_host`)
**continua varrendo entre partidas**: quando o processo do jogo morre e volta,
ele engancha de novo sozinho, sem ninguém reiniciar nada. O comentário está no
código deles, em `_run_ltk_patcher`:

    "exited" only means this game process closed; the host goes back to
    scanning so a reconnect is hooked again

Manter a nossa repetição por cima disso seria reaplicar a skin duas vezes por
caminhos diferentes, competindo com o mecanismo oficial. Foi por isso que ela
saiu, e é por isso que a opção sumiu da bandeja: não havia mais o que ligar ou
desligar.

## O QUE SOBROU, E POR QUÊ

1. **A trava de parada de emergência** (`cancelled`). O "Parar Rose nesta
   partida" continua sendo nosso: o Rose oficial tem `stop_injection_by_user`,
   mas só alcançável pelo botão dentro do cliente. A trava garante que, depois
   de parar, nenhuma injeção recomece **nesta partida** — nem por pedido do
   cliente, nem por uma nova tentativa qualquer.

2. **O reset por partida** (`note_phase`). Uma parada vale até a próxima
   seleção de campeões ou fila. Sem isso a trava ficaria presa entre partidas —
   exatamente o bug #255 que o upstream acabou de consertar no botão deles.

3. **`game_pids`**, usado pela vigilância do `overlay_manager` para dizer ao
   usuário o que foi observado.
"""

from __future__ import annotations

import threading

try:
    import psutil
except ImportError:  # Mantém o módulo testável sem psutil.
    psutil = None

from utils.core.logging import get_logger

log = get_logger()

from config import GAME_EXECUTABLE_NAMES
GAME_PROCESS_NAMES = {name.lower() for name in GAME_EXECUTABLE_NAMES}
ACTIVE_PHASES = {"GameStart", "InProgress", "Reconnect"}


def game_pids() -> set:
    """PIDs do processo do jogo agora. Conjunto vazio se não der para saber."""
    if psutil is None:
        return set()
    found = set()
    try:
        for process in psutil.process_iter(["pid", "name"]):
            try:
                if (process.info.get("name") or "").lower() in GAME_PROCESS_NAMES:
                    found.add(process.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as exc:
        log.debug("[RECOVERY] Cannot enumerate game processes: %s", exc)
    return found


class MatchRecovery:
    """Trava de parada de emergência, válida só para a partida atual."""

    def __init__(self, state):
        self.state = state
        self.cancelled = threading.Event()
        self._lock = threading.RLock()
        self.clear_issue_callback = None

    def note_phase(self, phase: str, previous_phase: str) -> None:
        """Libera a trava quando começa uma partida nova."""
        if (
            phase == "ChampSelect" and previous_phase not in ACTIVE_PHASES | {"ChampSelect"}
        ) or (
            phase == "Matchmaking" and previous_phase in (None, "Lobby", "EndOfGame")
        ):
            if self.cancelled.is_set():
                log.info("[RECOVERY] New match: emergency stop reset")
            self.cancelled.clear()
            if self.clear_issue_callback:
                self.clear_issue_callback()

    def stop_current_match(self, injection_manager) -> None:
        """Para o Rose nesta partida e devolve o jogo ao usuário.

        A ordem importa: a trava vem primeiro, para que nada que esteja em voo
        recomece enquanto desligamos o resto.
        """
        self.cancelled.set()
        with self._lock:
            try:
                # Caminho oficial do 1.3.1: derruba o aplicador e o mod-tools,
                # marcando que a parada foi pedida (para não virar "falha").
                injection_manager.stop_injection_by_user()
            except Exception as exc:
                log.warning("[RECOVERY] Could not stop injection cleanly: %s", exc)
            try:
                injection_manager.resume_if_suspended()
                injection_manager.game_monitor.stop()
            except Exception as exc:
                log.warning("[RECOVERY] Could not release the game: %s", exc)
        log.warning("[RECOVERY] Rose stopped for this match; game released")
