"""Graphics — GPU, driver modules and acceleration capabilities.

The acceleration section distinguishes three things that are easy to conflate:

* the **Vulkan ICD/driver** (e.g. ``radeon_icd.json`` / RADV),
* the **vulkaninfo** diagnostic tool (``vulkan-tools``), and
* whether a device is actually enumerated.

A missing ``vulkaninfo`` used to read as "Vulkan missing" even with a working
RADV stack, which is exactly the false alarm this panel now avoids.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .. import form, util
from . import base

ICD_DIRS = [Path("/usr/share/vulkan/icd.d"), Path("/etc/vulkan/icd.d")]
DRI_DIRS = [
    Path("/usr/lib/dri"),
    Path("/usr/lib/x86_64-linux-gnu/dri"),
    Path("/usr/lib64/dri"),
]


def vulkan_icds() -> list[dict]:
    found: list[dict] = []
    for root in ICD_DIRS:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            api = ""
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                api = str((data.get("ICD") or {}).get("api_version") or "")
            except (OSError, ValueError):
                pass
            found.append({"name": path.name, "api": api})
    return found


def parse_vulkan_summary(text: str) -> list[dict]:
    """Parse the device blocks of ``vulkaninfo --summary``."""
    devices: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^GPU\d+:$", stripped):
            current = {}
            devices.append(current)
            continue
        if current is None or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip().lower()
        if key in ("devicename", "drivername", "driverid", "apiversion", "devicetype"):
            current[key] = value.strip()
    return [device for device in devices if device.get("devicename")]


def _dri_drivers() -> list[str]:
    found: set[str] = set()
    for root in DRI_DIRS:
        if not root.is_dir():
            continue
        for path in root.glob("*_drv_video.so"):
            found.add(path.name)
    return sorted(found)


def _vulkan_state() -> tuple[list[dict], list[dict], str]:
    icds = vulkan_icds()
    if util.which("vulkaninfo") is None:
        return icds, [], ""
    result = util.run(["vulkaninfo", "--summary"], timeout=25)
    if not result.ok:
        return icds, [], (result.err or result.out).strip()[:240]
    return icds, parse_vulkan_summary(result.out), ""


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
    icds, devices, vk_error = _vulkan_state()
    dri = _dri_drivers()

    accel: list[dict] = []
    if devices:
        for device in devices:
            accel.append(form.info(
                "Vulkan device",
                f"{device.get('devicename')} · "
                f"{device.get('drivername') or device.get('driverid') or 'unknown driver'} · "
                f"API {device.get('apiversion') or '?'}",
            ))
    elif icds:
        accel.append(form.info("Vulkan", "driver installed; vulkaninfo not available", tone="ok"))
        accel.append(form.note(
            "Install vulkan-tools to run vulkaninfo. A missing diagnostic tool does "
            "not mean the Vulkan driver is missing.", "info"))
    else:
        accel.append(form.info("Vulkan", "no ICD installed", tone="warn"))

    icd_labels = [icd["name"] + (f" ({icd['api']})" if icd["api"] else "") for icd in icds]
    accel.append(form.info("Vulkan ICDs", ", ".join(icd_labels) or "none"))
    accel.append(form.info("VA-API drivers", ", ".join(dri) or "none"))
    accel.append(form.info(
        "VA-API tool", "vainfo available" if util.which("vainfo") else "vainfo not installed"))
    accel.append(form.info(
        "OpenGL tool", "glxinfo available" if util.which("glxinfo") else "glxinfo not installed"))
    if vk_error:
        accel.append(form.note(f"vulkaninfo failed: {vk_error}", "warn"))

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
            form.note("Power limits and fan curves are managed outside this app "
                      "(gpu-powercap, gpu-fand).", "info"),
        ]),
    ])
