"""List and launch applications for a file (Open With)."""

from __future__ import annotations

import configparser
import mimetypes
import os
import shlex
import shutil
import subprocess
from pathlib import Path

FIELD_CODES = {"%f", "%F", "%u", "%U", "%i", "%c", "%k", "%d", "%D", "%n", "%N",
               "%v", "%m"}


def _gio_available() -> bool:
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio  # noqa: F401
        return True
    except Exception:
        return False


def _content_type(path: str) -> str:
    guessed, _ = mimetypes.guess_type(path)
    if guessed:
        return guessed
    try:
        proc = subprocess.run(
            ["file", "-b", "--mime-type", path],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "application/octet-stream"
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return "application/octet-stream"


def _icon_name(app) -> str:
    try:
        icon = app.get_icon()
    except Exception:
        return ""
    if icon is None:
        return ""
    names = getattr(icon, "get_names", None)
    if callable(names):
        try:
            values = names() or []
        except Exception:
            values = []
        if values:
            return str(values[0])
    name = getattr(icon, "get_name", None)
    if callable(name):
        try:
            return str(name() or "")
        except Exception:
            return ""
    return ""


def _gio_entries(mime: str) -> list[dict]:
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    default = None
    try:
        default = Gio.AppInfo.get_default_for_type(mime, False)
    except Exception:
        default = None
    default_id = default.get_id() if default else ""

    seen: set[str] = set()
    entries: list[dict] = []

    def add(app, recommended: bool) -> None:
        if app is None or not app.should_show():
            return
        app_id = app.get_id() or app.get_name() or ""
        if not app_id or app_id in seen:
            return
        seen.add(app_id)
        filename = ""
        getter = getattr(app, "get_filename", None)
        if callable(getter):
            try:
                filename = str(getter() or "")
            except Exception:
                filename = ""
        argv: list[str] = []
        if not filename:
            try:
                argv = shlex.split(app.get_commandline() or "")
            except ValueError:
                argv = []
        entries.append({
            "id": app_id,
            "name": app.get_display_name() or app.get_name() or app_id,
            "icon": _icon_name(app),
            "desktopFile": filename,
            "default": app_id == default_id,
            "recommended": recommended,
            "argv": argv,
        })

    try:
        recommended = Gio.AppInfo.get_recommended_for_type(mime) or []
    except Exception:
        recommended = []
    for app in recommended:
        add(app, True)
    try:
        everything = Gio.AppInfo.get_all_for_type(mime) or []
    except Exception:
        everything = []
    for app in everything:
        add(app, False)
    return entries


def _data_dirs() -> list[Path]:
    dirs: list[Path] = []
    home = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    dirs.append(home)
    for item in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"):
        if item:
            dirs.append(Path(item))
    return dirs


def _desktop_ids() -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for base in _data_dirs():
        apps = base / "applications"
        if not apps.is_dir():
            continue
        for path in sorted(apps.glob("*.desktop")):
            if path.name in seen:
                continue
            seen.add(path.name)
            files.append(path)
    return files


def _read_desktop(path: Path) -> dict:
    parser = configparser.RawConfigParser(
        interpolation=None, strict=False, delimiters=("=",),
        comment_prefixes=("#", ";"),
    )
    parser.optionxform = str
    try:
        parser.read(path, encoding="utf-8")
    except Exception:
        return {}
    if not parser.has_section("Desktop Entry"):
        return {}
    return dict(parser.items("Desktop Entry"))


def _desktop_exec(path: str | Path) -> str:
    if not path:
        return ""
    return _read_desktop(Path(path)).get("Exec", "")


def _matches_mime(data: dict, mime: str) -> bool:
    values = (data.get("MimeType") or "").replace("\n", ";").split(";")
    return mime in {item.strip() for item in values if item.strip()}


def _exec_argv(exec_line: str, target: str) -> list[str]:
    try:
        tokens = shlex.split(exec_line or "")
    except ValueError:
        tokens = (exec_line or "").split()
    argv: list[str] = []
    placed = False
    for token in tokens:
        if token in {"%f", "%F", "%u", "%U"}:
            if not placed:
                argv.append(target)
                placed = True
            continue
        if token.startswith("%") and token.endswith("%") and len(token) == 2:
            continue
        if token in FIELD_CODES:
            continue
        if any(code in token for code in ("%f", "%F", "%u", "%U")):
            placed = True
        replaced = (token.replace("%%", "%")
                    .replace("%F", target).replace("%U", target)
                    .replace("%f", target).replace("%u", target))
        argv.append(replaced)
    if not placed and argv:
        argv.append(target)
    return argv


def _desktop_entries(mime: str) -> list[dict]:
    entries: list[dict] = []
    for path in _desktop_ids():
        data = _read_desktop(path)
        if not data:
            continue
        if data.get("Hidden", "").strip().lower() == "true":
            continue
        if data.get("NoDisplay", "").strip().lower() == "true":
            continue
        if not _matches_mime(data, mime):
            continue
        exec_line = data.get("Exec", "")
        if not exec_line:
            continue
        try_exec = data.get("TryExec", "").strip()
        if try_exec and not shutil.which(try_exec):
            continue
        entries.append({
            "id": path.name,
            "name": data.get("Name") or path.name,
            "icon": data.get("Icon", ""),
            "desktopFile": str(path),
            "default": False,
            "recommended": False,
            "argv": [],
        })
    entries.sort(key=lambda item: item["name"].lower())
    return entries


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))


