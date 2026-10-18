"""Fixed-room regressions against the current relay API, no live networking."""

import asyncio
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from party.core.party_manager import PartyManager, PERMANENT_PARTY_ROOM_KEY
from party.discovery.skin_collector import SkinCollector
from party.network.relay_config import RELAY_URL


class FixedPartyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.relays = []
        self.can_connect = True

        def relay(key, sid, name):
            obj = SimpleNamespace(
                room_key=key, members=[], connected=False, stopped=False, last_error=None, sid=sid, name=name
            )

            async def connect():
                obj.connected = self.can_connect
                obj.last_error = None if obj.connected else "network unavailable"
                return obj.connected

            async def disconnect():
                obj.connected = False

            obj.connect = AsyncMock(side_effect=connect)
            obj.disconnect = AsyncMock(side_effect=disconnect)
            obj.send_state = AsyncMock()
            obj.set_callbacks = Mock()
            obj.resume = Mock()
            self.relays.append(obj)
            return obj

        matcher = Mock()
        matcher.get_my_summoner_id.return_value = 123
        matcher.get_my_summoner_name.return_value = "Amigo"
        collector = Mock()
        collector.get_my_selection.return_value = None
        for name, obj in [
            ("LobbyMatcher", Mock(return_value=matcher)),
            ("SkinCollector", Mock(return_value=collector)),
            ("PartyRelay", relay),
            ("get_config_option", lambda section, option, fallback=None: fallback),
        ]:
            p = patch("party.core.party_manager." + name, obj)
            p.start()
            self.addCleanup(p.stop)
        self.matcher = matcher
        self.party = PartyManager(Mock(), SimpleNamespace(phase="Lobby"))
        self.addAsyncCleanup(self.party.disable)

    async def test_friends_share_same_room(self):
        self.assertEqual(await self.party.enable(), "S3XO")
        self.matcher.get_my_summoner_id.return_value = 456
        friend = PartyManager(Mock(), SimpleNamespace(phase="Lobby"))
        self.addAsyncCleanup(friend.disable)
        await friend.enable()
        self.assertEqual([r.room_key for r in self.relays], [PERMANENT_PARTY_ROOM_KEY] * 2)
        self.assertEqual([r.sid for r in self.relays], [123, 456])

    async def test_invitation_cannot_replace_room(self):
        await self.party.enable()
        home = self.party._home_room
        ok, message = await self.party.add_peer("legacy-token")
        self.assertFalse(ok)
        self.assertIn("sala fixa", message)
        self.assertEqual(list(self.party._relays), [home])
        self.relays[0].disconnect.assert_not_awaited()

    async def test_reconnect_retains_room_and_updates_indicator(self):
        await self.party.enable()
        self.assertTrue(self.party.get_state_dict()["relay_connected"])
        self.assertTrue(await self.party.force_reconnect())
        self.assertEqual([r.room_key for r in self.relays], [PERMANENT_PARTY_ROOM_KEY] * 2)
        self.relays[0].disconnect.assert_awaited_once()
        self.assertTrue(self.party.get_state_dict()["relay_connected"])

    async def test_initial_failure_is_reported_and_can_retry(self):
        self.can_connect = False
        with self.assertRaisesRegex(RuntimeError, "network unavailable"):
            await self.party.enable()
        self.assertFalse(self.party.enabled)
        self.can_connect = True
        await self.party.enable()
        self.assertTrue(self.party.get_state_dict()["relay_connected"])

    async def test_room_override_is_preserved(self):
        with patch("party.core.party_manager.get_party_room", return_value=("Outra", "fixed-other")):
            self.assertEqual(await self.party.enable(), "Outra")
            self.assertTrue(await self.party.force_reconnect())
            self.assertEqual(list(self.party._relays), ["fixed-other"])

    async def test_peer_advertisements_cannot_change_fixed_room(self):
        await self.party.enable()
        self.relays[0].members = [{"summoner_id": 456, "skin": {"rooms": ["a" * 32]}}]
        self.party._follow_advertised_rooms()
        self.assertEqual(len(self.relays), 1)

    async def test_simultaneous_startup_shares_one_connection(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        original = self.party._join_room

        async def blocked(room):
            entered.set()
            await release.wait()
            return await original(room)

        self.party._join_room = AsyncMock(side_effect=blocked)
        first = asyncio.create_task(self.party.enable())
        await entered.wait()
        second = asyncio.create_task(self.party.enable())
        await asyncio.sleep(0)
        release.set()
        self.assertEqual(await asyncio.gather(first, second), ["S3XO", "S3XO"])
        self.party._join_room.assert_awaited_once()
        self.assertEqual(len(self.relays), 1)

    async def test_cancelled_ui_request_does_not_cancel_other_callers(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        original = self.party._join_room

        async def blocked(room):
            entered.set()
            await release.wait()
            return await original(room)

        self.party._join_room = AsyncMock(side_effect=blocked)
        first = asyncio.create_task(self.party.enable())
        await entered.wait()
        second = asyncio.create_task(self.party.enable())
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        release.set()
        self.assertEqual(await second, "S3XO")
        self.party._join_room.assert_awaited_once()

    async def test_leaving_cancels_pending_startup(self):
        entered = asyncio.Event()

        async def blocked(room):
            entered.set()
            await asyncio.Event().wait()

        self.party._join_room = AsyncMock(side_effect=blocked)
        first = asyncio.create_task(self.party.enable())
        await entered.wait()
        await self.party.disable()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertFalse(self.party.enabled)
        self.assertFalse(self.party._running)
        self.assertIsNone(self.party._home_room)

    async def test_identity_request_does_not_block_the_websocket_loop(self):
        started = threading.Event()
        released = threading.Event()

        def slow_identity():
            started.set()
            if not released.wait(2):
                raise AssertionError("websocket loop could not release identity request")
            return 123

        self.matcher.get_my_summoner_id.side_effect = slow_identity
        first = asyncio.create_task(self.party.enable())
        try:
            while not started.is_set():
                await asyncio.sleep(0.001)
            # This coroutine must run before the synchronous request returns.
            released.set()
            self.assertEqual(await first, "S3XO")
        finally:
            released.set()


class FixedPartyPackagingTests(unittest.TestCase):
    def test_endpoint_and_modules_are_packaged(self):
        self.assertTrue(RELAY_URL.startswith("wss://"))
        spec = (Path(__file__).resolve().parents[1] / "Rose.spec").read_text(encoding="utf-8")
        for name in ["party.network.relay_config", "pengu.processing.swiftplay_pins"]:
            self.assertIn(name, spec)

    def test_plugin_is_automatic_fixed_room(self):
        plugin = (Path(__file__).resolve().parents[1] / "Pengu Loader/plugins/ROSE-PartyMode/index.js").read_text(
            encoding="utf-8"
        )
        for name in ["SEXO2", "scheduleAutomaticEnable", "party-reconnect", "rose-party-champ-status"]:
            self.assertIn(name, plugin)
        self.assertNotIn("party-add-peer", plugin)

    def test_same_champion_in_another_match_cannot_supply_skin(self):
        collector = SkinCollector(SimpleNamespace())
        members = [dict(summoner_id=sid, skin=dict(champion_id=11, skin_id=11001)) for sid in [123, 456, 789]]

        def collect(team):
            return collector.collect_relay_skins(members, 123, team, require_team_membership=True)

        self.assertEqual([s.summoner_id for s in collect({456: 11})], [456])
        self.assertEqual(collect({}), [])
        self.assertEqual(collect({456: 22}), [])
