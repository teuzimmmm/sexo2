"""Restore build-only binaries (Pengu Loader, injection tools, cloudflared) from a previous build.

These executables are not kept in Git. Both the local release (prepare_release.py) and the CI
test build copy them from an earlier SEXO2 folder; source plugins are never overwritten.

    python scripts/restore_build_binaries.py --base <folder containing _internal> [--core <core.dll>]

--core replaces the baseline's Pengu core.dll with the one built by .github/workflows/pengu-core.yml
(source: native/pengu-core). It is accepted only if its SHA-256 matches native/pengu-core/core.lock.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

FOLDERS = ("Pengu Loader", "injection/tools", "hosting-tools")
SUFFIXES = {".exe", ".dll", ".bat"}
CORE_LOCK = Path(__file__).resolve().parent.parent / "native" / "pengu-core" / "core.lock.json"


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
    return copied


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_core(core: Path, target: Path = Path("."), lock: Path = CORE_LOCK) -> Path:
    """Replace the restored Pengu core.dll with the source-built one, after checking its hash."""
    expected = json.loads(lock.read_text(encoding="utf-8"))["sha256"].lower()
    actual = sha256_of(core)
    if actual != expected:
        raise SystemExit(f"core.dll hash {actual} does not match {lock.name} ({expected})")
    dest = target / "Pengu Loader" / "core.dll"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(core, dest)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--core", type=Path, help="source-built core.dll (hash-checked)")
    args = parser.parse_args()
    copied = restore(args.base)
    if args.core:
        apply_core(args.core)
        print(f"core.dll replaced by {args.core}")
    print(f"restored {len(copied)} binaries")
    return 0 if copied else 1


if __name__ == "__main__":
    sys.exit(main())
