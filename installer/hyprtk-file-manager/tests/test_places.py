import tempfile
import unittest
from pathlib import Path

from hyprtk_file_manager import places


class PlacesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.config = self.home / ".config"
        self.config.mkdir()
        (self.home / "Downloads").mkdir()
        (self.home / "Documents").mkdir()
        (self.home / ".local" / "share" / "Trash" / "files").mkdir(parents=True)
        (self.config / "user-dirs.dirs").write_text(
            'XDG_DOWNLOAD_DIR="$HOME/Downloads"\nXDG_DOCUMENTS_DIR="$HOME/Documents"\n'
        )
        gtk = self.config / "gtk-3.0"
        gtk.mkdir()
        (gtk / "bookmarks").write_text(
            "file://" + str(self.home / "Downloads") + " Downloads\n"
            "file://" + str(self.home / "Downloads") + " Downloads again\n"
            "file:///does/not/exist missing\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_user_dirs(self):
        dirs = places.parse_user_dirs(self.home, self.config)
        self.assertEqual(dirs["Downloads"], str(self.home / "Downloads"))
        self.assertEqual(dirs["Documents"], str(self.home / "Documents"))
        self.assertEqual(dirs["Music"], str(self.home / "Music"))

    def test_places(self):
        items = places.places(self.home, self.config)
        names = [item["name"] for item in items]
        self.assertEqual(names[0], "Home")
        self.assertIn("Downloads", names)
        self.assertIn("Documents", names)
        self.assertIn("Trash", names)
        self.assertNotIn("Music", names)

    def test_bookmarks(self):
        items = places.bookmarks(self.home, self.config)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Downloads")

    def test_drives_is_a_list(self):
        self.assertIsInstance(places.drives(), list)


if __name__ == "__main__":
    unittest.main()
