"""Discover LAN storage hosts/shares and mount them via GVfs."""

from __future__ import annotations

import concurrent.futures
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

PORTS = {445: "smb", 139: "smb", 2049: "nfs", 548: "afp"}
AVAHI_TYPES = {
    "_smb._tcp": "smb",
    "_nfs._tcp": "nfs",
    "_afpovertcp._tcp": "afp",
}
SKIP_INTERFACES = ("lo", "virbr", "docker", "br-", "veth", "tun", "tap")


def parse_ip_output(text: str) -> list[str]:
    nets: list[str] = []
    for line in text.splitlines():
        match = re.search(r"^\d+:\s+(\S+)\s+inet (\d+\.\d+\.\d+\.\d+)/(\d+)", line)
        if not match:
            continue
        iface, address, _prefix = match.group(1), match.group(2), match.group(3)
        if iface.startswith(SKIP_INTERFACES):
            continue
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if ip.is_loopback or not ip.is_private:
            continue
        network = str(ipaddress.ip_network(f"{address}/24", strict=False))
        if network not in nets:
            nets.append(network)
    return nets


def local_subnets() -> list[str]:
    try:
        proc = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "scope", "global"],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return parse_ip_output(proc.stdout)


def _probe(host: str) -> tuple[str, set[str]]:
    services: set[str] = set()
    for port, service in PORTS.items():
        try:
            with socket.create_connection((host, port), timeout=0.25):
                services.add(service)
        except OSError:
            pass
    return host, services


def port_scan(subnets: list[str], limit: int = 512) -> dict[str, set[str]]:
    hosts: list[str] = []
    for cidr in subnets:
        try:
            hosts.extend(str(ip) for ip in ipaddress.ip_network(cidr).hosts())
        except ValueError:
            continue
    hosts = hosts[:limit]
    found: dict[str, set[str]] = {}
    if not hosts:
        return found
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        for host, services in pool.map(_probe, hosts):
            if services:
                found[host] = services
    return found


