"""The LCU facade offers what the assistant's typed clients call (LCUPerks, LCUItemSets).

The assistant tests run against fakes with the full transport interface; this
checks the real facade has it too, so a missing method shows here rather than
in the client.
"""

import inspect
import unittest
from unittest.mock import MagicMock

from lcu.core.client import LCU
from lcu.features.lcu_item_sets import LCUItemSets
from lcu.features.lcu_perks import LCUPerks, LCUTransport


def facade():
    lcu = object.__new__(LCU)
    lcu._api = MagicMock()
    return lcu


class FacadeTests(unittest.TestCase):
    def test_facade_has_every_transport_method_with_compatible_parameters(self):
        for name, member in inspect.getmembers(LCUTransport, inspect.isfunction):
            if name.startswith("_"):
                continue
            with self.subTest(method=name):
                self.assertTrue(hasattr(LCU, name), name)
                wanted = set(inspect.signature(member).parameters)
                offered = set(inspect.signature(getattr(LCU, name)).parameters)
                self.assertLessEqual(wanted, offered)

    def test_uncached_reads_and_writes_reach_the_api(self):
        lcu = facade()
        lcu._api.get.return_value = {"summonerId": 7}
        LCUItemSets(lcu).summoner_id()
        args, kwargs = lcu._api.get.call_args
        self.assertEqual(args[0], "/lol-summoner/v1/current-summoner")
        self.assertIs(kwargs["use_cache"], False)
        lcu.put("/x", {"a": 1}, 2.0)
        lcu._api.put.assert_called_once_with("/x", {"a": 1}, 2.0, None)
        lcu.post("/y", [1], 2.0)
        lcu._api.post.assert_called_once_with("/y", [1], 2.0)

    def test_perks_client_accepts_the_facade(self):
        lcu = facade()
        lcu._api.get.return_value = []
        self.assertEqual(LCUPerks(lcu).pages(), [])


if __name__ == "__main__":
    unittest.main()
