"""Guard against version drift between the package and the Nix derivation."""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from hyprtk_bar_qt import __version__  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


class DerivationVersion(unittest.TestCase):
    def test_matches_package_version(self) -> None:
        nix = (REPO_ROOT / "derivation.nix").read_text()
        match = re.search(r'^\s*version\s*=\s*"([^"]+)"', nix, re.MULTILINE)
        self.assertIsNotNone(match, "no version attribute in derivation.nix")
        self.assertEqual(match.group(1), __version__)


if __name__ == "__main__":
    unittest.main()
