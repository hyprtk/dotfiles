"""Raw Lua file read/save used by the per-section editor."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import make_tree
from config_manager import lua_probe, state
from config_manager.rpc import handle


class FileEditor(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make_tree(Path(self.tmp.name))
        self._old = state.BACKUP_ROOT
        state.BACKUP_ROOT = Path(self.tmp.name) / "backups"

    def tearDown(self) -> None:
        state.BACKUP_ROOT = self._old
        self.tmp.cleanup()

    def _read(self, file: str) -> str:
        res = handle({"id": 1, "method": "file.read",
                      "params": {"root": str(self.root), "file": file}})
        self.assertIn("result", res, res)
        return res["result"]["text"]

    def test_read(self) -> None:
        text = self._read("startup.lua")
        self.assertIn('hl.bind("SUPER, Return"', text)

    def test_save_rejects_syntax_errors_and_keeps_file(self) -> None:
        original = self._read("startup.lua")
        res = handle({"id": 2, "method": "file.save",
                      "params": {"root": str(self.root), "file": "startup.lua",
                                 "text": original + "\nthis is not lua("}})
        self.assertIn("error", res, res)
        self.assertEqual((self.root / "startup.lua").read_text(encoding="utf-8"), original)

    def test_save_writes_and_reprobes(self) -> None:
        original = self._read("startup.lua")
        changed = original.replace('hl.env("XCURSOR_THEME", "Bibata-Modern-Ice")',
                                   'hl.env("XCURSOR_THEME", "Adwaita")')
        res = handle({"id": 3, "method": "file.save",
                      "params": {"root": str(self.root), "file": "startup.lua",
                                 "text": changed}})
        self.assertIn("result", res, res)
        self.assertTrue(res["result"]["changed"])
        self.assertEqual(lua_probe.probe(self.root)["env"]["XCURSOR_THEME"], "Adwaita")

    def test_save_inactive_module(self) -> None:
        text = self._read("animations-low.lua")
        changed = text.replace('leaf = "windows"', 'leaf = "fade"')
        res = handle({"id": 4, "method": "file.save",
                      "params": {"root": str(self.root), "file": "animations-low.lua",
                                 "text": changed}})
        self.assertIn("result", res, res)
        low = lua_probe.probe(self.root, main="animations-low.lua")
        self.assertIn("fade", low["animations"])


if __name__ == "__main__":
    unittest.main()
