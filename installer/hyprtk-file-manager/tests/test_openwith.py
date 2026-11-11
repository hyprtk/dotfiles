import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hyprtk_file_manager import openwith


def make_desktop(directory: Path, name: str, body: str) -> Path:
    applications = directory / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    path = applications / name
    path.write_text("[Desktop Entry]\n" + body, encoding="utf-8")
    return path


class OpenWithTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.image = self.root / "photo.png"
        self.image.write_bytes(b"\x89PNG\r\n")
        self.env = patch.dict(os.environ, {
            "XDG_DATA_HOME": str(self.home),
            "XDG_DATA_DIRS": str(self.root / "system"),
            "HOME": str(self.home),
        })
        self.env.start()
        self.gio = patch("hyprtk_file_manager.openwith._gio_available", return_value=False)
        self.gio.start()

    def tearDown(self):
        self.gio.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_lists_matching_desktop_apps(self):
        make_desktop(self.home, "painter.desktop",
                     "Name=Painter\nExec=painter %f\nIcon=painter\n"
                     "MimeType=image/png;\n")
        make_desktop(self.home, "text.desktop",
                     "Name=Editor\nExec=editor %f\nMimeType=text/plain;\n")
        make_desktop(self.home, "hidden.desktop",
                     "Name=Hidden\nExec=hidden %f\nNoDisplay=true\n"
                     "MimeType=image/png;\n")
        result = openwith.applications(str(self.image))
        self.assertEqual(result["kind"], "open_with")
        self.assertEqual(result["mime"], "image/png")
        self.assertEqual([app["name"] for app in result["apps"]], ["Painter"])
        self.assertEqual(result["apps"][0]["id"], "painter.desktop")
        self.assertFalse(result["apps"][0]["default"])

    def test_system_apps_are_seen(self):
        system = self.root / "system"
        make_desktop(system, "viewer.desktop",
                     "Name=Viewer\nExec=viewer %U\nMimeType=image/png;\n")
        result = openwith.applications(str(self.image))
        self.assertEqual([app["name"] for app in result["apps"]], ["Viewer"])

    def test_skips_missing_tryexec(self):
        make_desktop(self.home, "ghost.desktop",
                     "Name=Ghost\nExec=ghost %f\nTryExec=no-such-binary-xyz\n"
                     "MimeType=image/png;\n")
        result = openwith.applications(str(self.image))
        self.assertEqual(result["apps"], [])

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            openwith.applications(str(self.root / "nope.png"))

    def test_exec_argv_placeholders(self):
        target = "/tmp/a b.mp4"
        self.assertEqual(
            openwith._exec_argv("vlc --started-from-file %U", target),
            ["vlc", "--started-from-file", target],
        )
        self.assertEqual(
            openwith._exec_argv("app --file=%f %i", target),
            ["app", f"--file={target}"],
        )
        self.assertEqual(
            openwith._exec_argv("app", target),
            ["app", target],
        )

    def test_launch_uses_gio(self):
        entry = {
            "id": "painter.desktop", "name": "Painter",
            "desktopFile": "/apps/painter.desktop", "argv": [],
        }
        with patch("hyprtk_file_manager.openwith._entries", return_value=[entry]), \
                patch("hyprtk_file_manager.openwith.shutil.which",
                      return_value="/usr/bin/gio"), \
                patch("hyprtk_file_manager.openwith.subprocess.Popen") as popen:
            result = openwith.launch(str(self.image), "painter.desktop")
        popen.assert_called_once()
        self.assertEqual(
            popen.call_args.args[0],
            ["gio", "launch", "/apps/painter.desktop", str(self.image)],
        )
        self.assertEqual(result["kind"], "open_with_launch")

    def test_launch_without_gio_uses_exec(self):
        desktop = make_desktop(self.home, "painter.desktop",
                               "Name=Painter\nExec=painter --open %f\n"
                               "MimeType=image/png;\n")
        with patch("hyprtk_file_manager.openwith.shutil.which", return_value=None), \
                patch("hyprtk_file_manager.openwith.subprocess.Popen") as popen:
            openwith.launch(str(self.image), "painter.desktop")
        self.assertEqual(
            popen.call_args.args[0],
            ["painter", "--open", str(self.image)],
        )
        self.assertTrue(desktop.exists())

    def test_launch_unknown_app(self):
        with self.assertRaises(ValueError):
            openwith.launch(str(self.image), "missing.desktop")

    def test_order_default_then_recommended(self):
        entries = [
            {"id": "b.desktop", "name": "Beta", "desktopFile": "", "argv": [],
             "default": False, "recommended": False},
            {"id": "r.desktop", "name": "Rec", "desktopFile": "", "argv": [],
             "default": False, "recommended": True},
            {"id": "d.desktop", "name": "Default", "desktopFile": "", "argv": [],
             "default": True, "recommended": True},
        ]
        with patch("hyprtk_file_manager.openwith._gio_available", return_value=True), \
                patch("hyprtk_file_manager.openwith._gio_entries", return_value=entries):
            result = openwith.applications(str(self.image))
        self.assertEqual(
            [app["id"] for app in result["apps"]],
            ["d.desktop", "r.desktop", "b.desktop"],
        )


if __name__ == "__main__":
    unittest.main()
