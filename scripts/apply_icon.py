"""Use one of the icon options (design/propostas/icone, D-121) as SEXO2's icon everywhere.

    python scripts/apply_icon.py b

Writes the executable and installer icon (sexo2.ico), the shortcut icons (sexo2-v2.ico,
sexo2-black-v3.ico), the window and dialog icon (icon.ico), the tray pictures (icon.png,
tray_starting.png, tray_ready.png) and the picture in Pengu's welcome dialog
(sexo2-toast.png, written into core.dll by patch_core_dll.rebrand).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ROOT / "design" / "propostas" / "icone"
ASSETS = ROOT / "assets"
ICO_FILES = ("sexo2.ico", "sexo2-v2.ico", "sexo2-black-v3.ico", "icon.ico")
PNG_FILES = ("icon.png", "tray_starting.png", "tray_ready.png")
TOAST = "sexo2-toast.png"


def apply(letter: str, assets: Path = ASSETS) -> list[Path]:
    ico = OPTIONS / "ico" / f"{letter}.ico"
    if not ico.is_file():
        raise SystemExit(f"no icon option {letter!r} in {OPTIONS / 'ico'}")
    written = []
    for name in ICO_FILES:
        shutil.copyfile(ico, assets / name)
        written.append(assets / name)
    for name in PNG_FILES:
        shutil.copyfile(OPTIONS / "png" / f"{letter}-256.png", assets / name)
        written.append(assets / name)
    shutil.copyfile(OPTIONS / "png" / f"{letter}-64.png", assets / TOAST)  # shown at 40 px
    written.append(assets / TOAST)
    return written


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    for path in apply(sys.argv[1].lower()):
        print(path.relative_to(ROOT))
