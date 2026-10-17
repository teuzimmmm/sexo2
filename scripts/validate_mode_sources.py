"""Explicit one-champion live smoke. No League, credentials, or full dataset.

python scripts/validate_mode_sources.py --champion jinx --champion-id 222
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lolalytics import Client, Query
from sexo2.sources.mayhem import MayhemClient
from lolalytics.transport import HTTPTransport


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--champion',required=True)
    parser.add_argument('--champion-id',type=int,required=True)
    parser.add_argument('--modes',nargs='+',choices=['swift','arena','mayhem'],default=['swift','arena','mayhem'])
    parser.add_argument('--fixtures-dir',type=Path)
    args=parser.parse_args()
    class Capture(HTTPTransport):
        def get(self,url):
            body=super().get(url)
            if args.fixtures_dir is not None and '/swift/' in url:
                args.fixtures_dir.mkdir(parents=True,exist_ok=True)
                (args.fixtures_dir/(args.champion+'-swift.json')).write_bytes(body)
            return body
    report={'champion':args.champion,'champion_id':args.champion_id}
    with Client(transport=Capture()) as client:
        if 'swift' in args.modes:
            pages=client.collect_builds(Query(args.champion,mode='swift')).pages
            if not pages or any(p.resolved.get('cid')!=args.champion_id for p in pages):
                raise ValueError('Champion identity mismatch')
            report['swift']={'patch':pages[0].resolved['patch'],'conditioning':pages[0].conditioning,
                             'blocks':[len(p.blocks) for p in pages],
                             'source_url':pages[0].source_url}
        if 'arena' in args.modes:
            arena=client.recommend(Query(args.champion,mode='arena'))
            rows=next((v for k,v in arena.item_rankings.items() if k.startswith('augment_statistics:') and k.endswith(':payload.augment.augment0')),[])
            if not rows:raise ValueError('Arena augment table unavailable')
            report['arena']={'patch':arena.resolved['patch'],'augments':len(rows),
                             'metrics':'pick_rate/games only','source_url':Query(args.champion,mode='arena').url}
    mayhem=MayhemClient()
    try:
        if 'mayhem' not in args.modes:
            print(json.dumps(report,ensure_ascii=False,indent=2));return
        pools=mayhem.pools(args.champion_id)
        pages=mayhem.builds(args.champion_id,args.champion,args.champion)
        report['mayhem']={'patch':pools.patch,'data_date':pools.data_date,
            'champion_popularity_rows':len(pools.metrics),'item_pages':len(pages),
            'source_url':pages[0].source_url,'core_order':'unconfirmed'}
    finally:mayhem.close()
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
