"""Local-model helpers: describe a file with the suite's local LLM roles.

The commands come from the suite's ``local-llm`` helper (``llm-vision``,
``llm-chat``). Nothing leaves the machine, and a missing model is reported
rather than silently doing nothing. The description is stored as the file's
note in the tag store, so it is searchable from the Tags dialog and stays with
the file in this file manager's own metadata.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import tags

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
TEXT_LIMIT = 6000
OUTPUT_LIMIT = 600


def available() -> dict:
    return {"vision": shutil.which("llm-vision") or "",
            "chat": shutil.which("llm-chat") or ""}


def _run(argv: list[str], timeout: float = 180) -> str:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"{argv[0]} failed: {exc}") from exc
    text = (result.stdout or "").strip()
    if result.returncode != 0 and not text:
        raise RuntimeError((result.stderr or "the local model failed").strip()[:300])
    return text.splitlines()[0][:OUTPUT_LIMIT] if text else ""


def describe(path: str) -> dict:
    target = Path(path).expanduser()
    if not target.is_file():
        raise RuntimeError(f"{target} is not a file")
    roles = available()
    suffix = target.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        if not roles["vision"]:
            raise RuntimeError("llm-vision is not installed (see the local-llm skill)")
        text = _run([roles["vision"], "Describe this image in one sentence.", str(target)])
        role = "vision"
    else:
        if not roles["chat"]:
            raise RuntimeError("llm-chat is not installed (see the local-llm skill)")
        try:
            body = target.read_text(encoding="utf-8", errors="replace")[:TEXT_LIMIT]
        except OSError as exc:
            raise RuntimeError(str(exc)) from exc
        text = _run([roles["chat"],
                     f"Summarise this file in one sentence:\n\n{body}"])
        role = "chat"
    if not text:
        raise RuntimeError("the model returned nothing")
    existing = tags.for_paths([str(target)]).get(str(target)) or {}
    tags.set_paths([str(target)], existing.get("tags") or [],
                   existing.get("color") or "", note=text)
    return {"path": str(target), "role": role, "text": text}
