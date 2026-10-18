import tempfile, unittest, zipfile, json, shutil
from pathlib import Path
from injection.mods.storage import ModStorageService
from sexo2.services.mod_library import ModLibrary, identify

CHAMPIONS = [
    {"id": 22, "name": "Ashe", "alias": "Ashe"},
    {"id": 254, "name": "Vi", "alias": "Vi"},
    {"id": 11, "name": "Master Yi", "alias": "MasterYi"},
]


class LibraryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.storage = ModStorageService(self.root / "mods")
        self.library = ModLibrary(self.storage, self.root, lambda: CHAMPIONS)
        self.library.refresh()

    def archive(self, name, wad="Ashe", metadata=None, data=b"mod"):
        source = self.library.inbox / name
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("WAD/" + wad + ".wad.client/file.bin", data)
            if metadata is not None:
                z.writestr("META/info.json", json.dumps(metadata))
        return source

    def test_identifies_internal_wad_and_avoids_vi_inside_silver(self):
        source = self.archive("Silver cosplay.fantome", wad="unknown")
        self.assertIsNone(identify(source, CHAMPIONS)["championId"])
        source = self.archive("Outfit.fantome")
        self.assertEqual(identify(source, CHAMPIONS)["championId"], 22)

    def test_conflicting_metadata_goes_to_review(self):
        source = self.archive("Outfit.fantome", metadata={"Champions": [254]})
        self.assertIsNone(identify(source, CHAMPIONS)["championId"])

    def test_bulk_waits_until_file_is_stable_and_deduplicates_preserving_originals(self):
        source = self.archive("Ashe.fantome")
        self.library.scan()
        self.assertEqual(self.library.mods, [])
        self.library.scan()
        self.assertEqual(len(self.library.mods), 1)
        self.assertTrue(source.exists())
        shutil.copy2(source, self.library.inbox / "another name.fantome")
        self.library.scan()
        self.library.scan()
        self.assertEqual(len(self.library.mods), 1)
        self.assertIn("duplicado", [row["status"] for row in self.library.incoming.values()])

    def test_ambiguous_file_can_be_resolved_manually(self):
        self.archive("Unknown.fantome", wad="unknown")
        self.library.scan()
        self.library.scan()
        row = next(iter(self.library.incoming.values()))
        self.assertEqual(row["status"], "revisar")
        self.library.resolve(row["id"], 11, [11001])
        self.assertEqual(len(self.library.mods), 1)
        self.assertEqual(self.library.mods[0]["targets"], [11001])

    def test_corrupt_file_does_not_stop_next_file(self):
        (self.library.inbox / "a.fantome").write_bytes(b"bad")
        self.archive("b.fantome")
        self.library.scan()
        self.library.scan()
        self.assertEqual(len(self.library.mods), 1)
        self.assertIn("erro", [row["status"] for row in self.library.incoming.values()])

    def test_export_restore_keeps_names_targets_and_categories_without_app_secrets(self):
        self.archive("Ashe.fantome", metadata={"Author": "Original creator"})
        self.library.scan()
        self.library.scan()
        row = self.library.mods[0]
        self.library.rename(row["id"], "Meu mod")
        self.library.targets(row["id"], [22000, 22001])
        self.library.import_one(self.archive("Map.fantome", wad="Map11", data=b"map"), "maps")
        (self.root / "update-access.json").write_text("synthetic secret")
        output = self.library.export()
        with zipfile.ZipFile(output) as z:
            self.assertFalse(any("update-access" in name for name in z.namelist()))
            data = json.loads(z.read("sexo2-library.json"))
            self.assertEqual(len(data["mods"]), 2)
        other = ModLibrary(ModStorageService(self.root / "other-mods"), self.root / "other", lambda: CHAMPIONS)
        other.refresh()
        other.restore(output)
        self.assertEqual(len(other.mods), 2)
        skin = next(m for m in other.mods if m["category"] == "skins")
        self.assertEqual(skin["name"], "Meu mod")
        self.assertEqual(skin["targets"], [22000, 22001])
        other.restore(output)
        self.assertEqual(len(other.mods), 2)

    def test_corrupt_export_is_rejected_before_importing_any_mod(self):
        self.archive("Ashe.fantome")
        self.library.scan()
        self.library.scan()
        output = self.library.export()
        corrupt = self.root / "corrupt.zip"
        with zipfile.ZipFile(output) as z, zipfile.ZipFile(corrupt, "w") as out:
            for name in z.namelist():
                data = z.read(name)
                if name == "sexo2-library.json":
                    manifest = json.loads(data)
                    manifest["mods"][0]["sha256"] = "bad"
                    data = json.dumps(manifest)
                out.writestr(name, data)
        other = ModLibrary(ModStorageService(self.root / "other-mods"), self.root / "other", lambda: CHAMPIONS)
        other.refresh()
        with self.assertRaisesRegex(ValueError, "corrompida"):
            other.restore(corrupt)
        self.assertEqual(other.mods, [])

    def test_game_phase_guard_prevents_commit_if_phase_changes_during_extraction(self):
        source = self.archive("Ashe.fantome")
        calls = [0]

        def busy():
            calls[0] += 1
            return calls[0] >= 2

        self.library.busy = busy
        with self.assertRaisesRegex(ValueError, "Aguardando"):
            self.library.import_one(source, "skins", 22, [22000])
        self.library.busy = lambda: False
        self.library.refresh()
        self.assertEqual(self.library.mods, [])
        self.assertTrue(source.exists())

    def test_delete_and_rename_preserve_unrelated_mods(self):
        self.library.import_one(self.archive("Ashe.fantome"), "skins", 22, [22000])
        self.library.import_one(self.archive("Vi.fantome", wad="Vi", data=b"vi"), "skins", 254, [254000])
        row = self.library.mods[0]
        self.library.delete(row["id"])
        self.assertEqual(len(self.library.mods), 1)

    def test_category_subfolders_cannot_mix_skin_and_map_imports(self):
        folder = self.library.inbox / "maps"
        folder.mkdir()
        source = folder / "Map.fantome"
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("WAD/Map11.wad.client/file.bin", b"map")
        self.library.scan()
        self.library.scan()
        self.assertEqual(self.library.mods[0]["category"], "maps")

    def test_duplicate_with_new_target_merges_targets_instead_of_losing_selection(self):
        source = self.archive("Ashe.fantome")
        self.library.import_one(source, "skins", 22, [22000])
        self.library.import_one(source, "skins", 22, [22001])
        self.assertEqual(len(self.library.mods), 1)
        self.assertEqual(self.library.mods[0]["targets"], [22000, 22001])

    def test_modified_import_is_not_mistaken_for_unchanged_duplicate(self):
        source = self.archive("Ashe.fantome")
        self.library.import_one(source, "skins", 22, [22000])
        file = self.storage.mods_root / self.library.mods[0]["path"] / "WAD/Ashe.wad.client/file.bin"
        file.write_bytes(b"user edited")
        self.library.import_one(source, "skins", 22, [22000])
        self.assertEqual(len(self.library.mods), 2)
        self.assertEqual(file.read_bytes(), b"user edited")

    def test_zip_containing_fantome_packages_is_prepared_then_imported(self):
        inner = self.archive("Ashe.fantome")
        outer = self.library.inbox / "download.zip"
        with zipfile.ZipFile(outer, "w") as z:
            z.write(inner, "download/Ashe.fantome")
        inner.unlink()
        for _ in range(4):
            self.library.scan()
        self.assertEqual(len(self.library.mods), 1)
        self.assertTrue(outer.exists())
        self.assertIn("preparado", [row["status"] for row in self.library.incoming.values()])

    def test_corrected_file_replaces_its_previous_error_entry(self):
        source = self.library.inbox / "Ashe.fantome"
        source.write_bytes(b"bad")
        self.library.scan()
        self.library.scan()
        self.assertEqual(len(self.library.incoming), 1)
        self.archive("Ashe.fantome")
        self.library.scan()
        self.library.scan()
        self.assertEqual(len(self.library.incoming), 1)
        self.assertEqual(next(iter(self.library.incoming.values()))["status"], "importado")

    def test_plain_zip_named_after_champion_is_not_imported_as_a_skin(self):
        source = self.library.inbox / "Ashe.zip"
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("wallpaper.png", b"not a mod")
        self.library.scan()
        self.library.scan()
        self.assertEqual(self.library.mods, [])
        self.assertEqual(next(iter(self.library.incoming.values()))["status"], "erro")

    def test_nested_single_mod_folder_is_flattened_to_compatible_layout(self):
        source = self.library.inbox / "Ashe.zip"
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("download/WAD/Ashe.wad.client/file.bin", b"mod")
        self.library.scan()
        self.library.scan()
        path = self.storage.mods_root / self.library.mods[0]["path"]
        self.assertTrue((path / "WAD/Ashe.wad.client/file.bin").is_file())
        self.assertFalse((path / "download").exists())

    def test_restart_does_not_reimport_a_removed_mod_from_unchanged_inbox(self):
        self.archive("Ashe.fantome")
        self.library.scan()
        self.library.scan()
        self.library.delete(self.library.mods[0]["id"])
        restarted = ModLibrary(self.storage, self.root, lambda: CHAMPIONS)
        restarted.refresh()
        restarted.scan()
        self.assertEqual(restarted.mods, [])

    def test_cancellation_during_large_zip_read_removes_partial_import(self):
        source = self.archive("Ashe.fantome", data=b"x" * (4 * 1024 * 1024))
        calls = [0]

        def stop_during_read():
            calls[0] += 1
            if calls[0] > 8:
                self.library.cancel.set()
            return False

        self.library.busy = stop_during_read
        with self.assertRaises(ValueError):
            self.library.import_one(source, "skins", 22, [22000])
        self.library.busy = lambda: False
        self.library.cancel.clear()
        self.library.refresh()
        self.assertEqual(self.library.mods, [])
        self.assertTrue(source.exists())

    def test_modpkg_authors_license_and_readme_metadata_survive_export_restore(self):
        from utils.tests.test_modpkg import build_package, Chunk

        metadata = {
            "name": "yi",
            "display_name": "Meu Yi",
            "authors": [{"name": "Criador", "role": "Artist"}],
            "license": {"type": "spdx", "spdx_id": "MIT"},
            "champions": ["MasterYi"],
        }
        source = self.library.inbox / "Yi.modpkg"
        source.write_bytes(
            build_package(
                [
                    Chunk("DATA/Characters/MasterYi/Skins/Skin0/Skin0.bin", b"asset", wad="masteryi.wad.client"),
                    Chunk("_meta_/license", b"License text", layer=None, wad=None),
                    Chunk("_meta_/readme.md", b"Readme text", layer=None, wad=None),
                ],
                metadata=metadata,
            )
        )
        self.library.scan()
        self.library.scan()
        output = self.library.export()
        other = ModLibrary(ModStorageService(self.root / "other-mods"), self.root / "other", lambda: CHAMPIONS)
        other.refresh()
        other.restore(output)
        restored = json.loads(other.metadata_path(other.mods[0]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(restored["authors"], metadata["authors"])
        self.assertEqual(restored["license"], metadata["license"])
        self.assertEqual(restored["license_text"], "License text")
        self.assertEqual(restored["readme"], "Readme text")
