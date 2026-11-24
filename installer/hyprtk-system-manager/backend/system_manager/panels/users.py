"""Users & Groups — local accounts, passwords, groups and shells."""

from __future__ import annotations

import getpass
import os
import pwd
import re

from .. import form, priv, util
from . import base

USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def parse_passwd(text: str) -> list[dict]:
    """Return regular (login) accounts from ``getent passwd`` output."""
    users: list[dict] = []
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) < 7:
            continue
        name, _pw, uid_s, gid_s, gecos, home, shell = parts[:7]
        try:
            uid = int(uid_s)
            gid = int(gid_s)
        except ValueError:
            continue
        if uid == 0:
            kind = "root"
        elif 1000 <= uid < 60000:
            kind = "user"
        else:
            continue
        users.append({
            "name": name, "uid": uid, "gid": gid,
            "fullname": (gecos or "").split(",", 1)[0],
            "home": home, "shell": shell, "kind": kind,
        })
    users.sort(key=lambda item: (item["kind"] != "root", item["uid"]))
    return users


def parse_groups(text: str) -> list[str]:
    return [part for part in text.replace(",", " ").split() if part]


def shells() -> list[str]:
    found: list[str] = []
    for line in util.read_text("/etc/shells").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(("nologin", "false")):
            continue
        if os.access(line, os.X_OK):
            found.append(line)
    return sorted(set(found)) or ["/bin/sh"]


def _groups_for(name: str) -> list[str]:
    return parse_groups(util.run(["id", "-nG", name], timeout=6).out)


def _password_state(name: str) -> str:
    """Only the current user can read their own shadow entry unprivileged."""
    if name != getpass.getuser():
        return ""
    result = util.run(["passwd", "-S", name], timeout=6)
    parts = result.out.split()
    if len(parts) >= 2:
        return {"P": "set", "L": "locked", "NP": "empty"}.get(parts[1], parts[1])
    return ""


def _accounts() -> list[dict]:
    users = parse_passwd(util.run(["getent", "passwd"], timeout=10).out)
    me = getpass.getuser()
    items: list[dict] = []
    for user in users:
        groups = _groups_for(user["name"])
        badges = []
        if user["kind"] == "root":
            badges.append("system")
        if "wheel" in groups:
            badges.append("administrator")
        if user["name"] == me:
            badges.append("current session")
        state = _password_state(user["name"])
        if state:
            badges.append(f"password {state}")
        subtitle = " · ".join(part for part in [
            user["fullname"] or user["name"],
            user["shell"],
            f"uid {user['uid']}",
            f"{len(groups)} groups",
        ] if part)
        actions = []
        if user["kind"] != "root":
            locked = state == "locked"
            actions.append({
                "label": "Unlock" if locked else "Lock",
                "action": "users.lock",
                "args": {"username": user["name"], "locked": not locked},
                "variant": "default",
            })
            actions.append({
                "label": "Groups", "action": "users.groups",
                "args": {"username": user["name"], "groups": groups},
                "variant": "default", "needs": "groups",
            })
            actions.append({
                "label": "Shell", "action": "users.shell",
                "args": {"username": user["name"], "shell": user["shell"]},
                "variant": "default", "needs": "shell",
            })
            actions.append({
                "label": "Change password", "action": "users.password",
                "args": {"username": user["name"]}, "variant": "default",
                "needs": "password",
            })
            if user["name"] != me:
                actions.append({
                    "label": "Delete", "action": "users.delete",
                    "args": {"username": user["name"]}, "variant": "danger",
                    "danger": True, "confirm": user["name"],
                })
        items.append({
            "title": user["name"], "subtitle": subtitle,
            "badges": badges, "actions": actions,
            "groups": groups, "home": user["home"], "uid": user["uid"],
        })
    return items


def probe() -> dict:
    items = _accounts()
    me = getpass.getuser()
    shell_list = shells()
    group_list = sorted({
        line.split(":", 1)[0]
        for line in util.read_text("/etc/group").splitlines()
        if ":" in line and not line.startswith("#")
    })

    sections = [
        form.section("Accounts", [
            form.list_row(items, label=""),
            form.note(f"You are signed in as {me}. Account changes need administrator "
                      "authentication and are irreversible without a backup.", "info"),
        ]),
        form.section("Available shells", [
            form.kv([{"label": path, "value": ""} for path in shell_list]),
        ]),
        form.section("Groups on this system", [
            form.kv([{"label": name, "value": ""} for name in group_list]),
        ]),
        form.section("Password policy", [
            form.info("Tooling", "useradd · usermod · chpasswd"),
            form.note("Passwords are sent to chpasswd on stdin and are never logged or "
                      "stored by this application.", "info"),
        ]),
    ]
    page = base.make_page("users", sections)
    page["accounts"] = items
    page["shells"] = shell_list
    page["groups"] = group_list
    try:
        current_shell = pwd.getpwuid(os.getuid()).pw_shell
    except KeyError:
        current_shell = ""
    page["defaultShell"] = current_shell if current_shell in shell_list else (
        shell_list[0] if shell_list else "/bin/sh")
    return page


