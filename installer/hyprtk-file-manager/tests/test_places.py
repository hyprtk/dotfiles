import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hyprtk_file_manager import places


class PlacesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.config = self.home / ".config"
        self.config.mkdir()
        for name in ("Downloads", "Documents", "Projects"):
            (self.home / name).mkdir()
        (self.home / ".local" / "share" / "Trash" / "files").mkdir(parents=True)
        (self.config / "user-dirs.dirs").write_text(
            'XDG_DOWNLOAD_DIR="$HOME/Downloads"\nXDG_DOCUMENTS_DIR="$HOME/Documents"\n'
        )
        gtk = self.config / "gtk-3.0"
        gtk.mkdir()
        (gtk / "bookmarks").write_text(
            "file://" + str(self.home / "Downloads") + " Downloads\n"
            "file://" + str(self.home / "Downloads") + " Downloads again\n"
            "file://" + str(self.home / "Projects") + " Projects\n"
            "file:///does/not/exist missing\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_user_dirs(self):
        dirs = places.parse_user_dirs(self.home, self.config)
        self.assertEqual(dirs["Downloads"], str(self.home / "Downloads"))
        self.assertEqual(dirs["Documents"], str(self.home / "Documents"))
        self.assertEqual(dirs["Music"], str(self.home / "Music"))

    def test_places_merges_defaults_and_custom(self):
        items = places.places(self.home, self.config)
        names = [item["name"] for item in items]
        self.assertEqual(names[0], "Home")
        self.assertIn("Downloads", names)
        self.assertIn("Documents", names)
        self.assertIn("Trash", names)
        self.assertIn("Projects", names)
        self.assertNotIn("Music", names)
        custom = [item for item in items if item.get("custom")]
        self.assertEqual([item["name"] for item in custom], ["Projects"])

    def test_bookmarks(self):
        items = places.bookmarks(self.home, self.config)
        self.assertEqual([item["name"] for item in items], ["Downloads", "Projects"])
        self.assertTrue(all(item["custom"] for item in items))

    def test_add_and_remove_bookmark(self):
        target = self.home / "New Place"
        target.mkdir()
        first = places.add_bookmark(str(target), home=self.home, config=self.config)
        self.assertTrue(first["added"])
        second = places.add_bookmark(str(target), home=self.home, config=self.config)
        self.assertFalse(second["added"])
        names = [item["name"] for item in places.bookmarks(self.home, self.config)]
        self.assertIn("New Place", names)
        removed = places.remove_bookmark(str(target), home=self.home, config=self.config)
        self.assertTrue(removed["removed"])
        names = [item["name"] for item in places.bookmarks(self.home, self.config)]
        self.assertNotIn("New Place", names)

    def test_network_bookmark(self):
        uri = "smb://192.168.0.20/Documents"
        added = places.add_bookmark(uri, label="Docs", home=self.home, config=self.config)
        self.assertTrue(added["added"])
        self.assertTrue(added["uri"])
        items = places.bookmarks(self.home, self.config)
        match = [item for item in items if item.get("uri")]
        self.assertEqual([item["name"] for item in match], ["Docs"])
        self.assertEqual(match[0]["path"], uri)
        self.assertEqual(match[0]["icon"], "folder-remote")
        again = places.add_bookmark(uri, home=self.home, config=self.config)
        self.assertFalse(again["added"])
        self.assertIn(uri, [item["path"] for item in places.places(self.home, self.config)])
        removed = places.remove_bookmark(uri, home=self.home, config=self.config)
        self.assertTrue(removed["removed"])
        self.assertFalse(any(item.get("uri") for item in places.bookmarks(self.home, self.config)))

    def test_parse_devices(self):
        data = [
            {
                "name": "sda", "fstype": None, "rm": False, "tran": "sata",
                "children": [
                    {"name": "sda1", "label": "Documents", "fstype": "ntfs",
                     "size": "1.4T", "mountpoints": ["/mnt/Documents"], "rm": False, "tran": "sata"},
                ],
            },
            {
                "name": "sdb", "fstype": None, "rm": False, "tran": "usb",
                "children": [
                    {"name": "sdb1", "label": "USB", "fstype": "exfat",
                     "size": "32G", "mountpoints": [], "rm": False, "tran": None},
                ],
            },
            {
                "name": "nvme1n1", "fstype": None, "rm": False, "tran": "nvme",
                "children": [
                    {"name": "nvme1n1p2", "label": None, "fstype": "ext4",
                     "size": "300G", "mountpoints": ["/", "/home"], "rm": False, "tran": None},
                ],
            },
        ]
        devices = places.parse_devices(data)
        by_device = {item["device"]: item for item in devices}
        self.assertEqual(by_device["/dev/sda1"]["name"], "Documents")
        self.assertTrue(by_device["/dev/sda1"]["mounted"])
        self.assertEqual(by_device["/dev/sdb1"]["icon"], "drive-removable-media-usb")
        self.assertTrue(by_device["/dev/sdb1"]["removable"])
        self.assertTrue(by_device["/dev/sdb1"]["external"])
        self.assertEqual(by_device["/dev/sdb1"]["tran"], "usb")
        self.assertFalse(by_device["/dev/sda1"]["external"])
        self.assertFalse(by_device["/dev/sdb1"]["mounted"])
        self.assertIsNone(by_device["/dev/sdb1"]["path"])
        mounted_names = {item["name"] for item in devices if item["device"] == "/dev/nvme1n1p2"}
        self.assertEqual(mounted_names, {"System", "home"})

    def test_external_transport_inherited_from_disk(self):
        data = [{
            "name": "sdc", "fstype": None, "rm": False, "tran": "usb",
            "children": [{
                "name": "sdc1", "label": "OneTouch", "fstype": "ntfs",
                "mountpoints": [], "rm": False, "tran": None,
            }],
        }]
        device = places.parse_devices(data)[0]
        self.assertTrue(device["removable"])
        self.assertEqual(device["tran"], "usb")

    def test_is_system_partition(self):
        for parttype in ("c12a7328-f81f-11d2-ba4b-00a0c93ec93b", "0xef",
                         "e3c9e316-0b5c-4db8-817d-f92df00215ae",
                         "de94bba4-06d1-4d40-a16a-bfd50179d6ac",
                         "21686148-6449-6e6f-744e-656564454649"):
            self.assertTrue(places._is_system_partition(
                {"parttype": parttype, "path": None}))
        self.assertTrue(places._is_system_partition(
            {"parttype": None, "path": "/boot"}))
        self.assertTrue(places._is_system_partition(
            {"parttype": None, "path": "/boot/efi"}))
        self.assertFalse(places._is_system_partition(
            {"parttype": "0x7", "path": None}))
        self.assertFalse(places._is_system_partition(
            {"parttype": None, "path": "/mnt/Documents"}))

    def test_size_label(self):
        self.assertEqual(places._size_label("494.1G"), "531 GB Volume")
        self.assertEqual(places._size_label("155.2G"), "167 GB Volume")
        self.assertEqual(places._size_label("279.4G"), "300 GB Volume")
        self.assertEqual(places._size_label("2.7T"), "3.0 TB Volume")
        self.assertEqual(places._size_label(""), "")

    def test_filter_devices_filesystem_and_external(self):
        rules = {"mountpoints": {"/"}, "devices": set(), "uuids": set(),
                 "labels": set(), "partuuids": set(), "partlabels": set()}
        root = {"name": "System", "path": "/", "icon": "drive-harddisk",
                "device": "/dev/nvme1n1p2", "removable": False, "external": False,
                "fs": "ext4", "size": "", "mounted": True, "label": "",
                "uuid": None, "partuuid": None, "partlabel": None, "tran": "nvme"}
        stick = {"name": "OneTouch", "path": None, "icon": "drive-harddisk",
                 "device": "/dev/sdc1", "removable": True, "external": True,
                 "fs": "ntfs", "size": "", "mounted": False, "label": "OneTouch",
                 "uuid": "X", "partuuid": None, "partlabel": None, "tran": "usb"}
        out = places._filter_devices([root, stick], rules)
        self.assertEqual([item["name"] for item in out], ["File System", "OneTouch"])
        self.assertEqual(out[0]["path"], "/")
        self.assertFalse(out[0]["external"])
        self.assertTrue(out[1]["external"])

    def test_filter_devices_synthesizes_filesystem(self):
        rules = {"mountpoints": set(), "devices": set(), "uuids": set(),
                 "labels": set(), "partuuids": set(), "partlabels": set()}
        out = places._filter_devices([], rules)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["name"], "File System")
        self.assertEqual(out[0]["path"], "/")

    def test_filter_devices_keeps_internal_unmounted_hides_system(self):
        rules = {"mountpoints": set(), "devices": set(), "uuids": set(),
                 "labels": set(), "partuuids": set(), "partlabels": set()}
        base = {"icon": "drive-harddisk", "removable": False, "external": False,
                "size": "", "mounted": False, "uuid": None, "partuuid": None,
                "partlabel": None, "tran": "nvme"}
        windows = {**base, "name": "531 GB Volume", "path": None,
                   "device": "/dev/nvme1n1p2", "fs": "ntfs",
                   "parttype": "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"}
        efi = {**base, "name": "EFI", "path": None, "device": "/dev/nvme1n1p4",
               "fs": "vfat", "parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"}
        boot = {**base, "name": "VTOYEFI", "path": None, "device": "/dev/sdc2",
                "fs": "vfat", "parttype": "0xef"}
        out = places._filter_devices([windows, efi, boot], rules)
        self.assertEqual([item["name"] for item in out], ["File System", "531 GB Volume"])

    def test_eject_device_unmounts_only(self):
        calls = []

        def fake(cmd, **kwargs):
            calls.append(cmd)
            if cmd[:2] == ["udisksctl", "unmount"]:
                return subprocess.CompletedProcess(cmd, 0, "Unmounted /dev/sdc1.\n", "")
            raise AssertionError(cmd)

        with patch.object(places, "devices", return_value=[
                {"device": "/dev/sdc1", "path": "/run/media/hyprtk/OneTouch"}]):
            with patch("hyprtk_file_manager.places.subprocess.run", side_effect=fake):
                result = places.eject_device("/dev/sdc1")
        self.assertTrue(result["unmounted"])
        self.assertTrue(result["ejected"])
        self.assertFalse(result["powered_off"])
        self.assertEqual(result["path"], "/run/media/hyprtk/OneTouch")
        self.assertFalse(any(cmd[:2] == ["udisksctl", "power-off"] for cmd in calls))

    def test_eject_device_busy(self):
        def fake(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, "", "Error unmounting /dev/sdc1: target is busy")

        with patch.object(places, "devices", return_value=[
                {"device": "/dev/sdc1", "path": "/run/media/hyprtk/OneTouch"}]):
            with patch("hyprtk_file_manager.places.subprocess.run", side_effect=fake):
                with self.assertRaises(RuntimeError):
                    places.eject_device("/dev/sdc1")

    def test_mount_device(self):
        proc = subprocess.CompletedProcess(
            ["udisksctl"], 0, stdout="Mounted /dev/sdc1 at /run/media/hyprtk/OneTouch.\n", stderr=""
        )
        with patch("hyprtk_file_manager.places.subprocess.run", return_value=proc):
            result = places.mount_device("/dev/sdc1")
        self.assertEqual(result["path"], "/run/media/hyprtk/OneTouch")

    def test_mount_device_already_mounted(self):
        proc = subprocess.CompletedProcess(
            ["udisksctl"], 0, stdout="", stderr="Error: Device /dev/sdc1 is already mounted at `/mnt/OneTouch`.\n"
        )
        with patch("hyprtk_file_manager.places.subprocess.run", return_value=proc):
            result = places.mount_device("/dev/sdc1")
        self.assertEqual(result["path"], "/mnt/OneTouch")

    def test_fstab_filter(self):
        fstab = self.home / "fstab"
        fstab.write_text(
            "UUID=ABC-123 /mnt/Docs ntfs defaults 0 0\n"
            "/dev/sdb1 /mnt/Apps ext4 defaults 0 0\n"
            "UUID=1111 none swap sw 0 0\n"
        )
        rules = places.parse_fstab(str(fstab))
        self.assertIn("/mnt/Docs", rules["mountpoints"])
        self.assertIn("ABC-123", rules["uuids"])
        self.assertIn("/dev/sdb1", rules["devices"])
        inside = {"name": "Docs", "path": "/mnt/Docs", "device": "/dev/sda1", "uuid": "abc-123"}
        outside = {"name": "USB", "path": None, "device": "/dev/sdc1", "uuid": "DEF"}
        self.assertTrue(places._is_fstab(inside, rules))
        self.assertFalse(places._is_fstab(outside, rules))

    def test_drives_is_a_list(self):
        self.assertIsInstance(places.drives(), list)


if __name__ == "__main__":
    unittest.main()
