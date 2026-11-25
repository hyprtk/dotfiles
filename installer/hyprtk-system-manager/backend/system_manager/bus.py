"""A small local settings bus so other apps can deep-link into a running window.

A second ``hyprtk-settings open --page power --row "Charge limit"`` must not
start a second window: it writes one JSON line to
``$XDG_RUNTIME_DIR/hyprtk-settings.sock``, where the running backend queues it,
and the front end polls it and navigates.

Where PyGObject is available the same queue is also exported on the session bus
as ``org.hyprtk.Settings`` with ``Open(panel, row)``, so a suite app can call it
without shelling out. PyGObject is optional: the socket always works.
"""

from __future__ import annotations

import json
import os
import socket
import threading
from pathlib import Path
from typing import Any

SOCKET = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp") / "hyprtk-settings.sock"
BUS_NAME = "org.hyprtk.Settings"
OBJECT_PATH = "/org/hyprtk/Settings"
INTERFACE = """<node>
  <interface name="org.hyprtk.Settings">
    <method name="Open">
      <arg name="panel" type="s" direction="in"/>
      <arg name="row" type="s" direction="in"/>
    </method>
  </interface>
</node>"""

_LOCK = threading.Lock()
_QUEUE: list[dict] = []
_STARTED = {"socket": False, "dbus": False}


def _queue(payload: dict) -> None:
    with _LOCK:
        _QUEUE.append(payload)


def poll(limit: int = 20) -> list[dict]:
    with _LOCK:
        items = _QUEUE[:limit]
        del _QUEUE[:limit]
    return items


def _serve_socket(server: socket.socket) -> None:
    while True:
        try:
            conn, _ = server.accept()
        except OSError:
            return
        try:
            conn.settimeout(2)
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            payload = json.loads(data.decode("utf-8", "replace") or "{}")
            if isinstance(payload, dict):
                _queue({"panel": str(payload.get("panel") or ""),
                        "row": str(payload.get("row") or "")})
            conn.sendall(b'{"ok":true}\n')
        except (OSError, ValueError):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass


def _start_socket() -> bool:
    try:
        if SOCKET.exists():
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            probe.settimeout(0.4)
            try:
                probe.connect(str(SOCKET))
            except OSError:
                SOCKET.unlink(missing_ok=True)
            finally:
                probe.close()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(SOCKET))
        os.chmod(str(SOCKET), 0o600)
        server.listen(8)
    except OSError:
        return False
    threading.Thread(target=_serve_socket, args=(server,), name="sm-bus",
                     daemon=True).start()
    return True


def _start_dbus() -> bool:
    if _STARTED["dbus"]:
        return True
    try:
        from gi.repository import Gio, GLib  # noqa: F401 - optional dependency
    except Exception:  # noqa: BLE001 - not installed, socket only
        return False

    try:
        from gi.repository import Gio, GLib

        node = Gio.DBusNodeInfo.new_for_xml(INTERFACE)

        def on_call(connection, sender, path, interface, method, params, invocation):
            if method != "Open":
                invocation.return_value(None)
                return
            panel, row = params.unpack()
            _queue({"panel": str(panel), "row": str(row)})
            invocation.return_value(None)

        def acquired(connection, name) -> None:
            try:
                connection.register_object(
                    OBJECT_PATH, node.interfaces[0], on_call, None, None)
            except Exception:  # noqa: BLE001 - another instance owns the name
                pass

        def run() -> None:
            loop = GLib.MainLoop()
            Gio.bus_own_name(
                Gio.BusType.SESSION, BUS_NAME, Gio.BusNameOwnerFlags.NONE,
                acquired, None, None,
            )
            loop.run()

        _STARTED["dbus"] = True
        threading.Thread(target=run, name="sm-dbus", daemon=True).start()
        return True
    except Exception:  # noqa: BLE001 - a bus failure must not stop the app
        return False


def start() -> dict:
    """Start the listeners once; returns what is available."""
    with _LOCK:
        if _STARTED["socket"]:
            return {"socket": str(SOCKET), "dbus": BUS_NAME, "started": True}
        _STARTED["socket"] = _start_socket()
    dbus = _start_dbus()
    return {"socket": str(SOCKET) if _STARTED["socket"] else "", "dbus": dbus,
            "started": _STARTED["socket"]}


def send(payload: dict, timeout: float = 1.5) -> dict | None:
    """Deliver to a running instance; None when nobody is listening."""
    if not SOCKET.exists():
        return None
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        client.connect(str(SOCKET))
        client.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        reply = client.recv(4096)
        return json.loads(reply.decode("utf-8", "replace") or "{}")
    except (OSError, ValueError):
        return None
    finally:
        client.close()
