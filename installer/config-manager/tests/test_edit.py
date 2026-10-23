"""Write-path tests: surgical edits round-trip through the probe."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import make_tree

from config_manager import lua_edit, lua_probe


def apply_edit(root: Path, edit: lua_edit.Edit) -> None:
    (root / edit.relpath).write_text(edit.updated, encoding="utf-8")


class ConfigEdits(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_tree(Path(self.tmp.name))

    def test_replace_keeps_comment_and_verifies(self) -> None:
        edit = lua_edit.set_config(self.root, "decoration.rounding", 12)
        self.assertEqual(edit.relpath, "general.lua")
        self.assertIn("rounding = 12, -- keep me", edit.updated)
        apply_edit(self.root, edit)
        self.assertEqual(lua_probe.probe(self.root)["config"]["decoration"]["rounding"], 12)

    def test_insert_new_nested_key(self) -> None:
        edit = lua_edit.set_config(self.root, "general.float_gap", 8)
        self.assertIn("float_gap = 8", edit.updated)
        apply_edit(self.root, edit)
        self.assertEqual(lua_probe.probe(self.root)["config"]["general"]["float_gap"], 8)

    def test_insert_into_nested_table(self) -> None:
        edit = lua_edit.set_config(self.root, "decoration.blur.passes", 3)
        apply_edit(self.root, edit)
        self.assertEqual(
            lua_probe.probe(self.root)["config"]["decoration"]["blur"]["passes"], 3
        )

    def test_bool_and_string(self) -> None:
        edit = lua_edit.set_config(self.root, "decoration.blur.enabled", False)
        apply_edit(self.root, edit)
        edit = lua_edit.set_config(self.root, "general.mode", "master", kind="str")
        apply_edit(self.root, edit)
        cfg = lua_probe.probe(self.root)["config"]
        self.assertFalse(cfg["decoration"]["blur"]["enabled"])
        self.assertEqual(cfg["general"]["mode"], "master")

    def test_legacy_int_colour_is_preserved_as_number(self) -> None:
        edit = lua_edit.set_config(self.root, "decoration.shadow.color", 0x55000000)
        self.assertIn("shadow", edit.updated)
        apply_edit(self.root, edit)
        self.assertEqual(
            lua_probe.probe(self.root)["config"]["decoration"]["shadow"]["color"],
            0x55000000,
        )

    def test_unknown_owner_is_an_error(self) -> None:
        with self.assertRaises(lua_edit.EditError):
            lua_edit.set_config(self.root, "cursor.size", 24)


class AnimationEdits(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_tree(Path(self.tmp.name))

    def test_set_existing_field(self) -> None:
        edit = lua_edit.set_animation(self.root, "windows", "speed", 9)
        self.assertEqual(edit.relpath, "animations-high.lua")
        apply_edit(self.root, edit)
        model = lua_probe.probe(self.root)
        self.assertEqual(model["animations"]["windows"]["speed"], 9)

    def test_add_new_leaf(self) -> None:
        edit = lua_edit.set_animation(self.root, "border", "speed", 2)
        apply_edit(self.root, edit)
        model = lua_probe.probe(self.root)
        self.assertIn("border", model["animations"])
        self.assertEqual(model["animations"]["border"]["speed"], 2)

    def test_replace_curve(self) -> None:
        edit = lua_edit.set_curve(
            self.root, "wind", {"type": "bezier", "points": [[0.2, 0.8], [0.2, 1.0]]}
        )
        apply_edit(self.root, edit)
        model = lua_probe.probe(self.root)
        self.assertEqual(model["curves"]["wind"]["points"], [[0.2, 0.8], [0.2, 1.0]])

    def test_add_spring_curve(self) -> None:
        edit = lua_edit.set_curve(
            self.root, "snappy", {"type": "spring", "mass": 1, "stiffness": 90, "damping": 12}
        )
        apply_edit(self.root, edit)
        curve = lua_probe.probe(self.root)["curves"]["snappy"]
        self.assertEqual(curve["type"], "spring")
        self.assertEqual(curve["stiffness"], 90)

    def test_switch_mode_flips_require(self) -> None:
        edit = lua_edit.set_animations_mode(self.root, "low")
        self.assertIn('require("animations-low")', edit.updated)
        self.assertIn('-- require("animations-high")', edit.updated)
        apply_edit(self.root, edit)
        self.assertEqual(lua_probe.probe(self.root)["requires"][1], "animations-low")


if __name__ == "__main__":
    unittest.main()
