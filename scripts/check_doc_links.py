"""Verifica se os links relativos e as referências `docs/...` dos Markdown existem.

Uso: python scripts/check_doc_links.py
Sai com código 1 e lista cada link quebrado.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", ".claude", "release-secrets"}
LINK = re.compile(r"\]\(([^)\s]+)\)")
CODE_REF = re.compile(r"`((?:docs|design)/[\w./-]+\.(?:md|html|json))`")


def markdown_files():
    for path in ROOT.rglob("*.md"):
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            yield path


def broken_links(path):
    text = path.read_text(encoding="utf-8")
    for match in LINK.finditer(text):
        target = match.group(1).split("#")[0]
        if not target or re.match(r"[a-zA-Z][\w+.-]*:", target):
            continue
        if not (path.parent / target).exists():
            yield target
    for match in CODE_REF.finditer(text):
        if not (ROOT / match.group(1)).exists():
            yield match.group(1)


def main():
    failures = 0
    for path in sorted(markdown_files()):
        for target in broken_links(path):
            print(f"{path.relative_to(ROOT).as_posix()}: {target}")
            failures += 1
    print(f"{failures} link(s) quebrado(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