def parse_avahi_output(text: str, service: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for line in text.splitlines():
        if not line.startswith("="):
            continue
        parts = line.split(";")
        if len(parts) < 10:
            continue
        name = parts[3].strip() or parts[6].strip()
        address = parts[7].strip()
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", address):
            continue
        entry = found.setdefault(address, {"name": name or address, "services": set()})
        if name:
            entry["name"] = name
        entry["services"].add(service)
    return found


def avahi_services() -> dict[str, dict]:
    if not shutil.which("avahi-browse"):
        return {}
    found: dict[str, dict] = {}
    for service_type, service in AVAHI_TYPES.items():
        try:
            proc = subprocess.run(
                ["avahi-browse", "-rt", service_type],
                capture_output=True, text=True, timeout=6,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        for address, entry in parse_avahi_output(proc.stdout, service).items():
            merged = found.setdefault(address, {"name": entry["name"], "services": set()})
            merged["services"] |= entry["services"]
            if entry["name"]:
                merged["name"] = entry["name"]
    return found


def smb_shares(host: str) -> list[dict]:
    if not shutil.which("smbclient"):
        return []
    try:
        proc = subprocess.run(
            ["smbclient", "-L", f"//{host}", "-N", "-g"],
            capture_output=True, text=True, timeout=6,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    shares = []
    for line in proc.stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 2 or parts[0] != "Disk":
            continue
        name = parts[1].strip()
        if not name or name.lower() in {"admin$", "ipc$", "print$"}:
            continue
        shares.append({"name": name, "uri": f"smb://{host}/{quote(name)}"})
    return shares


def scan() -> dict:
    subnets = local_subnets()
    hosts: dict[str, dict] = {}
    for host, services in port_scan(subnets).items():
        hosts[host] = {"name": host, "services": set(services)}
    for host, entry in avahi_services().items():
        merged = hosts.setdefault(host, {"name": host, "services": set()})
        merged["services"] |= entry["services"]
        if entry.get("name"):
            merged["name"] = entry["name"]

    smb_hosts = [host for host, data in hosts.items() if "smb" in data["services"]][:16]
    share_map: dict[str, list] = {}
    if smb_hosts:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            share_map = dict(zip(smb_hosts, pool.map(smb_shares, smb_hosts)))

    devices = []
    for host, data in sorted(hosts.items(), key=lambda item: item[1]["name"].lower()):
        devices.append({
            "name": data["name"] or host,
            "host": host,
            "services": sorted(data["services"]),
            "shares": share_map.get(host, []),
            "icon": "network-server",
        })
    return {
        "kind": "network",
        "subnets": subnets,
        "scanned_at": time.time(),
        "devices": devices,
    }


def _gvfs_dir() -> Path:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}")
    return runtime / "gvfs"


def _find_mount(uri: str) -> Path | None:
    parsed = urlparse(uri)
    host = parsed.hostname or ""
    share = unquote(parsed.path.lstrip("/")) if parsed.path else ""
    gvfs = _gvfs_dir()
    for _ in range(20):
        try:
            entries = list(gvfs.iterdir())
        except OSError:
            entries = []
        candidates = [entry for entry in entries if host and host in unquote(entry.name)]
        if share:
            exact = [entry for entry in candidates if share in unquote(entry.name)]
            if exact:
                return exact[0]
        if candidates:
            return candidates[0]
        time.sleep(0.25)
    return None


def _gio_available() -> bool:
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib  # noqa: F401
        return True
    except Exception:
        return False


def _credential_uri(uri: str, username: str, password: str) -> str:
    if not username:
        return uri
    parsed = urlparse(uri)
    host = parsed.hostname or ""
    netloc = f"{quote(username, safe='')}:{quote(password or '', safe='')}@{host}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def _gio_mount(uri: str, username: str, password: str, domain: str) -> None:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    loop = GLib.MainLoop()
    state = {"error": None, "done": False, "asked": 0}
    operation = Gio.MountOperation()
    if username:
        operation.set_username(username)
    if password:
        operation.set_password(password)
    if domain:
        operation.set_domain(domain)
    if not username:
        operation.set_anonymous(True)

    def ask(op, message, default_user, default_domain, flags):
        state["asked"] += 1
        if state["asked"] > 1:
            op.reply(Gio.MountOperationResult.ABORTED)
            return
        if flags & Gio.AskPasswordFlags.NEED_USERNAME:
            op.set_username(username)
        if flags & Gio.AskPasswordFlags.NEED_PASSWORD:
            op.set_password(password)
        if flags & Gio.AskPasswordFlags.NEED_DOMAIN:
            op.set_domain(domain)
        op.reply(Gio.MountOperationResult.HANDLED)

    operation.connect("ask-password", ask)
    gfile = Gio.File.new_for_uri(uri)

    def done(file, result):
        try:
            file.mount_enclosing_volume_finish(result)
        except GLib.Error as exc:
            state["error"] = exc.message
        state["done"] = True
        loop.quit()

    def timeout():
        if not state["done"]:
            state["error"] = "mount timed out"
            loop.quit()
        return False

    GLib.timeout_add_seconds(30, timeout)
    gfile.mount_enclosing_volume(Gio.MountMountFlags.NONE, operation, None, done)
    loop.run()
    if state["error"]:
        raise RuntimeError(state["error"])


def mount(uri: str, username: str = "", password: str = "", domain: str = "") -> dict:
    if not uri or not uri.lower().startswith(("smb://", "nfs://")):
        raise ValueError("unsupported network URI")
    username = str(username or "")
    password = str(password or "")
    domain = str(domain or "")
    if _gio_available():
        _gio_mount(uri, username, password, domain)
    else:
        if not shutil.which("gio"):
            raise RuntimeError("gio is required to mount network shares")
        target = _credential_uri(uri, username, password)
        try:
            proc = subprocess.run(
                ["gio", "mount", target],
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"mount failed: {exc}") from exc
        message = (proc.stderr + "\n" + proc.stdout).strip()
        if proc.returncode != 0 and "already mounted" not in message.lower():
            raise RuntimeError(message or "mount failed")
    path = _find_mount(uri)
    if path is None:
        raise RuntimeError("mounted but the GVfs path was not found")
    return {"kind": "network_mount", "uri": uri, "path": str(path)}
