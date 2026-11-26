"""Privileged helper for polkit: a tiny allow-list in front of root.

``pkexec /usr/libexec/hyprtk-sm-helper <action> -- <command…>`` runs only the
commands on that action's list, with path constraints where a command can write
anywhere. Everything else is refused before touching the system. This is the
only root entry point the app has, so an allow-list (not a shell) is the whole
security model.
"""

from __future__ import annotations

import os
import sys
from typing import Sequence

ACTIONS = {
    "storage": {
        # fstab edits, mount-point creation and formatting a block device
        "install",
        "mkfs.ext4", "mkfs.ext3", "mkfs.vfat", "mkfs.exfat",
        "systemctl",  # only `start`/`enable` unit verbs are accepted below
    },
    "power": {"tee", "install"},
    "privacy": {"ufw", "systemctl", "nft"},
    "users": {"usermod", "chpasswd", "systemctl", "passwd"},
    "system": {
        "systemctl", "timedatectl", "localectl", "locale-gen", "install",
        "lpadmin", "cupsenable", "cupsaccept", "lp", "chpasswd", "fc-cache",
        "update-grub", "grub-mkconfig",
    },
}

SYSTEMCTL_VERBS = {
    "start", "stop", "restart", "reload", "enable", "disable", "mask",
    "unmask", "is-active", "hibernate", "suspend", "poweroff", "reboot",
    "set-timezone", "set-ntp",
}

SYS_PREFIXES = (
    "/sys/class/power_supply/",
    "/sys/class/backlight/",
    "/sys/class/leds/",
)
ETC_FILES = {
    "/etc/fstab", "/etc/locale.gen", "/etc/vconsole.conf", "/etc/localtime",
    "/etc/default/grub", "/etc/ufw/ufw.conf",
}
WRITE_ROOT_FILES = ("/etc/fstab", "/mnt/", "/media/", "/run/media/")


def _fail(message: str) -> int:
    print(f"hyprtk-sm-helper: {message}", file=sys.stderr)
    return 126


def _norm(path: str) -> str:
    """Normalise a path before it is compared against an allow-list.

    ``abspath`` collapses ``.``/``..`` lexically (no filesystem access, so a
    target that does not exist yet still normalises), then the deepest existing
    ancestor is resolved so a symlink cannot point the write somewhere else.
    Without this, ``/run/media/../../etc/sudoers`` passed the prefix check.
    """
    if not path:
        return ""
    absolute = os.path.abspath(path)
    head, tail = absolute, []
    while head not in ("/", "") and not os.path.exists(head):
        head, leaf = os.path.split(head)
        tail.insert(0, leaf)
    return os.path.join(os.path.realpath(head), *tail) if tail else os.path.realpath(head)


def _write_target_ok(path: str) -> bool:
    if not path:
        return False
    target = _norm(path)
    if target in ETC_FILES:
        return True
    if any(target.startswith(prefix) for prefix in SYS_PREFIXES):
        return True
    return any(target.startswith(prefix) for prefix in WRITE_ROOT_FILES)


def _install_ok(argv: Sequence[str]) -> str:
    """``install`` may create directories and copy files, but never with a
    setuid/setgid/owner override: that turns any writable source into root's
    own binary."""
    allowed_flags = {"-d", "-D", "-p", "-v", "--directory", "--preserve-timestamps"}
    targets: list[str] = []
    mode = None
    index = 1
    while index < len(argv):
        part = argv[index]
        if part in ("-m", "--mode"):
            index += 1
            if index >= len(argv):
                return "install -m needs a mode"
            mode = argv[index]
        elif part.startswith("--mode="):
            mode = part.split("=", 1)[1]
        elif part in allowed_flags:
            pass
        elif part.startswith("-"):
            return f"install {part} is not allowed"
        else:
            targets.append(part)
        index += 1
    if mode is not None:
        try:
            bits = int(mode, 8)
        except ValueError:
            return f"install mode {mode!r} is not octal"
        if bits & 0o6000:
            return "install may not set the setuid/setgid bits"
    if not targets:
        return "install needs a target"
    if "-d" not in argv and "--directory" not in argv:
        if len(targets) < 2:
            return "install needs a source and a target"
        for source in targets[:-1]:
            if not _norm(source).startswith(("/tmp/", "/var/tmp/", "/run/user/", "/mnt/",
                                             "/media/", "/run/media/")):
                return f"install may not copy {source}"
    if not _write_target_ok(targets[-1]):
        return f"{targets[-1]} is outside the paths this action may write"
    return ""


