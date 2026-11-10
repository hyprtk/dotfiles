"""JSON-lines RPC used by the Quickshell front end."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from . import __version__
from . import launch
from . import meta
from . import network as network_mod
from . import places as places_mod
from . import preview as preview_mod
from . import search as search_mod
from . import store
from . import trash
from .journal import Journal
from .listing import DirCache, list_dir
from .ops import GioTrash, JobManager
from .watch import WatchManager

CACHE = DirCache()
WRITE_LOCK = threading.Lock()


def state_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return base / "hyprtk-file-manager" / "journal.json"


def write_message(message: dict) -> None:
    line = json.dumps(message)
    with WRITE_LOCK:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


MANAGER = JobManager(
    emit=write_message,
    journal=Journal(state_path()),
    trash=GioTrash(),
)
WATCHER = WatchManager(emit=write_message)


def _list(params: dict) -> dict:
    result = list_dir(
        CACHE,
        str(params.get("path") or places_mod.home_dir()),
        offset=params.get("offset", 0),
        limit=params.get("limit", 250),
        sort=str(params.get("sort") or "name"),
        desc=bool(params.get("desc", False)),
        hidden=bool(params.get("hidden", False)),
        dirs_first=bool(params.get("dirsFirst", True)),
        query=str(params.get("query") or ""),
    )
    result["kind"] = "list"
    return result


def _places(_params: dict) -> dict:
    home = places_mod.home_dir()
    return {
        "kind": "places",
        "home": str(home),
        "places": places_mod.places(home),
        "devices": places_mod.devices(),
    }


def _open(params: dict) -> dict:
    target = params.get("path")
    if not target:
        raise ValueError("no path")
    if not Path(str(target)).exists():
        raise FileNotFoundError(str(target))
    subprocess.Popen(
        ["xdg-open", str(target)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"kind": "open", "path": str(target)}


def handle(request: dict) -> dict:
    rid = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}
    try:
        if method == "ping":
            return {"id": rid, "result": {"kind": "ping", "version": __version__}}
        if method == "list":
            return {"id": rid, "result": _list(params)}
        if method == "places":
            return {"id": rid, "result": _places(params)}
        if method == "open":
            return {"id": rid, "result": _open(params)}
        if method == "terminal":
            return {
                "id": rid,
                "result": launch.open_terminal(str(params.get("path") or places_mod.home_dir()), False),
            }
        if method == "open_root":
            return {
                "id": rid,
                "result": launch.open_terminal(str(params.get("path") or places_mod.home_dir()), True),
            }
        if method == "trash_restore":
            return {"id": rid, "result": trash.restore(str(params.get("path") or ""))}
        if method == "bookmarks.add":
            return {
                "id": rid,
                "result": places_mod.add_bookmark(
                    str(params.get("path") or ""), params.get("label"),
                ),
            }
        if method == "bookmarks.remove":
            return {
                "id": rid,
                "result": places_mod.remove_bookmark(str(params.get("path") or "")),
            }
        if method == "version":
            return {"id": rid, "result": {"kind": "version", "version": __version__}}
        if method.startswith("job."):
            return {"id": rid, "result": MANAGER.dispatch(method[4:], params)}
        if method == "undo":
            return {"id": rid, "result": MANAGER.dispatch("undo", params)}
        if method == "redo":
            return {"id": rid, "result": MANAGER.dispatch("redo", params)}
        if method == "stat":
            return {"id": rid, "result": meta.file_info(str(params.get("path") or ""))}
        if method == "chmod":
            return {
                "id": rid,
                "result": meta.chmod(str(params.get("path") or ""), params.get("mode")),
            }
        if method == "jobs":
            return {"id": rid, "result": MANAGER.dispatch("list", params)}
        if method == "journal":
            return {"id": rid, "result": {"records": MANAGER.journal.records[-20:]}}
        if method == "config.get":
            return {"id": rid, "result": {"kind": "config", "values": store.load(store.config_path())}}
        if method == "config.set":
            values = params.get("values") or {}
            return {"id": rid, "result": {"kind": "config", "values": store.merge(store.config_path(), values)}}
        if method == "session.get":
            session = store.load(store.session_path())
            return {"id": rid, "result": {"kind": "session", "session": session or None}}
        if method == "session.set":
            session = params.get("session") or {}
            store.save(store.session_path(), session)
            return {"id": rid, "result": {"kind": "session", "ok": True}}
        if method == "watch":
            WATCHER.watch(str(params.get("token") or ""), str(params.get("path") or ""))
            return {"id": rid, "result": {"kind": "watch", "ok": True}}
        if method == "unwatch":
            WATCHER.unwatch(str(params.get("token") or ""))
            return {"id": rid, "result": {"kind": "unwatch", "ok": True}}
        return {"id": rid, "error": f"unknown method: {method}"}
    except Exception as exc:
        return {"id": rid, "error": f"{type(exc).__name__}: {exc}"}


def _serve_async(request: dict) -> None:
    rid = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}
    try:
        if method == "preview":
            result = preview_mod.build_preview(str(params.get("path") or ""))
        elif method == "search":
            result = search_mod.search(
                str(params.get("root") or places_mod.home_dir()),
                str(params.get("query") or ""),
                mode=str(params.get("mode") or "name"),
                hidden=bool(params.get("hidden", False)),
                no_ignore=bool(params.get("noIgnore", False)),
                limit=int(params.get("limit", 500)),
            )
        elif method == "checksum":
            result = meta.checksum(
                str(params.get("path") or ""),
                str(params.get("algo") or "sha256"),
            )
        elif method == "devices.mount":
            result = places_mod.mount_device(str(params.get("device") or ""))
        elif method == "devices.eject":
            result = places_mod.eject_device(str(params.get("device") or ""))
        elif method == "network.scan":
            result = network_mod.scan()
        elif method == "network.shares":
            result = network_mod.list_shares(
                str(params.get("uri") or ""),
                str(params.get("username") or ""),
                str(params.get("password") or ""),
                str(params.get("domain") or ""),
            )
        elif method == "network.mount":
            result = network_mod.mount(
                str(params.get("uri") or ""),
                str(params.get("username") or ""),
                str(params.get("password") or ""),
                str(params.get("domain") or ""),
                bool(params.get("anonymous", False)),
            )
        else:
            raise ValueError(f"unknown async method: {method}")
        write_message({"id": rid, "result": result})
    except Exception as exc:
        write_message({"id": rid, "error": f"{type(exc).__name__}: {exc}"})


ASYNC_METHODS = {
    "preview", "search", "checksum", "devices.mount", "devices.eject",
    "network.scan", "network.mount", "network.shares",
}


def serve() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            write_message({"id": None, "error": f"bad json: {exc}"})
            continue
        if not isinstance(request, dict):
            write_message({"id": None, "error": "request must be an object"})
            continue
        if request.get("method") in ASYNC_METHODS:
            threading.Thread(target=_serve_async, args=(request,), daemon=True).start()
            continue
        write_message(handle(request))
    return 0
