"""Post-write semantic verification against the effective model."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .lua_probe import probe


class VerifyError(RuntimeError):
    pass


def _equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    return a == b


def _dig(model: dict, path: str) -> Any:
    node: Any = model["config"]
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


_MISSING = object()


def expect_config(root: Path, path: str, expected: Any) -> Callable[[], None]:
    def check() -> None:
        model = probe(root)
        got = _dig(model, path)
        if got is _MISSING:
            raise VerifyError(f"{path} missing after write")
        if not _equal(got, expected):
            raise VerifyError(f"{path}: wrote {expected!r} but effective value is {got!r}")

    return check


def expect_animation(root: Path, leaf: str, key: str, expected: Any) -> Callable[[], None]:
    def check() -> None:
        model = probe(root)
        spec = model["animations"].get(leaf)
        if spec is None:
            raise VerifyError(f"animation {leaf} missing after write")
        if key not in spec:
            raise VerifyError(f"animation {leaf}.{key} missing after write")
        if not _equal(spec[key], expected):
            raise VerifyError(
                f"animation {leaf}.{key}: wrote {expected!r} but effective value is {spec[key]!r}"
            )

    return check


def expect_require(root: Path, module: str) -> Callable[[], None]:
    def check() -> None:
        model = probe(root)
        if module not in model["requires"]:
            raise VerifyError(f"require({module!r}) is not active after write")

    return check


def verify_specs(root: Path, specs: list[dict]) -> None:
    """Check expectations, probing once per target file (or the whole tree)."""
    groups: dict[str | None, list[dict]] = {}
    for spec in specs:
        groups.setdefault(spec.get("main"), []).append(spec)
    for main, items in groups.items():
        model = probe(root, main=main) if main else probe(root)
        for spec in items:
            _check(model, spec)


def _check(model: dict, spec: dict) -> None:
    kind = spec.get("type")
    if kind == "config":
        got = _dig(model, spec["path"])
        if got is _MISSING:
            raise VerifyError(f"{spec['path']} missing after write")
        if not _equal(got, spec["value"]):
            raise VerifyError(
                f"{spec['path']}: wrote {spec['value']!r} but effective value is {got!r}"
            )
    elif kind == "animation":
        leaf = spec["leaf"]
        anim = model["animations"].get(leaf)
        if anim is None:
            raise VerifyError(f"animation {leaf} missing after write")
        got = anim.get(spec["key"], _MISSING)
        if got is _MISSING or not _equal(got, spec["value"]):
            raise VerifyError(
                f"animation {leaf}.{spec['key']}: wrote {spec['value']!r} but got {got!r}"
            )
    elif kind == "curve":
        name = spec["name"]
        wanted = spec.get("spec") or spec
        curve = model["curves"].get(name)
        if curve is None:
            raise VerifyError(f"curve {name} missing after write")
        ctype = wanted.get("type", "bezier")
        if curve.get("type", "bezier") != ctype:
            raise VerifyError(f"curve {name}: wrong type after write")
        if ctype == "bezier" and curve.get("points") != wanted.get("points"):
            raise VerifyError(f"curve {name}: points did not round-trip")
    elif kind == "env":
        got = (model.get("env") or {}).get(spec["key"], _MISSING)
        if got is _MISSING or not _equal(got, spec["value"]):
            raise VerifyError(
                f"env {spec['key']}: wrote {spec['value']!r} but got {got!r}"
            )
    elif kind == "require":
        if spec["module"] not in model["requires"]:
            raise VerifyError(f"require({spec['module']!r}) is not active after write")
    elif kind == "require_state":
        active = spec["module"] in model["requires"]
        if active != bool(spec.get("active")):
            raise VerifyError(
                f"require({spec['module']!r}) should be {'active' if spec.get('active') else 'inactive'}"
            )
    elif kind == "exec":
        if not any(c.get("command") == spec["command"] for c in model.get("exec") or []):
            raise VerifyError(f"exec command {spec['command']!r} missing after write")
    elif kind == "bind":
        if not any(b.get("keys") == spec["keys"] for b in model.get("binds") or []):
            raise VerifyError(f"binding {spec['keys']!r} missing after write")
    elif kind == "probe":
        pass
    else:
        raise VerifyError(f"unknown verify spec: {kind!r}")


def chain(*checks: Callable[[], None]) -> Callable[[], None]:
    def run() -> None:
        for check in checks:
            check()

    return run
