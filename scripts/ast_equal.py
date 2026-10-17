"""Prove a commit only reformatted Python: every changed file parses to the same AST.

Usage:
    python scripts/ast_equal.py [BASE [HEAD]]   (defaults: HEAD~1 HEAD)

Positions, comments and formatting are ignored, and so is whitespace inside
docstrings (the formatter strips trailing spaces there; only ``__doc__`` sees it).
Any change to names, literals, docstring text or structure is reported and the
exit code is 1.
"""

from __future__ import annotations

import ast
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout


def source(rev: str, path: str) -> str:
    return git("show", f"{rev}:{path}")


def _normalize_docstrings(node: ast.AST) -> None:
    for owner in ast.walk(node):
        if not isinstance(owner, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = owner.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            value = body[0].value.value
            if isinstance(value, str):
                lines = [line.strip() for line in value.strip().splitlines()]
                body[0].value.value = "\n".join(line for line in lines if line)


def tree(text: str) -> str:
    parsed = ast.parse(text)
    _normalize_docstrings(parsed)
    return ast.dump(parsed, include_attributes=False)


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
