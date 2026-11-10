import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_serve_answers_ping(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "backend")
        proc = subprocess.run(
            [sys.executable, "-u", "-m", "hyprtk_file_manager.cli", "serve"],
            input='{"id": 1, "method": "ping"}\n',
            text=True,
            capture_output=True,
            env=env,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"kind": "ping"', proc.stdout)

    def test_version(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "backend")
        proc = subprocess.run(
            [sys.executable, "-u", "-m", "hyprtk_file_manager.cli", "version"],
            text=True,
            capture_output=True,
            env=env,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("hyprtk-file-manager", proc.stdout)


if __name__ == "__main__":
    unittest.main()
