"""Shared fixture tree for the tests (no dependency on the live config)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

MAIN = """\
require("general")
-- require("animations-low")
require("animations-high")
require("startup")
"""

GENERAL = """\
local base = 3

hl.config({
    general = {
        gaps_in = base + 2,
        gaps_out = 20,
        border_size = 2,
    },
    decoration = {
        rounding = 10, -- keep me
        blur = { enabled = true, size = 6 },
        shadow = { enabled = true, color = 0x66000000 },
    },
})
"""

HIGH = """\
hl.curve("wind", { type = "bezier", points = { { 0.05, 0.9 }, { 0.1, 1.05 } } })
hl.curve("rubber", { type = "spring", mass = 1, stiffness = 70, damping = 10 })

hl.animation({
    leaf = "windows",
    enabled = true,
    speed = 6,
    bezier = "wind",
    style = "slide",
})

hl.animation({
    leaf = "fade",
    enabled = true,
    speed = 10,
    bezier = "default",
})
"""

LOW = """\
hl.animation({ leaf = "windows", enabled = false })
"""

STARTUP = """\
hl.env("XCURSOR_THEME", "Bibata-Modern-Ice")
hl.bind("SUPER, Return", "exec", { terminal = "kitty" })
hl.monitor({ output = "DP-1", mode = "2560x1440@144", scale = 1.0 })
hl.window_rule({ match = { class = "^(kitty)$" }, float = true })
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
hl.on("hyprland.start", function()
    hl.exec_cmd("waybar")
end)
hl.dsp.window.close()
"""


def make_tree(base: Path, *, main: str = MAIN) -> Path:
    root = Path(base) / "hypr"
    root.mkdir(parents=True, exist_ok=True)
    (root / "hyprland.lua").write_text(main, encoding="utf-8")
    (root / "general.lua").write_text(GENERAL, encoding="utf-8")
    (root / "animations-high.lua").write_text(HIGH, encoding="utf-8")
    (root / "animations-low.lua").write_text(LOW, encoding="utf-8")
    (root / "startup.lua").write_text(STARTUP, encoding="utf-8")
    return root