def check(action: str, argv: Sequence[str]) -> str:
    """Return "" when the call is allowed, otherwise the reason it is not."""
    if action not in ACTIONS:
        return f"unknown action {action!r}"
    if not argv:
        return "no command"
    binary = os.path.basename(argv[0])
    if binary not in ACTIONS[action]:
        return f"{binary} is not allowed for {action}"
    if binary == "systemctl":
        for part in argv[1:]:
            if part.startswith(("--root", "--machine", "--host", "-H")):
                return f"systemctl {part} is not allowed"
        verb = next((part for part in argv[1:] if not part.startswith("-")), "")
        if verb not in SYSTEMCTL_VERBS and not verb.startswith("is-"):
            return f"systemctl {verb} is not allowed"
        return ""
    if binary == "install":
        return _install_ok(argv)
    if binary == "tee":
        targets = [part for part in argv[1:] if not part.startswith("-")]
        for part in argv[1:]:
            if part.startswith("-") and part not in ("-a", "--append"):
                return f"tee {part} is not allowed"
        if not targets:
            return "tee needs a file"
        if not _write_target_ok(targets[0]):
            return f"{targets[0]} is outside the paths this action may write"
        return ""
    if binary == "grub-mkconfig":
        # `-o` writes the generated config anywhere as root.
        if len(argv) == 1:
            return ""
        if len(argv) == 3 and argv[1] == "-o" and _norm(argv[2]) == "/boot/grub/grub.cfg":
            return ""
        return "grub-mkconfig only accepts -o /boot/grub/grub.cfg"
    if binary == "update-grub":
        return "" if len(argv) == 1 else "update-grub takes no arguments"
    if binary == "usermod":
        for part in argv[1:]:
            if part in ("-p", "--password", "--root", "-R", "--prefix") or part.startswith(
                    ("--password=", "--root=", "--prefix=")):
                return f"usermod {part} is not allowed (password hashes are set with passwd)"
        return ""
    if binary == "passwd":
        if len(argv) != 2 or argv[1].startswith("-"):
            return "passwd needs exactly one user name"
        return ""
    if binary == "chpasswd":
        for part in argv[1:]:
            if part not in ("-e", "--encrypted"):
                return f"chpasswd {part} is not allowed"
        return ""
    if binary.startswith("mkfs."):
        if not argv[-1].startswith("/dev/") or not os.path.exists(argv[-1]):
            return "mkfs needs one existing /dev/ device"
        if any(part not in ("-F", "-f", "-q") for part in argv[1:-1]):
            return "mkfs only accepts the force/quiet flags"
        return ""
    if binary == "ufw":
        if len(argv) < 2 or argv[1] not in ("--force", "enable", "disable", "status"):
            return "only enable, disable and status are allowed"
        return ""
    if binary == "nft" and argv[1:2] not in ([], ["list"]):
        return "only `nft list` is allowed"
    return ""


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print("usage: hyprtk-sm-helper <action> -- <command…>", file=sys.stderr)
        return 2
    action = args[0]
    rest = args[1:]
    if rest[:1] == ["--"]:
        rest = rest[1:]
    reason = check(action, rest)
    if reason:
        return _fail(reason)
    if os.geteuid() != 0:
        return _fail("must run as root (started by pkexec)")
    try:
        os.execvp(rest[0], rest)
    except OSError as exc:
        return _fail(f"cannot run {rest[0]}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
