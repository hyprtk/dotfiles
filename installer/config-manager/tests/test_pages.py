"""Dynamic file sections and animation-file targeting."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import ROOT, make_tree  # noqa: F401  (sets sys.path)
from config_manager import lua_probe, pages, state
from config_manager.paths import find_hypr_dir
from config_manager.rpc import handle


class Sections(unittest.TestCase):
    def test_every_lua_file_becomes_a_section(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_tree(Path(d))
            data = pages.build(root)
            ids = [p["id"] for p in data["pages"]]
            # animations is collapsed; every other file is a section.
            self.assertEqual(ids[0], "animations")
            self.assertIn("hyprland", ids)
            self.assertIn("general", ids)
            self.assertIn("startup", ids)
            self.assertIn("animations-low", [f["id"] for f in data["animationFiles"]])
            titles = [p["title"].lower() for p in data["pages"]]
            self.assertEqual(titles, sorted(titles))

    def test_options_follow_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_tree(Path(d))
            data = pages.build(root)
            general = next(p for p in data["pages"] if p["id"] == "general")
            paths = [o["path"] for o in general["options"]]
            self.assertIn("general.gaps_in", paths)
            self.assertIn("decoration.rounding", paths)
            self.assertFalse(next(p for p in data["pages"] if p["id"] == "startup")["active"] is False)
            startup = next(p for p in data["pages"] if p["id"] == "startup")
            kinds = {i["kind"] for i in startup["items"]}
            self.assertTrue({"env", "bind", "monitor", "rule", "exec"} <= kinds)

    def test_animation_files_mark_active(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_tree(Path(d))
            data = pages.build(root)
            files = {f["id"]: f for f in data["animationFiles"]}
            self.assertTrue(files["animations-high"]["active"])
            self.assertFalse(files["animations-low"]["active"])
            self.assertEqual(files["animations-low"]["mode"], "low")


class AnimationTarget(unittest.TestCase):
    def test_edit_inactive_animation_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_tree(Path(d))
            old = state.BACKUP_ROOT
            state.BACKUP_ROOT = Path(d) / "backups"
            try:
                res = handle({
                    "id": 1,
                    "method": "apply",
                    "params": {
                        "root": str(root),
                        "edits": [
                            {"type": "animation", "module": "animations-low",
                             "leaf": "windows", "key": "speed", "value": 3},
                            {"type": "curve", "module": "animations-low", "name": "myBezier",
                             "spec": {"type": "bezier", "points": [[0.2, 0.3], [0.4, 0.9]]}},
                        ],
                    },
                })
            finally:
                state.BACKUP_ROOT = old
            self.assertNotIn("error", res, res)
            self.assertEqual(res["result"]["files"], ["animations-low.lua"])

            low = lua_probe.probe(root, main="animations-low.lua")
            self.assertEqual(low["animations"]["windows"]["speed"], 3)
            self.assertEqual(low["curves"]["myBezier"]["points"], [[0.2, 0.3], [0.4, 0.9]])

            # The active high file and the effective model stay untouched.
            self.assertEqual(lua_probe.probe(root)["animations"]["windows"]["speed"], 6)
            self.assertIn('require("animations-high")',
                          (root / "hyprland.lua").read_text(encoding="utf-8"))

    def test_module_dump(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_tree(Path(d))
            res = handle({"id": 1, "method": "module.dump",
                          "params": {"root": str(root), "file": "animations-low.lua"}})
            self.assertIn("result", res, res)
            self.assertEqual(res["result"]["file"], "animations-low.lua")
            self.assertIn("windows", res["result"]["model"]["animations"])


class EnvEdit(unittest.TestCase):
    def test_set_and_add_env(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_tree(Path(d))
            old = state.BACKUP_ROOT
            state.BACKUP_ROOT = Path(d) / "backups"
            try:
                res = handle({
                    "id": 1, "method": "apply",
                    "params": {"root": str(root), "edits": [
                        {"type": "env", "key": "XCURSOR_THEME", "value": "Adwaita"},
                        {"type": "env", "key": "NEW_VAR", "value": "yes"},
                    ]},
                })
            finally:
                state.BACKUP_ROOT = old
            self.assertNotIn("error", res, res)
            env = lua_probe.probe(root)["env"]
            self.assertEqual(env["XCURSOR_THEME"], "Adwaita")
            self.assertEqual(env["NEW_VAR"], "yes")


@unittest.skipUnless(find_hypr_dir() is not None, "live Hyprland tree not present")
class LiveSections(unittest.TestCase):
    def test_live_tree_builds(self) -> None:
        data = pages.build(find_hypr_dir())
        ids = [p["id"] for p in data["pages"]]
        for expected in ("animations", "hyprland", "input", "window", "decoration",
                         "keybindings", "windowrules", "environment", "autostart"):
            self.assertIn(expected, ids)


if __name__ == "__main__":
    unittest.main()
