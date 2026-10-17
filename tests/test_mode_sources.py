"""Real aggregate fixtures; no League, player data, or network required."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from lolalytics import Client, Query
from lolalytics.errors import SchemaError, QueryError, TransportError
from lolalytics.item_pages import plan_item_pages
from sexo2.sources.mayhem import MayhemClient, MayhemTransport, BASE, RARITIES, parse_pool, build_pages

DATA=Path(__file__).parent/'fixtures/modes'

def source(name):return json.loads((DATA/name).read_bytes())

class ModeSourceTests(unittest.TestCase):
    def test_swift_real_body_is_mode_summary_without_fake_keystone_filter(self):
        transport=Mock();transport.get.return_value=(DATA/'ahri-swift.json').read_bytes()
        with Client(transport=transport) as client:
            pages=client.collect_builds(Query('ahri',mode='swift')).pages
            self.assertEqual(transport.get.call_count,1)
            self.assertEqual([p.selection for p in pages],['win','pick'])
            self.assertTrue(all(p.conditioning=='mode' and p.query['mode']=='swift' and p.resolved['patch']=='16.20' for p in pages))
            self.assertTrue(all('mode_summary_unfiltered' in p.warnings for p in pages))
            self.assertNotIn('starting',[b.kind for b in pages[1].blocks])
            self.assertFalse(any(c.identifier=='0' for p in pages for b in p.blocks for c in b.choices))
            self.assertEqual(len(plan_item_pages(pages)),1)
            with self.assertRaises(QueryError):client.recommend(Query('ahri',mode='swift'))
        for kwargs in [dict(keystone=8112),dict(lane='middle'),dict(region='br'),dict(tier='gold')]:
            with self.assertRaises(QueryError):Query('ahri',mode='swift',**kwargs)

    def test_mayhem_champion_pr_is_scaled_global_fallback_and_wr_never_exposed(self):
        data=source('ahri-mayhem-silver.json');pool=parse_pool(data,103,'silver')
        first=next(r for r in data['augments'] if r['source']=='champion')
        self.assertAlmostEqual(pool.metrics[str(first['id'])]['pick_rate'],first['pickRate']*100)
        self.assertEqual(len(pool.metrics),34)
        self.assertTrue(all(r['win_rate'] is None for r in pool.metrics.values()))
        for row in data['augments']:
            if row['source']!='champion':self.assertNotIn(str(row['id']),pool.metrics)
        for field,value in [('stage',1),('rarity','gold'),('patch','changed')]:
            bad=deepcopy(data);bad[field]=value
            with self.assertRaises(SchemaError):parse_pool(bad,103,'silver')
        with self.assertRaises(SchemaError):parse_pool(data,222,'silver')
        bad=deepcopy(data);bad['augments'].append(deepcopy(bad['augments'][0]))
        with self.assertRaises(SchemaError):parse_pool(bad,103,'silver')
        for value in [float('nan'),1.01,-1,True,None]:
            bad=deepcopy(data);next(r for r in bad['augments'] if r['source']=='champion')['pickRate']=value
            with self.assertRaises(SchemaError):parse_pool(bad,103,'silver')

    def test_mayhem_items_keep_core_unordered_and_source_popularity_scoped(self):
        pages=build_pages(source('ahri-mayhem-builds.json'),103,'ahri','Ahri')
        self.assertEqual(pages[0].conditioning,'archetype')
        self.assertEqual(pages[0].runes,{})
        self.assertEqual(pages[0].core_metrics,{})
        core=next(b for b in pages[0].blocks if b.kind=='suggested_core')
        self.assertFalse(core.ordered);self.assertEqual(core.metrics,{})
        self.assertTrue(all(c.metrics=={} for c in core.choices))
        self.assertEqual(len(plan_item_pages(pages)),1)
        self.assertNotIn('win_rate',str(pages[0].core_metrics))

    def test_cache_expiry_identity_and_versions_fail_without_false_empty_success(self):
        now=[100];transport=Mock()
        bodies={BASE+f'/v1/pool?champion=103&rarity={r}':(DATA/f'ahri-mayhem-{r}.json').read_bytes() for r in RARITIES}
        transport.get.side_effect=lambda url:bodies[url]
        with tempfile.TemporaryDirectory() as tmp:
            c=MayhemClient(transport=transport,cache_dir=tmp,clock=lambda:now[0])
            result=c.pools(103);self.assertEqual(len(result.metrics),134);self.assertFalse(result.cache_hit)
            self.assertTrue(c.pools(103).cache_hit);self.assertEqual(transport.get.call_count,3)
            now[0]+=3601;self.assertFalse(c.pools(103).cache_hit);self.assertEqual(transport.get.call_count,6)
            now[0]+=3601
            bad=source('ahri-mayhem-gold.json');bad['patch']='16.19'
            bodies[BASE+'/v1/pool?champion=103&rarity=gold']=json.dumps(bad).encode()
            with self.assertRaises(SchemaError):c.pools(103)
            c.close();transport.close.assert_called_once()
        for body in [b'{',b'null',b'{"x":NaN}',b'[]']:
            transport.get.side_effect=None;transport.get.return_value=body
            with self.assertRaises(SchemaError):MayhemClient(transport=transport).pools(103)

    def test_transport_only_permits_fixed_anonymous_read_endpoints(self):
        for endpoint in ['/v1/champion?champion=103','/v1/pool?champion=222&rarity=gold']:
            MayhemTransport.validate_url(BASE+endpoint)
        for url in ['http://mayhemcache.drawyoursword.lol/v1/champion?champion=103',BASE+'/v1/all',BASE+'/v1/champion?champion=103&token=x',BASE+'/v1/pool?champion=103&rarity=gold&stage=1','https://other.invalid/v1/champion?champion=103']:
            with self.assertRaises(TransportError):MayhemTransport.validate_url(url)

if __name__=='__main__':unittest.main()
