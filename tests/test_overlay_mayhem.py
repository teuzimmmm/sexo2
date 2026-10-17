import json
import threading
import time
import unittest
from unittest.mock import Mock
from sexo2.sources.mayhem import MayhemClient
from sexo2.overlay.mayhem import MayhemFeed
from sexo2.overlay.offers import Choice, Offer, offer_view
from sexo2.overlay.screen import offer_band, title_rects
from tests.test_mode_sources import DATA

class MayhemOverlayTests(unittest.TestCase):
    def setUp(self):
        self.transport=Mock()
        self.transport.get.side_effect=lambda url:(DATA/('ahri-mayhem-'+url.rsplit('=',1)[1]+'.json')).read_bytes()
        self.client=MayhemClient(transport=self.transport)
        self.feed=MayhemFeed(client_factory=lambda:self.client)
        self.addCleanup(self.feed.close)
        data=json.loads((DATA/'ahri-mayhem-silver.json').read_bytes())
        rows=[r for r in data['augments'] if r['source']=='champion']
        self.choices=tuple(Choice(str(r['id']),r['name']) for r in rows[:3])
        self.offer=Offer(('match',103,'mayhem'),1,1,self.choices)

    def wait(self):
        deadline=time.monotonic()+3
        while self.feed._busy and time.monotonic()<deadline:time.sleep(.005)
        self.assertFalse(self.feed._busy)

    def test_confirmed_champion_pools_only_current_ids_and_three_metric_strips(self):
        self.feed.ensure('match',103);self.wait()
        view=self.feed.offered_view('match',103,self.offer,positioned=True)
        self.assertEqual(len(view.cards),3)
        self.assertEqual([r.title for r in view.cards],[c.name for c in self.choices])
        self.assertIn('aramkit',str(view));self.assertIn('16.20',str(view))
        self.assertNotIn('win_rate',str(view));self.assertNotIn('WR',str(view))
        for i,card in enumerate(view.cards):
            self.assertIn(str(self.feed._metrics[self.choices[i].identifier]['pick_rate']),card.lines[0])
        for _ in range(5):self.feed.ensure('match',103)
        self.assertEqual(self.transport.get.call_count,3)
        wrong=Offer(('match',103,'arena'),1,1,self.choices)
        self.assertFalse(self.feed.offered_view('match',103,wrong).cards)

    def test_failure_and_late_response_never_publish_other_context_metrics(self):
        entered,release=threading.Event(),threading.Event();original=self.client.pools
        def slow(cid):entered.set();release.wait(2);return original(cid)
        self.client.pools=slow
        try:
            self.feed.ensure('match',103);self.assertTrue(entered.wait(1))
            self.feed.clear();release.set();self.wait()
            self.assertFalse(self.feed.offered_view('match',103,self.offer).cards)
            self.feed.close()
            self.feed.ensure('match',103);self.assertFalse(self.feed._busy)
        finally:release.set()

    def test_region_geometry_stays_outside_ocr_and_separates_all_three_options(self):
        for w,h in [(1024,768),(1280,720),(1920,1080),(3440,1440),(3840,2160)]:
            (x,y,width,height),regions=offer_band(w,h)
            self.assertEqual(len(regions),3)
            self.assertTrue(x>=0 and y>=0 and x+width<=w and y+height<=h)
            for i,(rx,rw) in enumerate(regions):
                tx,ty,tw,th=title_rects(w,h)[i]
                self.assertEqual(x+rx,tx);self.assertEqual(rw,tw);self.assertGreater(y,ty+th)
                if i:self.assertGreater(rx,regions[i-1][0]+regions[i-1][1])
        view=offer_view('match',self.offer,{'999999':{'pick_rate':99.765,'games':999999}},positioned=True)
        self.assertNotIn('99.765',str(view));self.assertEqual(len(view.cards),3)

if __name__=='__main__':unittest.main()
