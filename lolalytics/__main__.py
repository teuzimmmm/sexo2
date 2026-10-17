"""Run with python -m lolalytics; JSON per champion allows resumable batches."""
import argparse
import json
import sys

from .client import Client
from .errors import CollectorError
from .query import LANES, MODES, REGIONS, TIERS, Query
from .risk import RISK_LEVELS


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
    parser.add_argument("--keystone", type=int, help="filter by a primary rune ID")
    parser.add_argument("--builds", action="store_true", help="collect win/common builds (Swiftplay: unfiltered mode summaries)")
    parser.add_argument("--opponent", help="explicit opponent champion slug for matchup data")
    parser.add_argument("--opponent-lane", choices=LANES, default="all")
    parser.add_argument("--matchup", action="store_true", help="collect one opponent-conditioned build page")
    parser.add_argument("--recommend", action="store_true", help="rank one local risk-adjusted recommendation")
    parser.add_argument("--risk-level", choices=RISK_LEVELS, help="local recommendation prior strength (requires --recommend)")
    parser.add_argument("--min-games", type=int, default=100, help="warn on item samples below this count (0 disables the low-sample threshold)")
    args = parser.parse_args(argv)
    try:
        if len(args.champions) > 20:
            parser.error("at most 20 explicit champions per batch")
        if args.builds and args.item_sets:
            parser.error("--builds and --item-sets are incompatible")
        if args.builds and args.mode == "arena":
            parser.error("--builds supports ranked, ARAM and Swiftplay")
        if args.item_sets and args.keystone is not None:
            parser.error("--item-sets does not support --keystone")
        if args.matchup and not args.opponent:
            parser.error("--matchup requires --opponent")
        if args.risk_level is not None and not args.recommend:
            parser.error("--risk-level requires --recommend")
        if args.recommend and (args.builds or args.item_sets or args.matchup):
            parser.error("--recommend is incompatible with --builds, --item-sets, and --matchup")
        if args.opponent and args.builds:
            parser.error("--builds and --opponent are incompatible")
        if args.opponent and args.item_sets:
            parser.error("--item-sets and --opponent are incompatible")
        if args.min_games < 0:
            parser.error("--min-games must be non-negative")
        queries = [Query(champion, mode=args.mode, patch=args.patch, lane=args.lane,
                         tier=args.tier, region=args.region, keystone=args.keystone,
                         opponent=args.opponent, opponent_lane=args.opponent_lane) for champion in args.champions]
        if args.item_sets and args.mode != "ranked":
            parser.error("--item-sets currently supports ranked only")
        with Client(cache_dir=args.cache_dir, ttl=args.ttl) as client:
            for query in queries:
                if args.recommend:
                    result = client.recommend(query, risk_level=args.risk_level or "medium").to_dict()
                elif args.matchup:
                    result = client.collect_matchup(query, min_games=args.min_games).to_dict()
                elif args.builds:
                    result = client.collect_builds(query).to_dict()
                else:
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
