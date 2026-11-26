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
import subprocess
import signal
import socket
import threading
import time
from pathlib import Path
from typing import Any

_RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")
SOCKET = _RUNTIME / "hyprtk-settings.sock"
# The QML front end polls the queue from a timer. A server whose front end is
# gone (the window was closed but the backend kept running) still answers on the
# socket, which made every later launch print "focused the running window" and
# show nothing. The heartbeat is the front end's liveness signal.
HEARTBEAT = _RUNTIME / "hyprtk-settings.heartbeat"
PIDFILE = _RUNTIME / "hyprtk-settings.pid"
HEARTBEAT_MAX_AGE = 4.0
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


def touch_heartbeat() -> None:
    """Called by the front end while a window exists."""
    try:
        HEARTBEAT.write_text(str(int(time.time())))
    except OSError:
        pass


def _heartbeat_fresh() -> bool:
    try:
        return time.time() - HEARTBEAT.stat().st_mtime <= HEARTBEAT_MAX_AGE
    except OSError:
        return False


def _surface_pids() -> set[int] | None:
    """Pids that own a mapped surface, or None when Hyprland cannot be asked."""
    try:
        import subprocess

        done = subprocess.run(["hyprctl", "layers", "-j"], capture_output=True,
                              text=True, timeout=2)
        layers = json.loads(done.stdout or "{}")
        clients = json.loads(subprocess.run(["hyprctl", "clients", "-j"],
                                            capture_output=True, text=True,
                                            timeout=2).stdout or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    # {"DP-2": {"levels": {"1": [ {"pid": 1234, ...}, ... ]}}}
    pids = {int(surface.get("pid", 0))
            for monitor in layers.values()
            for surfaces in (monitor.get("levels") or {}).values()
            for surface in (surfaces or [])
            if (surface or {}).get("pid")}
    pids |= {int(window.get("pid", 0)) for window in clients}
    pids.discard(0)
    return pids


def is_ours_argv(argv: list[str]) -> bool:
    """Is this argv our Quickshell front end or its backend?

    Matching a substring anywhere in the command line is not enough: a shell
    whose -c string merely mentions the project path looks like a target, and
    reaping it would kill an unrelated process.
    """
    if not argv:
        return False
    exe = os.path.basename(argv[0])
    if exe in ("qs", "quickshell"):
        return any("hyprtk-system-manager" in part for part in argv[1:])
    if exe.startswith("python"):
        return any(part == "system_manager.cli" for part in argv[1:])
    return False


def _is_ours(pid: int) -> bool:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    argv = [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]
    return is_ours_argv(argv)


def reap_stale(force: bool = False) -> bool:
    """Kill a backend whose window is gone and clear its socket. True if it did."""
    if not force and _heartbeat_fresh():
        return False
    dropped = False
    try:
        pid = int(PIDFILE.read_text().strip())
    except (OSError, ValueError):
        pid = 0
    if pid and pid != os.getpid() and _is_ours(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            dropped = True
        except OSError:
            pass
    for path in (SOCKET, HEARTBEAT, PIDFILE):
        try:
            path.unlink()
            dropped = True
        except OSError:
            pass
    return dropped


def poll(limit: int = 20) -> list[dict]:
    touch_heartbeat()
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
    try:
        # The *window* pid, not this backend's: Hyprland reports surfaces
        # against the Quickshell process, which is our parent. Recording our own
        # pid made every healthy instance look windowless.
        PIDFILE.write_text(str(os.getppid()))
    except OSError:
        pass
    touch_heartbeat()
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
    """Deliver to a running instance; None when nobody is listening.

    A listener with no live front end is not "running" — it would swallow the
    request and leave the user with no window.
    """
    if not SOCKET.exists():
        return None
    if not _heartbeat_fresh():
        reap_stale()
        return None
    # A backend whose window the compositor dropped (a monitor reload can unmap
    # a layer surface) keeps answering while polling. Only treat it as running
    # when its process actually owns a surface — or is young enough to still be
    # mapping.
    try:
        pid = int(PIDFILE.read_text().strip())
    except (OSError, ValueError):
        pid = 0
    if pid:
        try:
            age = time.time() - PIDFILE.stat().st_mtime
        except OSError:
            age = 0.0
        pids = _surface_pids()
        if pids is not None and pid not in pids and age > 6.0:
            # force: the heartbeat is fresh (the orphan is still polling).
            reap_stale(force=True)
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
