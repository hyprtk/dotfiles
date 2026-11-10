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
                capture_output=True, text=True, timeout=4,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        for address, entry in parse_avahi_output(proc.stdout, service).items():
            merged = found.setdefault(address, {"name": entry["name"], "services": set()})
            merged["services"] |= entry["services"]
            if entry["name"]:
                merged["name"] = entry["name"]
    return found


def smb_shares(host: str, username: str = "", password: str = "",
               domain: str = "") -> list[dict]:
    if not shutil.which("smbclient"):
        return []
    command = ["smbclient", "-L", f"//{host}", "-g"]
    if username:
        command += ["-U", f"{username}%{password or ''}"]
        if domain:
            command += ["-W", domain]
    else:
        command.append("-N")
    try:
        proc = subprocess.run(
            command,
            capture_output=True, text=True, timeout=8,
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        ports_future = pool.submit(port_scan, subnets)
        avahi_future = pool.submit(avahi_services)
        ports = ports_future.result()
        discovered = avahi_future.result()
    for host, services in ports.items():
        hosts[host] = {"name": host, "services": set(services)}
    for host, entry in discovered.items():
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


NETWORK_SCHEMES = ("smb://", "nfs://")


def is_network_uri(value: str) -> bool:
    return str(value or "").strip().lower().startswith(NETWORK_SCHEMES)


def _gvfs_dir() -> Path:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}")
    return runtime / "gvfs"


def _gvfs_mount_name(entry_name: str) -> tuple[str, str]:
    """Split a gvfs fuse name into (server, share), unquoted."""
    name = unquote(entry_name)
    fields: dict[str, str] = {}
    head, _, rest = name.partition(":")
    if not head.endswith("-share"):
        return "", ""
    for part in rest.split(","):
        key, _, value = part.partition("=")
        if key and value:
            fields[key] = value
    return fields.get("server", ""), fields.get("share", "")


def _find_mount(uri: str) -> Path | None:
    parsed = urlparse(uri)
    host = (parsed.hostname or "").lower()
    share = unquote(parsed.path.lstrip("/")).lower().strip("/") if parsed.path else ""
    if not host:
        return None
    gvfs = _gvfs_dir()
    for _ in range(40):
        try:
            entries = list(gvfs.iterdir())
        except OSError:
            entries = []
        fallback = None
        for entry in entries:
            server, mounted_share = _gvfs_mount_name(entry.name)
            if server.lower() != host:
                continue
            if fallback is None:
                fallback = entry
            if not share:
                return entry
            if mounted_share.lower().strip("/") == share:
                return entry
        if share and fallback is not None and not parsed.path.strip("/"):
            return fallback
        time.sleep(0.25)
    return None


def uri_for_path(path: str) -> str:
    """Map a GVfs fuse path back to its smb:// or nfs:// URI."""
    if not path:
        return path
    gvfs = _gvfs_dir()
    try:
        rel = Path(path).relative_to(gvfs)
    except ValueError:
        return path
    parts = rel.parts
    if not parts:
        return path
    mount_name = unquote(parts[0])
    server, share = _gvfs_mount_name(parts[0])
    if not server or not share:
        return path
    if mount_name.startswith("smb-share:"):
        uri = f"smb://{server}/{quote(share.lstrip('/'), safe='/')}"
    elif mount_name.startswith("nfs-share:"):
        uri = f"nfs://{server}{quote('/' + share.lstrip('/'), safe='/')}"
    else:
        return path
    if len(parts) > 1:
        uri = uri.rstrip("/") + "/" + quote("/".join(parts[1:]), safe="/")
    return uri


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


