"""Command line interface for hyprtk-system-manager."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__, apps, catalog, form, priv, state, util

APP_DIR = Path(__file__).resolve().parents[2]
def cmd_open(args) -> int:
    env = dict(os.environ)
    # Quickshell reports every toplevel as org.quickshell unless this is set,
    # which costs the app its desktop entry, icon and window rules.
    env.setdefault("QS_APP_ID", "hyprtk-system-manager")
    if args.page:
        env["HYPRTK_SM_PAGE"] = args.page
    if args.overlay:
        env["HYPRTK_SM_OVERLAY"] = "1"
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


def cmd_panels(args) -> int:
    if args.json:
        print(json.dumps(catalog.catalog(), indent=2))
        return 0
    for group in catalog.GROUPS:
        print(f"[{group['title']}]")
        for panel in catalog.PANELS:
            if panel["group"] != group["id"]:
                continue
            print(f"  {panel['id']:<14} {panel['status']:<8} {panel['title']}")
    return 0


def cmd_panel(args) -> int:
    from . import rpc

    response = rpc.handle({"id": 1, "method": "panel", "params": {"id": args.id}})
    if "error" in response:
        print(response["error"], file=sys.stderr)
        return 1
    model = response["result"]
    problems = form.validate(model)
    if problems:
        for problem in problems:
            print(f"contract: {problem}", file=sys.stderr)
    print(json.dumps(model, indent=2, ensure_ascii=False))
    return 0 if not problems else 2


def cmd_apply(args) -> int:
    from . import rpc

    changes: dict = {}
    for pair in args.changes:
        key, _, value = pair.partition("=")
        if not key:
            print(f"bad change {pair!r} (use key=value)", file=sys.stderr)
            return 2
        try:
            changes[key] = json.loads(value)
        except ValueError:
            changes[key] = value
    response = rpc.handle({
        "id": 1, "method": "apply",
        "params": {"id": args.id, "changes": changes},
    })
    if "error" in response:
        print(response["error"], file=sys.stderr)
        return 1
    result = response["result"]
    print(result.get("message", ""))
    for line in result.get("details") or []:
        print(f"  {line}")
    return 0 if result.get("ok") else 1


def _action_name(panel_id: str, name: str) -> str:
    """Accept both ``create`` and ``users.create`` on the CLI."""
    name = (name or "").strip()
    if name and "." not in name:
        return f"{panel_id}.{name}"
    return name


def cmd_action(args) -> int:
    from . import rpc

    payload = {}
    if args.args:
        try:
            payload = json.loads(args.args)
        except ValueError:
            print("--args must be JSON", file=sys.stderr)
            return 2
    response = rpc.handle({
        "id": 1, "method": "action",
        "params": {"id": args.id, "action": _action_name(args.id, args.action),
                   "args": payload},
    })
    if "error" in response:
        print(response["error"], file=sys.stderr)
        return 1
    result = response["result"]
    print(result.get("message", ""))
    for line in result.get("details") or []:
        print(f"  {line}")
    return 0 if result.get("ok") else 1


def cmd_doctor(args) -> int:
    print(f"hyprtk-system-manager {__version__}")
    print(f"host        {util.hostname()} · {util.os_release().get('PRETTY_NAME', 'Linux')}")
    print(f"session     {util.session_kind()} · {util.desktop() or 'unknown'}")
    print(f"privilege   {priv.mode()}")
    print(f"hyprland    {util.read_text('/etc/hostname').strip() or util.hostname()}")
    print()
    failures = 0
    for panel in catalog.PANELS:
        try:
            module = catalog.module_for(panel["id"])
            model = module.probe()
            problems = form.validate(model)
            state_text = "ok" if not problems else f"{len(problems)} contract problem(s)"
            if problems:
                failures += 1
            print(f"{panel['id']:<14} {panel['status']:<8} {state_text}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"{panel['id']:<14} {panel['status']:<8} FAILED {type(exc).__name__}: {exc}")
    print()
    print(f"suite apps: {len([a for a in apps.all_apps() if a['installed']])} installed")
    return 0 if failures == 0 else 1


def cmd_backups(args) -> int:
    if args.action == "list":
        for item in state.backups():
            print(f"{item['stamp']}  {item.get('status', '?'):<10} {item.get('reason', '')} "
                  f"({len(item.get('files') or [])} files)")
        return 0
    if args.action == "restore":
        if not args.stamp:
            print("restore needs a stamp", file=sys.stderr)
            return 2
        print(json.dumps(state.restore(args.stamp), indent=2))
        return 0
    print("usage: backups {list|restore <stamp>}", file=sys.stderr)
    return 2


def cmd_version(args) -> int:
    print(f"hyprtk-system-manager {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hyprtk-settings",
        description="Configure the hyprtk desktop and the Linux system under it",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("open", help="open the GUI")
    p.add_argument("--page")
    p.add_argument("--overlay", action="store_true", help="layer-shell overlay for the bar")
    p.add_argument("--foreground", action="store_true")
    p.set_defaults(func=cmd_open)

    p = sub.add_parser("serve", help="JSON-lines RPC over stdio")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("panels", help="list panels")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_panels)

    p = sub.add_parser("panel", help="print a panel form model")
    p.add_argument("id")
    p.set_defaults(func=cmd_panel)

    p = sub.add_parser("apply", help="apply key=value changes to a panel")
    p.add_argument("id")
    p.add_argument("changes", nargs="+")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("action", help="run a panel action")
    p.add_argument("id")
    p.add_argument("action")
    p.add_argument("--args", help="JSON object")
    p.set_defaults(func=cmd_action)

    p = sub.add_parser("doctor", help="probe every panel and report contract problems")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("backups", help="list or restore file snapshots")
    p.add_argument("action", choices=["list", "restore"])
    p.add_argument("stamp", nargs="?")
    p.set_defaults(func=cmd_backups)

    p = sub.add_parser("version", help="print the version")
    p.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        return cmd_open(argparse.Namespace(page=None, overlay=False, foreground=False))
    try:
        return args.func(args)
    except (state.TransactionError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
