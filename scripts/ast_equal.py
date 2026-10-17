"""Prove a commit only reformatted Python: every changed file parses to the same AST.

Usage:
    python scripts/ast_equal.py [BASE [HEAD]]   (defaults: HEAD~1 HEAD)

Positions, comments and formatting are ignored; any change to names, literals,
docstrings or structure is reported and the exit code is 1.
"""

from __future__ import annotations

import ast
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout


def source(rev: str, path: str) -> str:
    return git("show", f"{rev}:{path}")


def tree(text: str) -> str:
    return ast.dump(ast.parse(text), include_attributes=False)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    changed = git("diff", "--name-status", "--no-renames", base, head).splitlines()
    differing = []
    checked = 0
    for line in changed:
        status, path = line.split("\t", 1)
        if not path.endswith(".py"):
            continue
        if status != "M":
            differing.append(f"{status} {path} (added or removed, not a reformat)")
            continue
        checked += 1
        if tree(source(base, path)) != tree(source(head, path)):
            differing.append(f"M {path}")
    print(f"{checked} Python files compared between {base} and {head}")
    for entry in differing:
        print(f"AST differs: {entry}")
    return 1 if differing else 0


if __name__ == "__main__":
    sys.exit(main())
