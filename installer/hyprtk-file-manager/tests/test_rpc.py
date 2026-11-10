import tempfile
import unittest
from pathlib import Path

from hyprtk_file_manager import rpc


class RpcTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "folder").mkdir()
        (self.root / "file.txt").write_text("x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ping(self):
        response = rpc.handle({"id": 1, "method": "ping"})
        self.assertEqual(response["id"], 1)
        self.assertEqual(response["result"]["kind"], "ping")
        self.assertIn("version", response["result"])

    def test_list(self):
        response = rpc.handle({"id": 2, "method": "list", "params": {"path": str(self.root)}})
        result = response["result"]
        self.assertEqual(result["kind"], "list")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["entries"][0]["name"], "folder")

    def test_list_missing_path(self):
        response = rpc.handle({"id": 3, "method": "list", "params": {"path": str(self.root / "nope")}})
        self.assertIn("error", response)
        self.assertIn("FileNotFoundError", response["error"])

    def test_places(self):
        response = rpc.handle({"id": 4, "method": "places"})
        result = response["result"]
        self.assertEqual(result["kind"], "places")
        for key in ("places", "bookmarks", "drives", "home"):
            self.assertIn(key, result)

    def test_unknown_method(self):
        response = rpc.handle({"id": 5, "method": "wat"})
        self.assertIn("error", response)

    def test_version(self):
        response = rpc.handle({"id": 6, "method": "version"})
        self.assertEqual(response["result"]["kind"], "version")


if __name__ == "__main__":
    unittest.main()
