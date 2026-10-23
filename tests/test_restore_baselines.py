import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import restore_baselines  # noqa: E402


def make_zip(path: Path, names: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in names.items():
            zf.writestr(name, data)


class ExtractTests(unittest.TestCase):
    def test_extracts_the_app_tree_and_requires_the_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_zip(tmp / "ok.zip", {"SEXO2.exe": b"x", "_internal/a.txt": b"a"})
            restore_baselines.extract_safely(tmp / "ok.zip", tmp / "out")
            self.assertEqual((tmp / "out" / "_internal" / "a.txt").read_bytes(), b"a")
            make_zip(tmp / "bad.zip", {"_internal/a.txt": b"a"})
            with self.assertRaises(ValueError):
                restore_baselines.extract_safely(tmp / "bad.zip", tmp / "out2")

    def test_refuses_paths_that_escape_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_zip(tmp / "evil.zip", {"SEXO2.exe": b"x", "../escaped.txt": b"no"})
            with self.assertRaises(ValueError):
                restore_baselines.extract_safely(tmp / "evil.zip", tmp / "out")
            self.assertFalse((tmp / "escaped.txt").exists())


if __name__ == "__main__":
    unittest.main()
