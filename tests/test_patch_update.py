import json, shutil, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch, Mock
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
from scripts.build_patch import build
from sexo2.update.engine import apply_patch, digest


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = self.root / "old"
        self.new = self.root / "new"
        self.old.mkdir()
        self.new.mkdir()
        for base, value in [(self.old, b"old app"), (self.new, b"new app")]:
            (base / "SEXO2.exe").write_bytes(value)
            (base / "same.bin").write_bytes(b"same")
        (self.new / "added.bin").write_bytes(b"added")
        (self.old / "config.ini").write_bytes(b"personal settings")
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.package = self.root / "update.zip"
        self.make()

    def make(self):
        build(
            self.old,
            self.new,
            self.package,
            "1.5.0",
            self.key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
        )

    def test_delta_keeps_data_and_does_not_include_unchanged_files(self):
        with zipfile.ZipFile(self.package) as z:
            self.assertNotIn("payload/same.bin", z.namelist())
        self.assertEqual(apply_patch(self.package, self.old, self.public), "1.5.0")
        self.assertEqual((self.old / "config.ini").read_bytes(), b"personal settings")
        self.assertEqual((self.old / "SEXO2.exe").read_bytes(), b"new app")
        self.assertTrue((self.old / ".sexo2-update/rollback").exists())

    def test_invalid_signature_never_changes_installed_app(self):
        wrong = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        with self.assertRaisesRegex(ValueError, "assinatura"):
            apply_patch(self.package, self.old, wrong)
        self.assertEqual((self.old / "SEXO2.exe").read_bytes(), b"old app")

    def test_incompatible_installation_is_rejected_before_any_replacement(self):
        (self.old / "SEXO2.exe").write_bytes(b"other version")
        with self.assertRaisesRegex(ValueError, "versão instalada"):
            apply_patch(self.package, self.old, self.public)
        self.assertFalse((self.old / "added.bin").exists())

    def test_failure_mid_update_restores_originals_and_removes_new_files(self):
        from sexo2.update import engine

        original = engine.os.replace
        calls = [0]

        def fail_second(source, dest):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("synthetic disk failure")
            return original(source, dest)

        with patch.object(engine.os, "replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                apply_patch(self.package, self.old, self.public)
        self.assertEqual((self.old / "SEXO2.exe").read_bytes(), b"old app")
        self.assertFalse((self.old / "added.bin").exists())

    def test_two_updates_retain_only_latest_backup(self):
        apply_patch(self.package, self.old, self.public)
        (self.new / "SEXO2.exe").write_bytes(b"newer app")
        self.make()
        apply_patch(self.package, self.old, self.public)
        backups = list((self.old / ".sexo2-update").glob("rollback*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "files/SEXO2.exe").read_bytes(), b"new app")

    def test_process_check_blocks_before_transaction_and_installed_file_changes(self):
        def blocked():
            raise ValueError("LoL aberto")

        with self.assertRaisesRegex(ValueError, "LoL aberto"):
            apply_patch(self.package, self.old, self.public, blocked)
        self.assertFalse((self.old / ".sexo2-update/transaction/journal.json").exists())

    def test_traversal_and_personal_files_are_rejected_even_if_signed(self):
        for name in ["../outside.txt", "config.ini", "_internal/config.ini", "C:/bad", "a\\b", "skins/x.zip"]:
            raw = json.dumps(
                {"schema": 1, "app": "SEXO2", "version": "1.5.0", "files": {name: {"old": None, "new": "0" * 64}}}
            ).encode()
            with zipfile.ZipFile(self.package, "w") as z:
                z.writestr("manifest.json", raw)
                z.writestr("manifest.sig", self.key.sign(raw))
                z.writestr("payload/" + name, b"x")
            with self.assertRaises(ValueError):
                apply_patch(self.package, self.old, self.public)
            self.assertEqual((self.old / "SEXO2.exe").read_bytes(), b"old app")

    def test_invalid_package_never_requests_application_shutdown(self):
        wrong = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        close = Mock()
        with self.assertRaises(ValueError):
            apply_patch(self.package, self.old, wrong, close)
        close.assert_not_called()

    def test_incompatible_patch_keeps_running_app_untouched(self):
        (self.old / "SEXO2.exe").write_bytes(b"other version")
        close = Mock()
        with self.assertRaises(ValueError):
            apply_patch(self.package, self.old, self.public, close)
        close.assert_not_called()


if __name__ == "__main__":
    unittest.main()
