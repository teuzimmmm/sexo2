"""Warning for an LTK patcher that the installed game has outgrown (D-150).

SEXO2 never downloads the patcher: it says what happened and where the two files are. The
check at startup cannot see an update that arrives while SEXO2 is open, so the injection
calls :func:`notify_patcher_outdated` when it finds the patcher refused by the game.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Callable

from utils.core.logging import get_logger

log = get_logger()

# The folder of the LTK Manager repository that holds ltk_patcher_host.exe and ltk_patcher_dll.dll
LTK_PATCHER_FILES_URL = "https://github.com/LeagueToolkit/ltk-manager/tree/main/src-tauri/resources"

# MessageBoxW results
_YES, _NO = 6, 7

_lock = threading.Lock()
_shown: set[str] = set()


def notice_text(eol: str) -> tuple[str, str]:
    """(title, body) of the warning."""
    since = f" (ele vale até {eol})" if eol else ""
    body = (
        f"O LoL foi atualizado e o patcher do SEXO2 não funciona mais com essa versão{since}. "
        "Por isso as skins não entram no jogo.\n\n"
        "Como resolver:\n"
        f"1. Baixe os dois arquivos, ltk_patcher_host.exe e ltk_patcher_dll.dll, nesta página:\n{LTK_PATCHER_FILES_URL}\n"
        "2. Coloque os dois na pasta de ferramentas do SEXO2, no lugar dos atuais.\n"
        "3. Feche o SEXO2 e abra de novo.\n\n"
        "Sim: abrir a página dos arquivos\nNão: abrir a pasta de ferramentas\nCancelar: fechar este aviso"
    )
    return "SEXO2 - Patcher desatualizado", body


def _message_box(title: str, body: str) -> int:
    import ctypes

    # MB_YESNOCANCEL | MB_ICONWARNING | MB_TOPMOST
    return ctypes.windll.user32.MessageBoxW(0, body, title, 0x00000003 | 0x00000030 | 0x00040000)


def _open_folder(path: Path) -> None:
    subprocess.run(["explorer", str(path)], check=False)


def notify_patcher_outdated(
    tools_dir: Path,
    eol: str = "",
    *,
    show: Callable[[str, str], int] = _message_box,
    open_url: Callable[[str], object] = webbrowser.open,
    open_folder: Callable[[Path], object] = _open_folder,
    background: bool = True,
) -> bool:
    """Warn the player once per end-of-life date and run; True when the warning was started.

    Never raises and never blocks the injection: the dialog runs in its own thread.
    """
    if show is _message_box and sys.platform != "win32":
        return False
    with _lock:
        if eol in _shown:
            return False
        _shown.add(eol)

    def work() -> None:
        try:
            title, body = notice_text(eol)
            answer = show(title, body)
            if answer == _YES:
                open_url(LTK_PATCHER_FILES_URL)
            elif answer == _NO:
                open_folder(tools_dir)
        except Exception as error:
            log.warning(f"[LTK] Could not show the outdated patcher warning: {error}")

    if background:
        threading.Thread(target=work, name="SEXO2-PatcherNotice", daemon=True).start()
    else:
        work()
    return True


def forget_shown() -> None:
    """Allow the warning again (tests)."""
    with _lock:
        _shown.clear()