def _set_ini_default(lines: list[str], mime: str, desktop_id: str) -> list[str]:
    section = "Default Applications"
    out: list[str] = []
    in_section = False
    seen_section = False
    replaced = False
    inserted = False

    def flush_insert() -> None:
        nonlocal inserted
        if in_section and not replaced and not inserted:
            out.append(f"{mime}={desktop_id};")
            inserted = True

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            flush_insert()
            in_section = stripped == f"[{section}]"
            if in_section:
                seen_section = True
            out.append(line)
            continue
        if in_section and not replaced:
            key = line.split("=", 1)[0].strip()
            if key == mime:
                out.append(f"{mime}={desktop_id};")
                replaced = True
                continue
        out.append(line)
    flush_insert()
    if not seen_section:
        if out and out[-1].strip():
            out.append("")
        out.append(f"[{section}]")
        out.append(f"{mime}={desktop_id};")
    return out


def _write_mimeapps_default(desktop_id: str, mime: str) -> None:
    path = _config_home() / "mimeapps.list"
    lines: list[str] = []
    if path.exists():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
    lines = _set_ini_default(lines, mime, desktop_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _apply_default(desktop_id: str, mime: str) -> None:
    xdg_mime = shutil.which("xdg-mime")
    if xdg_mime:
        try:
            proc = subprocess.run(
                [xdg_mime, "default", desktop_id, mime],
                capture_output=True, text=True, timeout=5,
            )
            if proc.returncode == 0:
                return
        except (OSError, subprocess.TimeoutExpired):
            pass
    if _gio_available():
        try:
            import gi

            gi.require_version("Gio", "2.0")
            from gi.repository import Gio

            info = Gio.DesktopAppInfo.new(desktop_id)
            if info is not None and info.set_as_default_for_type(mime):
                return
        except Exception:
            pass
    _write_mimeapps_default(desktop_id, mime)


def _entries(path: str) -> list[dict]:
    mime = _content_type(path)
    if not _gio_available():
        return _desktop_entries(mime)
    entries = _gio_entries(mime)
    default = [item for item in entries if item["default"]]
    recommended = [
        item for item in entries
        if item["recommended"] and not item["default"]
    ]
    rest = sorted(
        (item for item in entries if not item["recommended"] and not item["default"]),
        key=lambda item: item["name"].lower(),
    )
    return default + recommended + rest


def applications(path: str) -> dict:
    target = Path(path).expanduser()
    if not target.exists():
        raise FileNotFoundError(str(target))
    mime = _content_type(str(target))
    apps = []
    for item in _entries(str(target)):
        apps.append({
            "id": item["id"],
            "name": item["name"],
            "icon": item.get("icon", ""),
            "desktopFile": item.get("desktopFile", ""),
            "default": bool(item.get("default", False)),
        })
    return {
        "kind": "open_with",
        "path": str(target),
        "mime": mime,
        "apps": apps,
    }


def set_default(path: str, app_id: str) -> dict:
    target = Path(path).expanduser()
    if not target.exists():
        raise FileNotFoundError(str(target))
    app_id = str(app_id or "")
    if not app_id:
        raise ValueError("no application selected")
    mime = _content_type(str(target))
    entry = next((item for item in _entries(str(target)) if item["id"] == app_id), None)
    if entry is None:
        raise ValueError(f"application not available: {app_id}")
    desktop = entry.get("desktopFile") or ""
    desktop_id = Path(desktop).name if desktop else app_id
    _apply_default(desktop_id, mime)
    return {
        "kind": "open_with_default",
        "path": str(target),
        "mime": mime,
        "app": app_id,
        "desktopId": desktop_id,
    }


def launch(path: str, app_id: str) -> dict:
    target = Path(path).expanduser()
    if not target.exists():
        raise FileNotFoundError(str(target))
    app_id = str(app_id or "")
    if not app_id:
        raise ValueError("no application selected")
    entry = next((item for item in _entries(str(target)) if item["id"] == app_id), None)
    if entry is None:
        raise ValueError(f"application not available: {app_id}")
    desktop = entry.get("desktopFile") or ""
    if desktop and shutil.which("gio"):
        argv = ["gio", "launch", desktop, str(target)]
    elif desktop:
        argv = _exec_argv(_desktop_exec(desktop), str(target))
    else:
        argv = list(entry.get("argv") or [])
        argv = _exec_argv(" ".join(shlex.quote(part) for part in argv), str(target))
    if not argv:
        raise RuntimeError(f"cannot launch {app_id}")
    subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"kind": "open_with_launch", "path": str(target), "app": app_id, "argv": argv}
