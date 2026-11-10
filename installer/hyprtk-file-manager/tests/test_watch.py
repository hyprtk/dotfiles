import tempfile
import time
import unittest
from pathlib import Path

from hyprtk_file_manager.watch import WatchManager


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.events = []
        self.manager = WatchManager(emit=self.events.append)

    def tearDown(self):
        self.manager.stop_all()
        self.tmp.cleanup()

    def test_emits_on_create(self):
        self.manager.watch("pane", str(self.root))
        deadline = time.monotonic() + 2.0
        (self.root / "created.txt").write_text("x")
        while time.monotonic() < deadline:
            if self.events:
                break
            time.sleep(0.05)
        self.assertTrue(self.events)
        self.assertEqual(self.events[0]["event"], "fs")
        self.assertEqual(self.events[0]["token"], "pane")

    def test_unwatch_stops_events(self):
        self.manager.watch("pane", str(self.root))
        self.manager.unwatch("pane")
        (self.root / "after.txt").write_text("x")
        time.sleep(0.4)
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
