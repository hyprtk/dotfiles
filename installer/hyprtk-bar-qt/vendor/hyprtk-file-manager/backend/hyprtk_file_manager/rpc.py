"""JSON-lines RPC used by the Quickshell front end."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from . import __version__
from . import archive as archive_mod
from . import clipboard as clipboard_mod
from . import actions as actions_mod
from . import gitinfo
from . import llm as llm_mod
from . import remote as remote_mod
from . import share as share_mod
from . import launch
from . import meta
from . import network as network_mod
from . import openwith as openwith_mod
from . import places as places_mod
from . import preview as preview_mod
from . import search as search_mod
from . import store
from . import tags as tags_mod
from . import tools as tools_mod
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
        tag=str(params.get("tag") or ""),
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
            return {"id": rid, "result": {"kind": "ping", "version": __version__, "root": os.geteuid() == 0}}
        if method == "list":
            return {"id": rid, "result": _list(params)}
        if method == "places":
            return {"id": rid, "result": _places(params)}
        if method == "open":
            return {"id": rid, "result": _open(params)}
        if method == "open_with.launch":
            return {
                "id": rid,
                "result": openwith_mod.launch(
                    str(params.get("path") or ""), str(params.get("app") or ""),
                ),
            }
        if method == "open_with.set_default":
            return {
                "id": rid,
                "result": openwith_mod.set_default(
                    str(params.get("path") or ""), str(params.get("app") or ""),
                ),
            }
        if method == "terminal":
            return {
                "id": rid,
                "result": launch.open_terminal(str(params.get("path") or places_mod.home_dir()), False),
            }
        if method == "open_root":
            return {
                "id": rid,
                "result": launch.open_as_root(str(params.get("path") or places_mod.home_dir())),
            }
        if method == "terminal_root":
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
        if method == "clipboard.set":
            return {
                "id": rid,
                "result": {
                    "kind": "clipboard",
                    "ok": clipboard_mod.set_files(
                        params.get("paths") or [], bool(params.get("cut", False)),
                    ),
                },
            }
        if method == "clipboard.clear":
            return {
                "id": rid,
                "result": {"kind": "clipboard", "ok": clipboard_mod.clear()},
            }
        if method.startswith("job."):
            return {"id": rid, "result": MANAGER.dispatch(method[4:], params)}
        if method == "undo":
            return {"id": rid, "result": MANAGER.dispatch("undo", params)}
        if method == "redo":
            return {"id": rid, "result": MANAGER.dispatch("redo", params)}
        if method == "stat":
            return {"id": rid, "result": meta.file_info(str(params.get("path") or ""))}
        if method == "tags.set":
            return {"id": rid, "result": tags_mod.set_paths(
                [str(item) for item in (params.get("paths") or [])],
                params.get("tags") or [],
                str(params.get("color") or ""),
                params.get("note") if "note" in params else None,
            )}
        if method == "tags.list":
            return {"id": rid, "result": {"tags": tags_mod.all_tags()}}
        if method == "tags.for_paths":
            return {"id": rid, "result": {"paths": tags_mod.for_paths(
                [str(item) for item in (params.get("paths") or [])])}}
        if method == "tags.listing":
            return {"id": rid, "result": {"paths": tags_mod.listing(
                str(params.get("path") or ""))}}
        if method == "smart.list":
            return {"id": rid, "result": {"smart": tags_mod.smart_list()}}
        if method == "smart.save":
            return {"id": rid, "result": tags_mod.smart_save(
                str(params.get("name") or ""), str(params.get("query") or ""),
                str(params.get("mode") or "name"), str(params.get("root") or ""))}
        if method == "smart.delete":
            return {"id": rid, "result": {"deleted": tags_mod.smart_delete(
                str(params.get("name") or ""))}}
        if method == "share.list":
            return {"id": rid, "result": {"shares": share_mod.shares()}}
        if method == "share.stop":
            return {"id": rid, "result": share_mod.stop(str(params.get("id") or ""))}
        if method == "llm.available":
            return {"id": rid, "result": llm_mod.available()}
        if method == "remote.mounts":
            return {"id": rid, "result": {"mounts": remote_mod.mounts(),
                                          "devices": remote_mod.devices()}}
        if method == "tools.duplicates":
            return {"id": rid, "result": tools_mod.duplicates(
                str(params.get("path") or ""), int(params.get("minSize") or 1))}
        if method == "tools.usage":
            return {"id": rid, "result": tools_mod.usage(str(params.get("path") or ""))}
        if method == "tools.compare":
            return {"id": rid, "result": tools_mod.compare(
                str(params.get("left") or ""), str(params.get("right") or ""))}
        if method == "actions.list":
            return {"id": rid, "result": {"actions": actions_mod.load(),
                                          "dir": str(actions_mod.actions_dir()),
                                          "example": actions_mod.example()}}
        if method == "actions.run":
            return {"id": rid, "result": actions_mod.run(
                str(params.get("id") or ""),
                [str(item) for item in (params.get("paths") or [])],
                str(params.get("dir") or ""),
            )}
        if method == "git.root":
            return {"id": rid, "result": {"root": gitinfo.repo_root(
                str(params.get("path") or ""))}}
        if method == "archive.kind":
            return {
                "id": rid,
                "result": {"kind": archive_mod.kind_of(str(params.get("path") or ""))},
            }
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
        elif method == "clipboard.get":
            result = clipboard_mod.get_files()
            result["kind"] = "clipboard"
        elif method == "thumb":
            result = preview_mod.build_thumb(str(params.get("path") or ""))
        elif method == "open_with.apps":
            result = openwith_mod.applications(str(params.get("path") or ""))
        elif method == "search":
            result = search_mod.search(
                str(params.get("root") or places_mod.home_dir()),
                str(params.get("query") or ""),
                mode=str(params.get("mode") or "name"),
                hidden=bool(params.get("hidden", False)),
                no_ignore=bool(params.get("noIgnore", False)),
                limit=int(params.get("limit", 500)),
            )
        elif method == "share.start":
            result = share_mod.start(str(params.get("path") or ""),
                                     int(params.get("port") or 0))
        elif method == "llm.describe":
            result = llm_mod.describe(str(params.get("path") or ""))
        elif method == "remote.mount":
            result = remote_mod.connect(
                str(params.get("uri") or ""),
                str(params.get("username") or ""),
                str(params.get("password") or ""),
                str(params.get("domain") or ""),
            )
        elif method == "git.status":
            result = gitinfo.status(str(params.get("path") or ""))
        elif method == "git.diff":
            result = gitinfo.diff(str(params.get("path") or ""))
        elif method == "archive.list":
            result = archive_mod.list_archive(
                str(params.get("path") or ""), str(params.get("inner") or ""))
        elif method == "archive.extract":
            result = archive_mod.extract(
                str(params.get("path") or ""),
                str(params.get("inner") or ""),
                str(params.get("destination") or "") or None,
            )
        elif method == "archive.create":
            result = archive_mod.create(
                [str(item) for item in (params.get("paths") or [])],
                str(params.get("destination") or ""),
                str(params.get("format") or "zip"),
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
    "preview", "thumb", "search", "checksum", "devices.mount", "devices.eject",
    "archive.list", "archive.extract", "archive.create", "git.status", "git.diff",
    "share.start", "llm.describe", "remote.mount",
    "network.scan", "network.mount", "network.shares", "open_with.apps",
    "clipboard.get",
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
