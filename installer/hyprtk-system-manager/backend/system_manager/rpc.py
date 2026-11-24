"""JSON-lines RPC used by the Quickshell front end.

    {"id": 1, "method": "panel", "params": {"id": "displays"}}
    {"id": 1, "result": {...}}
    {"id": 1, "error": "message"}

One request per line on stdin, one response per line on stdout.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

from . import __version__, apps, catalog, form, paths, priv, util


class RpcError(RuntimeError):
    pass


def _module(panel_id: str):
    try:
        return catalog.module_for(panel_id)
    except KeyError as exc:
        raise RpcError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - a broken panel must not kill the app
        raise RpcError(f"panel {panel_id!r} failed to load: {type(exc).__name__}: {exc}") from exc


def _hello(params: dict) -> dict:
    return {
        "version": __version__,
        "catalog": catalog.catalog(),
        "hostname": util.hostname(),
        "os": util.os_release().get("PRETTY_NAME", "Linux"),
        "user": os.environ.get("USER") or os.environ.get("LOGNAME") or "user",
        "session": util.session_kind(),
        "desktop": util.desktop(),
        "kernel": util.kernel(),
        "capabilities": {
            **priv.capabilities(),
            "hyprctl": util.which("hyprctl"),
            "qs": util.which("qs"),
            "nmcli": util.which("nmcli"),
            "wpctl": util.which("wpctl"),
            "bluetoothctl": util.which("bluetoothctl"),
            "gsettings": util.which("gsettings"),
            "checkupdates": util.which("checkupdates"),
        },
        "ui": _ui_get({}),
    }


def _catalog(params: dict) -> dict:
    return catalog.catalog()


def _panel(params: dict) -> dict:
    panel_id = str(params.get("id") or "")
    if panel_id not in catalog.PANEL_INDEX:
        raise RpcError(f"unknown panel {panel_id!r}")
    module = _module(panel_id)
    probe = getattr(module, "probe", None)
    if probe is None:
        raise RpcError(f"panel {panel_id!r} has no probe()")
    try:
        model = probe()
    except Exception as exc:  # noqa: BLE001 - degrade to an explaining page
        traceback.print_exc(file=sys.stderr)
        return form.unavailable_page(catalog.PANEL_INDEX[panel_id],
                                     f"{type(exc).__name__}: {exc}")
    if not isinstance(model, dict):
        raise RpcError(f"panel {panel_id!r} returned {type(model).__name__}")
    problems = form.validate(model)
    if problems:
        model.setdefault("sections", []).append(
            form.section("Contract problems", [form.note("; ".join(problems), "danger")])
        )
    model["version"] = __version__
    return model


def _apply(params: dict) -> dict:
    panel_id = str(params.get("id") or "")
    changes = params.get("changes") or {}
    if not isinstance(changes, dict):
        raise RpcError("changes must be an object")
    module = _module(panel_id)
    apply = getattr(module, "apply", None)
    if apply is None:
        raise RpcError(f"{panel_id} is read-only")
    result = apply(changes)
    if not isinstance(result, dict):
        raise RpcError(f"{panel_id}.apply returned {type(result).__name__}")
    result.setdefault("ok", True)
    result.setdefault("message", "Applied")
    result.setdefault("refresh", True)
    return result


def _action(params: dict) -> dict:
    panel_id = str(params.get("id") or "")
    name = str(params.get("action") or "")
    args = params.get("args") or {}
    if name == "panel.refresh":
        return {"ok": True, "message": "Refreshed", "refresh": True}
    if not isinstance(args, dict):
        raise RpcError("args must be an object")
    module = _module(panel_id)
    action = getattr(module, "action", None)
    if action is None:
        raise RpcError(f"{panel_id} has no actions")
    result = action(name, args)
    if not isinstance(result, dict):
        raise RpcError(f"{panel_id}.action returned {type(result).__name__}")
    result.setdefault("ok", True)
    result.setdefault("message", "Done")
    result.setdefault("refresh", True)
    return result


def _search(params: dict) -> dict:
    query = str(params.get("query") or "")
    return {"query": query, "results": catalog.search(query)}


def _fs_list(params: dict) -> dict:
    raw = str(params.get("path") or "~")
    target = Path(raw).expanduser()
    if not target.is_dir():
        target = target.parent
    limit = int(params.get("limit") or 500)
    entries = []
    try:
        for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if child.name.startswith(".") and not params.get("hidden"):
                continue
            try:
                is_dir = child.is_dir()
                size = 0 if is_dir else child.stat().st_size
            except OSError:
                continue
            entries.append({
                "name": child.name,
                "path": str(child),
                "dir": is_dir,
                "size": size,
            })
            if len(entries) >= limit:
                break
    except OSError as exc:
        raise RpcError(f"cannot read {target}: {exc}") from exc
    parent = str(target.parent) if target.parent != target else ""
    return {"path": str(target), "parent": parent, "entries": entries}


def _ui_get(params: dict) -> dict:
    data = util.read_json(paths.UI_STATE, {})
    return data if isinstance(data, dict) else {}


def _ui_set(params: dict) -> dict:
    updates = params.get("values") or {}
    if not isinstance(updates, dict):
        raise RpcError("values must be an object")
    current = _ui_get({})
    current.update(updates)
    util.write_json(paths.UI_STATE, current)
    return current


def _status(params: dict) -> dict:
    return {
        "version": __version__,
        "hostname": util.hostname(),
        "session": util.session_kind(),
        "privilege": priv.mode(),
        "panels": len(catalog.PANELS),
        "suite": apps.all_apps(),
    }


HANDLERS: dict[str, Callable[[dict], Any]] = {
    "hello": _hello,
    "catalog": _catalog,
    "panel": _panel,
    "apply": _apply,
    "action": _action,
    "search": _search,
    "fs.list": _fs_list,
    "ui.get": _ui_get,
    "ui.set": _ui_set,
    "status": _status,
}


def handle(request: dict) -> dict:
    rid = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}
    try:
        fn = HANDLERS.get(method)
        if fn is None:
            raise RpcError(f"unknown method {method!r}")
        return {"id": rid, "result": fn(params if isinstance(params, dict) else {})}
    except RpcError as exc:
        return {"id": rid, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - report, never kill the session
        traceback.print_exc(file=sys.stderr)
        return {"id": rid, "error": f"{type(exc).__name__}: {exc}"}


def serve() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            print(json.dumps({"id": None, "error": f"bad json: {exc}"}), flush=True)
            continue
        response = handle(request if isinstance(request, dict) else {})
        print(json.dumps(response), flush=True)
    return 0
