"""Derive every app icon from assets/sexo2.svg (the single source, never edited).

    python scripts/render_icon.py [--chrome PATH]

Renders one PNG per size with a headless Chromium (the Playwright cache is searched when
--chrome is not given), then writes the multi-resolution .ico files (PNG entries) with struct.
The result is committed, so CI and the build never need a browser.
"""

from __future__ import annotations

import argparse
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "sexo2.svg"
SIZES = (16, 24, 32, 48, 64, 128, 256)
ICO_FILES = ("sexo2.ico", "sexo2-v2.ico", "sexo2-black-v3.ico", "icon.ico")
PNG_256 = ("icon.png", "tray_ready.png", "tray_starting.png")
TOAST = "sexo2-toast.png"  # shown at 40 px inside core.dll


def find_chrome() -> Path:
    cache = Path.home() / "Library/Caches/ms-playwright"
    found = sorted(cache.glob("chromium_headless_shell-*/*/chrome-headless-shell"))
    if not found:
        raise SystemExit("no chrome-headless-shell in the Playwright cache; pass --chrome")
    return found[-1]


def render(chrome: Path, size: int, out: Path, work: Path) -> bytes:
    page = work / f"icon-{size}.html"
    page.write_text(
        f'<!doctype html><body style="margin:0"><img src="{SOURCE.as_uri()}" width="{size}" height="{size}" '
        'style="display:block"></body>',
        encoding="utf-8",
    )
    subprocess.run(
        [str(chrome), "--no-sandbox", "--hide-scrollbars", "--force-device-scale-factor=1",
         f"--window-size={size},{size}", f"--screenshot={out}", page.as_uri()],
        check=True, capture_output=True,
    )  # fmt: skip
    return out.read_bytes()


def build_ico(pngs: dict[int, bytes]) -> bytes:
    head = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, data = b"", b""
    for size, png in sorted(pngs.items()):
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    return head + entries + data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chrome", type=Path)
    chrome = parser.parse_args().chrome or find_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        pngs = {size: render(chrome, size, work / f"{size}.png", work) for size in SIZES}
    ico = build_ico(pngs)
    for name in ICO_FILES:
        (ASSETS / name).write_bytes(ico)
    for name in PNG_256:
        (ASSETS / name).write_bytes(pngs[256])
    (ASSETS / TOAST).write_bytes(pngs[64])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
