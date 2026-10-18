import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

import requests

from lcu.core.lcu_api import LCUAPI
from lcu.features.lcu_perks import LCUPerks, PageBody, PerksError, parse_page

PAGE = {
    "id": 7,
    "name": "SEXO2",
    "isEditable": True,
    "isDeletable": True,
    "isActive": False,
    "current": True,
    "order": 0,
    "primaryStyleId": 8100,
    "subStyleId": 8200,
    "selectedPerkIds": [8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001],
}
BODY = PageBody("SEXO2", 8100, 8200, (8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001))


class FakeApi:
    def __init__(self, gets=None, status=200, body=b"{}"):
        self.gets = gets or {}
        self.status = status
        self.body = body
        self.calls = []

    def _response(self):
        response = MagicMock(status_code=self.status, content=self.body)
        response.json.return_value = PAGE
        return response

    def get(self, path, timeout=1.0, cache_ttl=None, use_cache=True):
        self.calls.append(("GET", path, use_cache))
        return self.gets.get(path)

    def put(self, path, json_data, timeout, headers=None):
        self.calls.append(("PUT", path, json_data))
        return self._response()

    def post(self, path, json_data, timeout):
        self.calls.append(("POST", path, json_data))
        return self._response()


class PerksTests(unittest.TestCase):
    def test_reads_are_uncached_and_typed(self):
        api = FakeApi({"/lol-perks/v1/pages": [PAGE], "/lol-perks/v1/inventory": {"ownedPageCount": 3}})
        perks = LCUPerks(api)
        self.assertEqual(perks.pages()[0].selected_perk_ids, tuple(PAGE["selectedPerkIds"]))
        self.assertTrue(perks.pages()[0].is_custom)
        self.assertEqual(perks.owned_page_count(), 3)
        self.assertTrue(all(call[2] is False for call in api.calls))

    def test_missing_answer_and_missing_fields_are_errors(self):
        perks = LCUPerks(FakeApi())
        with self.assertRaises(PerksError) as raised:
            perks.current_page()
        self.assertEqual(raised.exception.code, "unavailable")
        for field in ("id", "isEditable", "isDeletable", "current", "primaryStyleId", "selectedPerkIds"):
            broken = {key: value for key, value in PAGE.items() if key != field}
            with self.subTest(field=field), self.assertRaises(PerksError) as raised:
                parse_page(broken)
            self.assertEqual(raised.exception.code, "schema")
        with self.assertRaises(PerksError):
            parse_page({**PAGE, "id": True})
        with self.assertRaises(PerksError):
            LCUPerks(FakeApi({"/lol-perks/v1/inventory": {}})).owned_page_count()

    def test_writes_send_the_documented_bodies(self):
        api = FakeApi()
        perks = LCUPerks(api)
        self.assertEqual(perks.create_page(BODY).id, 7)
        perks.update_page(7, BODY)
        perks.set_current(7)
        post, put, current = api.calls
        self.assertEqual(post[:2], ("POST", "/lol-perks/v1/pages"))
        self.assertEqual(post[2]["selectedPerkIds"], list(BODY.selected_perk_ids))
        self.assertIs(post[2]["current"], True)
        self.assertEqual(put[:2], ("PUT", "/lol-perks/v1/pages/7"))
        self.assertEqual(put[2]["id"], 7)
        self.assertEqual(current, ("PUT", "/lol-perks/v1/currentpage", 7))

    def test_rejected_or_unanswered_write_is_an_error(self):
        with self.assertRaises(PerksError) as raised:
            LCUPerks(FakeApi(status=400)).update_page(7, BODY)
        self.assertEqual((raised.exception.code, raised.exception.status), ("rejected", 400))
        api = FakeApi()
        api.post = lambda path, json_data, timeout: None
        with self.assertRaises(PerksError) as raised:
            LCUPerks(api).create_page(BODY)
        self.assertEqual(raised.exception.code, "unavailable")


class LcuApiPostTests(unittest.TestCase):
    def test_post_is_not_retried_after_a_transport_error(self):
        session = MagicMock()
        session.post.side_effect = requests.exceptions.ConnectionError("client closed")
        connection = SimpleNamespace(
            ok=True, base="https://127.0.0.1:1", session=session, refresh_if_needed=MagicMock()
        )
        with self.assertLogs(level="WARNING"):
            self.assertIsNone(LCUAPI(connection).post("/lol-perks/v1/pages", {}, timeout=1.0))
        self.assertEqual(session.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
