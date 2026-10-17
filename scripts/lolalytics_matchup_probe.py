"""Opt-in live integration checks for keystone builds plus opponent suggestions."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lolalytics import Client, CollectorError, Query, QueryError, plan_item_pages
from lolalytics.transport import HTTPTransport


class CountingHTTPTransport(HTTPTransport):
    """Count logical GET calls while retaining HTTPTransport pacing/retries."""

    def __init__(self):
        super().__init__(attempts=3)
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return super().get(url)


def _require(condition, message):
    if not condition:
        raise CollectorError(message)


def _build_summary(page):
    return {
        "selection": page.selection,
        "title": page.title,
        "patch": page.resolved.get("patch"),
        "block_count": len(page.blocks),
        "warnings": list(page.warnings),
        "source_url": page.source_url,
    }


def _matchup_summary(page):
    return {
        "selection": page.selection,
        "conditioning": page.conditioning,
        "opponent": page.query.get("opponent"),
        "title": page.title,
        "patch": page.resolved.get("patch"),
        "rune_count": sum(len(page.runes.get(slot, [])) for slot in ("pri", "sec", "mod")),
        "block_count": len(page.blocks),
        "core_metrics_available": any(value is not None for value in page.core_metrics.values()),
        "cache_hit": page.cache_hit,
        "warnings": list(page.warnings),
        "source_url": page.source_url,
    }


def _fingerprint(page):
    value = page.to_dict()
    value.pop("cache_hit", None)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def run_live():
    transport = CountingHTTPTransport()
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "logical_query_budget": 5,
        "max_http_attempts_per_get": 3,
        "checks": {},
    }
    try:
        with Client(transport=transport, ttl=900) as client:
            general_query = Query("ahri", lane="middle")
            before = len(transport.urls)
            collection = client.collect_builds(general_query)
            general_calls = len(transport.urls) - before
            _require(
                [page.selection for page in collection.pages] == ["win", "pick"],
                "expected complete WR and Common build pages",
            )
            _require(1 <= general_calls <= 3, "WR/Common collection exceeded its three-query budget")
            for page in collection.pages:
                core = next((block for block in page.blocks if block.kind == "core"), None)
                _require(
                    core is not None and len(core.choices) == 3, "a WR/Common page has no observed three-item core"
                )
                _require(page.core_metrics == core.metrics, "WR/Common core metrics are inconsistent")
                _require(
                    page.keystone == page.resolved.get("keystone"),
                    "WR/Common page keystone does not match resolved navigation",
                )
            patch = collection.pages[0].resolved.get("patch")
            _require(isinstance(patch, str) and patch, "WR/Common collection did not resolve a patch")
            report["checks"]["general"] = {
                "query": general_query.to_dict(),
                "patch": patch,
                "logical_queries": general_calls,
                "pages": [_build_summary(page) for page in collection.pages],
            }

            def collect_target(opponent):
                query = Query("ahri", patch=patch, lane="middle", opponent=opponent, opponent_lane="middle")
                before_count = len(transport.urls)
                page = client.collect_matchup(query)
                calls = len(transport.urls) - before_count
                _require(calls == 1, "an uncached matchup must issue exactly one logical query")
                _require(
                    page.selection == "vs" and page.conditioning == "opponent",
                    "matchup suggestion has the wrong conditioning",
                )
                _require(
                    page.query.get("opponent") == opponent and page.resolved.get("opponent") == opponent,
                    "matchup response resolved the wrong opponent",
                )
                _require(
                    page.query.get("keystone") is None and page.resolved.get("keystone") is None,
                    "matchup response unexpectedly has a keystone filter",
                )
                _require(
                    sum(len(page.runes.get(slot, [])) for slot in ("pri", "sec", "mod")) == 9,
                    "matchup rune suggestion is incomplete",
                )
                _require(
                    page.core_metrics == {"win_rate": None, "games": None},
                    "matchup page must not claim core build metrics",
                )
                _require(
                    not any(block.kind == "core" for block in page.blocks), "matchup page inferred a core item set"
                )
                _require(page.resolved.get("patch") == patch, "matchup response patch differs from WR/Common patch")
                return query, page, calls

            annie_query, annie_page, annie_calls = collect_target("annie")
            annie_original = _fingerprint(annie_page)
            ryze_query, ryze_page, ryze_calls = collect_target("ryze")
            _require(
                _fingerprint(annie_page) == annie_original, "collecting a second opponent mutated the Annie result"
            )

            before_repeat = len(transport.urls)
            annie_again = client.collect_matchup(annie_query)
            repeat_calls = len(transport.urls) - before_repeat
            _require(
                repeat_calls == 0 and annie_again.cache_hit, "repeated Annie matchup did not reuse the cached response"
            )
            _require(annie_again.query.get("opponent") == "annie", "cached Annie result lost its target identity")
            _require(_fingerprint(annie_again) == annie_original, "cached Annie result differs from its first result")

            suggestions = [*collection.pages, annie_page, ryze_page]
            three_suggestions = [*collection.pages, annie_page]
            three_plan = plan_item_pages(three_suggestions, max_pages=1, max_blocks_per_page=20)
            three_blocks = sum(len(item_page.blocks) for item_page in three_plan)
            _require(
                len(three_suggestions) == 3 and three_blocks == 17, "WR, Common and Annie should produce 17 item blocks"
            )
            overflow_rejected = False
            try:
                plan_item_pages(suggestions, max_pages=1, max_blocks_per_page=20)
            except QueryError:
                overflow_rejected = True
            _require(overflow_rejected, "24 suggestions blocks should exceed a single 20-block page")
            packed = plan_item_pages(suggestions, max_pages=2, max_blocks_per_page=20)
            packed_blocks = sum(len(item_page.blocks) for item_page in packed)
            _require(
                len(suggestions) == 4 and packed_blocks == 24 and len(packed) == 2,
                "WR, Common, Annie and Ryze should preserve all 24 blocks across two pages",
            )

            total_calls = len(transport.urls)
            _require(total_calls <= 5, "integration scenario exceeded its five-query logical budget")
            report["checks"]["matchups"] = {
                "queries": [annie_query.to_dict(), ryze_query.to_dict()],
                "logical_queries": annie_calls + ryze_calls,
                "pages": [_matchup_summary(annie_page), _matchup_summary(ryze_page)],
                "annie_repeat": {
                    "cache_hit": annie_again.cache_hit,
                    "logical_queries": repeat_calls,
                    "opponent": annie_again.query.get("opponent"),
                },
            }
            report["checks"]["item_pages"] = {
                "three_suggestions": len(three_suggestions),
                "three_suggestion_blocks": three_blocks,
                "single_page_overflow_rejected": overflow_rejected,
                "four_suggestions": len(suggestions),
                "four_suggestion_blocks": packed_blocks,
                "packed_pages": len(packed),
                "packed_block_counts": [len(item_page.blocks) for item_page in packed],
            }
            report["logical_queries"] = total_calls
            report["status"] = "passed"
    except CollectorError as error:
        report["logical_queries"] = len(transport.urls)
        report["status"] = "failed"
        report["failure"] = str(error)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="required: up to five logical q-data queries, at most three HTTP attempts per query",
    )
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("pass --live to permit the bounded HTTP integration checks")
    return run_live()


if __name__ == "__main__":
    raise SystemExit(main())
