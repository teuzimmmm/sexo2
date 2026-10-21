"""Restore build-only binaries (Pengu Loader, injection tools, cloudflared) from a previous build.

These executables are not kept in Git. Both the local release (prepare_release.py) and the CI
test build copy them from an earlier SEXO2 folder; source plugins are never overwritten.
The inherited core.dll is then made to read SEXO2's data folder and to show SEXO2's name and
picture in Pengu's dialogs (patch_core_dll.py).

    python scripts/restore_build_binaries.py --base <folder containing _internal>
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

FOLDERS = ("Pengu Loader", "injection/tools", "hosting-tools")
SUFFIXES = {".exe", ".dll", ".bat"}


def find_internal(base: Path) -> Path:
    """Accept the app folder itself or any folder that contains exactly one app folder."""
    if (base / "_internal").is_dir():
        return base / "_internal"
    found = [p for p in base.rglob("_internal") if p.is_dir() and (p / "Pengu Loader").is_dir()]
    if len(found) != 1:
        raise SystemExit(f"Expected one SEXO2 _internal folder under {base}, found {len(found)}")
    return found[0]


def restore(base: Path, target: Path = Path(".")) -> list[Path]:
    internal = find_internal(base)
    copied = []
    for folder in FOLDERS:
        for file in (internal / folder).rglob("*"):
            if file.is_file() and file.suffix.lower() in SUFFIXES:
                dest = target / folder / file.relative_to(internal / folder)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, dest)
                copied.append(dest)
    core = target / "Pengu Loader" / "core.dll"
    if core.is_file():
        from patch_core_dll import PatchError, patch, rebrand

        try:
            core.write_bytes(patch(core.read_bytes()))
        except PatchError as error:
            raise SystemExit(f"core.dll could not be made to read %LOCALAPPDATA%\\SEXO2: {error}") from None
        picture = target / "assets" / "sexo2-toast.png"
        if picture.is_file():
            try:
                core.write_bytes(rebrand(core.read_bytes(), picture.read_bytes()))
            except PatchError as error:
                raise SystemExit(f"Pengu's dialogs in core.dll could not show SEXO2: {error}") from None
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, type=Path)
    copied = restore(parser.parse_args().base)
    print(f"restored {len(copied)} binaries")
    return 0 if copied else 1


if __name__ == "__main__":
    sys.exit(main())
