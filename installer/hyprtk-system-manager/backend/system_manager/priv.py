"""Privilege escalation for the handful of actions that need root.

Order: already root → ``sudo -n`` (cached or NOPASSWD) → ``pkexec`` with the
allow-listed ``hyprtk-sm-helper`` (polkit). No long-running root daemon and no
setuid binary. Every call reports which path was used so the UI can say what
happened; the helper validates the action and the command before exec.
"""

from __future__ import annotations

import os

from .util import RunResult, run, which


def euid() -> int:
    return os.geteuid()


def sudo_ready() -> bool:
    """True when ``sudo -n true`` succeeds without a prompt."""
    if euid() == 0:
        return True
    if which("sudo") is None:
        return False
    return run(["sudo", "-n", "true"], timeout=5).ok


def pkexec_ready() -> bool:
    return which("pkexec") is not None


def mode() -> str:
    if euid() == 0:
        return "root"
    if sudo_ready():
        return "sudo"
    if pkexec_ready():
        return "pkexec"
    return "none"


def capabilities() -> dict[str, object]:
    return {
        "mode": mode(),
        "root": euid() == 0,
        "sudo": which("sudo"),
        "sudo_passwordless": sudo_ready(),
        "pkexec": which("pkexec"),
        "can_escalate": mode() != "none",
    }


HELPER_PATHS = ("/usr/libexec/hyprtk-sm-helper", "/usr/local/libexec/hyprtk-sm-helper")


def helper_path() -> str | None:
    found = which("hyprtk-sm-helper")
    if found:
        return found
    for candidate in HELPER_PATHS:
        if os.path.exists(candidate):
            return candidate
    return None


def run_priv(
    argv: list[str],
    *,
    input: str | None = None,
    timeout: float = 120,
    action: str = "system",
) -> RunResult:
    """Run *argv* as root through the best available mechanism."""
    if euid() == 0:
        result = run(argv, input=input, timeout=timeout)
        result.argv = ["(root)"] + list(argv)
        return result

    if sudo_ready():
        result = run(["sudo", "-n", *argv], input=input, timeout=timeout)
        return result

    helper = helper_path()
    if pkexec_ready() and helper:
        # The helper validates the action and command, then execs as root.
        return run(["pkexec", helper, action, "--", *argv], input=input, timeout=timeout)

    if pkexec_ready():
        # pkexec sanitises the environment but runs the binary directly, so
        # absolute system binaries are fine; PATH lookups are not.
        resolved = []
        for index, part in enumerate(argv):
            if index == 0 and "/" not in part:
                found = which(part)
                if found is None:
                    return RunResult(127, "", f"{part}: not found", argv)
                resolved.append(found)
            else:
                resolved.append(part)
        return run(["pkexec", *resolved], input=input, timeout=timeout)

    return RunResult(126, "", "no privilege escalation available (sudo/pkexec)", argv)


def command_for(argv: list[str], action: str = "system") -> str:
    """Human-readable form of how *argv* would be run, for the UI."""
    current = mode()
    if current == "root":
        return " ".join(argv)
    if current == "sudo":
        return "sudo " + " ".join(argv)
    helper = helper_path()
    if helper:
        return f"pkexec {helper} {action} -- " + " ".join(argv)
    return "pkexec " + " ".join(argv)
