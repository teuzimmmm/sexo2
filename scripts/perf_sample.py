"""Sample memory and CPU of SEXO2 and the League client into a CSV.

Usage (Windows, while the scenario runs):
    python scripts/perf_sample.py record --seconds 600 --out lobby-1.csv
    python scripts/perf_sample.py summary lobby-1.csv lobby-2.csv lobby-3.csv

``record`` samples once per second. Each process is attributed to a group:
``sexo2`` (SEXO2.exe and every descendant: mod-tools, patcher, cloudflared),
``client`` (LeagueClient/LeagueClientUx/LeagueClientUxRender, where the Pengu
plugins run) and ``game``. ``summary`` adds the processes of each group per
sample, reports mean and p95 per file, and the spread between files, which is
the noise any before/after comparison must exceed.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import psutil

GROUP_ROOTS = {
    "sexo2": {"sexo2.exe"},
    "client": {"leagueclient.exe", "leagueclientux.exe", "leagueclientuxrender.exe"},
    "game": {"league of legends.exe"},
}
FIELDS = ("elapsed_s", "group", "pid", "name", "rss_mb", "uss_mb", "cpu_pct", "threads", "handles")
METRICS = ("rss_mb", "uss_mb", "cpu_pct", "threads", "handles")


def group_processes() -> dict[int, tuple[str, psutil.Process]]:
    """Map pid to (group, process); descendants of SEXO2 count as sexo2."""
    found = {}
    for proc in psutil.process_iter(["name"]):
        name = (proc.info["name"] or "").lower()
        for group, roots in GROUP_ROOTS.items():
            if name in roots:
                found[proc.pid] = (group, proc)
                if group == "sexo2":
                    try:
                        for child in proc.children(recursive=True):
                            found.setdefault(child.pid, ("sexo2", child))
                    except psutil.Error:
                        pass
    return found


def sample(proc: psutil.Process) -> dict[str, float] | None:
    try:
        with proc.oneshot():
            rss = proc.memory_info().rss
            try:
                uss = proc.memory_full_info().uss
            except psutil.AccessDenied:
                uss = float("nan")
            handles = proc.num_handles() if hasattr(proc, "num_handles") else 0
            return {
                "name": proc.name(),
                "rss_mb": rss / 2**20,
                "uss_mb": uss / 2**20,
                "cpu_pct": proc.cpu_percent(None),
                "threads": proc.num_threads(),
                "handles": handles,
            }
    except psutil.Error:
        return None


def record(seconds: float, out: Path) -> int:
    tracked: dict[int, psutil.Process] = {}
    start = time.monotonic()
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        while (elapsed := time.monotonic() - start) < seconds:
            for pid, (group, proc) in group_processes().items():
                if pid not in tracked:
                    tracked[pid] = proc
                    proc.cpu_percent(None)  # first call only primes the counter
                    continue
                row = sample(tracked[pid])
                if row:
                    writer.writerow({"elapsed_s": f"{elapsed:.1f}", "group": group, "pid": pid, **row})
            stream.flush()
            time.sleep(max(0.0, 1.0 - (time.monotonic() - start - elapsed)))
    print(f"wrote {out}")
    return 0


def per_sample_totals(path: Path) -> dict[str, dict[str, list[float]]]:
    """Group -> metric -> list of per-sample totals across that group's processes."""
    buckets: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    with path.open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            totals = buckets[(row["group"], row["elapsed_s"])]
            for metric in METRICS:
                totals[metric] += float(row[metric])
    series: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (group, _), totals in buckets.items():
        for metric, value in totals.items():
            series[group][metric].append(value)
    return series


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]


def summary(paths: list[Path]) -> int:
    runs = {path.name: per_sample_totals(path) for path in paths}
    groups = sorted({group for series in runs.values() for group in series})
    for group in groups:
        print(f"\n[{group}]")
        for metric in METRICS:
            means = []
            for name, series in runs.items():
                values = [v for v in series.get(group, {}).get(metric, []) if v == v]  # drop NaN
                if values:
                    means.append(statistics.fmean(values))
                    print(f"  {metric:8} {name}: mean {statistics.fmean(values):9.2f}  p95 {p95(values):9.2f}")
            if len(means) > 1:
                print(f"  {metric:8} spread between runs (max-min of means): {max(means) - min(means):.2f}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    rec = commands.add_parser("record", help="sample once per second into a CSV")
    rec.add_argument("--seconds", type=float, required=True)
    rec.add_argument("--out", type=Path, required=True)
    summ = commands.add_parser("summary", help="summarize one or more CSV runs")
    summ.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args()
    if args.command == "record":
        return record(args.seconds, args.out)
    return summary(args.files)


if __name__ == "__main__":
    sys.exit(main())
