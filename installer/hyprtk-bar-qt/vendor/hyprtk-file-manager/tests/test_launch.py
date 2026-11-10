import os
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
