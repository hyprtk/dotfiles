"""About — operating system, hardware, compositor and suite versions."""

from __future__ import annotations

import re

from .. import apps, form, paths, priv, util
from . import base


def _hyprland_version() -> str:
    result = util.run(["hyprctl", "version"], timeout=6)
    line = base.first_line(result)
    match = re.search(r"Hyprland\s+([0-9][^\s]*)", line)
    return match.group(1) if match else (line or "not running")


def _monitor_count() -> str:
    data = util.run_json(["hyprctl", "-j", "monitors"], timeout=6)
    if isinstance(data, list):
        return str(len(data))
    return "—"


def report() -> str:
    release = util.os_release()
    memory = util.meminfo()
    disk = util.disk_usage("/")
    lines = [
        "hyprtk system report",
        f"host        {util.hostname()}",
        f"os          {release.get('PRETTY_NAME', 'Linux')}",
        f"kernel      {util.kernel()}",
        f"session     {util.session_kind()} / {util.desktop() or 'unknown'}",
        f"uptime      {util.human_uptime(util.uptime_seconds())}",
        f"cpu         {util.cpu_model()} ({util.cpu_cores()} threads)",
        f"gpu         {util.gpu_from_lspci() or 'unknown'}",
        f"memory      {util.human_bytes(memory.get('MemTotal', 0))} "
        f"({util.human_bytes(memory.get('MemAvailable', 0))} available)",
        f"disk /      {util.human_bytes(disk['used'])} used of {util.human_bytes(disk['total'])}",
        f"hyprland    {_hyprland_version()}",
        f"monitors    {_monitor_count()}",
        "",
        "suite",
    ]
    for app in apps.all_apps():
        if app["installed"]:
            lines.append(f"  {app['title']:<18} {app['version'] or '(no version)':<10} {app['binary']}")
    return "\n".join(lines) + "\n"


def probe() -> dict:
    release = util.os_release()
    memory = util.meminfo()
    disk = util.disk_usage("/")
    gpu = util.gpu_from_lspci()
    installed = [app for app in apps.all_apps() if app["installed"]]

    hero = {
        "eyebrow": "This device",
        "title": util.hostname(),
        "subtitle": f"{release.get('PRETTY_NAME', 'Linux')} · {util.cpu_model()}",
        "chips": [
            {"label": f"kernel {util.kernel()}"},
            {"label": f"Hyprland {_hyprland_version()}"},
            {"label": util.session_kind()},
        ],
    }

    device = [
        form.info("Device name", util.hostname()),
        form.info("Operating system", release.get("PRETTY_NAME", "Linux")),
        form.info("Kernel", util.kernel(), mono=True),
        form.info("Session", f"{util.session_kind()} · {util.desktop() or 'unknown'}"),
        form.info("Uptime", util.human_uptime(util.uptime_seconds())),
    ]

    hardware = [
        form.info("Processor", util.cpu_model()),
        form.info("Threads", util.cpu_cores()),
        form.info("Graphics", gpu or "unknown"),
        form.info("Memory", f"{util.human_bytes(memory.get('MemTotal', 0))} "
                            f"({util.human_bytes(memory.get('MemAvailable', 0))} available)"),
        form.info("Disk /", f"{util.human_bytes(disk['used'])} used of {util.human_bytes(disk['total'])}"),
    ]

    compositor = [
        form.info("Hyprland", _hyprland_version(), mono=True),
        form.info("Monitors connected", _monitor_count()),
        form.info("Config", str(paths.hypr_dir() or "not found"), mono=True),
        form.info("Privilege", priv.mode(), mono=True),
    ]

    suite_rows = [
        form.info(app["title"], f"{app['version'] or '—'}   {app['binary']}", mono=True)
        for app in installed
    ] or [form.note("No suite applications detected.", "warn")]

    return base.make_page("about", [
        form.section("Device", device),
        form.section("Hardware", hardware),
        form.section("Compositor", compositor),
        form.section("Suite", suite_rows),
        form.section("Diagnostics", [
            form.action("Copy system report", "about.copy_report"),
            form.note("The report contains no secrets: versions, hardware names and paths only."),
        ]),
    ], hero=hero)


def action(name: str, args: dict) -> dict:
    if name == "about.copy_report":
        text = report()
        if util.which("wl-copy") is None:
            return base.fail("wl-copy is not installed", details=[text[:400]])
        result = util.run(["wl-copy"], input=text, timeout=10)
        if not result.ok:
            return base.fail(f"Could not copy: {result.err.strip() or result.code}")
        return base.ok("System report copied to the clipboard")
    return base.fail(f"unknown action {name!r}")
