"""Read-path tests: execute the fixture tree, assert the effective model."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import make_tree

from config_manager import lua_probe


class ProbeFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_tree(Path(self.tmp.name))
        self.model = lua_probe.probe(self.root)

    def test_computed_value(self) -> None:
        self.assertEqual(self.model["config"]["general"]["gaps_in"], 5)

    def test_active_requires_skip_comments(self) -> None:
        self.assertEqual(
            self.model["requires"], ["general", "animations-high", "startup"]
        )

    def test_provenance_points_at_owner(self) -> None:
        src = self.model["sources"]["config.general"]
        self.assertTrue(src["file"].endswith("general.lua"), src)
        self.assertGreater(src["line"], 0)

    def test_animations_and_curves(self) -> None:
        self.assertEqual(self.model["animation_order"], ["windows", "fade"])
        self.assertTrue(self.model["animations"]["windows"]["enabled"])
        self.assertEqual(self.model["curves"]["rubber"]["type"], "spring")

    def test_binds_monitors_rules_env(self) -> None:
        self.assertEqual(len(self.model["binds"]), 1)
        self.assertEqual(self.model["binds"][0]["keys"], "SUPER, Return")
        self.assertEqual(self.model["monitors"][0]["output"], "DP-1")
        self.assertEqual(len(self.model["rules"]["window_rule"]), 1)
        self.assertEqual(self.model["gestures"][0]["fingers"], 3)
        self.assertEqual(self.model["env"]["XCURSOR_THEME"], "Bibata-Modern-Ice")

    def test_callback_and_exec_once(self) -> None:
        execs = [e["command"] for e in self.model["exec"]]
        self.assertIn("waybar", execs)

    def test_unknown_namespace_does_not_crash(self) -> None:
        names = [u["name"] for u in self.model["unknown"]]
        self.assertIn("dsp.window.close", names)

    def test_dump_is_json_serializable(self) -> None:
        import json

        json.dumps(self.model)


class ProbeErrors(unittest.TestCase):
    def test_missing_main(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(lua_probe.ProbeError):
                lua_probe.probe(Path(d))

    def test_lua_error_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_tree(Path(d), main='require("does-not-exist")\n')
            with self.assertRaises(lua_probe.ProbeError):
                lua_probe.probe(root)


if __name__ == "__main__":
    unittest.main()
