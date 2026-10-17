"""Explicit, limited live integration checks. Offline unittest never invokes this."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

# Executable from a checkout without installing SEXO2 or importing its runtime.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lolalytics import Client, CollectorError, Query


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="required: allow 8 public queries, at most 3 attempts each")
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("pass --live to run the bounded integration checks")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": []}
    try:
        with Client(ttl=0) as client:
            for mode in ("ranked", "aram", "arena"):
                for champion in ("ahri", "jinx"):
                    query = Query(champion, mode=mode)
                    snapshot = client.collect(query)
                    if snapshot.overview["games"] <= 0 or snapshot.stale:
                        raise CollectorError("live check: expected fresh nonempty champion statistics")
                    combos = [r for r in snapshot.records if r.category == "item_combination"]
                    if not combos:
                        raise CollectorError("live check: missing observed item combinations")
                    if mode == "arena":
                        cards = [r for r in snapshot.records if r.category == "augment_statistics"]
                        if not cards or not any(r.metrics["pick_rate"] is not None for r in cards):
                            raise CollectorError("live check: missing augment pick rates")
                        if any(r.metrics["win_rate"] is not None for r in snapshot.records):
                            raise CollectorError("live check: Arena item/augment win rate was not suppressed")
                    elif not any(r.category == "rune_suggestion" for r in snapshot.records):
                        raise CollectorError("live check: missing rune layouts")
                    report["checks"].append(
                        {
                            "query": query.to_dict(),
                            "resolved": snapshot.resolved,
                            "source_url": snapshot.source_url,
                            "records": len(snapshot.records),
                            "categories": sorted({r.category for r in snapshot.records}),
                            "status": "passed",
                        }
                    )
            # Separate historical patch/filter check, never infer it from the current patch.
            old = client.collect(Query("ahri", patch="16.19", lane="middle", tier="gold", region="br"))
            report["checks"].append(
                {"query": old.query, "resolved": old.resolved, "source_url": old.source_url, "status": "passed"}
            )
        # Lazy source is independent. One request; inspect only schema, not a ranking.
        from lolalytics.transport import HTTPTransport

        url = (
            "https://a1.lolalytics.com/mega/?ep=build-itemset&v=1&patch=16.20&c=ahri"
            "&lane=all&tier=emerald_plus&queue=ranked&region=all"
        )
        with HTTPTransport() as transport:
            extra = json.loads(transport.get(url))
        if not isinstance(extra.get("itemSets"), dict) or extra.get("response", {}).get("valid") is not True:
            raise CollectorError("live check: lazy itemSets schema changed")
        report["checks"].append({"source_url": url, "tables": sorted(extra["itemSets"]), "status": "passed"})
    except (CollectorError, ValueError, TypeError, KeyError) as error:
        report["failure"] = str(error) if isinstance(error, CollectorError) else "live check: malformed response"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
