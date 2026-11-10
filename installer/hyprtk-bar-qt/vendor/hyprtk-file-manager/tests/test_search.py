import tempfile
import unittest
from pathlib import Path

from hyprtk_file_manager.search import search


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "alpha.txt").write_text("nothing here\nneedle in a haystack\n")
        (self.root / "beta.md").write_text("plain text\n")
        sub = self.root / "sub"
        sub.mkdir()
        (sub / "gamma-needle.txt").write_text("other\n")
        (self.root / ".hidden-needle").write_text("hidden\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_name_search(self):
        result = search(str(self.root), "needle", mode="name")
        names = sorted(entry["name"] for entry in result["results"])
        self.assertEqual(names, ["gamma-needle.txt"])

    def test_name_search_hidden(self):
        result = search(str(self.root), "hidden", mode="name", hidden=True)
        self.assertIn(".hidden-needle", [entry["name"] for entry in result["results"]])

    def test_content_search(self):
        result = search(str(self.root), "haystack", mode="content")
        self.assertEqual(len(result["results"]), 1)
        entry = result["results"][0]
        self.assertEqual(entry["name"], "alpha.txt")
        self.assertEqual(entry["lineno"], 2)
        self.assertIn("haystack", entry["line"])

    def test_empty_query(self):
        result = search(str(self.root), "   ", mode="name")
        self.assertEqual(result["results"], [])

    def test_missing_root_returns_empty(self):
        result = search(str(self.root / "nope"), "needle", mode="name")
        self.assertEqual(result["results"], [])


if __name__ == "__main__":
    unittest.main()
