"""Panel registry served to the sidebar and the search field.

One entry per settings page. ``module`` is imported lazily by the RPC layer, so
one broken panel can never stop the app from starting.
"""

from __future__ import annotations

import importlib
from typing import Any

GROUPS: list[dict[str, str]] = [
    {"id": "system", "title": "System"},
    {"id": "hardware", "title": "Hardware"},
    {"id": "network", "title": "Network"},
    {"id": "personal", "title": "Personalisation"},
    {"id": "desktop", "title": "Desktop"},
    {"id": "apps", "title": "Applications"},
    {"id": "security", "title": "Privacy & Security"},
    {"id": "accessibility", "title": "Accessibility"},
]

# id, title, group, icon (Nerd Font), status, module, keywords, description
PANELS: list[dict[str, Any]] = [
    # ── System ──────────────────────────────────────────────────────────
    {
        "id": "about", "title": "About", "group": "system", "icon": "\uf05a",
        "status": "read", "module": "about",
        "keywords": ["about", "system", "os", "version", "kernel", "cpu", "gpu",
                     "memory", "ram", "disk", "hyprland", "hostname", "hardware"],
        "description": "Operating system, hardware and suite versions.",
    },
    {
        "id": "datetime", "title": "Date & Time", "group": "system", "icon": "\uf017",
        "status": "full", "module": "datetime",
        "keywords": ["date", "time", "clock", "timezone", "time zone", "ntp",
                     "synchronise", "sync", "utc", "rtc", "calendar"],
        "description": "Clock, time zone and automatic synchronisation.",
    },
    {
        "id": "locale", "title": "Region & Language", "group": "system", "icon": "\uf0ac",
        "status": "partial", "module": "locale",
        "keywords": ["locale", "language", "region", "keymap", "keyboard layout",
                     "formats", "currency", "lc_"],
        "description": "Language, locale and regional formats.",
    },
    {
        "id": "users", "title": "Users & Groups", "group": "system", "icon": "\uf0c0",
        "status": "full", "module": "users",
        "keywords": ["users", "accounts", "groups", "password", "admin", "sudo",
                     "wheel", "shell", "login", "lock", "useradd", "usermod"],
        "description": "Accounts, passwords, groups and login shells.",
    },
    {
        "id": "services", "title": "Services", "group": "system", "icon": "\uf233",
        "status": "partial", "module": "services",
        "keywords": ["services", "systemd", "daemon", "unit", "enable", "disable",
                     "start", "stop", "boot", "socket"],
        "description": "Systemd units: start, stop, enable at boot.",
    },
    {
        "id": "updates", "title": "Updates", "group": "system", "icon": "\uf0ed",
        "status": "partial", "module": "updates",
        "keywords": ["updates", "upgrade", "packages", "pacman", "yay", "aur",
                     "mirror", "cache", "paccache"],
        "description": "Pending packages, last upgrade and cache.",
    },

    # ── Hardware ────────────────────────────────────────────────────────
    {
        "id": "displays", "title": "Displays", "group": "hardware", "icon": "\uf108",
        "status": "full", "module": "displays",
        "keywords": ["display", "monitor", "screen", "resolution", "refresh",
                     "scale", "scaling", "rotation", "transform", "position",
                     "output", "mode", "vrr", "hidpi", "mirror", "bit depth",
                     "10-bit", "hdr", "colour management", "color management"],
        "description": "Arrange, mirror, scale, rotate and colour your monitors.",
    },
    {
        "id": "graphics", "title": "Graphics", "group": "hardware", "icon": "\uf2db",
        "status": "read", "module": "graphics",
        "keywords": ["graphics", "gpu", "gpu", "driver", "mesa", "vulkan", "vaapi",
                     "drm", "render", "amdgpu", "nvidia", "intel", "opengl"],
        "description": "GPU, driver and acceleration capabilities.",
    },
    {
        "id": "sound", "title": "Sound", "group": "hardware", "icon": "\uf028",
        "status": "partial", "module": "sound",
        "keywords": ["sound", "audio", "volume", "mute", "sink", "output",
                     "input", "microphone", "pipewire", "wireplumber", "pulse",
                     "profile", "card", "codec", "hdmi", "stream", "per-app"],
        "description": "Output and input devices, volume, card profiles and streams.",
    },
    {
        "id": "input", "title": "Input Devices", "group": "hardware", "icon": "\uf11c",
        "status": "partial", "module": "input",
        "keywords": ["keyboard", "mouse", "touchpad", "input", "layout", "repeat",
                     "sensitivity", "acceleration", "natural scroll", "tap to click",
                     "keyboard backlight", "numlock"],
        "description": "Keyboard layout, repeat and pointer behaviour.",
    },
    {
        "id": "power", "title": "Power", "group": "hardware", "icon": "\uf0e7",
        "status": "read", "module": "power",
        "keywords": ["power", "battery", "ac", "charge", "suspend", "hibernate",
                     "idle", "hypridle", "profile", "thermal", "temperature"],
        "description": "Power source, battery and idle behaviour.",
    },
    {
        "id": "bluetooth", "title": "Bluetooth", "group": "hardware", "icon": "\uf294",
        "status": "partial", "module": "bluetooth",
        "keywords": ["bluetooth", "bt", "adapter", "pair", "device", "headset",
                     "mouse", "keyboard", "bluez"],
        "description": "Adapter state and paired devices.",
    },
    {
        "id": "printers", "title": "Printers", "group": "hardware", "icon": "\uf02f",
        "status": "partial", "module": "printers",
        "keywords": ["printer", "printing", "cups", "queue", "scanner", "paper",
                     "lpadmin", "driver", "test page", "default printer"],
        "description": "CUPS queues: add, remove, test and set the default.",
    },
    {
        "id": "storage", "title": "Storage", "group": "hardware", "icon": "\uf0a0",
        "status": "partial", "module": "storage",
        "keywords": ["storage", "disk", "drive", "partition", "mount", "unmount",
                     "block", "filesystem", "usb", "ssd", "hdd", "luks"],
        "description": "Block devices, usage and removable media.",
    },

    # ── Network ─────────────────────────────────────────────────────────
    {
        "id": "network", "title": "Network", "group": "network", "icon": "\uf1eb",
        "status": "partial", "module": "network",
        "keywords": ["network", "wifi", "wi-fi", "wireless", "ethernet", "vpn",
                     "connection", "nmcli", "networkmanager", "ip", "dns", "proxy",
                     "openvpn", "wireguard", "ovpn", "import", "forget"],
        "description": "Wi-Fi, saved networks, VPN profiles and radio state.",
    },

    # ── Personalisation ─────────────────────────────────────────────────
    {
        "id": "appearance", "title": "Appearance", "group": "personal", "icon": "\uf1fc",
        "status": "full", "module": "appearance",
        "keywords": ["appearance", "theme", "colour", "color", "palette", "pywal",
                     "wallpaper", "background", "accent", "opacity", "border",
                     "icons", "cursor", "gtk", "dark", "light"],
        "description": "Theme, wallpaper, colours and desktop accents.",
    },
    {
        "id": "fonts", "title": "Fonts", "group": "personal", "icon": "\uf031",
        "status": "full", "module": "fonts",
        "keywords": ["fonts", "font", "typeface", "family", "size", "monospace",
                     "interface", "text", "antialias", "hinting", "install"],
        "description": "Interface and monospace fonts, size and installation.",
    },
    {
        "id": "notifications", "title": "Notifications", "group": "personal", "icon": "\uf0f3",
        "status": "partial", "module": "notifications",
        "keywords": ["notifications", "alerts", "banner", "timeout", "history",
                     "do not disturb", "dnd", "popup"],
        "description": "Notification timeout, history and do-not-disturb.",
    },

    # ── Desktop ─────────────────────────────────────────────────────────
    {
        "id": "hyprland", "title": "Hyprland", "group": "desktop", "icon": "\uf1de",
        "status": "link", "module": "hyprland",
        "keywords": ["hyprland", "compositor", "gaps", "blur", "rounding", "shadow",
                     "animations", "decorations", "window rules", "monitor config"],
        "description": "Compositor settings, opened in the Hyprland settings app.",
    },
    {
        "id": "shortcuts", "title": "Keyboard Shortcuts", "group": "desktop", "icon": "\uf11c",
        "status": "read", "module": "shortcuts",
        "keywords": ["shortcuts", "keybindings", "binds", "hotkeys", "keys",
                     "keyboard shortcuts", "super"],
        "description": "Every key binding in the Hyprland configuration.",
    },
    {
        "id": "autostart", "title": "Autostart", "group": "desktop", "icon": "\uf135",
        "status": "full", "module": "autostart",
        "keywords": ["autostart", "startup", "login", "session", "desktop entry",
                     "xdg", "boot", "launch at login"],
        "description": "Programs started with your session.",
    },

    # ── Applications ────────────────────────────────────────────────────
    {
        "id": "defaults", "title": "Default Applications", "group": "apps", "icon": "\uf00a",
        "status": "partial", "module": "defaults",
        "keywords": ["default", "applications", "apps", "mime", "file types",
                     "associations", "browser", "mail", "terminal", "file manager"],
        "description": "Which application opens which kind of file.",
    },
    {
        "id": "suite", "title": "hyprtk Suite", "group": "apps", "icon": "\uf1b2",
        "status": "full", "module": "suite",
        "keywords": ["suite", "hyprtk", "bar", "bar-qt", "file manager", "terminal",
                     "editor", "calculator", "screenshot", "recorder", "settings",
                     "apps", "versions", "update"],
        "description": "Suite applications, versions and their own settings.",
    },

    # ── Security ────────────────────────────────────────────────────────
    {
        "id": "privacy", "title": "Privacy & Security", "group": "security", "icon": "\uf132",
        "status": "partial", "module": "privacy",
        "keywords": ["privacy", "security", "firewall", "lock", "screen lock",
                     "session", "permissions", "nftables", "ufw", "camera",
                     "microphone", "location"],
        "description": "Screen lock, firewall and session security.",
    },

    # ── Accessibility ───────────────────────────────────────────────────
    {
        "id": "accessibility", "title": "Accessibility", "group": "accessibility", "icon": "\uf29a",
        "status": "partial", "module": "accessibility",
        "keywords": ["accessibility", "a11y", "large text", "zoom", "contrast",
                     "sticky keys", "slow keys", "bounce keys", "mouse keys",
                     "screen reader", "orca", "on-screen keyboard", "osk",
                     "cursor size", "visual alerts", "text scaling", "reduced motion"],
        "description": "Text scaling, contrast, motion, keyboard aids, reader and OSK.",
    },
]

