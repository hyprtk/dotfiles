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
        "XDG_DATA_HOME",
        "XDG_DATA_DIRS",
        "QT_QPA_PLATFORMTHEME",
    )
    values = [f"{key}={os.environ[key]}" for key in keys if os.environ.get(key)]
    wal_home = os.environ.get("HYPRTK_WAL_HOME") or str(Path.home())
    values.append(f"HYPRTK_WAL_HOME={wal_home}")
    return values


def launcher_path() -> Path:
    return Path(__file__).resolve().parents[2] / "bin" / "hyprtk-fm"


def open_as_root(path: str) -> dict:
    target = Path(path).expanduser()
    if target.is_file():
        target = target.parent
    if not target.is_dir():
        raise NotADirectoryError(str(target))
    if not shutil.which("pkexec"):
        raise RuntimeError("pkexec not found")
    launcher = launcher_path()
    if not launcher.is_file():
        fallback = shutil.which("hyprtk-fm")
        if not fallback:
            raise FileNotFoundError("hyprtk-fm launcher not found")
        launcher = Path(fallback)
    command = ["pkexec", "env"] + _forward_env() + [str(launcher), str(target)]
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"kind": "open_root_fm", "path": str(target), "launcher": str(launcher)}


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
