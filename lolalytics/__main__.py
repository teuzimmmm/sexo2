"""Run with python -m lolalytics; JSON per champion allows resumable batches."""
import argparse
import json
import sys

from .client import Client
from .errors import CollectorError
from .query import LANES, MODES, REGIONS, TIERS, Query


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Unofficial LoLalytics collector; one JSON object per champion")
    parser.add_argument("champions", nargs="+", help="1–20 explicit lowercase LoLalytics slugs")
    parser.add_argument("--mode", choices=MODES, default="ranked")
    parser.add_argument("--patch", help="explicit patch, e.g. 16.20; default resolves current upstream patch")
    parser.add_argument("--lane", choices=LANES, default="all")
    parser.add_argument("--tier", choices=TIERS, default="emerald_plus")
    parser.add_argument("--region", choices=REGIONS, default="all")
    parser.add_argument("--cache-dir", help="optional private directory for a resumable disk cache")
    parser.add_argument("--ttl", type=float, default=900, help="cache lifetime in seconds, 0–86400 (default 900)")
    parser.add_argument("--item-sets", action="store_true", help="also fetch reproduced ranked lazy item sets; preserve raw counters")
    args = parser.parse_args(argv)
    try:
        if len(args.champions) > 20:
            parser.error("at most 20 explicit champions per batch")
        queries = [Query(champion, mode=args.mode, patch=args.patch, lane=args.lane,
                         tier=args.tier, region=args.region) for champion in args.champions]
        if args.item_sets and args.mode != "ranked":
            parser.error("--item-sets currently supports ranked only")
        with Client(cache_dir=args.cache_dir, ttl=args.ttl) as client:
            for query in queries:
                result = client.collect(query).to_dict()
                if args.item_sets:
                    result["lazy_item_sets"] = client.collect_item_sets(query)
                print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
    except CollectorError as error:
        print(f"lolalytics: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("lolalytics: unable to access the configured cache or output", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
