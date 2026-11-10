"""Launch external terminals, optionally elevated."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def terminal_argv(path: str) -> list[str]:
    candidates = [
        ["alacritty", "--working-directory", path],
        ["kitty", "--directory", path],
        ["foot", "--working-directory", path],
        ["wezterm", "start", "--cwd", path],
    ]
    env_terminal = os.environ.get("TERMINAL")
    if env_terminal:
        candidates.append(env_terminal.split())
    for argv in candidates:
        executable = shutil.which(argv[0])
        if executable:
            return [executable] + argv[1:]
    raise RuntimeError("no terminal found (set $TERMINAL)")


def _forward_env() -> list[str]:
    keys = (
        "WAYLAND_DISPLAY",
        "XDG_RUNTIME_DIR",
        "DISPLAY",
        "XAUTHORITY",
        "DBUS_SESSION_BUS_ADDRESS",
        "XDG_SESSION_TYPE",
    )
    return [f"{key}={os.environ[key]}" for key in keys if os.environ.get(key)]


def open_terminal(path: str, root: bool = False) -> dict:
    target = Path(path).expanduser()
    if target.is_file():
        target = target.parent
    if not target.is_dir():
        raise NotADirectoryError(str(target))
    argv = terminal_argv(str(target))
    if root:
        if not shutil.which("pkexec"):
            raise RuntimeError("pkexec not found")
        command = ["pkexec", "env"] + _forward_env() + argv
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        subprocess.Popen(
            argv,
            cwd=str(target),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    return {"kind": "terminal", "path": str(target), "root": bool(root), "terminal": argv[0]}
