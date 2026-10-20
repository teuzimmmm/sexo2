"""The ranked-stats read used by the champion-select assistant (D-122)."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from lcu.core.client import LCU
from lcu.core.lcu_api import LCUAPI


def api_with(response):
    session = MagicMock()
    session.get.return_value = response
    connection = SimpleNamespace(
        ok=True,
        base="https://127.0.0.1:1",
        session=session,
        refresh_if_needed=lambda force=False: None,
    )
    return LCUAPI(connection), session


class RankedStatsTests(unittest.TestCase):
    def test_reads_the_player_ranked_stats_path(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {"queueMap": {"RANKED_SOLO_5x5": {"tier": "GOLD"}}}
        api, session = api_with(response)
        payload = api.ranked_stats("abc-123", timeout=0.5)
        self.assertEqual(payload["queueMap"]["RANKED_SOLO_5x5"]["tier"], "GOLD")
        session.get.assert_called_once_with("https://127.0.0.1:1/lol-ranked/v1/ranked-stats/abc-123", timeout=0.5)

    def test_a_missing_player_is_none(self):
        response = MagicMock(status_code=404)
        api, _ = api_with(response)
        self.assertIsNone(api.ranked_stats("abc-123"))

    def test_an_empty_puuid_does_not_reach_the_client(self):
        api, session = api_with(MagicMock(status_code=200))
        self.assertIsNone(api.ranked_stats(""))
        self.assertIsNone(api.ranked_stats(None))
        session.get.assert_not_called()

    def test_the_puuid_is_encoded_in_the_path(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {}
        api, session = api_with(response)
        api.ranked_stats("a/b+c")
        session.get.assert_called_once_with("https://127.0.0.1:1/lol-ranked/v1/ranked-stats/a%2Fb%2Bc", timeout=1.0)

    def test_the_facade_delegates(self):
        lcu = object.__new__(LCU)
        lcu._api = MagicMock()
        lcu.ranked_stats("abc-123", timeout=0.5)
        lcu._api.ranked_stats.assert_called_once_with("abc-123", 0.5)


if __name__ == "__main__":
    unittest.main()
