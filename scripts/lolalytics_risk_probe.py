"""Opt-in live checks: four contexts, two risk levels, at most eight source GETs."""

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


def check(result):
    if result.resolved["patch"] != result.item_source["resolved"]["patch"]:
        raise CollectorError("Recommendation mixed patches")
    if result.query["mode"] == "arena":
        if result.build_page is not None or result.policy["method"] != "pick_rate":
            raise CollectorError("Arena must use popularity without a rune build")
        for rows in result.item_rankings.values():
            for row in rows:
                if row["metrics"]["win_rate"] is not None or row["risk"]["score"] is not None:
                    raise CollectorError("Arena exposed an item or augment WR score")
    else:
        page = result.build_page
        if page is None or not all(len(page.runes[s]) == n for s, n in [("pri", 4), ("sec", 2), ("mod", 3)]):
            raise CollectorError("Recommendation has no complete rune layout")
        if str(page.keystone) != page.runes["pri"][0]:
            raise CollectorError("Primary rune differs from selected keystone")
        winner = result.rune_candidates[0]
        if winner["risk"]["score"] is None or winner["selection"] != result.recommended_selection:
            raise CollectorError("Recommendation did not select a scored candidate")
        if winner["keystone"] != page.keystone:
            raise CollectorError("Build differs from selected primary rune")
        if result.query["opponent"] is not None:
            if page.conditioning != "opponent" or "keystone=" in page.source_url:
                raise CollectorError("Matchup added an unconfirmed keystone filter")
        elif page.query["keystone"] != page.keystone:
            raise CollectorError("General build lacks its keystone condition")
    if not result.item_rankings:
        raise CollectorError("No observed item/augment tables to validate")


def sample(result):
    first_group = next(iter(result.item_rankings))
    return {
        "risk_level": result.risk_level,
        "recommended_selection": result.recommended_selection,
        "keystone": result.build_page.keystone if result.build_page else None,
        "patch": result.resolved["patch"],
        "cache_hit": result.cache_hit,
        "source_url": result.source_url,
        "item_source": result.item_source,
        "policy": result.policy,
        "warnings": result.warnings,
        "rune_candidates": [
            {key: row[key] for key in ("selection", "keystone", "metrics", "metric_scope", "source_url", "risk")}
            for row in result.rune_candidates
        ],
        "item_table_count": len(result.item_rankings),
        "sample_table": first_group,
        "sample_rows": [
            {key: row[key] for key in ("identifiers", "metrics", "metric_scope", "source_path", "risk")}
            for row in result.item_rankings[first_group][:3]
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="required; each source GET has at most three HTTP attempts")
    parser.add_argument("--output", type=Path, help="optional sanitized JSON report destination")
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("pass --live to permit the bounded HTTP checks")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": []}
    cases = [
        Query("ahri", lane="middle"),
        Query("jinx", mode="aram", tier="all"),
        Query("ahri", lane="middle", opponent="annie", opponent_lane="middle"),
        Query("jinx", mode="arena", tier="all"),
    ]
    transport = CountingTransport()
    status = 0
    try:
        with Client(transport=transport) as client:
            for query in cases:
                start = len(transport.queries)
                rows = []
                for level in ("very-low", "very-high"):
                    result = client.recommend(query, risk_level=level)
                    check(result)
                    rows.append(sample(result))
                before_repeat = len(transport.queries)
                repeated = client.recommend(query, risk_level="very-low")
                check(repeated)
                if not repeated.cache_hit or before_repeat != len(transport.queries):
                    raise CollectorError("Warm source queries were not reused")
                calls = len(transport.queries) - start
                ceiling = 1 if query.opponent or query.mode == "arena" else 3
                if calls > ceiling:
                    raise CollectorError("Recommendation exceeded its source query budget")
                report["checks"].append(
                    {
                        "query": query.to_dict(),
                        "status": "passed",
                        "http_queries": calls,
                        "warm_repeat_reused": True,
                        "levels": rows,
                    }
                )
        if len(transport.queries) > 8 or len(set(transport.queries)) != len(transport.queries):
            raise CollectorError("Live probe repeated an identical source GET or exceeded its budget")
    except CollectorError as error:
        report["failure"] = str(error)
        status = 1
    report["total_source_gets"] = len(transport.queries)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
