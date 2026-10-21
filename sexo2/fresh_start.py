"""One clean start for SEXO2 1.7.0, asked by the user on 20/10/2026.

The data folders of earlier versions, ``%LOCALAPPDATA%\\Rose`` and ``%LOCALAPPDATA%\\SEXO2``,
are deleted once with everything in them (settings, favourites, mod library, Pengu Loader
and its plugins, logs), so nothing of an earlier build is left; SEXO2 then starts empty.
A marker in the new SEXO2 folder makes it happen only once.

Standard library only: main.py runs it before any SEXO2 module touches those folders.
Skipped, and tried again at the next start, while League or another SEXO2 or Rose runs
(their files are in use). The folder SEXO2 itself runs from is never deleted. A Pengu hook
that would run a core.dll from a deleted folder is removed first, or League couldn't start;
SEXO2 registers its own a moment later.
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = ".inicio-limpo-1.7.0"
FOLDERS = ("Rose", "SEXO2")
BUSY = frozenset(
    name.casefold()
    for name in (
        "LeagueClient.exe",
        "LeagueClientUx.exe",
        "League of Legends.exe",
        "SEXO2.exe",
        "Rose.exe",
        "Rose Sala.exe",
    )
)
IFEO_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\LeagueClientUx.exe"


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def clean(localappdata: Path, exe: Path, busy: bool, clear_hook=lambda folders: None) -> list[Path]:
    """Delete the old folders once; returns the folders deleted (empty when nothing was done)."""
    new = localappdata / "SEXO2"
    if busy or (new / MARKER).exists():
        return []
    folders = [localappdata / name for name in FOLDERS]
    folders = [folder for folder in folders if folder.is_dir() and not _inside(exe, folder)]
    clear_hook(folders)
    for folder in folders:
        shutil.rmtree(folder, ignore_errors=True)
    if any(folder.exists() for folder in folders):
        return []  # a file was in use: no marker, the next start tries again
    new.mkdir(parents=True, exist_ok=True)
    (new / MARKER).write_text("", encoding="utf-8")
    return folders


def _other_processes_running() -> bool:
    try:
        output = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return True  # unknown: don't delete anything this time
    for row in csv.reader(io.StringIO(output)):
        if len(row) > 1 and row[0].casefold() in BUSY and row[1] != str(os.getpid()):
            return True
    return False


def _clear_hook(folders: list[Path]) -> None:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, IFEO_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        ) as key:
            debugger, _ = winreg.QueryValueEx(key, "Debugger")
            if any(
                folder.as_posix().casefold() + "/" in str(debugger).replace("\\", "/").casefold() for folder in folders
            ):
                winreg.DeleteValue(key, "Debugger")
    except OSError:
        pass  # no hook, or no right to change it: SEXO2 replaces it when it activates its loader


def main() -> None:
    localappdata = os.environ.get("LOCALAPPDATA")
    if not localappdata:
        return
    busy = _other_processes_running()
    clean(Path(localappdata), Path(sys.executable), busy, _clear_hook)
