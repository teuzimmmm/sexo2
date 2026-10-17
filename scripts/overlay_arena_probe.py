"""Limited real-source check; writes only public popularity metadata, no raw WR."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lolalytics import Client, Query
from sexo2.overlay.arena import cards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--champion', default='jinx')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with Client(ttl=0) as client:
        recommendation = client.recommend(Query(args.champion, mode='arena'))
    views = cards(recommendation, recommendation.resolved['champion_name'], {})
    groups = recommendation.item_rankings
    augment = [row for key, rows in groups.items() if key.endswith(':payload.augment.augment0') for row in rows]
    assert all(row['metrics'].get('win_rate') is None for rows in groups.values() for row in rows)
    report = {'source': recommendation.source_url, 'resolved': recommendation.resolved,
              'collected_at': recommendation.collected_at, 'card_count': len(views),
              'groups': {key: len(rows) for key, rows in groups.items()},
              'sample_augments': [{'ids': row['identifiers'], 'pick_rate': row['metrics'].get('pick_rate'),
                                   'games': row['metrics'].get('games')} for row in augment[:3]],
              'restricted_win_rates': 'suppressed', 'native_game_validation': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cards': len(views), 'augment_rows': len(augment), 'patch': recommendation.resolved['patch'],
                      'restricted_win_rates': 'suppressed'}))


if __name__ == '__main__':
    main()
