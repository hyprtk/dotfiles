"""Scanner tests: comments and strings must never confuse spans."""

from __future__ import annotations

import unittest

from support import ROOT  # noqa: F401  (sets sys.path)
from config_manager import lua_scan

TRICKY = """\
-- hl.config({ general = { gaps_in = 99 } })
hl.config({
    general = {
        gaps_in = 5,        -- not a key = 1
        message = "a, b } = c",
    },
    other = { x = 1 },
})
hl.animation({ leaf = "windows", speed = 6 })
"""


class Mask(unittest.TestCase):
    def test_comments_and_strings_are_blanked(self) -> None:
        masked = lua_scan.mask(TRICKY)
        self.assertEqual(len(masked), len(TRICKY))
        self.assertNotIn("gaps_in = 99", masked)
        self.assertNotIn("a, b } = c", masked)
        self.assertEqual(masked.count("\n"), TRICKY.count("\n"))

    def test_find_calls_skips_commented_call(self) -> None:
        kinds = [(c.kind) for c in lua_scan.find_calls(TRICKY)]
        self.assertEqual(kinds, ["config", "animation"])

    def test_key_spans(self) -> None:
        calls = lua_scan.find_calls(TRICKY, ("config",))
        table = lua_scan.first_table_arg(TRICKY, calls[0])
        masked = lua_scan.mask(TRICKY)
        span = lua_scan.find_path(masked, table, ["general", "gaps_in"])
        self.assertIsNotNone(span)
        self.assertEqual(TRICKY[span.start:span.end], "5")

    def test_nested_other_branch(self) -> None:
        calls = lua_scan.find_calls(TRICKY, ("config",))
        table = lua_scan.first_table_arg(TRICKY, calls[0])
        masked = lua_scan.mask(TRICKY)
        span = lua_scan.find_path(masked, table, ["other", "x"])
        self.assertEqual(TRICKY[span.start:span.end], "1")

    def test_require_flip(self) -> None:
        text = 'require("animations-low")\n-- require("animations-high")\n'
        out = lua_scan.set_require_active(text, "animations-high")
        active = [ln for ln in out.splitlines() if not ln.lstrip().startswith("--")]
        self.assertEqual(active, ['require("animations-high")'])


if __name__ == "__main__":
    unittest.main()
