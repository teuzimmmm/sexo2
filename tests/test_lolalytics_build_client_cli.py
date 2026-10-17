"""Offline integration tests for keystone conditioned build collection."""
import json
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from lolalytics.client import Client
from lolalytics.errors import HTTPStatusError, QueryError, SchemaError
from lolalytics.query import Query

FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics" / "keystone"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def entry(filename):
    return next(row for row in MANIFEST if row["fixture"] == filename)


class FixtureTransport:
    def __init__(self, names, errors=None):
        self.bodies = {entry(name)["source_url"]: (FIXTURES / name).read_bytes() for name in names}
        self.errors = errors or {}
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        source_url = url.replace("&patch=16.20", "").replace("?patch=16.20&", "?")
        if source_url in self.errors:
            raise self.errors[source_url]
        if source_url not in self.bodies:
            raise AssertionError(f"unexpected URL: {url}")
        return self.bodies[source_url]

    def close(self):
        pass


class BuildClientTests(unittest.TestCase):
    def test_automatic_two_keystones_uses_matching_filtered_pages(self):
        transport = FixtureTransport(("ahri-ranked-base.json", "ahri-ranked-pick.json", "ahri-ranked-win.json"))
        query = Query("ahri", lane="middle")
        result = Client(transport=transport, ttl=0).collect_builds(query)
        self.assertEqual([p.selection for p in result.pages], ["win", "pick"])
        self.assertEqual([p.keystone for p in result.pages], [8992, 8112])
        self.assertEqual(len(transport.calls), 3)
        self.assertTrue(all("keystone=" in p.source_url for p in result.pages))

    def test_same_keystone_reuses_filtered_response_with_zero_ttl(self):
        transport = FixtureTransport(("jinx-aram-base.json", "jinx-aram-filtered.json"))
        result = Client(transport=transport, ttl=0).collect_builds(
            Query("jinx", mode="aram", tier="all"))
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual([p.keystone for p in result.pages], [8008, 8008])
        self.assertEqual([p.source_url for p in result.pages], [transport.calls[1], transport.calls[1]])

    def test_explicit_keystone_is_one_filtered_request(self):
        transport = FixtureTransport(("ahri-ranked-win.json",))
        result = Client(transport=transport, ttl=0).collect_builds(
            Query("ahri", lane="middle", keystone=8992))
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(len(result.pages), 2)

    def test_filtered_status_failure_does_not_return_partial_collection(self):
        transport = FixtureTransport(("ahri-ranked-base.json", "ahri-ranked-win.json"))
        transport.errors[entry("ahri-ranked-pick.json")["source_url"]] = HTTPStatusError(503)
        with self.assertRaises(HTTPStatusError):
            Client(transport=transport, ttl=0).collect_builds(Query("ahri", lane="middle"))

    def test_ignored_filtered_keystone_fails_validation(self):
        transport = FixtureTransport(("ahri-ranked-base.json", "ahri-ranked-pick.json"))
        win_url = entry("ahri-ranked-win.json")["source_url"]
        transport.bodies[win_url] = (FIXTURES / "ahri-ranked-pick.json").read_bytes()
        with self.assertRaises(SchemaError):
            Client(transport=transport, ttl=0).collect_builds(Query("ahri", lane="middle"))

    def test_automatic_flow_pins_patch_and_resolved_lane(self):
        transport = FixtureTransport(("ahri-ranked-base.json", "ahri-ranked-pick.json", "ahri-ranked-win.json"))
        client = Client(transport=transport, ttl=0)
        collect = client.collect

        def collect_with_all_lane_snapshot(query):
            if query.lane == "all":
                snapshot = collect(Query(query.champion, mode=query.mode, lane="middle", tier=query.tier,
                                         region=query.region))
                snapshot.query = query.to_dict()
                snapshot.resolved["lane"] = "all"
                snapshot.resolved["effective_lane"] = "middle"
                return snapshot
            return collect(query)

        client.collect = collect_with_all_lane_snapshot
        result = client.collect_builds(Query("ahri"))
        self.assertEqual(len(transport.calls), 3)
        self.assertIn("patch=16.20", transport.calls[1])
        self.assertIn("lane=middle", transport.calls[1])
        self.assertTrue(all(page.resolved["patch"] == "16.20" for page in result.pages))
        self.assertTrue(all(page.query["lane"] == "middle" and page.query["patch"] == "16.20" for page in result.pages))

    def test_lazy_item_sets_reject_keystone_before_transport(self):
        transport = FixtureTransport(())
        with self.assertRaises(QueryError):
            Client(transport=transport).collect_item_sets(Query("ahri", keystone=8112))
        self.assertEqual(transport.calls, [])


class BuildCliTests(unittest.TestCase):
    def test_incompatible_builds_and_item_sets_rejected_before_client(self):
        from lolalytics.__main__ import main
        with patch("lolalytics.__main__.Client") as client_class:
            with self.assertRaises(SystemExit):
                main(["ahri", "--builds", "--item-sets"])
            client_class.assert_not_called()

    def test_arena_builds_rejected_before_client(self):
        from lolalytics.__main__ import main
        with patch("lolalytics.__main__.Client") as client_class:
            with self.assertRaises(SystemExit):
                main(["jinx", "--mode", "arena", "--builds"])
            client_class.assert_not_called()

    def test_keystone_flag_reaches_query(self):
        from lolalytics.__main__ import main

        class FakeClient:
            seen_query = None

            def __init__(self, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def collect(self, query):
                FakeClient.seen_query = query
                return type("Result", (), {"to_dict": lambda _self: {"ok": True}})()

        with patch("lolalytics.__main__.Client", FakeClient):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["ahri", "--keystone", "8112"]), 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True})
        self.assertEqual(FakeClient.seen_query.keystone, 8112)

    def test_keystone_item_sets_rejected_before_client(self):
        from lolalytics.__main__ import main
        with patch("lolalytics.__main__.Client") as client_class:
            with self.assertRaises(SystemExit):
                main(["ahri", "--keystone", "8112", "--item-sets"])
            client_class.assert_not_called()

    def test_builds_flag_emits_two_page_json(self):
        from lolalytics.__main__ import main
        transport = FixtureTransport(("ahri-ranked-base.json", "ahri-ranked-pick.json", "ahri-ranked-win.json"))
        output = io.StringIO()
        with patch("lolalytics.__main__.Client", lambda **_kwargs: Client(transport=transport, ttl=0)):
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["ahri", "--lane", "middle", "--builds"]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual([page["selection"] for page in data["pages"]], ["win", "pick"])
        self.assertEqual(len(transport.calls), 3)


if __name__ == "__main__":
    unittest.main()
