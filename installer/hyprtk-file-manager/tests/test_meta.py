import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path

from hyprtk_file_manager import meta


class MetaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.file = self.root / "note.txt"
        self.file.write_text("hello meta")
        os.chmod(self.file, 0o640)

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_info(self):
        info = meta.file_info(str(self.file))
        self.assertEqual(info["name"], "note.txt")
        self.assertEqual(info["type"], "file")
        self.assertEqual(info["mode_octal"], "0640")
        self.assertEqual(info["size"], 10)
        self.assertTrue(info["owner"])
        self.assertTrue(info["group"])

    def test_directory_info(self):
        info = meta.file_info(str(self.root))
        self.assertEqual(info["type"], "dir")

    def test_chmod(self):
        result = meta.chmod(str(self.file), "600")
        self.assertEqual(result["mode_octal"], "0600")
        self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)

    def test_chmod_invalid(self):
        with self.assertRaises(ValueError):
            meta.chmod(str(self.file), "9999")

    def test_checksum(self):
        result = meta.checksum(str(self.file), "sha256")
        self.assertEqual(result["hex"], hashlib.sha256(b"hello meta").hexdigest())
        self.assertEqual(result["size"], 10)

    def test_checksum_algo(self):
        with self.assertRaises(ValueError):
            meta.checksum(str(self.file), "crc32")


if __name__ == "__main__":
    unittest.main()
