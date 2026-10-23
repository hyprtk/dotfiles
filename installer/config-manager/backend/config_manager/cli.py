"""Command line interface for hyprtk-config-manager."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__, lua_edit, schema, state, verify
from .lua_probe import ProbeError, discover, probe
from .paths import find_hypr_dir
from .rpc import handle
from .writers import bar as bar_writer

APP_DIR = Path(__file__).resolve().parents[2]


def _root(args) -> Path:
    if args.root:
        return Path(args.root).expanduser()
    found = find_hypr_dir()
    if found is None:
        raise SystemExit("no hyprland.lua found (use --root or set HYPR_CM_DIR)")
    return found


def _parse_value(raw: str, kind: str | None):
    if kind in ("str", "enum", "color"):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _kind_for(path: str) -> str | None:
    opt = schema.option(path)
    return opt.get("type") if opt else None


def cmd_dump(args) -> int:
    model = probe(_root(args))
    if args.summary:
        print(f"root       {model['root']}")
        print(f"requires   {', '.join(model['requires']) or '-'}")
        print(f"curves     {', '.join(model['curves']) or '-'}")
        print(f"animations {', '.join(model['animation_order']) or '-'}")
        print(f"binds      {len(model['binds'])}")
        print(f"monitors   {len(model['monitors'])}")
        print(f"rules      {sum(len(v) for v in model['rules'].values())}")
        print(f"env        {len(model['env'])}")
        print(f"error      {model['error'] or '-'}")
        return 0
    print(json.dumps(model, indent=2))
    return 0


def cmd_schema(args) -> int:
    print(json.dumps(schema.schema(), indent=2))
    return 0


def cmd_get(args) -> int:
    model = probe(_root(args))
    node = model["config"]
    for part in args.path.split("."):
        if not isinstance(node, dict) or part not in node:
            print(f"{args.path} is not set", file=sys.stderr)
            return 1
        node = node[part]
    if args.json:
        print(json.dumps({"path": args.path, "value": node}))
    else:
        print(f"{args.path} = {json.dumps(node) if isinstance(node, (dict, list)) else node}")
    return 0


def _apply(args, root: Path) -> dict:
    return handle({
        "id": 1,
        "method": "apply",
        "params": {
            "root": str(root),
            "reason": f"cli set {args.path}",
            "edits": [{"type": "config", "path": args.path, "value": _parse_value(args.value, args.kind or _kind_for(args.path)), "kind": args.kind or _kind_for(args.path)}],
        },
    })


def cmd_set(args) -> int:
    root = _root(args)
    if args.dry_run:
        return _dry_run(args, root)
    res = _apply(args, root)
    if "error" in res:
        print(res["error"], file=sys.stderr)
        return 1
    result = res["result"]
    for entry in result["diffs"]:
        print(entry["diff"], end="")
    if result["backup"]:
        print(f"backup: {result['backup']['stamp']}")
    print(f"verified {args.path}")
    return 0


def _dry_run(args, root: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="hypr-cm-dry-") as tmp:
        copy = Path(tmp) / "hypr"
        shutil.copytree(root, copy)
        saved_backup = state.BACKUP_ROOT
        state.BACKUP_ROOT = Path(tmp) / "backups"
        try:
            res = _apply(args, copy)
        finally:
            state.BACKUP_ROOT = saved_backup
        if "error" in res:
            print(res["error"], file=sys.stderr)
            return 1
        import difflib

        changed = False
        for rel in res["result"]["files"]:
            before = (root / rel).read_text(encoding="utf-8")
            after = (copy / rel).read_text(encoding="utf-8")
            if before != after:
                changed = True
                print("".join(difflib.unified_diff(
                    before.splitlines(keepends=True),
                    after.splitlines(keepends=True),
                    fromfile=f"a/{rel}", tofile=f"b/{rel}",
                )), end="")
        print("dry-run: no files written" + ("" if changed else " (no change)"))
    return 0


def cmd_validate(args) -> int:
    res = handle({"id": 1, "method": "validate", "params": {"root": str(_root(args))}})["result"]
    if res["ok"]:
        print(f"ok: {', '.join(res['requires']) or 'no requires'}")
        return 0
    print(f"error: {res['error']}", file=sys.stderr)
    return 1


def cmd_apply(args) -> int:
    payload = json.loads(Path(args.file).read_text()) if args.file else json.load(sys.stdin)
    res = handle({"id": 1, "method": "apply", "params": {"root": str(_root(args)), **payload}})
    print(json.dumps(res, indent=2))
    return 0 if "result" in res else 1


def cmd_backup(args) -> int:
    if args.action == "list":
        for item in state.backups():
            print(f"{item['stamp']}  {item['status']:12}  {item['reason']}  ({len(item.get('files') or [])} files)")
        return 0
    if args.action == "restore":
        print(json.dumps(state.restore(args.stamp, root=Path(args.root).expanduser() if args.root else None), indent=2))
        return 0
    print("usage: backup {list|restore <stamp>}", file=sys.stderr)
    return 2


def cmd_bar(args) -> int:
    path = Path(args.path).expanduser() if args.path else bar_writer.BAR_CONFIG
    if args.action == "get":
        print(json.dumps(bar_writer.get(path), indent=2))
        return 0
    updates = {args.key: _parse_value(args.value, None)}
    print(json.dumps(bar_writer.update(updates, path), indent=2))
    return 0


def cmd_open(args) -> int:
    import os

    env = dict(os.environ)
    if args.page:
        env["HYPR_CM_PAGE"] = args.page
    if getattr(args, "overlay", False):
        env["HYPR_CM_OVERLAY"] = "1"
    try:
        proc = subprocess.Popen(
            ["qs", "-p", str(APP_DIR)], env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print("qs (Quickshell) not found in PATH", file=sys.stderr)
        return 1
    if args.foreground:
        return proc.wait()
    return 0


def cmd_serve(args) -> int:
    from . import rpc

    return rpc.serve()


def cmd_version(args) -> int:
    print(f"hyprtk-config-manager {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="config-manager", description="Hyprland Lua configuration manager")
    ap.add_argument("--root", help="Hyprland config dir (default: auto-detect)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("open", help="open the GUI")
    p.add_argument("--page")
    p.add_argument("--overlay", action="store_true",
                   help="open as a layer-shell overlay (used by bar-qt Settings)")
    p.add_argument("--foreground", action="store_true")
    p.set_defaults(func=cmd_open)

    p = sub.add_parser("dump", help="dump the effective model")
    p.add_argument("--summary", action="store_true")
    p.set_defaults(func=cmd_dump)

    p = sub.add_parser("schema", help="dump page/option metadata")
    p.set_defaults(func=cmd_schema)

    p = sub.add_parser("get", help="read an effective config value")
    p.add_argument("path")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("set", help="write a config value to its owning module")
    p.add_argument("path")
    p.add_argument("value")
    p.add_argument("--kind")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("validate", help="syntax-check and probe the tree")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("apply", help="apply a JSON edit batch from a file or stdin")
    p.add_argument("file", nargs="?")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("backup", help="list or restore backups")
    p.add_argument("action", choices=["list", "restore"])
    p.add_argument("stamp", nargs="?")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("bar", help="read/write hyprtk-bar-qt animation keys")
    p.add_argument("action", choices=["get", "set"])
    p.add_argument("key", nargs="?")
    p.add_argument("value", nargs="?")
    p.add_argument("--path")
    p.set_defaults(func=cmd_bar)

    p = sub.add_parser("serve", help="JSON-lines RPC over stdio")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("version", help="print the version")
    p.set_defaults(func=cmd_version)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        return cmd_open(argparse.Namespace(page=None, foreground=False))
    try:
        return args.func(args)
    except (ProbeError, lua_edit.EditError, verify.VerifyError, state.TransactionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
