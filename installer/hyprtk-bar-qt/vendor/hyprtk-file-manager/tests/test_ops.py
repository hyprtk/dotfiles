import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from hyprtk_file_manager.journal import Journal
from hyprtk_file_manager.ops import JobManager


class FakeTrash:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def trash(self, path: str):
        source = Path(path)
        target = self.root / source.name
        index = 1
        while target.exists():
            target = self.root / f"{source.name}.{index}"
            index += 1
        shutil.move(str(source), str(target))
        return str(target)

    def restore(self, path: str):
        source = Path(path)
        trashed = self.root / source.name
        if not trashed.exists():
            raise FileNotFoundError(str(trashed))
        shutil.move(str(trashed), str(source))


class OpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.dest = self.root / "dest"
        self.dest.mkdir()
        self.events = []
        self.policy = None
        self.manager = JobManager(
            emit=self.events.append,
            journal=Journal(self.root / "journal.json"),
            trash=FakeTrash(self.root / "trash"),
            threaded=False,
            ask_handler=(lambda src, dst: self.policy) if self.policy else None,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def make_manager(self, policy):
        return JobManager(
            emit=self.events.append,
            journal=Journal(self.root / "journal.json"),
            trash=FakeTrash(self.root / "trash"),
            threaded=False,
            ask_handler=lambda src, dst: policy,
        )

    def test_copy_file(self):
        source = self.work / "a.txt"
        source.write_text("hello")
        job = self.manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.assertEqual(job["state"], "done")
        self.assertEqual((self.dest / "a.txt").read_text(), "hello")
        self.assertTrue(source.exists())

    def test_copy_conflict_keep_both(self):
        source = self.work / "a.txt"
        source.write_text("new")
        (self.dest / "a.txt").write_text("old")
        manager = self.make_manager("keep-both")
        manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.assertEqual((self.dest / "a.txt").read_text(), "old")
        self.assertEqual((self.dest / "a (1).txt").read_text(), "new")

    def test_copy_conflict_skip(self):
        source = self.work / "a.txt"
        source.write_text("new")
        (self.dest / "a.txt").write_text("old")
        manager = self.make_manager("skip")
        manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.assertEqual((self.dest / "a.txt").read_text(), "old")

    def test_copy_conflict_replace(self):
        source = self.work / "a.txt"
        source.write_text("new")
        (self.dest / "a.txt").write_text("old")
        manager = self.make_manager("replace")
        manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.assertEqual((self.dest / "a.txt").read_text(), "new")

    def test_copy_directory_recursive(self):
        source = self.work / "folder"
        source.mkdir()
        (source / "one.txt").write_text("1")
        inner = source / "sub"
        inner.mkdir()
        (inner / "two.txt").write_text("2")
        self.manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.assertEqual((self.dest / "folder" / "one.txt").read_text(), "1")
        self.assertEqual((self.dest / "folder" / "sub" / "two.txt").read_text(), "2")

    def test_move_and_undo(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("move", {"sources": [str(source)], "dest": str(self.dest)})
        self.assertFalse(source.exists())
        self.assertTrue((self.dest / "a.txt").exists())
        self.manager.dispatch("undo", {})
        self.assertTrue(source.exists())
        self.assertFalse((self.dest / "a.txt").exists())

    def test_trash_and_undo(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("trash", {"paths": [str(source)]})
        self.assertFalse(source.exists())
        self.manager.dispatch("undo", {})
        self.assertTrue(source.exists())

    def test_delete_is_not_undoable(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("delete", {"paths": [str(source)]})
        self.assertFalse(source.exists())
        job = self.manager.dispatch("undo", {})
        self.assertEqual(job["state"], "failed")

    def test_rename_and_undo(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("rename", {"path": str(source), "name": "b.txt"})
        self.assertTrue((self.work / "b.txt").exists())
        self.manager.dispatch("undo", {})
        self.assertTrue(source.exists())
        self.assertFalse((self.work / "b.txt").exists())

    def test_batch_rename_and_undo(self):
        first = self.work / "a.txt"
        second = self.work / "b.txt"
        first.write_text("a")
        second.write_text("b")
        job = self.manager.dispatch("batchrename", {"renames": [
            {"path": str(first), "name": "one.txt"},
            {"path": str(second), "name": "two.txt"},
        ]})
        self.assertEqual(job["state"], "done")
        self.assertTrue((self.work / "one.txt").exists())
        self.assertTrue((self.work / "two.txt").exists())
        self.manager.dispatch("undo", {})
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())
        self.assertFalse((self.work / "one.txt").exists())

    def test_batch_rename_collision_rejected(self):
        first = self.work / "a.txt"
        second = self.work / "b.txt"
        first.write_text("a")
        second.write_text("b")
        (self.work / "taken.txt").write_text("x")
        with self.assertRaises(FileExistsError):
            self.manager.dispatch("batchrename", {"renames": [
                {"path": str(first), "name": "taken.txt"},
            ]})

    def test_redo_copy(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.manager.dispatch("undo", {})
        self.assertFalse((self.dest / "a.txt").exists())
        self.manager.dispatch("redo", {})
        self.assertTrue((self.dest / "a.txt").exists())

    def test_redo_move(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("move", {"sources": [str(source)], "dest": str(self.dest)})
        self.manager.dispatch("undo", {})
        self.assertTrue(source.exists())
        self.manager.dispatch("redo", {})
        self.assertFalse(source.exists())
        self.assertTrue((self.dest / "a.txt").exists())

    def test_redo_trash(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("trash", {"paths": [str(source)]})
        self.manager.dispatch("undo", {})
        self.assertTrue(source.exists())
        self.manager.dispatch("redo", {})
        self.assertFalse(source.exists())

    def test_redo_rename(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("rename", {"path": str(source), "name": "b.txt"})
        self.manager.dispatch("undo", {})
        self.assertTrue(source.exists())
        self.manager.dispatch("redo", {})
        self.assertTrue((self.work / "b.txt").exists())

    def test_redo_mkdir_and_newfile(self):
        self.manager.dispatch("mkdir", {"path": str(self.work), "name": "dir"})
        self.manager.dispatch("newfile", {"path": str(self.work), "name": "f.txt"})
        self.manager.dispatch("undo", {})
        self.manager.dispatch("undo", {})
        self.assertFalse((self.work / "dir").exists())
        self.assertFalse((self.work / "f.txt").exists())
        self.manager.dispatch("redo", {})
        self.manager.dispatch("redo", {})
        self.assertTrue((self.work / "dir").exists())
        self.assertTrue((self.work / "f.txt").exists())

    def test_redo_persists_across_journal_reload(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("rename", {"path": str(source), "name": "b.txt"})
        self.manager.dispatch("undo", {})
        reloaded = Journal(self.root / "journal.json")
        self.assertIsNotNone(reloaded.last_redo())

    def test_new_operation_clears_redo(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.manager.dispatch("undo", {})
        (self.work / "other.txt").write_text("y")
        self.manager.dispatch("rename", {"path": str(self.work / "other.txt"), "name": "third.txt"})
        job = self.manager.dispatch("redo", {})
        self.assertEqual(job["state"], "failed")

    def test_empty_trash_job(self):
        with patch("hyprtk_file_manager.ops.trash_mod.empty") as empty:
            job = self.manager.dispatch("emptytrash", {})
            self.assertEqual(job["state"], "done")
            empty.assert_called_once()

    def test_mkdir_and_undo(self):
        self.manager.dispatch("mkdir", {"path": str(self.work), "name": "newdir"})
        self.assertTrue((self.work / "newdir").is_dir())
        self.manager.dispatch("undo", {})
        self.assertFalse((self.work / "newdir").exists())

    def test_newfile_and_undo(self):
        self.manager.dispatch("newfile", {"path": str(self.work), "name": "note.txt"})
        self.assertTrue((self.work / "note.txt").exists())
        self.manager.dispatch("undo", {})
        self.assertFalse((self.work / "note.txt").exists())

    def test_copy_undo_trashes_copies(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.dest)})
        self.manager.dispatch("undo", {})
        self.assertFalse((self.dest / "a.txt").exists())
        self.assertTrue(source.exists())

    def test_copy_onto_self_replace_is_noop(self):
        source = self.work / "a.txt"
        source.write_text("keep")
        manager = self.make_manager("replace")
        job = manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.work)})
        self.assertTrue(source.exists())
        self.assertEqual(source.read_text(), "keep")
        self.assertEqual(job["state"], "done")

    def test_copy_onto_self_keep_both(self):
        source = self.work / "a.txt"
        source.write_text("keep")
        manager = self.make_manager("keep-both")
        manager.dispatch("copy", {"sources": [str(source)], "dest": str(self.work)})
        self.assertTrue(source.exists())
        self.assertTrue((self.work / "a (1).txt").exists())

    def test_move_into_same_dir_is_noop(self):
        source = self.work / "a.txt"
        source.write_text("keep")
        self.manager.dispatch("move", {"sources": [str(source)], "dest": str(self.work)})
        self.assertTrue(source.exists())

    def test_destination_inside_source_rejected(self):
        source = self.work / "folder"
        source.mkdir()
        inner = source / "sub"
        inner.mkdir()
        with self.assertRaises(ValueError):
            self.manager.dispatch("copy", {"sources": [str(source)], "dest": str(inner)})

    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            self.manager.dispatch("mkdir", {"path": str(self.work), "name": "a/b"})

    def test_missing_source_reports_error(self):
        job = self.manager.dispatch(
            "copy",
            {"sources": [str(self.work / "nope")], "dest": str(self.dest)},
        )
        self.assertEqual(job["state"], "failed")
        self.assertTrue(job["errors"])

    def test_journal_persists(self):
        source = self.work / "a.txt"
        source.write_text("x")
        self.manager.dispatch("rename", {"path": str(source), "name": "b.txt"})
        reloaded = Journal(self.root / "journal.json")
        self.assertTrue(reloaded.records)
        self.assertEqual(reloaded.records[-1]["kind"], "rename")


if __name__ == "__main__":
    unittest.main()
