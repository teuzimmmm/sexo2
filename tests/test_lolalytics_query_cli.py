"""Offline tests for explicit query contracts and the JSON command-line interface."""
import contextlib
import io
import json
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from lolalytics.client import Client
from lolalytics.errors import HTTPStatusError, QueryError
from lolalytics.query import Query

FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def fixture_entry(name):
    return next(entry for entry in MANIFEST if entry["fixture"] == name)


class FixtureTransport:
    def __init__(self, fixture_names=(), *, error_urls=None):
        self.bodies = {
            Query(**fixture_entry(name)["filters"]).url: (FIXTURES / name).read_bytes()
            for name in fixture_names
        }
        self.error_urls = error_urls or {}
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if url in self.error_urls:
            raise self.error_urls[url]
        if url not in self.bodies:
            raise AssertionError(f"unexpected offline URL: {url}")
        return self.bodies[url]

    def close(self):
        pass


class QueryContractTests(unittest.TestCase):
    def test_canonical_ranked_url_and_cache_key_include_all_filters(self):
        query = Query("ahri", lane="middle", tier="gold", region="br", patch="16.19")
        expected = (
            "https://lolalytics.com/lol/ahri/build/q-data.json?"
            "lane=middle&tier=gold&region=br&patch=16.19"
        )
        self.assertEqual(query.url, expected)
        self.assertEqual(query.key, expected)
        self.assertEqual(Query("ahri").url,
                         "https://lolalytics.com/lol/ahri/build/q-data.json?lane=all&tier=emerald_plus&region=all")

    def test_modes_and_explicit_patches_have_distinct_routes_and_keys(self):
        ranked = Query("ahri", patch="16.20")
        old_patch = Query("ahri", patch="16.19")
        aram = Query("jinx", mode="aram", tier="all")
        arena = Query("jinx", mode="arena", tier="all")
        self.assertIn("/lol/ahri/build/q-data.json?", ranked.url)
        self.assertIn("/lol/jinx/aram/build/q-data.json?", aram.url)
        self.assertIn("/lol/jinx/arena/build/q-data.json?", arena.url)
        self.assertNotIn("lane", parse_qs(urlsplit(aram.url).query))
        self.assertNotIn("lane", parse_qs(urlsplit(arena.url).query))
        self.assertNotEqual(ranked.key, old_patch.key)
        self.assertNotEqual(aram.key, arena.key)
        self.assertNotEqual(Query("ahri").key, Query("ahri", mode="arena").key)

    def test_rejects_unsupported_filter_combinations(self):
        invalid = (
            {"mode": "aram", "lane": "middle"},
            {"mode": "arena", "tier": "diamond_plus"},
            {"mode": "aram", "region": "br"},
            {"mode": "ranked", "lane": "bot"},
            {"tier": "challenger"},
            {"patch": "latest"},
            {"patch": "16.200"},
        )
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(QueryError):
                Query("ahri", **kwargs)

    def test_slug_validation_blocks_path_query_and_header_injection(self):
        for slug in (
            "Ahri", "ahri/../jinx", "ahri?lane=all", "ahri#fragment", "ahri%2f", "ahri\nheader", "áhri", "",
        ):
            with self.subTest(slug=slug), self.assertRaises(QueryError):
                Query(slug)
        self.assertTrue(Query("wukong-2").url.startswith("https://lolalytics.com/lol/wukong-2/"))


class CommandLineTests(unittest.TestCase):
    def test_cli_emits_json_for_fixture_and_uses_explicit_patch(self):
        transport = FixtureTransport(("ahri-ranked-16.19-br-gold.json",))
        original_client = Client
        created = []

        def client_factory(**kwargs):
            client = original_client(transport=transport, **kwargs)
            created.append(client)
            return client

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("lolalytics.__main__.Client", side_effect=client_factory):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = __import__("lolalytics.__main__", fromlist=["main"]).main([
                    "ahri", "--patch", "16.19", "--lane", "middle", "--tier", "gold", "--region", "br",
                ])
        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["query"]["patch"], "16.19")
        self.assertEqual(output["resolved"]["patch"], "16.19")
        self.assertEqual(output["query"]["region"], "br")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(len(created), 1)

    def test_cli_failure_is_stderr_exit_one_and_never_prints_response_body(self):
        query = Query("ahri")
        transport = FixtureTransport(error_urls={query.url: HTTPStatusError(403)})
        original_client = Client

        def client_factory(**kwargs):
            return original_client(transport=transport, **kwargs)

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("lolalytics.__main__.Client", side_effect=client_factory):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = __import__("lolalytics.__main__", fromlist=["main"]).main(["ahri"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("HTTP 403", stderr.getvalue())
        self.assertNotIn("SECRET", stderr.getvalue())
        self.assertNotIn("_objs", stderr.getvalue())

    def test_cli_keeps_first_json_line_when_later_batch_query_fails(self):
        failed_query = Query("jinx")
        transport = FixtureTransport(
            ("ahri-ranked.json",), error_urls={failed_query.url: HTTPStatusError(503)},
        )
        transport.bodies[Query("ahri").url] = (FIXTURES / "ahri-ranked.json").read_bytes()
        original_client = Client

        def client_factory(**kwargs):
            return original_client(transport=transport, **kwargs)

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("lolalytics.__main__.Client", side_effect=client_factory):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = __import__("lolalytics.__main__", fromlist=["main"]).main(["ahri", "jinx"])
        lines = stdout.getvalue().splitlines()
        self.assertEqual(code, 1)
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["query"]["champion"], "ahri")
        self.assertIn("HTTP 503", stderr.getvalue())
        self.assertNotIn("_objs", stdout.getvalue() + stderr.getvalue())
        self.assertEqual(transport.calls, [Query("ahri").url, failed_query.url])

    def test_cli_rejects_more_than_twenty_without_constructing_client(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("lolalytics.__main__.Client") as client_class:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
                __import__("lolalytics.__main__", fromlist=["main"]).main(["ahri"] * 21)
        self.assertEqual(caught.exception.code, 2)
        client_class.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
