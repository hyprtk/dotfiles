"""Serve one folder over the local network (read-only HTTP).

This is the "LAN drop" side of the file manager: a temporary HTTP server bound
to all interfaces, showing the folder for anyone on the same network. It is
deliberately read-only and stops with the app or when told to.
"""

from __future__ import annotations

import http.server
import socket
import threading
import uuid
from pathlib import Path

SERVERS: dict[str, dict] = {}


def lan_address() -> str:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.settimeout(0.5)
        probe.connect(("192.0.2.1", 9))  # no packet is sent; picks the route
        address = probe.getsockname()[0]
        probe.close()
        return address
    except OSError:
        return "127.0.0.1"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep the app's journal quiet
        pass

    def do_PUT(self):  # noqa: N802 - read-only by design
        self.send_error(405, "This share is read-only")

    def do_POST(self):  # noqa: N802
        self.send_error(405, "This share is read-only")


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start(path: str, port: int = 0) -> dict:
    folder = Path(path).expanduser()
    if not folder.is_dir():
        raise RuntimeError(f"{folder} is not a directory")
    handler = lambda *args, **kwargs: _Handler(*args, directory=str(folder), **kwargs)  # noqa: E731
    server = _Server(("0.0.0.0", int(port or 0)), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True,
                              name=f"hyprtk-share-{server.server_port}")
    thread.start()
    share_id = uuid.uuid4().hex[:8]
    entry = {"id": share_id, "path": str(folder), "port": server.server_port,
             "url": f"http://{lan_address()}:{server.server_port}/",
             "local": f"http://127.0.0.1:{server.server_port}/",
             "server": server, "thread": thread}
    SERVERS[share_id] = entry
    return {key: value for key, value in entry.items()
            if key not in ("server", "thread")}


def stop(share_id: str) -> dict:
    entry = SERVERS.pop(share_id, None)
    if entry is None:
        raise RuntimeError(f"no share {share_id!r}")
    entry["server"].shutdown()
    entry["server"].server_close()
    return {"id": share_id, "stopped": True}


def shares() -> list[dict]:
    return [{key: value for key, value in entry.items()
             if key not in ("server", "thread")} for entry in SERVERS.values()]


def stop_all() -> None:
    for share_id in list(SERVERS):
        try:
            stop(share_id)
        except RuntimeError:
            pass
