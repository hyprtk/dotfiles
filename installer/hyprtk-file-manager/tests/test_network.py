import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hyprtk_file_manager import network


class NetworkTests(unittest.TestCase):
    def test_parse_ip_output(self):
        text = (
            "2: enp7s0    inet 192.168.0.192/24 brd 192.168.0.255 scope global\n"
            "3: wlp6s0    inet 192.168.0.183/24 brd 192.168.0.255 scope global\n"
            "4: virbr0    inet 192.168.122.1/24 brd 192.168.122.255 scope global\n"
        )
        self.assertEqual(network.parse_ip_output(text), ["192.168.0.0/24"])

    def test_parse_avahi_output(self):
        text = (
            "=;eth0;IPv4;nas;_smb._tcp;local;nas.local;192.168.0.20;445;txt\n"
            "=;eth0;IPv4;nas;_nfs._tcp;local;nas.local;192.168.0.20;2049;txt\n"
        )
        found = network.parse_avahi_output(text, "smb")
        self.assertIn("192.168.0.20", found)
        self.assertEqual(found["192.168.0.20"]["name"], "nas")

    def test_smb_shares(self):
        proc = subprocess.CompletedProcess(
            ["smbclient"], 0, stdout="Disk|public|Public share\nDisk|ADMIN$|Remote Admin\n", stderr=""
        )
        with patch("hyprtk_file_manager.network.shutil.which", return_value="/usr/bin/smbclient"), \
                patch("hyprtk_file_manager.network.subprocess.run", return_value=proc):
            shares = network.smb_shares("192.168.0.20")
        self.assertEqual([share["name"] for share in shares], ["public"])
        self.assertEqual(shares[0]["uri"], "smb://192.168.0.20/public")

    def test_scan_merges_sources(self):
        with patch("hyprtk_file_manager.network.local_subnets", return_value=["192.168.0.0/24"]), \
                patch("hyprtk_file_manager.network.port_scan",
                      return_value={"192.168.0.20": {"smb"}, "192.168.0.30": {"nfs"}}), \
                patch("hyprtk_file_manager.network.avahi_services",
                      return_value={"192.168.0.20": {"name": "nas", "services": {"nfs"}}}), \
                patch("hyprtk_file_manager.network.smb_shares",
                      return_value=[{"name": "public", "uri": "smb://192.168.0.20/public"}]):
            result = network.scan()
        self.assertEqual(result["kind"], "network")
        self.assertEqual(len(result["devices"]), 2)
        by_host = {device["host"]: device for device in result["devices"]}
        self.assertEqual(by_host["192.168.0.20"]["name"], "nas")
        self.assertEqual(set(by_host["192.168.0.20"]["services"]), {"smb", "nfs"})
        self.assertEqual(by_host["192.168.0.20"]["shares"][0]["name"], "public")

    def test_gvfs_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            gvfs = Path(tmp) / "gvfs"
            gvfs.mkdir()
            (gvfs / "smb-share:server=192.168.0.20,share=public").mkdir()
            with patch.dict("os.environ", {"XDG_RUNTIME_DIR": tmp}):
                found = network._find_mount("smb://192.168.0.20/public")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "smb-share:server=192.168.0.20,share=public")

    def test_credential_uri(self):
        self.assertEqual(
            network._credential_uri("smb://host/share", "u", "p@ss"),
            "smb://u:p%40ss@host/share",
        )

    def test_mount_uses_credentials(self):
        with patch("hyprtk_file_manager.network._gio_available", return_value=True), \
                patch("hyprtk_file_manager.network._gio_mount") as gio_mount, \
                patch("hyprtk_file_manager.network._find_mount",
                      return_value=Path("/run/user/1000/gvfs/smb-share:server=host,share=share")):
            result = network.mount("smb://host/share", "user", "pass", "WORKGROUP")
        gio_mount.assert_called_once_with("smb://host/share", "user", "pass", "WORKGROUP", False)
        self.assertEqual(result["kind"], "network_mount")
        self.assertEqual(result["path"], "/run/user/1000/gvfs/smb-share:server=host,share=share")

    def test_mount_unsupported(self):
        with self.assertRaises(ValueError):
            network.mount("ftp://example.com/share")

    def test_mount_requires_share(self):
        with self.assertRaises(ValueError):
            network.mount("smb://host/")
        with self.assertRaises(ValueError):
            network.mount("smb://host")

    def test_list_shares(self):
        children = [
            {"name": "documents", "display": "Documents", "type": 6},
            {"name": "IPC$", "display": "IPC$", "type": 6},
            {"name": "readme.txt", "display": "readme.txt", "type": 1},
        ]
        with patch.object(network, "_gio_available", return_value=True), \
                patch.object(network, "_gio_children", return_value=children):
            result = network.list_shares("smb://host/", "u", "p", "WG")
        self.assertEqual(result["kind"], "network_shares")
        self.assertEqual(result["host"], "host")
        self.assertEqual([share["name"] for share in result["shares"]], ["Documents"])
        self.assertEqual(result["shares"][0]["uri"], "smb://host/documents")

    def test_list_shares_nfs(self):
        with patch.object(network, "_nfs_exports", return_value=["/export/data"]):
            result = network.list_shares("nfs://host/")
        self.assertEqual(result["kind"], "network_shares")
        self.assertEqual(result["shares"][0]["uri"], "nfs://host/export/data")

    def test_uri_for_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            gvfs = Path(tmp) / "gvfs"
            target = gvfs / "smb-share:server=192.168.0.20,share=documents" / "sub dir"
            target.mkdir(parents=True)
            with patch.dict("os.environ", {"XDG_RUNTIME_DIR": tmp}):
                self.assertEqual(
                    network.uri_for_path(str(target)),
                    "smb://192.168.0.20/documents/sub%20dir",
                )

    def test_find_mount_matches_share_case_insensitively(self):
        with tempfile.TemporaryDirectory() as tmp:
            gvfs = Path(tmp) / "gvfs"
            gvfs.mkdir()
            wanted = gvfs / "smb-share:server=192.168.0.20,share=documents"
            wanted.mkdir()
            (gvfs / "smb-share:server=192.168.0.20,share=music").mkdir()
            with patch.dict("os.environ", {"XDG_RUNTIME_DIR": tmp}):
                found = network._find_mount("smb://192.168.0.20/Documents")
        self.assertEqual(found, wanted)


if __name__ == "__main__":
    unittest.main()
