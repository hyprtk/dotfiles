"""Transaction/backup tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import make_tree

from config_manager import lua_edit, lua_probe, state, verify


class Session(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_tree(Path(self.tmp.name))
        self._old_backup = state.BACKUP_ROOT
        state.BACKUP_ROOT = Path(self.tmp.name) / "backups"
        self.addCleanup(lambda: setattr(state, "BACKUP_ROOT", self._old_backup))

    def test_sequential_edits_compose(self) -> None:
        session = state.Session(self.root, "test compose")
        for path, value in (("decoration.rounding", 12), ("general.gaps_out", 30)):
            session.write(lua_edit.set_config(self.root, path, value))
        verify.verify_specs(self.root, [
            {"type": "config", "path": "decoration.rounding", "value": 12},
            {"type": "config", "path": "general.gaps_out", "value": 30},
        ])
        manifest = session.finish("ok")
        self.assertEqual(manifest["status"], "ok")
        self.assertEqual(sorted(manifest["files"]), ["general.lua"])

    def test_rollback_restores_bytes(self) -> None:
        original = (self.root / "general.lua").read_text()
        session = state.Session(self.root, "test rollback")
        session.write(lua_edit.set_config(self.root, "decoration.rounding", 12))
        self.assertNotEqual((self.root / "general.lua").read_text(), original)

        with self.assertRaises(verify.VerifyError):
            verify.verify_specs(self.root, [
                {"type": "config", "path": "decoration.rounding", "value": 99},
            ])
        session.rollback()
        self.assertEqual((self.root / "general.lua").read_text(), original)

    def test_backup_restore(self) -> None:
        original = (self.root / "general.lua").read_text()
        session = state.Session(self.root, "test backup")
        session.write(lua_edit.set_config(self.root, "decoration.rounding", 12))
        manifest = session.finish("ok")

        self.assertTrue((Path(state.BACKUP_ROOT) / manifest["stamp"] / "general.lua").is_file())
        self.assertIn(manifest["stamp"], [b["stamp"] for b in state.backups()])

        state.restore(manifest["stamp"], root=self.root)
        self.assertEqual((self.root / "general.lua").read_text(), original)

    def test_noop_session_has_no_backup(self) -> None:
        session = state.Session(self.root, "nothing")
        self.assertIsNone(session.finish("ok"))


class FileSafety(unittest.TestCase):
    def test_atomic_write_keeps_mode(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.lua"
            path.write_text("a = 1\n")
            path.chmod(0o640)
            state.atomic_write(path, "a = 2\n")
            self.assertEqual(path.read_text(), "a = 2\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
