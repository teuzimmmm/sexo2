"""Real child-process failures and display protocol, without game or desktop."""
import json
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock,patch
from sexo2.overlay.display import Frame
from sexo2.overlay.model import Card,View
from sexo2.overlay.worker_wire import Inbox,encode,decode,ProtocolError
from sexo2.overlay.isolated import IsolatedOverlay
from sexo2.overlay.readiness import GameReadiness


def sample(active=True):return Frame(active,View('a'*24,(Card('Inventário',('Itens observados: 1000 G',)),)))

class ProtocolTests(unittest.TestCase):
    def test_roundtrip_omits_private_context_and_expires_without_renewal(self):
        clock=[0.0];inbox=Inbox(clock=lambda:clock[0]);frame=sample()
        raw=encode(frame,1,2);self.assertNotIn(b'a'*24,raw)
        inbox.accept(raw);self.assertTrue(inbox.frame().active)
        clock[0]=2;self.assertFalse(inbox.frame().active)
        inbox.accept(encode(Frame(),2,2));self.assertFalse(inbox.frame().active)
        inbox.close();self.assertFalse(inbox.frame().active)

    def test_invalid_or_out_of_order_message_closes_inbox_immediately(self):
        for raw in [b'{}\n',b'null\n',b'{',b'x'*(256*1024+1),encode(sample(),1,0)]:
            inbox=Inbox();inbox.accept(encode(sample(),1,0))
            with self.assertRaises(ProtocolError):inbox.accept(raw)
            self.assertFalse(inbox.frame().active)
        data=json.loads(encode(sample(),1,0));data['account']='forbidden'
        with self.assertRaises(ProtocolError):decode((json.dumps(data)+'\n').encode())
        with self.assertRaises(ProtocolError):encode(Frame(True,View('',(Card('x',('y',)),)),offer_layout=True),1,0)

class ReadinessTests(unittest.TestCase):
    def test_zero_time_timeout_clock_reset_and_expiration_do_not_activate(self):
        clock=[0.0];client=Mock();gate=GameReadiness(client=client,clock=lambda:clock[0])
        for value in [0,None,True,float('inf')]:
            client.get.return_value={'gameTime':value};self.assertFalse(gate.check('match'))
        client.get.return_value={'gameTime':1};self.assertTrue(gate.check('match'))
        clock[0]=3;self.assertFalse(gate.fresh())
        client.get.return_value={'gameTime':.5};self.assertFalse(gate.check('match'))
        client.get.return_value={'gameTime':5};self.assertFalse(gate.check('match'))
        self.assertTrue(gate.check('new-match'))
        client.get.side_effect=OSError('synthetic timeout');self.assertFalse(gate.check('match'))
        gate.close();client.close.assert_called_once()

class ChildTests(unittest.TestCase):
    def until(self,fn):
        end=time.monotonic()+3
        while not fn() and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(fn())

    def test_inactive_does_not_spawn_and_disabling_kills_only_own_child(self):
        current=[Frame()];spawner=Mock(wraps=subprocess.Popen)
        renderer=IsolatedOverlay(lambda:current[0],command=[sys.executable,'-c','import time; time.sleep(30)'],popen=spawner)
        self.addCleanup(renderer.stop)
        renderer.tick();spawner.assert_not_called()
        current[0]=sample();renderer.tick();child=renderer._child
        self.assertIsNotNone(child)
        self.until(renderer._write_done.is_set)
        current[0]=Frame();renderer.tick();self.assertIsNotNone(child.poll())
        self.assertIsNone(renderer._child)

    def test_exited_child_retries_twice_per_match_without_restart_loop(self):
        clock=[0.0]
        renderer=IsolatedOverlay(sample,command=[sys.executable,'-c','pass'],clock=lambda:clock[0])
        self.addCleanup(renderer.stop)
        for attempt in range(2):
            renderer.tick();child=renderer._child;child.wait(timeout=3)
            renderer.tick();clock[0]+=3
        renderer.tick();self.assertIsNone(renderer._child)
        self.assertEqual(renderer._attempts,2)
        self.assertEqual(renderer.diagnostic()['code'],'worker-failed')

    def test_blocked_pipe_does_not_block_supervisor_and_child_is_terminated(self):
        clock=[0.0]
        large=Frame(True,View('b'*24,tuple(Card('offer',tuple('x'*500 for _ in range(100))) for _ in range(4))))
        renderer=IsolatedOverlay(lambda:large,command=[sys.executable,'-c','import time; time.sleep(30)'],clock=lambda:clock[0])
        self.addCleanup(renderer.stop)
        started=time.monotonic();renderer.tick();child=renderer._child
        self.assertLess(time.monotonic()-started,1)
        self.assertFalse(renderer._write_done.wait(.1))
        clock[0]=2;renderer.tick()
        self.assertIsNotNone(child.poll());self.assertIsNone(renderer._child)
        self.assertEqual(renderer.diagnostic()['code'],'worker-failed')

class SessionContinuityTests(unittest.TestCase):
    def test_confirmed_session_can_bridge_lcu_loss_only_with_fresh_game_signal(self):
        from sexo2.overlay.runtime import OverlayRuntime
        from tests.test_build_workflow import FakeLCU
        clock=[0.0];lcu=FakeLCU();lcu.phase='InProgress'
        runtime=OverlayRuntime(lcu,enabled=lambda:True,clock=lambda:clock[0])
        self.addCleanup(runtime.stop)
        client=Mock();client.get.return_value={'gameTime':5}
        runtime._readiness=GameReadiness(client=client,clock=lambda:clock[0])
        self.assertTrue(runtime.poll().active)
        lcu.draft_request=Mock(side_effect=OSError('synthetic disconnected LCU'))
        clock[0]=2;client.get.return_value={'gameTime':7}
        self.assertTrue(runtime.poll().active)
        clock[0]=11
        self.assertFalse(runtime.poll().active)
        self.assertIsNone(runtime._cached_session)

    def test_end_of_game_never_reuses_a_previous_mode(self):
        from sexo2.overlay.runtime import OverlayRuntime
        from tests.test_build_workflow import FakeLCU
        lcu=FakeLCU();runtime=OverlayRuntime(lcu,enabled=lambda:True)
        self.addCleanup(runtime.stop)
        lcu.phase='InProgress';runtime.poll();self.assertIsNotNone(runtime._cached_session)
        lcu.phase='EndOfGame';runtime.poll();self.assertIsNone(runtime._cached_session)
