import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.parse import quote

from hyprtk_file_manager import trash


class TrashTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.trash = self.root / "Trash"
        (self.trash / "files").mkdir(parents=True)
        (self.trash / "info").mkdir()
        self.original = self.root / "restored.txt"
        self.original.write_text("payload")
        self.trashed = self.trash / "files" / "restored.txt"
        shutil.move(str(self.original), str(self.trashed))
        (self.trash / "info" / "restored.txt.trashinfo").write_text(
            "[Trash Info]\nPath=" + quote(str(self.original)) + "\nDeletionDate=2026-11-10T09:00:00\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_restore(self):
        result = trash.restore(str(self.trashed), self.trash)
        self.assertEqual(result["original"], str(self.original))
        self.assertTrue(self.original.exists())
        self.assertEqual(self.original.read_text(), "payload")
        self.assertFalse(self.trashed.exists())
        self.assertFalse((self.trash / "info" / "restored.txt.trashinfo").exists())

    def test_empty_invokes_gio(self):
        with patch("hyprtk_file_manager.trash.subprocess.run") as run:
            result = trash.empty()
            run.assert_called_once()
            self.assertTrue(result["ok"])

    def test_restore_conflict(self):
        self.original.write_text("occupied")
        with self.assertRaises(FileExistsError):
            trash.restore(str(self.trashed), self.trash)


if __name__ == "__main__":
    unittest.main()
