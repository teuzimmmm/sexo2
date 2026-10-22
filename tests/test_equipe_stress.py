"""Stress test of the team rows (D-153): sessions and client answers made of junk, many times over.

Whatever the client sends, the service must not raise, must publish rows that can be sent as JSON,
never more than five, never read the form of the local player, and open only addresses of the
profile site.
"""

import json
import random
import unittest

from sexo2.services.assistant import ELO_QUEUES, AssistantService
from tests.test_assistant_service import FakeController, FakeLCU, FakeStats, InlineWorker, ranked_payload

QUEUES = [400, 420, 430, 440, 450, 480, 490, 1750, 2400, 3140, None, 0, 99999]
ROW_KEYS = {"cellId", "position", "name", "tag", "championId", "elo", "form", "canOpen"}


def junk(rng):
    return rng.choice(
        [None, "", "x", " ", 0, -1, 7, 1e9, 3.5, True, False, [], {}, [1], {"a": 1}, "ü" * 300, "<b>x</b>", "a b/c?d#e"]
    )


def maybe(rng, good, p=0.6):
    return good() if rng.random() < p else junk(rng)


def ally(rng, cell):
    return {
        "cellId": maybe(rng, lambda: cell, 0.85),
        "puuid": maybe(rng, lambda: f"p{cell}", 0.8),
        "gameName": maybe(rng, lambda: rng.choice(["Fulano", "Beltrano", "A B", "ñ/ü?", "x" * 80])),
        "tagLine": maybe(rng, lambda: rng.choice(["BR1", "1234", "ü&g"])),
        "summonerName": maybe(rng, lambda: "Old", 0.3),
        "championId": maybe(rng, lambda: rng.choice([0, 86, 103, 22, 999999]), 0.7),
        "championPickIntent": maybe(rng, lambda: rng.choice([0, 86]), 0.3),
        "assignedPosition": maybe(rng, lambda: rng.choice(["top", "jungle", "middle", "bottom", "utility", ""]), 0.7),
    }


def history(rng, puuid):
    roll = rng.random()
    if roll < 0.15:
        return None
    if roll < 0.3:
        return RuntimeError("timeout")
    if roll < 0.45:
        return junk(rng)
    games = []
    for i in range(rng.randint(0, 25)):
        part = {
            "participantId": maybe(rng, lambda: 1, 0.9),
            "championId": maybe(rng, lambda: rng.choice([86, 103, 22]), 0.8),
            "stats": maybe(rng, lambda: {"win": maybe(rng, lambda: rng.random() < 0.5, 0.7)}, 0.8),
            "timeline": maybe(
                rng,
                lambda: {
                    "lane": rng.choice(["TOP", "MIDDLE", "BOTTOM", "JUNGLE", "NONE", junk(rng)]),
                    "role": junk(rng),
                },
                0.7,
            ),
        }
        games.append(
            {
                "gameCreation": maybe(rng, lambda: i, 0.8),
                "participants": maybe(rng, lambda: [part], 0.9),
                "participantIdentities": maybe(rng, lambda: [{"participantId": 1, "player": {"puuid": puuid}}], 0.7),
            }
        )
    return rng.choice([{"games": {"games": games}}, {"games": games}, games])


def ranked(rng):
    roll = rng.random()
    if roll < 0.15:
        return None
    if roll < 0.3:
        return RuntimeError("down")
    if roll < 0.45:
        return junk(rng)
    queue = rng.choice(["RANKED_SOLO_5x5", "RANKED_FLEX_SR", "OTHER"])
    payload = ranked_payload(
        queue, rng.choice(["GOLD", "NONE", "", junk(rng)]), junk(rng), maybe(rng, lambda: rng.randint(0, 100))
    )
    payload["queueMap"][queue].update(
        {"wins": maybe(rng, lambda: rng.randint(0, 300)), "losses": maybe(rng, lambda: rng.randint(0, 300))}
    )
    return payload


class TeamRowsStressTests(unittest.TestCase):
    def run_case(self, seed):
        rng = random.Random(seed)
        lcu = FakeLCU()
        size = rng.choice([0, 1, 2, 3, 4, 5, 5, 5, 5, 6, 10, 16])
        allies = [ally(rng, cell) for cell in range(size)]
        session = {
            "id": maybe(rng, lambda: f"cs-{seed}", 0.9),
            "localPlayerCellId": maybe(rng, lambda: rng.randint(0, 4), 0.8),
            "myTeam": maybe(rng, lambda: allies, 0.95),
            "theirTeam": maybe(rng, lambda: [ally(rng, 10 + i) for i in range(rng.randint(0, 6))], 0.7),
        }
        lcu.session = maybe(rng, lambda: session, 0.95)
        for a in allies:
            puuid = a["puuid"] if isinstance(a["puuid"], str) else None
            if puuid:
                lcu.ranked[puuid] = ranked(rng)
                lcu.history[puuid] = history(rng, puuid)
        lcu.region = rng.choice(
            [{"region": "BR"}, {"region": "EUW"}, {"region": "MARS"}, None, {}, RuntimeError("down"), junk(rng)]
        )
        queue = rng.choice(QUEUES)
        published, opened = [], []
        service = AssistantService(
            lcu,
            published.append,
            queue_id=lambda: queue,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            forms_worker=InlineWorker(),
            controller=FakeController(),
            open_url=opened.append,
        )
        for message in ({"type": "assistant-request"}, {"type": "assistant-ranked"}):
            service.handle(message)
        for cell in range(-1, 18):
            service.handle({"type": "assistant-open-profile", "cellId": cell})
        service.handle({"type": "assistant-open-profile", "cellId": junk(rng)})
        return size, queue, lcu.session, published, opened

    def test_two_thousand_random_selections(self):
        for seed in range(2000):
            with self.subTest(seed=seed):
                size, queue, session, published, opened = self.run_case(seed)
                for state in published:
                    json.dumps(state, allow_nan=False)  # can always be sent to the panel
                    ranked_state = state["ranked"]
                    self.assertLessEqual(len(ranked_state["team"]), 5)
                    for row in ranked_state["team"]:
                        self.assertEqual(set(row), ROW_KEYS)
                        self.assertIsInstance(row["canOpen"], bool)
                        self.assertIsInstance(row["name"], str)
                    if published:
                        allies = session.get("myTeam") if isinstance(session, dict) else None
                        count = len(allies) if isinstance(allies, list) else 0
                        if queue != 1750:  # Arena counts only the duo, not the whole roster
                            self.assertEqual(ranked_state["available"], queue in ELO_QUEUES and 1 <= count <= 5)
                if published and not published[-1]["ranked"]["available"]:
                    self.assertEqual(opened, [])
                for url in opened:
                    self.assertTrue(url.startswith("https://www.op.gg/summoners/"), url)
                    self.assertNotIn(" ", url)
                    self.assertEqual(url.count("/"), 5, url)  # nothing from a name can add a path


if __name__ == "__main__":
    unittest.main()
