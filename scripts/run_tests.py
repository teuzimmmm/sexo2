"""Run every Python test suite of the repository in one process.

The top-level ``tests`` folder is not a package and is discovered on its own;
package suites (``injection/tests`` and others) are discovered from the
repository root so their absolute imports resolve. A listed suite that is
missing or yields no tests fails the run instead of being skipped silently.
"""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STANDALONE_SUITES = ("tests",)
PACKAGE_SUITES = (
    "injection/tests",
    "launcher/tests",
    "lcu/tests",
    "party/tests",
    "pengu/tests",
    "threads/tests",
    "utils/tests",
)


def load_suites(loader: unittest.TestLoader) -> tuple[unittest.TestSuite, list[str]]:
    combined = unittest.TestSuite()
    problems = []
    for name in STANDALONE_SUITES + PACKAGE_SUITES:
        folder = ROOT / name
        if not folder.is_dir():
            problems.append(f"{name}: folder not found")
            continue
        top = None if name in STANDALONE_SUITES else str(ROOT)
        suite = loader.discover(str(folder), top_level_dir=top)
        count = suite.countTestCases()
        if count == 0:
            problems.append(f"{name}: no tests discovered")
        print(f"{name}: {count} tests", flush=True)
        combined.addTest(suite)
    return combined, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-q", "--quiet", action="store_true", help="minimal output")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    suite, problems = load_suites(unittest.TestLoader())
    print(f"total: {suite.countTestCases()} tests", flush=True)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)

    result = unittest.TextTestRunner(verbosity=0 if args.quiet else 1).run(suite)
    return 0 if result.wasSuccessful() and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
