"""Restore the baseline app folders of published versions from each release's SEXO2-baseline.zip.

    python scripts/restore_baselines.py [--registry scripts/compatibility_bases.json] [--only 1.6.4 1.9.0]

`build_compatibility.py` needs one app folder per supported version. Each GitHub release keeps the same tree as
SEXO2-baseline.zip (everything except hashes.game.txt and manifesto.json, which the patches skip), so the folders
can be deleted after a release and fetched again before the next one. Labels without a release (r1, r2, r3) cannot
be restored and are reported. Uses the Git Credential Manager login, like scripts/publish_local.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_LABEL = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
ASSET = "SEXO2-baseline.zip"


def extract_safely(archive: Path, target: Path) -> None:
    """Unpack into `target`, refusing any member that would land outside it."""
    root = target.resolve()
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if not (root / name).resolve().is_relative_to(root):
                raise ValueError(f"Unsafe path in {archive.name}: {name}")
        zf.extractall(root)
    if not (root / "SEXO2.exe").is_file():
        raise ValueError(f"{archive.name} has no SEXO2.exe at its top level")


def session():
    import requests

    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"},
    )
    credential = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    s = requests.Session()
    s.headers.update({"Authorization": "Bearer " + credential["password"], "Accept": "application/vnd.github+json"})
    return s


def download(s, repository: str, label: str, dest: Path) -> None:
    response = s.get(f"https://api.github.com/repos/{repository}/releases/tags/v{label}", timeout=20)
    response.raise_for_status()
    asset = next((a for a in response.json()["assets"] if a["name"] == ASSET), None)
    if asset is None:
        raise ValueError(f"release v{label} has no {ASSET}")
    with s.get(asset["url"], headers={"Accept": "application/octet-stream"}, stream=True, timeout=(10, 120)) as r:
        r.raise_for_status()
        with dest.open("wb") as out:
            shutil.copyfileobj(r.raw, out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", type=Path, default=ROOT / "scripts" / "compatibility_bases.json")
    parser.add_argument("--only", nargs="*", help="only these labels")
    args = parser.parse_args()
    bases = json.loads(args.registry.read_text(encoding="utf-8"))
    repository = json.loads((ROOT / "assets" / "update-source.json").read_text(encoding="utf-8"))["repository"]
    s = None
    failed = 0
    for label, folder in bases.items():
        if args.only and label not in args.only:
            continue
        target = (ROOT / folder).resolve()
        if (target / "SEXO2.exe").is_file():
            print(f"{label}: already at {target}")
            continue
        if not RELEASE_LABEL.fullmatch(label):
            print(f"{label}: no release to restore from; keep or recreate {target} by hand")
            failed += 1
            continue
        s = s or session()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / ASSET
                download(s, repository, label, archive)
                target.mkdir(parents=True, exist_ok=True)
                extract_safely(archive, target)
            print(f"{label}: restored to {target}")
        except Exception as error:  # report every label, do not stop at the first
            print(f"{label}: FAILED ({error})")
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
