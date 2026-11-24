"""Graphics — GPU, driver modules and acceleration capabilities."""

from __future__ import annotations

from pathlib import Path

from .. import form, util
from . import base


def _drm_cards() -> list[str]:
    cards: list[str] = []
    root = Path("/sys/class/drm")
    if not root.is_dir():
        return cards
    for entry in sorted(root.glob("card[0-9]*")):
        if "-" in entry.name:
            continue
        device = entry / "device"
        vendor = util.read_text(device / "vendor").strip()
        driver = ""
        link = device / "driver"
        try:
            driver = link.resolve().name
        except OSError:
            pass
        cards.append(f"{entry.name}: vendor {vendor or '?'} · driver {driver or '?'}")
    return cards


def probe() -> dict:
    gpu = util.gpu_from_lspci() or "not detected"
    drivers = sorted({
        line.split(":", 1)[0]
        for line in util.run(["lsmod"], timeout=8).lines()
        if line.split(":", 1)[0] in ("amdgpu", "nvidia", "nvidia_drm", "i915", "xe", "radeon")
    })
    vulkan = util.which("vulkaninfo") is not None
    vaapi = util.which("vainfo") is not None
    glx = util.which("glxinfo") is not None

    accel = []
    for label, present, how in [
        ("Vulkan", vulkan, "vulkaninfo"),
        ("VA-API", vaapi, "vainfo"),
        ("OpenGL", glx, "glxinfo"),
    ]:
        accel.append(form.info(label, "tool available" if present else f"{how} not installed"))

    return base.make_page("graphics", [
        form.section("Adapter", [
            form.info("GPU", gpu),
            form.info("Kernel drivers", ", ".join(drivers) or "none loaded", mono=True),
        ]),
        form.section("DRM devices", [
            form.kv([{"label": card, "value": ""} for card in _drm_cards()]) or
            form.note("No /sys/class/drm devices found.", "warn"),
        ]),
        form.section("Acceleration", accel),
        form.section("Notes", [
            form.note("This machine's GPU is driven through amdgpu/ROCm. Power limits and "
                      "fan curves are managed outside this app (gpu-powercap, gpu-fand).", "info"),
        ]),
    ])
