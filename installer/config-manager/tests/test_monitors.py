"""Live monitor/output parsing (nwg-displays' hyprctl approach)."""

from __future__ import annotations

import unittest

from support import ROOT  # noqa: F401  (sets sys.path)
from config_manager import monitors

ALL = [
    {
        "name": "DP-1",
        "make": "Samsung Electric Company",
        "model": "C49J89x",
        "serial": "HNTR300215",
        "width": 3840, "height": 1080, "refreshRate": 143.99899,
        "x": 0, "y": 0, "scale": 1, "transform": 0,
        "disabled": False, "focused": True,
        "availableModes": [
            "3840x1080@59.97Hz", "3840x1080@144.00Hz",
            "1920x1080@60.00Hz", "1920x1080@60.00Hz",
            "1280x720@59.94Hz",
        ],
    },
    {
        "name": "HDMI-A-1",
        "width": 1920, "height": 1080, "refreshRate": 60.0,
        "disabled": True,
        "availableModes": ["1920x1080@60.00Hz", "1280x720@60.00Hz"],
    },
]


class Parse(unittest.TestCase):
    def test_modes_are_normalized_and_deduplicated(self):
        result = monitors.parse(ALL, [{"name": "DP-1"}])
        dp = result[0]
        values = [m["value"] for m in dp["modes"]]
        self.assertEqual(values.count("1920x1080@60.00"), 1)
        self.assertIn("3840x1080@144.00", values)
        self.assertEqual(dp["modes"][0]["label"], "3840x1080 @ 59.97 Hz")
        self.assertTrue(dp["active"])
        self.assertFalse(result[1]["active"])

    def test_current_mode_is_added_when_missing(self):
        payload = [{
            "name": "DP-2", "width": 2560, "height": 1440,
            "refreshRate": 165.0, "availableModes": ["1920x1080@60.00Hz"],
        }]
        result = monitors.parse(payload, None)
        values = [m["value"] for m in result[0]["modes"]]
        self.assertEqual(values[0], "2560x1440@165.00")

    def test_unknown_modes_are_ignored(self):
        payload = [{"name": "X", "availableModes": ["bogus", "1024x768@60.00Hz"]}]
        result = monitors.parse(payload, [])
        self.assertEqual([m["value"] for m in result[0]["modes"]], ["1024x768@60.00"])


if __name__ == "__main__":
    unittest.main()