def _refuse(username: str) -> str:
    if not USERNAME_RE.match(username or ""):
        return "Invalid user name (lowercase letters, digits, underscore, dash)."
    if username == "root":
        return "The root account cannot be changed here."
    return ""


def action(name: str, args: dict) -> dict:
    if name == "users.create":
        username = str(args.get("username") or "").strip()
        problem = _refuse(username)
        if problem:
            return base.fail(problem)
        fullname = str(args.get("fullname") or "").strip()
        shell = str(args.get("shell") or "/bin/sh")
        groups = [g for g in parse_groups(str(args.get("groups") or "")) if g]
        if args.get("admin") and "wheel" not in groups:
            groups.append("wheel")
        argv = ["useradd", "--create-home", "--shell", shell]
        if fullname:
            argv += ["--comment", fullname]
        if groups:
            argv += ["--groups", ",".join(groups)]
        argv.append(username)
        result = priv.run_priv(argv)
        if not result.ok:
            return base.denied(f"Could not create {username}: {result.text.strip()}",
                               priv.command_for(argv))
        password = str(args.get("password") or "")
        if password:
            changed = priv.run_priv(["chpasswd"], input=f"{username}:{password}\n")
            if not changed.ok:
                return base.fail(f"{username} was created, but the password was not set: "
                                 f"{changed.text.strip()}", refresh=True)
        return base.ok(f"Created {username}", details=[priv.command_for(argv)])

    if name == "users.delete":
        username = str(args.get("username") or "").strip()
        if username == getpass.getuser():
            return base.fail("You cannot delete the account you are signed in to.")
        problem = _refuse(username)
        if problem:
            return base.fail(problem)
        argv = ["userdel"]
        if args.get("remove_home", True):
            argv.append("--remove")
        argv.append(username)
        result = priv.run_priv(argv)
        if not result.ok:
            return base.denied(f"Could not delete {username}: {result.text.strip()}",
                               priv.command_for(argv))
        return base.ok(f"Deleted {username}", details=[priv.command_for(argv)])

    if name == "users.lock":
        username = str(args.get("username") or "").strip()
        problem = _refuse(username)
        if problem:
            return base.fail(problem)
        option = "--lock" if args.get("locked") else "--unlock"
        argv = ["usermod", option, username]
        result = priv.run_priv(argv)
        if not result.ok:
            return base.denied(result.text.strip() or "usermod failed", priv.command_for(argv))
        return base.ok(f"{'Locked' if args.get('locked') else 'Unlocked'} {username}",
                       details=[priv.command_for(argv)])

    if name == "users.password":
        username = str(args.get("username") or "").strip()
        problem = _refuse(username)
        if problem:
            return base.fail(problem)
        password = str(args.get("password") or "")
        if len(password) < 1:
            return base.fail("Password cannot be empty")
        result = priv.run_priv(["chpasswd"], input=f"{username}:{password}\n")
        if not result.ok:
            return base.denied(f"Could not change the password: {result.text.strip()}",
                               priv.command_for(["chpasswd"]))
        return base.ok(f"Password changed for {username}", details=["chpasswd (stdin)"])

    if name == "users.groups":
        username = str(args.get("username") or "").strip()
        problem = _refuse(username)
        if problem:
            return base.fail(problem)
        groups = [g for g in parse_groups(str(args.get("groups") or "")) if g]
        argv = ["usermod", "--groups", ",".join(groups), username]
        result = priv.run_priv(argv)
        if not result.ok:
            return base.denied(result.text.strip() or "usermod failed", priv.command_for(argv))
        return base.ok(f"Groups updated for {username}", details=[priv.command_for(argv)])

    if name == "users.shell":
        username = str(args.get("username") or "").strip()
        problem = _refuse(username)
        if problem:
            return base.fail(problem)
        shell = str(args.get("shell") or "")
        if shell not in shells():
            return base.fail(f"{shell} is not a valid login shell")
        argv = ["usermod", "--shell", shell, username]
        result = priv.run_priv(argv)
        if not result.ok:
            return base.denied(result.text.strip() or "usermod failed", priv.command_for(argv))
        return base.ok(f"Shell for {username} set to {shell}", details=[priv.command_for(argv)])

    return base.fail(f"unknown action {name!r}")
