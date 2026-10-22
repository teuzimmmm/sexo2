#!/usr/bin/env python3
"""Pack only what a test build changes over an installed release, to extract on top of it.

The test build (CI, unsigned) is a whole application folder. Someone who already runs the last
release only needs the files that differ: the program file and the plugins. Nothing else is
taken, on purpose: the tools restored from an old baseline (injection tools, the tunnel, the
loader's own binaries) would overwrite newer ones. If the Python runtime differs between the
release and the build, no overlay is made: the program file would not start on it.

Usage:
    python scripts/build_test_overlay.py --base SEXO2-baseline.zip --new dist-test/SEXO2 \
        --output SEXO2-teste-arquivos.zip [--base-version v1.9.0]
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

PROGRAM = "SEXO2.exe"
PLUGINS = "_internal/Pengu Loader/plugins/"
RUNTIME = re.compile(r"^_internal/python3\d+\.dll$", re.IGNORECASE)

README = """\
Teste do SEXO2 sobre a versão que você já usa{base}

1. Feche o SEXO2 e o LoL.
2. Extraia este zip DENTRO da pasta onde o SEXO2 está instalado (onde fica o SEXO2.exe) e
   aceite substituir os arquivos. Não apague nada.
3. Abra o SEXO2. Na primeira vez o cliente do LoL fecha e abre sozinho, uma vez.

Para voltar atrás, atualize ou reinstale o SEXO2 pelo painel (Configurações > Atualizações).
Arquivos neste zip:
{files}
"""


def wanted(name: str) -> bool:
    return name == PROGRAM or name.startswith(PLUGINS)


def runtime_of(names) -> set[str]:
    return {n.lower() for n in names if RUNTIME.match(n)}


def build(base: Path, new: Path, output: Path, base_version: str = "") -> list[str]:
    """Write the overlay and return the files in it; raises ValueError when it cannot be made."""
    files = sorted(p for p in new.rglob("*") if p.is_file())
    names = {p.relative_to(new).as_posix(): p for p in files}
    with zipfile.ZipFile(base) as archive:
        known = set(archive.namelist())
        if runtime_of(known) != runtime_of(names):
            raise ValueError(
                f"Python runtime differs: release {sorted(runtime_of(known))}, build {sorted(runtime_of(names))}"
            )
        changed = []
        for name, path in names.items():
            if not wanted(name):
                continue
            if name not in known or archive.read(name) != path.read_bytes():
                changed.append(name)
    if PROGRAM not in names:
        raise ValueError(f"{PROGRAM} is not in the build")
    changed.sort()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name in changed:
            out.write(names[name], name)
        listing = "\n".join("  " + n for n in changed)
        out.writestr("LEIA-ME.txt", README.format(base=f" ({base_version})" if base_version else "", files=listing))
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-version", default="")
    args = parser.parse_args(argv)
    try:
        changed = build(args.base, args.new, args.output, args.base_version)
    except ValueError as error:
        print(f"No overlay: {error}", file=sys.stderr)
        return 2
    print(f"Overlay with {len(changed)} files: {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
