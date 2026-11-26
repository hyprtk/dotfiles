"""Reading and writing text files without surprising the user.

The editor keeps text internally as UTF-8-ish ``str`` with ``\\n`` line
endings, and remembers the original encoding, byte-order mark and line ending
so a save is byte-faithful. Saves are atomic (temp file + ``os.replace``) and
keep the file's mode.
"""

from __future__ import annotations

import codecs
import os
import stat
import tempfile
from dataclasses import dataclass, field

# Above LARGE_BYTES the editor keeps working but skips syntax highlighting and
# the minimap; above HUGE_BYTES it opens read-only with a banner. QML's text
# engine lays out the whole document, so these are honesty limits, not bugs.
LARGE_BYTES = 400_000
HUGE_BYTES = 2_000_000
MAX_READ_BYTES = 16 * 1024 * 1024

BOMS = {
    "utf-8": codecs.BOM_UTF8,
    "utf-16-le": codecs.BOM_UTF16_LE,
    "utf-16-be": codecs.BOM_UTF16_BE,
}

ENCODINGS = (
    ("utf-8", "UTF-8"),
    ("utf-16-le", "UTF-16 LE"),
    ("utf-16-be", "UTF-16 BE"),
    ("iso-8859-1", "ISO-8859-1"),
    ("cp1252", "Windows-1252"),
    ("ascii", "ASCII"),
)

EOLS = (("lf", "LF"), ("crlf", "CRLF"), ("cr", "CR"))

DISPLAY_ENCODING = dict(ENCODINGS)
DISPLAY_EOL = dict(EOLS)


@dataclass
class Loaded:
    ok: bool = False
    path: str = ""
    text: str = ""
    encoding: str = "utf-8"
    eol: str = "lf"
    bom: bool = False
    readonly: bool = False
    binary: bool = False
    large: bool = False
    huge: bool = False
    size: int = 0
    mtime: float = 0.0
    error: str = ""
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "path": self.path,
            "text": self.text,
            "encoding": self.encoding,
            "eol": self.eol,
            "bom": self.bom,
            "readonly": self.readonly,
            "binary": self.binary,
            "large": self.large,
            "huge": self.huge,
            "size": self.size,
            "mtime": self.mtime,
            "error": self.error,
        }


def display_name(path: str) -> str:
    name = os.path.basename(path.rstrip("/")) or path
    return name or "Untitled"


def _decode(raw: bytes) -> tuple[str, str, bool]:
    if raw.startswith(codecs.BOM_UTF8):
        return raw[len(codecs.BOM_UTF8):].decode("utf-8", "replace"), "utf-8", True
    if raw.startswith(codecs.BOM_UTF16_LE):
        return raw[2:].decode("utf-16-le", "replace"), "utf-16-le", True
    if raw.startswith(codecs.BOM_UTF16_BE):
        return raw[2:].decode("utf-16-be", "replace"), "utf-16-be", True
    for codec in ("utf-8", "cp1252", "iso-8859-1"):
        try:
            return raw.decode(codec), codec, False
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace"), "utf-8", False


def _detect_eol(raw: bytes) -> str:
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    cr = raw.count(b"\r") - crlf
    if crlf >= lf and crlf >= cr and crlf > 0:
        return "crlf"
    if cr > lf and cr > 0:
        return "cr"
    return "lf"


def read_text(path: str, encoding: str = "", max_bytes: int = MAX_READ_BYTES) -> Loaded:
    """Load a file, detecting BOM, encoding and line endings."""
    result = Loaded(path=str(path))
    try:
        st = os.stat(path)
    except FileNotFoundError:
        result.error = "File not found"
        return result
    except OSError as exc:
        result.error = str(exc)
        return result

    result.path = str(path)
    result.size = st.st_size
    result.mtime = st.st_mtime
    result.huge = st.st_size > HUGE_BYTES
    result.large = st.st_size > LARGE_BYTES
    if result.huge:
        result.readonly = True

    if st.st_size > max_bytes:
        result.error = f"File is too large to edit ({st.st_size / 1048576:.1f} MiB)"
        return result

    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        result.error = str(exc)
        return result

    if b"\x00" in raw[:8192]:
        # A real binary (or UTF-16 without a BOM): show it, but never overwrite.
        text, codec, bom = _decode(raw)
        if codec.startswith("utf-16"):
            result.binary = False
        else:
            result.binary = True
            result.readonly = True
            text = raw.decode("utf-8", "replace")
        result.text = text
        result.encoding = codec
        result.bom = bom
    else:
        if encoding:
            try:
                text = raw.decode(encoding, "replace")
                codec, bom = encoding, False
            except (LookupError, UnicodeDecodeError):
                text, codec, bom = _decode(raw)
        else:
            text, codec, bom = _decode(raw)
        result.text = text
        result.encoding = codec
        result.bom = bom

    result.eol = _detect_eol(raw)
    result.text = result.text.replace("\r\n", "\n").replace("\r", "\n")

    try:
        result.readonly = result.readonly or not os.access(path, os.W_OK)
    except OSError:
        result.readonly = True
    result.ok = True
    return result


def _encode(text: str, encoding: str, eol: str, bom: bool) -> tuple[bytes, str]:
    if eol == "crlf":
        text = text.replace("\n", "\r\n")
    elif eol == "cr":
        text = text.replace("\n", "\r")
    codec = encoding if encoding in dict(ENCODINGS) else "utf-8"
    try:
        data = text.encode(codec, "strict")
    except (UnicodeEncodeError, LookupError):
        # Never lose characters silently: fall back to UTF-8 (with a BOM when
        # the document insisted on one). The codec that was actually used is
        # returned so the document stops claiming the old one.
        codec = "utf-8"
        data = text.encode("utf-8", "replace")
        bom = bom or encoding == "utf-8"
    if bom and codec in BOMS:
        data = BOMS[codec] + data
    return data, codec


def write_text(
    path: str,
    text: str,
    encoding: str = "utf-8",
    eol: str = "lf",
    bom: bool = False,
    expected_mtime: float = 0.0,
) -> dict:
    """Atomically write ``text``; returns a small result dict for QML."""
    path = str(path)
    # Editing a symlinked dotfile must rewrite its target, not replace the link
    # with a regular file (which silently detaches it from the dotfiles tree).
    target = os.path.realpath(path) if os.path.islink(path) else path
    parent = os.path.dirname(os.path.abspath(target)) or "."
    if not os.path.isdir(parent):
        return {"ok": False, "error": "Folder does not exist"}

    try:
        if expected_mtime and os.path.exists(target):
            current = os.stat(target).st_mtime
            if abs(current - float(expected_mtime)) > 1e-6:
                return {"ok": False, "error": "File changed on disk", "stale": True}
    except OSError:
        pass

    data, codec = _encode(text, encoding, eol, bom)
    try:
        mode = stat.S_IMODE(os.stat(target).st_mode)
    except OSError:
        mode = 0o644

    fd = None
    tmp = ""
    try:
        fd, tmp = tempfile.mkstemp(dir=parent, prefix=f".{os.path.basename(target)}.", suffix=".tmp")
        with os.fdopen(fd, "wb") as fh:
            fd = None
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
        st = os.stat(target)
        return {
            "ok": True,
            "path": path,
            "encoding": codec,
            "size": st.st_size,
            "mtime": st.st_mtime,
            "eol": eol,
            "bom": bom,
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def file_mtime(path: str) -> float:
    try:
        return os.stat(path).st_mtime
    except OSError:
        return 0.0


def human_bytes(n: float) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(value) < 1024:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GiB"
