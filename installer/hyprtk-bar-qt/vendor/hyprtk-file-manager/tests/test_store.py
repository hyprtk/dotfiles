import json
import tempfile
import unittest
from pathlib import Path

from hyprtk_file_manager import store
from hyprtk_file_manager.journal import Journal


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip(self):
        path = self.root / "config.json"
        store.save(path, {"viewMode": "grid", "dualPane": True})
        self.assertEqual(store.load(path), {"viewMode": "grid", "dualPane": True})

    def test_merge(self):
        path = self.root / "config.json"
        store.save(path, {"viewMode": "grid"})
        merged = store.merge(path, {"viewMode": "list", "showHidden": True})
        self.assertEqual(merged["viewMode"], "list")
        self.assertTrue(merged["showHidden"])
        self.assertEqual(store.load(path), merged)

    def test_missing_and_corrupt(self):
        path = self.root / "config.json"
        self.assertEqual(store.load(path), {})
        path.write_text("not json")
        self.assertEqual(store.load(path), {})

    def test_legacy_journal_list_migration(self):
        path = self.root / "journal.json"
        path.write_text(json.dumps([{"kind": "rename", "id": "a", "undone": False}]))
        journal = Journal(path)
        self.assertEqual(len(journal.records), 1)
        self.assertEqual(journal.redo, [])


if __name__ == "__main__":
    unittest.main()
