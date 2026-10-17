import json
import unittest
from pathlib import Path

from lolalytics.decoding import decode_page
from lolalytics.errors import DataUnavailable, SchemaError


FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics"


class DecodeRealFixturesTests(unittest.TestCase):
    def test_sanitized_real_qdata_fixtures(self):
        expected = {
            "ahri-ranked.json": ("ahri", "ranked", "16.20"),
            "ahri-ranked-16.19-br-gold.json": ("ahri", "ranked", "16.19"),
            "jinx-aram.json": ("jinx", "aram", "16.20"),
            "ahri-arena.json": ("ahri", "arena", "16.20"),
            "jinx-arena.json": ("jinx", "arena", "16.20"),
        }
        # The real fixtures were reduced to only relevant loaders and rows.
        for filename, (champion, mode, patch) in expected.items():
            with self.subTest(filename=filename):
                path = FIXTURES / filename
                nav, payload = decode_page(path.read_bytes())
                self.assertEqual(nav["champion"], champion)
                self.assertEqual(nav["mode"], mode)
                self.assertEqual(nav["patch"], patch)
                self.assertIsInstance(payload["header"], dict)
                if mode != "arena":
                    self.assertEqual(payload["header"]["patch"], patch)


class DecodeMalformedTests(unittest.TestCase):
    def test_invalid_json_and_missing_entry(self):
        for body in (b"{", b"[]", b'{"_entry":"0","_objs":[]}'):
            with self.subTest(body=body), self.assertRaises(SchemaError):
                decode_page(body)

    def test_invalid_reference_and_unavailable_status(self):
        objects = [
            "16.20",
            "ahri",
            "ranked",
            {"currentPatch": "0", "champion": "zzzz", "mode": "2"},
            {"header": "5", "summary": "6"},
            {"patch": "0", "cid": 1},
            {},
            {"nav": "3", "payload": "4"},
            {"loaders": "7", "status": 200},
        ]
        with self.assertRaisesRegex(SchemaError, "reference is invalid"):
            decode_page(json.dumps({"_entry": "8", "_objs": objects}).encode())

        objects[8]["status"] = 404
        with self.assertRaisesRegex(DataUnavailable, "status 404"):
            decode_page(json.dumps({"_entry": "8", "_objs": objects}).encode())

    def test_json_and_body_size_limits(self):
        with self.assertRaisesRegex(SchemaError, "valid JSON"):
            decode_page(b'{"_entry":"0","_objs":[],"bad":NaN}')
        with self.assertRaisesRegex(SchemaError, "4 MiB"):
            decode_page(b" " * (4 * 1024 * 1024 + 1))
        deeply_nested = b"[" * 2_000 + b"0" + b"]" * 2_000
        with self.assertRaises(SchemaError):
            decode_page(deeply_nested)

    def test_overflowing_json_number_is_a_schema_error(self):
        objects = [
            "16.20",
            "ahri",
            "ranked",
            {"currentPatch": "0", "champion": "1", "mode": "2"},
            {"cid": 103, "n": 1},
            {"header": "4", "overflow": 1.5},
            {"nav": "3", "payload": "5"},
            {"loaders": "6", "status": 200},
        ]
        body = json.dumps({"_entry": "7", "_objs": objects}).encode().replace(b"1.5", b"1e999")
        with self.assertRaisesRegex(SchemaError, "finite"):
            decode_page(body)

    def test_literal_strings_in_object_table_are_not_reinterpreted(self):
        objects = [
            "16.20",
            "abc",
            "ranked",
            "emerald_plus",
            "all",
            {"currentPatch": "0", "champion": "1", "mode": "2"},
            {"header": "8", "summary": "9"},
            {"nav": "5", "payload": "6"},
            {"patch": "0", "n": 1},
            {},
            {"loaders": "7", "status": 200},
        ]
        # Ensure an interned literal that itself parses as base36 is returned
        # as a string rather than treated as another table index.
        objects.extend([None] * (13_369 - len(objects)))
        objects[1] = "abc"
        nav, payload = decode_page(json.dumps({"_entry": "a", "_objs": objects}).encode())
        self.assertEqual(nav["champion"], "abc")
        self.assertEqual(payload["header"]["patch"], "16.20")
        self.assertEqual(objects[1], "abc")

    def test_undefined_and_primitive_types_are_preserved(self):
        objects = [
            "16.20",
            "ahri",
            "ranked",
            "emerald_plus",
            "all",
            {"currentPatch": "0", "champion": "1", "mode": "2", "maybe": "\x01"},
            {"header": "7", "summary": "8", "int": 7, "float": 1.5, "bool": True, "null": None},
            {"patch": "0", "maybe": "\x01", "int": 7, "float": 1.5, "bool": True, "null": None},
            {},
            {"nav": "5", "payload": "6"},
            {"loaders": "9", "status": 200},
        ]
        nav, payload = decode_page(json.dumps({"_entry": "a", "_objs": objects}).encode())
        self.assertIsNone(nav["maybe"])
        self.assertEqual(payload["int"], 7)
        self.assertEqual(payload["float"], 1.5)
        self.assertIs(payload["bool"], True)
        self.assertIsNone(payload["null"])

    def test_unsupported_markers_fail_without_echoing_body(self):
        objects = [
            "16.20",
            "ahri",
            "ranked",
            "\x02marker",
            {"currentPatch": "0", "champion": "1", "mode": "2", "unexpected": "3"},
            {"header": "6", "summary": "7"},
            {},
            {},
            {"nav": "4", "payload": "5"},
            {"loaders": "8", "status": 200},
        ]
        with self.assertRaisesRegex(SchemaError, "unsupported marker") as caught:
            decode_page(json.dumps({"_entry": "9", "_objs": objects}).encode())
        self.assertNotIn("private-body", str(caught.exception))

    def test_cycles_and_contradictory_metadata_fail(self):
        objects = [
            "16.20",
            "ahri",
            "ranked",
            {"currentPatch": "0", "champion": "1", "mode": "3"},
            {"header": "6", "summary": "7"},
            {"nav": "3", "payload": "4"},
            {},
            {},
            {"loaders": "5", "status": 200},
        ]
        with self.assertRaisesRegex(SchemaError, "cycle"):
            decode_page(json.dumps({"_entry": "8", "_objs": objects}).encode())

        objects = [
            "16.20",
            "ahri",
            "ranked",
            "gold",
            {"currentPatch": "0", "champion": "1", "mode": "2"},
            {"currentPatch": "0", "champion": "1", "mode": "3"},
            {"header": "8", "summary": "9"},
            {"nav": "4", "payload": "6", "other-nav": "5"},
            {},
            {},
            {"loaders": "7", "status": 200},
        ]
        with self.assertRaisesRegex(SchemaError, "contradictory navigation"):
            decode_page(json.dumps({"_entry": "a", "_objs": objects}).encode())

    def test_limits_for_object_count_depth_and_expansion(self):
        too_many = [None] * 50_001
        with self.assertRaisesRegex(SchemaError, "object table exceeds"):
            decode_page(json.dumps({"_entry": "0", "_objs": too_many}).encode())

        deep = None
        for _ in range(81):
            deep = [deep]
        objects = [
            "16.20",
            "ahri",
            "ranked",
            {"currentPatch": "0", "champion": "1", "mode": "2"},
            {"patch": "0", "cid": 1},
            {},
            {"header": "4", "summary": "5", "deep": deep},
            {"nav": "3", "payload": "6"},
            {"loaders": "7", "status": 200},
        ]
        with self.assertRaisesRegex(SchemaError, "depth"):
            decode_page(json.dumps({"_entry": "8", "_objs": objects}).encode())

        wide = [None] * 200_000
        base = [
            "16.20",
            "ahri",
            "ranked",
            {"currentPatch": "0", "champion": "1", "mode": "2"},
            {"patch": "0", "cid": 1},
            {},
            wide,
            {"header": "4", "summary": "5", "rows": "6"},
            {"nav": "3", "payload": "7"},
            {"status": 200, "loaders": "8"},
        ]
        with self.assertRaisesRegex(SchemaError, "expansion exceeds"):
            decode_page(json.dumps({"_entry": "9", "_objs": base}).encode())


if __name__ == "__main__":
    unittest.main()
