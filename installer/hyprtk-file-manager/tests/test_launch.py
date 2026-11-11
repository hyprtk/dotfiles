import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hyprtk_file_manager import launch


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_terminal_argv_is_executable(self):
        argv = launch.terminal_argv(str(self.root))
        self.assertTrue(argv)
        self.assertTrue(os.path.isabs(argv[0]))
        self.assertTrue(os.access(argv[0], os.X_OK))

    def test_missing_path(self):
        with self.assertRaises(NotADirectoryError):
            launch.open_terminal(str(self.root / "nope"))

    def test_forward_env_is_list(self):
        self.assertIsInstance(launch._forward_env(), list)

    def test_open_as_root_uses_fm_launcher(self):
        with patch("hyprtk_file_manager.launch.shutil.which",
                   return_value="/usr/bin/pkexec"), \
                patch("hyprtk_file_manager.launch.subprocess.Popen") as popen:
            result = launch.open_as_root(str(self.root))
        argv = popen.call_args.args[0]
        self.assertEqual(argv[0], "pkexec")
        self.assertEqual(argv[1], "env")
        self.assertIn(
            "HYPRTK_WAL_HOME=" + (os.environ.get("HYPRTK_WAL_HOME") or str(Path.home())),
            argv,
        )
        self.assertEqual(argv[-2], str(launch.launcher_path()))
        self.assertEqual(argv[-1], str(self.root))
        self.assertEqual(result["kind"], "open_root_fm")

    def test_open_as_root_from_file_uses_parent(self):
        target = self.root / "note.txt"
        target.write_text("x", encoding="utf-8")
        with patch("hyprtk_file_manager.launch.shutil.which",
                   return_value="/usr/bin/pkexec"), \
                patch("hyprtk_file_manager.launch.subprocess.Popen") as popen:
            result = launch.open_as_root(str(target))
        self.assertEqual(popen.call_args.args[0][-1], str(self.root))
        self.assertEqual(result["path"], str(self.root))

    def test_open_as_root_requires_pkexec(self):
        with patch("hyprtk_file_manager.launch.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                launch.open_as_root(str(self.root))


if __name__ == "__main__":
    unittest.main()
