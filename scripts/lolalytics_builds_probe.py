"""Opt-in, bounded live checks for keystone-conditioned WR/Common pages."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lolalytics import Client, CollectorError, Query
from lolalytics.transport import HTTPTransport


class CountingTransport(HTTPTransport):
    def __init__(self):
        super().__init__()
        self.queries = []

    def get(self, url):
        self.queries.append(url)
        return super().get(url)


def check_collection(result):
    if [p.selection for p in result.pages] != ["win", "pick"]:
        raise CollectorError("Expected complete WR/Common pair")
    for page in result.pages:
        if page.keystone != page.resolved.get("keystone") or str(page.keystone) != page.runes["pri"][0]:
            raise CollectorError("Build and rune keystones differ")
        if page.query.get("keystone") != page.keystone or "keystone=" not in page.source_url:
            raise CollectorError("Missing filtered source provenance")
        core = next((b for b in page.blocks if b.kind == "core"), None)
        if core is None or len(core.choices) != 3 or page.core_metrics != core.metrics:
            raise CollectorError("Invalid observed core item block")
        if not all(
            page.runes.get(slot) and len(page.runes[slot]) == size
            for slot, size in [("pri", 4), ("sec", 2), ("mod", 3)]
        ):
            raise CollectorError("Incomplete rune layout")
        if not page.collected_at or not page.resolved.get("patch"):
            raise CollectorError("Missing collection provenance")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="required: up to 7 logical queries, at most 3 attempts each"
    )
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("pass --live to permit the bounded HTTP checks")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": []}
    cases = [
        Query("ahri", lane="middle"),
        Query("jinx", mode="aram", tier="all"),
        Query("ahri", lane="middle", keystone=8112),
    ]
    transport = CountingTransport()
    try:
        with Client(transport=transport, ttl=0) as client:
            for query in cases:
                start = len(transport.queries)
                result = client.collect_builds(query)
                check_collection(result)
                calls = len(transport.queries) - start
                ceiling = 1 if query.keystone is not None else 3
                if calls > ceiling:
                    raise CollectorError("Build collection exceeded its query budget")
                report["checks"].append(
                    {
                        "query": query.to_dict(),
                        "http_queries": calls,
                        "status": "passed",
                        "pages": [
                            {
                                "selection": p.selection,
                                "keystone": p.keystone,
                                "title": p.title,
                                "patch": p.resolved["patch"],
                                "source_url": p.source_url,
                                "core_ids": [c.identifier for b in p.blocks if b.kind == "core" for c in b.choices],
                                "blocks": [b.kind for b in p.blocks],
                            }
                            for p in result.pages
                        ],
                    }
                )
    except CollectorError as error:
        report["failure"] = str(error)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    report["total_http_queries"] = len(transport.queries)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
