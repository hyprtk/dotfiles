"""Schema invariants."""

from __future__ import annotations

import unittest

from support import ROOT  # noqa: F401  (sets sys.path)
from config_manager import schema

VALID_TYPES = {"bool", "int", "float", "str", "enum", "color", "vec2", "css_gaps", "font_weight"}


class Schema(unittest.TestCase):
    def test_paths_are_unique(self) -> None:
        paths = [o["path"] for o in schema.options()]
        self.assertEqual(len(paths), len(set(paths)))

    def test_types_and_ranges(self) -> None:
        for opt in schema.options():
            self.assertIn(opt["type"], VALID_TYPES, opt)
            self.assertIn("label", opt)
            if "min" in opt and "max" in opt:
                self.assertLessEqual(opt["min"], opt["max"], opt)
            if opt["type"] == "enum":
                self.assertTrue(opt.get("choices"), opt)

    def test_pages_reference_options(self) -> None:
        pages = {p["id"] for p in schema.pages()}
        for opt in schema.options():
            self.assertIn(opt["page"], pages)

    def test_animation_tree_styles(self) -> None:
        self.assertIn("windows", schema.ANIMATION_TREE)
        self.assertIn("borderangle", schema.ANIMATION_TREE)
        self.assertIn("loop", schema.ANIMATION_TREE["borderangle"])


if __name__ == "__main__":
    unittest.main()
