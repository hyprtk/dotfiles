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


def _write_target_ok(path: str) -> bool:
    if not path:
        return False
    if path in ETC_FILES:
        return True
    if path.startswith(SYS_PREFIXES):
        return True
    return any(path.startswith(prefix) for prefix in WRITE_ROOT_FILES)


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
        verb = next((part for part in argv[1:] if not part.startswith("-")), "")
        if verb not in SYSTEMCTL_VERBS and not verb.startswith("is-"):
            return f"systemctl {verb} is not allowed"
        return ""
    if binary in ("install", "tee"):
        targets = [part for part in argv[1:] if not part.startswith("-")]
        if binary == "install":
            # `install -d -m 0755 DIR` has no source; the last argument is the target.
            if not targets:
                return "install needs a target"
            if "-d" not in argv and len(targets) < 2:
                return "install needs a source and a target"
            target = targets[-1]
        else:
            if not targets:
                return "tee needs a file"
            target = targets[0]
        if not _write_target_ok(target):
            return f"{target} is outside the paths this action may write"
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
