import tempfile
import unittest
from pathlib import Path

from hyprtk_file_manager.preview import TEXT_LIMIT, build_preview


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_text_preview(self):
        target = self.root / "note.txt"
        target.write_text("hello preview")
        result = build_preview(str(target))
        self.assertEqual(result["kind"], "text")
        self.assertEqual(result["text"], "hello preview")
        self.assertFalse(result["truncated"])
        self.assertEqual(result["meta"]["name"], "note.txt")
        self.assertIn("text/", result["meta"]["mime"])

    def test_text_truncation(self):
        target = self.root / "big.txt"
        target.write_text("x" * (TEXT_LIMIT + 50))
        result = build_preview(str(target))
        self.assertEqual(result["kind"], "text")
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["text"]), TEXT_LIMIT)

    def test_directory(self):
        result = build_preview(str(self.root))
        self.assertEqual(result["kind"], "dir")
        self.assertTrue(result["meta"]["mime"])

    def test_binary(self):
        target = self.root / "blob.bin"
        target.write_bytes(b"\x00\x01\x02\x03" * 100)
        result = build_preview(str(target))
        self.assertEqual(result["kind"], "binary")

    def test_missing_path(self):
        with self.assertRaises(FileNotFoundError):
            build_preview(str(self.root / "nope"))


if __name__ == "__main__":
    unittest.main()
