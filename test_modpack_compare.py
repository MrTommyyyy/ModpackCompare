import contextlib
import io
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modpack_compare import FORMAT, compare, main, snapshot, validate_manifest


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_same_name_changed_content_is_detected(self):
        jar = self.folder / "example.jar"
        jar.write_bytes(b"old")
        before = snapshot(self.folder)
        jar.write_bytes(b"new")
        self.assertEqual(compare(before, snapshot(self.folder))["changed"], ["example.jar"])

    def test_unique_content_rename(self):
        jar = self.folder / "old.jar"
        jar.write_bytes(b"same")
        before = snapshot(self.folder)
        jar.rename(self.folder / "new.jar")
        result = compare(before, snapshot(self.folder))
        self.assertEqual(result["renamed"], [{"from": "old.jar", "to": "new.jar"}])
        self.assertFalse(result["added"] or result["removed"])

    def test_ambiguous_duplicates_are_not_assumed_to_be_renames(self):
        for name in ("a.jar", "b.jar"):
            (self.folder / name).write_bytes(b"duplicate")
        before = snapshot(self.folder)
        (self.folder / "a.jar").rename(self.folder / "c.jar")
        (self.folder / "b.jar").rename(self.folder / "d.jar")
        result = compare(before, snapshot(self.folder))
        self.assertEqual(result["renamed"], [])
        self.assertEqual(result["removed"], ["a.jar", "b.jar"])

    def test_recursive_is_explicit_and_case_insensitive_extension(self):
        (self.folder / "top.JAR").write_bytes(b"a")
        (self.folder / "notes.txt").write_text("ignore")
        sub = self.folder / "nested"
        sub.mkdir()
        (sub / "more.jar").write_bytes(b"b")
        self.assertEqual(len(snapshot(self.folder)["files"]), 1)
        self.assertEqual(len(snapshot(self.folder, True)["files"]), 2)

    def test_invalid_manifests_rejected(self):
        item = {"path": "../unsafe.jar", "size": 1, "sha256": "a" * 64}
        with self.assertRaises(ValueError):
            validate_manifest({"format": FORMAT, "files": [item]})
        item["path"] = "valid.jar"
        with self.assertRaises(ValueError):
            validate_manifest({"format": FORMAT, "files": [item, item]})
        item["size"] = True
        with self.assertRaises(ValueError):
            validate_manifest({"format": FORMAT, "files": [item]})

    def test_cli_report_and_difference_exit_codes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["snapshot", str(self.folder), "--output", str(self.folder / "old.json")]), 0)
            (self.folder / "new.jar").write_bytes(b"new")
            self.assertEqual(main(["snapshot", str(self.folder), "--output", str(self.folder / "new.json")]), 0)
            self.assertEqual(main(["compare", str(self.folder / "old.json"), str(self.folder / "new.json"), "--json"]), 2)
            self.assertEqual(main(["compare", str(self.folder / "new.json"), str(self.folder / "new.json")]), 0)

    def test_output_cannot_overwrite_jar(self):
        jar = self.folder / "keep.jar"
        jar.write_bytes(b"keep")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["snapshot", str(self.folder), "--output", str(jar)]), 1)
        self.assertEqual(jar.read_bytes(), b"keep")

    def test_scan_fails_if_file_changes_during_hash(self):
        jar = self.folder / "moving.jar"
        jar.write_bytes(b"original")
        original_sha256 = hashlib.sha256
        class ChangingDigest:
            def __init__(self):
                self.digest = original_sha256()
            def update(self, chunk):
                self.digest.update(chunk)
                jar.write_bytes(b"changed length")
            def hexdigest(self):
                return self.digest.hexdigest()
        with patch("modpack_compare.hashlib.sha256", ChangingDigest):
            with self.assertRaisesRegex(ValueError, "changed during"):
                snapshot(self.folder)


if __name__ == "__main__":
    unittest.main()