PANEL_INDEX = {panel["id"]: panel for panel in PANELS}
GROUP_INDEX = {group["id"]: group for group in GROUPS}


def catalog() -> dict[str, Any]:
    from .form import STATUS_LABELS

    return {
        "groups": [dict(group, panels=[p["id"] for p in PANELS if p["group"] == group["id"]])
                   for group in GROUPS],
        "panels": [
            {
                **{k: v for k, v in panel.items() if k != "module"},
                "statusLabel": STATUS_LABELS.get(panel["status"], panel["status"]),
            }
            for panel in PANELS
        ],
    }


def module_for(panel_id: str):
    meta = PANEL_INDEX.get(panel_id)
    if meta is None:
        raise KeyError(f"unknown panel {panel_id!r}")
    return importlib.import_module(f"{__package__}.panels.{meta['module']}")


def search(query: str, limit: int = 30) -> list[dict]:
    terms = [part for part in (query or "").lower().split() if part]
    if not terms:
        return []
    results: list[dict] = []
    for panel in PANELS:
        haystack = " ".join([
            panel["title"], panel["description"], panel["group"],
            " ".join(panel["keywords"]),
        ]).lower()
        score = 0
        for term in terms:
            if term in panel["title"].lower():
                score += 8
            elif term in panel["keywords"]:
                score += 5
            elif any(term in word for word in panel["keywords"]):
                score += 3
            elif term in haystack:
                score += 1
            else:
                score = -999
                break
        if score > 0:
            results.append({
                "id": panel["id"], "title": panel["title"],
                "group": panel["group"], "icon": panel["icon"],
                "description": panel["description"], "status": panel["status"],
                "score": score,
            })
    results.sort(key=lambda item: (-item["score"], item["title"]))
    return results[:limit]
