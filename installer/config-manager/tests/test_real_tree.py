"""Golden/integration checks against the real hyprtk tree (skipped if absent).

Writes always happen on a temp copy — never on the live config.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from support import ROOT  # noqa: F401  (sets sys.path)
from config_manager import lua_probe, state
from config_manager.rpc import handle

MERGED = Path.home() / "Projects" / "AI-Projects" / "hyprtk-merged" / "hypr"


@unittest.skipUnless((MERGED / "hyprland.lua").is_file(), "hyprtk-merged tree not present")
class RealTree(unittest.TestCase):
    def test_probe_effective_model(self) -> None:
        model = lua_probe.probe(MERGED)
        self.assertIsNone(model["error"])
        self.assertIn("animations-high", model["requires"])
        self.assertIn("decoration", model["config"])
        self.assertIn("windows", model["animations"])
        self.assertGreater(len(model["binds"]), 10)
        self.assertTrue(model["sources"]["config.decoration"]["file"].endswith("decoration.lua"))

    def test_apply_on_copy(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "hypr"
            shutil.copytree(MERGED, copy)
            old = state.BACKUP_ROOT
            state.BACKUP_ROOT = Path(d) / "backups"
            try:
                res = handle({
                    "id": 1,
                    "method": "apply",
                    "params": {
                        "root": str(copy),
                        "edits": [
                            {"type": "config", "path": "decoration.rounding", "value": 13},
                            {"type": "animation", "leaf": "windows", "key": "speed", "value": 7},
                        ],
                    },
                })
            finally:
                state.BACKUP_ROOT = old

            self.assertNotIn("error", res, res)
            self.assertEqual(sorted(res["result"]["files"]),
                             ["animations-high.lua", "decoration.lua"])
            model = lua_probe.probe(copy)
            self.assertEqual(model["config"]["decoration"]["rounding"], 13)
            self.assertEqual(model["animations"]["windows"]["speed"], 7)


if __name__ == "__main__":
    unittest.main()
