"""Small, side-effect-light helpers shared by every panel.

Everything that touches the host is funnelled through :func:`run` and
:func:`which` so tests can replace them with fixtures and no test depends on
this machine's hardware.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass
class RunResult:
    code: int = 127
    out: str = ""
    err: str = ""
    argv: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def text(self) -> str:
        return self.out or self.err

    def lines(self) -> list[str]:
        return [line for line in self.text.splitlines() if line.strip()]

    def json(self, default: Any = None) -> Any:
        try:
            return json.loads(self.out)
        except (TypeError, ValueError):
            return default


def which(name: str) -> str | None:
    return shutil.which(name)


def have(name: str) -> bool:
    return which(name) is not None


def run(
    argv: Sequence[str],
    *,
    timeout: float = 15,
    input: str | None = None,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> RunResult:
    """Run a command, never raise; capture text output."""
    args = [str(part) for part in argv]
    merged = None
    if env:
        merged = dict(os.environ)
        merged.update(env)
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input,
            env=merged,
            cwd=str(cwd) if cwd else None,
        )
        return RunResult(proc.returncode, proc.stdout or "", proc.stderr or "", args)
    except FileNotFoundError:
        return RunResult(127, "", f"{args[0]}: not found", args)
    except subprocess.TimeoutExpired:
        return RunResult(124, "", f"{args[0]}: timed out after {timeout}s", args)
    except OSError as exc:
        return RunResult(126, "", f"{args[0]}: {exc}", args)


def run_json(argv: Sequence[str], **kwargs: Any) -> Any:
    return run(argv, **kwargs).json()


def spawn(argv: Sequence[str], *, env: dict[str, str] | None = None) -> bool:
    """Start a detached process and return immediately.

    A GUI launched by an RPC handler must not be waited on: the panel would
    block until the app exits, and a killed parent would take the child with it.
    """
    args = [str(part) for part in argv]
    merged = None
    if env:
        merged = dict(os.environ)
        merged.update(env)
    try:
        subprocess.Popen(
            args, env=merged, start_new_session=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, ValueError):
        return False
    return True


def read_text(path: str | Path, default: str = "") -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return default


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {} if default is None else default
    return data


def atomic_write(path: str | Path, text: str, mode: int | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(path: str | Path, data: Any) -> None:
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# ── facts ────────────────────────────────────────────────────────────────────

def os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    for line in read_text("/etc/os-release").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return read_text("/etc/hostname").strip() or "unknown"


def kernel() -> str:
    return platform.release()


def uptime_seconds() -> int:
    try:
        return int(float(read_text("/proc/uptime").split()[0]))
    except (IndexError, ValueError):
        return 0


def human_uptime(seconds: int) -> str:
    days, rest = divmod(int(seconds), 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def meminfo() -> dict[str, int]:
    """MemTotal / MemAvailable / SwapTotal in bytes."""
    values: dict[str, int] = {}
    for line in read_text("/proc/meminfo").splitlines():
        key, _, rest = line.partition(":")
        bits = rest.split()
        if not bits:
            continue
        try:
            amount = int(bits[0])
        except ValueError:
            continue
        if bits[-1:].__contains__("kB"):
            amount *= 1024
        if key in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
            values[key] = amount
    return values


def cpu_model() -> str:
    for line in read_text("/proc/cpuinfo").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def cpu_cores() -> int:
    return os.cpu_count() or 0


def human_bytes(value: float, precision: int = 1) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    size = float(value or 0)
    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            return f"{size:.{precision}f} {unit}"
        size /= 1024
    return f"{size:.{precision}f} PiB"


def disk_usage(path: str | Path = "/") -> dict[str, int]:
    try:
        usage = shutil.disk_usage(str(path))
    except OSError:
        return {"total": 0, "used": 0, "free": 0}
    return {"total": usage.total, "used": usage.used, "free": usage.free}


def gpu_from_lspci() -> str:
    result = run(["lspci", "-nn"], timeout=8)
    for line in result.lines():
        if any(tag in line for tag in ("VGA compatible", "3D controller", "Display controller")):
            return line.split(": ", 1)[-1].strip()
    return ""


def session_kind() -> str:
    return os.environ.get("XDG_SESSION_TYPE") or ("wayland" if os.environ.get("WAYLAND_DISPLAY") else "tty")


def desktop() -> str:
    return os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or ""


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def split_desktop_exec(value: str) -> list[str]:
    """Best-effort Exec= splitter for .desktop files (quotes + %f placeholders)."""
    out: list[str] = []
    token = ""
    quote = ""
    for char in value or "":
        if quote:
            if char == quote:
                quote = ""
            else:
                token += char
        elif char in "\"'":
            quote = char
        elif char.isspace():
            if token:
                out.append(token)
                token = ""
        else:
            token += char
    if token:
        out.append(token)
    return [part for part in out if not part.startswith("%")]


def parse_desktop_file(path: str | Path) -> dict[str, str]:
    data: dict[str, str] = {}
    section = ""
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section != "Desktop Entry" or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip()
    return data


def iter_lines(text: str) -> Iterable[str]:
    for line in text.splitlines():
        if line.strip():
            yield line