def _gio_run(uri: str, username: str, password: str, domain: str,
             anonymous: bool, collect) -> list[dict] | None:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    loop = GLib.MainLoop()
    state: dict = {"error": None, "done": False, "asked": 0, "items": None}
    operation = Gio.MountOperation()
    if anonymous:
        operation.set_anonymous(True)
    else:
        if username:
            operation.set_username(username)
        if password:
            operation.set_password(password)
        if domain:
            operation.set_domain(domain)
        if username or password:
            operation.set_password_save(Gio.PasswordSave.PERMANENTLY)

    def ask(op, message, default_user, default_domain, flags):
        state["asked"] += 1
        if anonymous:
            op.reply(Gio.MountOperationResult.HANDLED)
            return
        if not username and not password:
            state["error"] = "credentials required"
            op.reply(Gio.MountOperationResult.ABORTED)
            return
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
            if "already mounted" not in exc.message.lower():
                state["error"] = exc.message
                state["done"] = True
                loop.quit()
                return
        if collect is not None:
            try:
                state["items"] = collect(file)
            except GLib.Error as exc:
                state["error"] = exc.message
        state["done"] = True
        loop.quit()

    def timeout():
        if not state["done"]:
            state["error"] = state["error"] or "mount timed out"
            loop.quit()
        return False

    GLib.timeout_add_seconds(30, timeout)
    gfile.mount_enclosing_volume(Gio.MountMountFlags.NONE, operation, None, done)
    loop.run()
    if state["error"]:
        message = state["error"]
        if (username or password) and message.lower() in {
            "password dialogue cancelled", "password dialog cancelled",
            "operation was cancelled",
        }:
            message = ("authentication failed — check the username, password "
                       "and workgroup/domain")
        raise RuntimeError(message)
    return state["items"]


def _gio_mount(uri: str, username: str, password: str, domain: str,
               anonymous: bool = False) -> None:
    _gio_run(uri, username, password, domain, anonymous, None)


def _gio_children(uri: str, username: str, password: str, domain: str,
                  anonymous: bool = False) -> list[dict]:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    def collect(file):
        import gi as gi_mod
        gi_mod.require_version("Gio", "2.0")
        from gi.repository import Gio as GioMod
        enumerator = file.enumerate_children(
            "standard::name,standard::display-name,standard::type,standard::icon",
            GioMod.FileQueryInfoFlags.NONE,
            None,
        )
        out = []
        while True:
            info = enumerator.next_file(None)
            if info is None:
                break
            out.append({
                "name": info.get_name(),
                "display": info.get_display_name() or info.get_name(),
                "type": int(info.get_file_type()),
            })
        return out

    return _gio_run(uri, username, password, domain, anonymous, collect) or []


def _server_uri(uri: str) -> str:
    parsed = urlparse(uri)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname or ''}{port}/"


def _share_uri(uri: str, name: str) -> str:
    parsed = urlparse(uri)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname or ''}{port}/{quote(name, safe='/')}"


def _nfs_exports(host: str) -> list[str]:
    if not shutil.which("showmount"):
        return []
    try:
        proc = subprocess.run(
            ["showmount", "-e", host],
            capture_output=True, text=True, timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    exports = []
    for line in proc.stdout.splitlines()[1:]:
        export = line.split()[0].strip() if line.split() else ""
        if export.startswith("/"):
            exports.append(export)
    return exports


def list_shares(uri: str, username: str = "", password: str = "",
                domain: str = "") -> dict:
    if not uri or not is_network_uri(uri):
        raise ValueError("unsupported network URI")
    parsed = urlparse(uri)
    host = parsed.hostname or ""
    if not host:
        raise ValueError("network URI has no host")
    shares: list[dict] = []
    if parsed.scheme == "nfs":
        for export in _nfs_exports(host):
            shares.append({
                "name": export.rstrip("/").rsplit("/", 1)[-1] or export,
                "uri": f"nfs://{host}{quote(export, safe='/')}",
                "export": export,
            })
    elif _gio_available():
        children = _gio_children(
            _server_uri(uri), str(username or ""), str(password or ""),
            str(domain or ""),
        )
        for child in children:
            if child.get("type") != 6:  # GFileType.MOUNTABLE
                continue
            name = child.get("name") or child.get("display") or ""
            if not name or name.lower() in {"admin$", "ipc$", "print$"}:
                continue
            shares.append({
                "name": child.get("display") or name,
                "uri": _share_uri(uri, name),
            })
    else:
        shares = smb_shares(host, username, password, domain)
    shares.sort(key=lambda share: share["name"].lower())
    return {"kind": "network_shares", "host": host, "uri": _server_uri(uri),
            "shares": shares}


def mount(uri: str, username: str = "", password: str = "", domain: str = "",
          anonymous: bool = False) -> dict:
    if not uri or not uri.lower().startswith(NETWORK_SCHEMES):
        raise ValueError("unsupported network URI")
    parsed = urlparse(uri)
    if not parsed.hostname:
        raise ValueError("network URI has no host")
    if not parsed.path.strip("/"):
        raise ValueError("choose a share to mount")
    username = str(username or "")
    password = str(password or "")
    domain = str(domain or "")
    if _gio_available():
        _gio_mount(uri, username, password, domain, bool(anonymous))
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
