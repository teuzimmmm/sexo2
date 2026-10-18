"""scripts/patch_core_dll.py on a small PE built like the inherited core.dll."""

import importlib.util
import struct
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "patch_core_dll", Path(__file__).resolve().parents[1] / "scripts" / "patch_core_dll.py"
)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)

TEXT_RVA, TEXT_RAW = 0x1000, 0x400
DATA_RVA, DATA_RAW = 0x2000, 0x600
CONFIG_AT, ROSE_AT = 0x600, 0x640  # file offsets of the two strings


def wide(text: str) -> bytes:
    return text.encode("utf-16-le") + b"\0\0"


def reference(code: bytearray, at: int, length: int, string_offset: int, *, with_length: bool = True) -> int:
    """mov r8d, length; lea rdx, [rip+string] at file offset ``at`` in .text."""
    if with_length:
        code[at : at + 6] = b"\x41\xb8" + struct.pack("<I", length)
    lea = at + 6
    target = string_offset - DATA_RAW + DATA_RVA
    rip_after = lea - TEXT_RAW + TEXT_RVA + 7
    code[lea : lea + 7] = b"\x48\x8d\x15" + struct.pack("<i", target - rip_after)
    return lea + 7


def build(*, unsized_reference: bool = False, signed: bool = True) -> bytes:
    data = bytearray(0x800)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x40)
    data[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x44, 0x8664, 2, 0, 0, 0, 240, 0x2022)
    struct.pack_into("<H", data, 0x58, 0x20B)  # PE32+ optional header
    table = 0x58 + 240
    struct.pack_into("<8sIIII", data, table, b".text", 0x200, TEXT_RVA, 0x200, TEXT_RAW)
    struct.pack_into("<8sIIII", data, table + 40, b".rdata", 0x200, DATA_RVA, 0x200, DATA_RAW)
    data[CONFIG_AT : CONFIG_AT + 34] = wide("\\Rose\\config.ini")
    data[ROSE_AT : ROSE_AT + 12] = wide("\\Rose")
    at = TEXT_RAW
    at = reference(data, at, 16, CONFIG_AT)
    at = reference(data, at, 16, CONFIG_AT)
    reference(data, at, 5, ROSE_AT, with_length=not unsized_reference)
    if signed:
        signature = b"CERT" * 8
        struct.pack_into("<II", data, 0x58 + 112 + 4 * 8, len(data), len(signature))
        data += signature
    return bytes(data)


class PatchCoreDllTests(unittest.TestCase):
    def test_strings_and_lengths_move_to_sexo2_and_the_signature_goes(self):
        original = build()
        patched = patcher.patch(original)
        self.assertIn(wide("\\SEXO2\\config.ini"), patched)
        self.assertIn(wide("\\SEXO2"), patched)
        self.assertNotIn("\\Rose".encode("utf-16-le"), patched)
        lengths = [struct.unpack_from("<I", patched, TEXT_RAW + 13 * i + 2)[0] for i in range(3)]
        self.assertEqual(lengths, [17, 17, 6])
        self.assertEqual(len(patched), 0x800)  # certificate table removed
        self.assertEqual(struct.unpack_from("<II", patched, 0x58 + 112 + 4 * 8), (0, 0))

    def test_patching_twice_changes_nothing(self):
        once = patcher.patch(build())
        self.assertEqual(patcher.patch(once), once)

    def test_a_reference_without_its_length_is_refused(self):
        with self.assertRaises(patcher.PatchError):
            patcher.patch(build(unsized_reference=True))

    def test_a_string_without_room_is_refused(self):
        data = bytearray(build(signed=False))
        data[ROSE_AT + 12] = 0x41  # something right after "\Rose"
        with self.assertRaises(patcher.PatchError):
            patcher.patch(bytes(data))


if __name__ == "__main__":
    unittest.main()
