"""The notification that knows where the file went.

``notify-send`` can report which button the user pressed, but only while the
notification is alive — so the process waiting for the answer has to outlive the
app. The recorder spawns ``hyprtk-rec notify-saved PATH`` detached; that process
blocks on notify-send and then opens the folder or copies the path.

Nothing here is required for a recording to work: a daemon without action
support simply shows the same notification with no buttons.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "Screen Recorder"
ACTIONS = (("open", "Open folder"), ("copy", "Copy path"))


def icon_path() -> str:
    return str(Path(__file__).resolve().parent / "assets" / "hyprtk-rec.svg")


def argv_for(path: str, *, program: str = "notify-send", app_name: str = APP_NAME,
             icon: str | None = None, actions: bool = True) -> list[str]:
    """The notify-send command line, with one button per action."""
    target = Path(path).expanduser()
    argv = [program, "-a", app_name]
    icon = icon_path() if icon is None else icon
    if icon:
        argv += ["-i", icon]
    if actions:
        for key, label in ACTIONS:
            argv += ["-A", f"{key}={label}"]
    argv += ["Recording saved", f"{target.name}"]
    return argv


def _open_folder(path: str) -> bool:
    folder = Path(path).expanduser().parent
    try:
        subprocess.Popen(["xdg-open", str(folder)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError:
        return False
    return True


def _copy_text(text: str) -> bool:
    for program, extra in (("wl-copy", []), ("xclip", ["-selection", "clipboard"])):
        if not shutil.which(program):
            continue
        try:
            result = subprocess.run([program, *extra], input=text.encode("utf-8"),
                                    timeout=5, check=False,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return True
    return False


def handle(action: str, path: str, *, opener=_open_folder, copier=_copy_text) -> bool:
    """Act on the pressed button; an empty action means "dismissed"."""
    action = (action or "").strip()
    if not path:
        return False
    if action == "open":
        return bool(opener(path))
    if action == "copy":
        return bool(copier(str(Path(path).expanduser())))
    return False


def run(path: str, *, program: str = "notify-send", icon: str | None = None,
        runner=subprocess.run) -> int:
    """Show the notification and act on the answer; blocks until it is gone."""
    if not path:
        print("hyprtk-rec: notify-saved needs a path", file=sys.stderr)
        return 2
    if not shutil.which(program):
        return 1
    try:
        result = runner(argv_for(path, program=program, icon=icon),
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        timeout=3600, check=False)
        if getattr(result, "returncode", 0) != 0:
            # "Actions are not supported by this notifications server" is a
            # real daemon (mako/swaync/dunst all support them, so this is a
            # minimal one): fall back to the same notification, no buttons.
            result = runner(argv_for(path, program=program, icon=icon, actions=False),
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=3600, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 1
    action = (getattr(result, "stdout", b"") or b"").decode("utf-8", "replace").strip()
    handle(action, path)
    return 0 if getattr(result, "returncode", 0) == 0 else 1
