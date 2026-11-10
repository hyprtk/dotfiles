import os
import tempfile
import unittest
from pathlib import Path

from hyprtk_file_manager.listing import DirCache, list_dir


class ListingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "adir").mkdir()
        (self.root / "zdir").mkdir()
        (self.root / "b.txt").write_text("hello")
        (self.root / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (self.root / ".hidden").write_text("x")
        os.utime(self.root / "a.png", (1000, 1000))
        os.utime(self.root / "b.txt", (2000, 2000))
        self.cache = DirCache()

    def tearDown(self):
        self.tmp.cleanup()

    def names(self, **kwargs):
        result = list_dir(self.cache, str(self.root), limit=100, **kwargs)
        return [entry["name"] for entry in result["entries"]]

    def test_dirs_first_then_name(self):
        self.assertEqual(self.names(), ["adir", "zdir", "a.png", "b.txt"])

    def test_hidden_excluded_by_default(self):
        self.assertNotIn(".hidden", self.names())
        self.assertIn(".hidden", self.names(hidden=True))

    def test_size_sort(self):
        self.assertEqual(self.names(sort="size"), ["adir", "zdir", "b.txt", "a.png"])

    def test_mtime_sort(self):
        self.assertEqual(self.names(sort="mtime"), ["adir", "zdir", "a.png", "b.txt"])

    def test_type_sort(self):
        self.assertEqual(self.names(sort="type"), ["adir", "zdir", "a.png", "b.txt"])

    def test_desc_keeps_dirs_first(self):
        self.assertEqual(self.names(desc=True), ["zdir", "adir", "b.txt", "a.png"])

    def test_query_filter(self):
        result = list_dir(self.cache, str(self.root), query="a.")
        self.assertEqual([entry["name"] for entry in result["entries"]], ["a.png"])
        self.assertEqual(result["total"], 1)

    def test_pagination(self):
        result = list_dir(self.cache, str(self.root), offset=2, limit=2)
        self.assertEqual(result["total"], 4)
        self.assertEqual([entry["name"] for entry in result["entries"]], ["a.png", "b.txt"])

    def test_cache_invalidation(self):
        list_dir(self.cache, str(self.root))
        (self.root / "c.txt").write_text("z")
        result = list_dir(self.cache, str(self.root))
        self.assertEqual(result["total"], 5)
        self.assertIn("c.txt", [entry["name"] for entry in result["entries"]])

    def test_icons(self):
        result = list_dir(self.cache, str(self.root))
        icons = {entry["name"]: entry["icon"] for entry in result["entries"]}
        self.assertEqual(icons["adir"], "folder")
        self.assertEqual(icons["a.png"], "image-x-generic")
        self.assertEqual(icons["b.txt"], "text-x-generic")

    def test_missing_path(self):
        with self.assertRaises(FileNotFoundError):
            list_dir(self.cache, str(self.root / "nope"))

    def test_file_is_not_a_directory(self):
        with self.assertRaises(NotADirectoryError):
            list_dir(self.cache, str(self.root / "b.txt"))


if __name__ == "__main__":
    unittest.main()
