"""JSON-lines RPC used by the Quickshell front end.

    {"id": 1, "method": "panel", "params": {"id": "displays"}}
    {"id": 1, "result": {...}}
    {"id": 1, "error": "message"}

Requests are handled on a small thread pool: one slow probe (Updates runs
``checkupdates``, which can take a minute) must never block the rest of the UI.
Responses may therefore arrive out of order; the front end keys them by id.
Apply/action calls are serialised so two writes cannot interleave.

A background index warms the panel probes after ``hello``; ``search`` then
matches row labels from the warmed models in addition to the catalog metadata.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from . import __version__, apps, bus, catalog, form, paths, preview, priv, util

PROBE_TTL = 600
WARM_SKIP = {"updates"}  # network-bound; catalog keywords still cover it

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()
_WRITE_LOCK = threading.Lock()
_PRINT_LOCK = threading.Lock()
_WARM_LOCK = threading.Lock()
_WARM = {"started": False, "running": False}


class RpcError(RuntimeError):
    pass


def _module(panel_id: str):
    try:
        return catalog.module_for(panel_id)
    except KeyError as exc:
        raise RpcError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - a broken panel must not kill the app
        raise RpcError(f"panel {panel_id!r} failed to load: {type(exc).__name__}: {exc}") from exc


def _cache_model(panel_id: str, model: dict) -> None:
    with _CACHE_LOCK:
        _CACHE[panel_id] = (time.time(), model)


def _cached() -> list[tuple[str, dict]]:
    with _CACHE_LOCK:
        return [(panel_id, model) for panel_id, (_at, model) in _CACHE.items()]


def _hello(params: dict) -> dict:
    _start_warm()
    bus.start()
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
    _cache_model(panel_id, model)
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
    if params.get("preview"):
        if getattr(module, "PREVIEW", "") != "files":
            return {"ok": False, "refresh": False,
                    "message": "This panel changes the system directly; there is "
                               "no file diff to show."}
        with preview.capture() as entries:
            returned = apply(changes)
        if not isinstance(returned, dict):
            raise RpcError(f"{panel_id}.apply returned {type(returned).__name__}")
        result = dict(returned)
        result["preview"] = list(entries)
        result["refresh"] = False
        if entries:
            result["ok"] = True
            result["message"] = (f"{len(entries)} file(s) would change")
        elif result.get("ok", True):
            result["ok"] = True
            result["message"] = "Nothing would change"
        return result
    result = apply(changes)
    if not isinstance(result, dict):
        raise RpcError(f"{panel_id}.apply returned {type(result).__name__}")
    result.setdefault("ok", True)
    result.setdefault("message", "Applied")
    result.setdefault("refresh", True)
    with _CACHE_LOCK:
        _CACHE.pop(panel_id, None)
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


def _row_texts(model: dict) -> list[str]:
    """Every human-readable label inside a panel model."""
    out: list[str] = []
    for section in model.get("sections") or []:
        if not isinstance(section, dict):
            continue
        if section.get("title"):
            out.append(str(section["title"]))
        for row in section.get("rows") or []:
            if not isinstance(row, dict):
                continue
            for key in ("label", "help", "value", "text"):
                value = row.get(key)
                if isinstance(value, str) and value:
                    out.append(value)
            for item in row.get("items") or []:
                if not isinstance(item, dict):
                    continue
                for key in ("label", "title", "subtitle", "value"):
                    value = item.get(key)
                    if isinstance(value, str) and value:
                        out.append(value)
    return out


def _row_matches(model: dict, terms: list[str], limit: int = 4) -> list[str]:
    labels: list[str] = []
    for section in model.get("sections") or []:
        for row in section.get("rows") or []:
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or row.get("text") or "").strip()
            texts = [str(row.get(k) or "") for k in ("label", "help", "value")]
            texts += [str(item.get("label") or item.get("title") or "")
                      for item in (row.get("items") or []) if isinstance(item, dict)]
            hay = " ".join(texts).lower()
            if label and all(term in hay for term in terms) and label not in labels:
                labels.append(label)
    return labels[:limit]


def _search(params: dict) -> dict:
    query = str(params.get("query") or "").strip()
    terms = [part for part in query.lower().split() if part]
    if not terms:
        return {"query": query, "results": [], "indexed": len(_cached()),
                "total": len(catalog.PANELS), "indexing": _WARM["running"]}

    found: dict[str, dict] = {}
    for hit in catalog.search(query):
        found[hit["id"]] = dict(hit, matches=[])

    for panel_id, model in _cached():
        matches = _row_matches(model, terms)
        if not matches:
            continue
        entry = found.get(panel_id)
        if entry is None:
            meta = catalog.PANEL_INDEX[panel_id]
            entry = {
                "id": panel_id, "title": meta["title"], "group": meta["group"],
                "icon": meta["icon"], "description": meta["description"],
                "status": meta["status"], "score": 3,
            }
            found[panel_id] = entry
        entry["matches"] = matches
        entry["score"] = entry.get("score", 0) + 2 * len(matches)

    results = sorted(found.values(), key=lambda item: (-item["score"], item["title"]))
    return {"query": query, "results": results[:30], "indexed": len(_cached()),
            "total": len(catalog.PANELS), "indexing": _WARM["running"]}


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
    if not isinstance(data, dict):
        return {}
    data.pop("recent", None)
    return data


def _ui_set(params: dict) -> dict:
    updates = params.get("values") or {}
    if not isinstance(updates, dict):
        raise RpcError("values must be an object")
    current = _ui_get({})
    if "last_page" in updates:
        updates["last_page"] = str(updates["last_page"])
    current.pop("recent", None)
    current.update(updates)
    util.write_json(paths.UI_STATE, current)
    return current


def _focus_poll(params: dict) -> dict:
    return {"requests": bus.poll()}


def _status(params: dict) -> dict:
    return {
        "version": __version__,
        "hostname": util.hostname(),
        "session": util.session_kind(),
        "privilege": priv.mode(),
        "panels": len(catalog.PANELS),
        "indexed": len(_cached()),
        "indexing": _WARM["running"],
        "suite": apps.all_apps(),
    }


def _warm_index() -> None:
    for panel in catalog.PANELS:
        panel_id = panel["id"]
        if panel_id in WARM_SKIP:
            continue
        with _CACHE_LOCK:
            hit = _CACHE.get(panel_id)
        if hit and (time.time() - hit[0]) < PROBE_TTL:
            continue
        try:
            module = catalog.module_for(panel_id)
            model = module.probe()
            if isinstance(model, dict):
                _cache_model(panel_id, model)
        except Exception:  # noqa: BLE001 - the index is best effort
            pass
        time.sleep(0.05)
    with _WARM_LOCK:
        _WARM["running"] = False


def _start_warm() -> None:
    with _WARM_LOCK:
        if _WARM["started"]:
            return
        _WARM["started"] = True
        _WARM["running"] = True
    threading.Thread(target=_warm_index, name="sm-index", daemon=True).start()


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
    "focus.poll": _focus_poll,
}


def handle(request: dict) -> dict:
    rid = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}
    try:
        fn = HANDLERS.get(method)
        if fn is None:
            raise RpcError(f"unknown method {method!r}")
        args = params if isinstance(params, dict) else {}
        if method in ("apply", "action"):
            with _WRITE_LOCK:
                result = fn(args)
        else:
            result = fn(args)
        return {"id": rid, "result": result}
    except RpcError as exc:
        return {"id": rid, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - report, never kill the session
        traceback.print_exc(file=sys.stderr)
        return {"id": rid, "error": f"{type(exc).__name__}: {exc}"}


def serve() -> int:
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=6, thread_name_prefix="sm-rpc")

    def emit(future) -> None:
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001 - a pool error must still answer
            response = {"id": None, "error": f"{type(exc).__name__}: {exc}"}
        with _PRINT_LOCK:
            try:
                print(json.dumps(response), flush=True)
            except (BrokenPipeError, OSError):
                pass

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                with _PRINT_LOCK:
                    print(json.dumps({"id": None, "error": f"bad json: {exc}"}), flush=True)
                continue
            pool.submit(handle, request if isinstance(request, dict) else {}).add_done_callback(emit)
    finally:
        pool.shutdown(wait=True)
    return 0
