import hashlib
import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_SHA256 = "ee8a0d414846af736215fbbf3690f5101348d1770b27bd907a05d1fe6f9ebb31"
SIZES = [16, 24, 32, 48, 64, 128, 256]
ICOS = ("sexo2.ico", "sexo2-v2.ico", "sexo2-black-v3.ico", "icon.ico")
PNG_SIZES = {"icon.png": 256, "tray_ready.png": 256, "tray_starting.png": 256, "sexo2-toast.png": 64}


def ico_sizes(data: bytes) -> list[int]:
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1)
    sizes = []
    for i in range(count):
        width, height, _, _, _, _, length, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i : 22 + 16 * i])
        assert width == height
        assert data[offset : offset + 8] == b"\x89PNG\r\n\x1a\n" and offset + length <= len(data)
        sizes.append(width or 256)
    return sizes


def png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


class IconTests(unittest.TestCase):
    def test_source_svg_is_unchanged(self):
        self.assertEqual(hashlib.sha256((ASSETS / "sexo2.svg").read_bytes()).hexdigest(), SVG_SHA256)

    def test_ico_files_have_every_resolution(self):
        for name in ICOS:
            self.assertEqual(ico_sizes((ASSETS / name).read_bytes()), SIZES, name)

    def test_png_files_match_the_svg_render(self):
        for name, size in PNG_SIZES.items():
            self.assertEqual(png_size((ASSETS / name).read_bytes()), (size, size), name)
        ico = (ASSETS / "icon.ico").read_bytes()
        offset = struct.unpack("<I", ico[6 + 16 * 6 + 12 : 6 + 16 * 6 + 16])[0]
        length = struct.unpack("<I", ico[6 + 16 * 6 + 8 : 6 + 16 * 6 + 12])[0]
        self.assertEqual(ico[offset : offset + length], (ASSETS / "icon.png").read_bytes())

    def test_build_files_reference_existing_icons(self):
        refs = []
        for name in ("SEXO2.spec", "SEXO2-Updater.spec"):
            refs += re.findall(r"icon\s*=\s*['\"]([^'\"]+)['\"]", (ROOT / name).read_text(encoding="utf-8"))
        installer = (ROOT / "installer-sexo2.iss").read_text(encoding="utf-8")
        refs += [m.replace("\\", "/") for m in re.findall(r"SetupIconFile=(\S+)", installer)]
        refs += ["assets/" + m for m in re.findall(r'IconFilename: "\{app\}\\_internal\\assets\\([^"]+)"', installer)]
        refs += [
            "assets/" + m for m in re.findall(r"assets\\\\?([\w.-]+\.ico)", (ROOT / "updater_main.py").read_text())
        ]
        self.assertGreaterEqual(len(refs), 6)
        for ref in refs:
            self.assertTrue((ROOT / ref).is_file(), ref)


if __name__ == "__main__":
    unittest.main()
