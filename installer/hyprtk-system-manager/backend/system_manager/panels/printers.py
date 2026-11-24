"""Printers — CUPS queues, defaults and simple queue management.

Adding or removing a queue needs root (``lpadmin`` is not in the user's groups
here). Privileged changes go through ``priv.run_priv`` so the app never keeps a
root daemon: sudo when passwordless, otherwise a pkexec prompt.
"""

from __future__ import annotations

from .. import form, priv, util
from . import base

TEST_PAGE = "/usr/share/cups/data/default-testpage.pdf"
CUPS_URL = "http://localhost:631"


def parse_lpstat(text: str) -> dict:
    queues: list[dict] = []
    default = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("printer "):
            parts = line.split()
            queues.append({"name": parts[1], "state": " ".join(parts[2:])})
        elif line.startswith("system default destination:"):
            default = line.split(":", 1)[1].strip()
    return {"queues": queues, "default": default}


def parse_lpinfo_v(text: str) -> list[dict]:
    """Parse ``lpinfo -v`` into ``{"uri", "label"}`` choices."""
    devices: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        kind, _, uri = line.partition(" ")
        uri = uri.strip()
        # ``lpinfo -v`` also prints bare backends ("network https"); those are
        # hints, not usable URIs, and lpadmin would reject them.
        if ":" not in uri:
            continue
        devices.append({"uri": uri, "label": f"{kind}: {uri}"})
    return devices


def parse_lpinfo_m(text: str) -> list[dict]:
    """Parse ``lpinfo -m`` into ``{"id", "label"}`` choices."""
    models: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        ident, _, label = line.partition(" ")
        models.append({"id": ident, "label": label.strip() or ident})
    return models


def probe() -> dict:
    if util.which("lpstat") is None:
        return base.make_page("printers", [
            form.section("Unavailable", [
                base.missing_note("lpstat", "CUPS"),
                form.note("Install cups and cups-pdf to manage printers here.", "info"),
            ]),
        ])

    parsed = parse_lpstat(util.run(["lpstat", "-p", "-d"], timeout=10).out)
    items = []
    for queue in parsed["queues"]:
        actions = []
        if queue["name"] != parsed["default"]:
            actions.append({
                "label": "Set default", "action": "printers.default",
                "args": {"name": queue["name"]},
            })
        actions.append({
            "label": "Test page", "action": "printers.test",
            "args": {"name": queue["name"]},
        })
        actions.append({
            "label": "Remove", "action": "printers.remove",
            "args": {"name": queue["name"]},
            "variant": "danger", "danger": True, "confirm": queue["name"],
        })
        items.append({
            "title": queue["name"],
            "subtitle": queue["state"],
            "badges": ["default"] if queue["name"] == parsed["default"] else [],
            "actions": actions,
        })

    devices = parse_lpinfo_v(util.run(["lpinfo", "-v"], timeout=20).out)
    models = parse_lpinfo_m(util.run(["lpinfo", "-m"], timeout=30).out)
    device_choices = [{"value": row["uri"], "label": row["label"]} for row in devices]
    model_choices = [{"value": "everywhere", "label": "Driverless (IPP Everywhere)"}]
    model_choices += [{"value": row["id"], "label": row["label"]} for row in models]

    add_rows: list[dict] = [
        form.text("new_name", "Queue name", "",
                  placeholder="Office", help="No spaces; used as the queue identifier."),
        form.choice("new_device", "Device", device_choices[0]["value"] if device_choices else "",
                    device_choices or [{"value": "", "label": "none found"}]),
        form.choice("new_model", "Driver", "everywhere", model_choices),
        form.text("new_uri", "…or a device URI", "",
                  placeholder="ipp://192.168.1.50/ipp/print",
                  help="Use this for a network printer when lpinfo lists no address."),
        form.text("new_location", "Location", "", placeholder="Living room"),
        form.text("new_description", "Description", "", placeholder="Colour laser"),
        form.note("Fill the fields and press Apply to create the queue. A driverless "
                  "(IPP Everywhere) queue needs a network printer that supports it.",
                  "info"),
    ]
    if not device_choices:
        add_rows.append(form.note("No local devices reported by lpinfo; enter the printer's "
                                  "ipp:// or socket:// address above.", "warn"))

    cups_active = util.run(["systemctl", "is-active", "cups"], timeout=6).out.strip() == "active"
    service_rows = [
        form.info("CUPS", "active" if cups_active else "not running"),
        form.info("Enabled at boot",
                  "yes" if util.run(["systemctl", "is-enabled", "cups"], timeout=6).ok
                  else "no"),
        form.info("Default printer", parsed["default"] or "none"),
        form.action("Open the CUPS web interface", "printers.open_cups"),
    ]
    if not cups_active:
        service_rows.append(form.note(
            "The cups service is not running; start it in Services or with "
            "`systemctl enable --now cups`.", "warn"))

    return base.make_page("printers", [
        form.section("Queues", [
            form.list_row(items) if items else form.note("No printers configured.", "info"),
        ]),
        form.section("Add a printer", add_rows),
        form.section("Service", service_rows),
    ], status="partial")


def _first_device() -> str:
    devices = parse_lpinfo_v(util.run(["lpinfo", "-v"], timeout=20).out)
    return devices[0]["uri"] if devices else ""


def _add(changes: dict) -> dict:
    name = str(changes.get("new_name") or "").strip()
    if not name:
        return base.fail("A queue name is required")
    if " " in name:
        return base.fail("The queue name cannot contain spaces")
    # A dropdown only submits a value when it is changed, so fall back to what the
    # row displays: the first device lpinfo reported.
    uri = (str(changes.get("new_uri") or "").strip()
           or str(changes.get("new_device") or "").strip()
           or _first_device())
    if not uri:
        return base.fail("Choose a device, or enter the printer's ipp:// address")
    model = str(changes.get("new_model") or "everywhere").strip() or "everywhere"
    argv = ["lpadmin", "-p", name, "-E", "-v", uri, "-m", model]
    description = str(changes.get("new_description") or "").strip()
    location = str(changes.get("new_location") or "").strip()
    if description:
        argv += ["-D", description]
    if location:
        argv += ["-L", location]
    result = priv.run_priv(argv)
    if not result.ok:
        text = (result.err or result.out).strip()
        return base.denied(text or "lpadmin failed", priv.command_for(argv))
    return base.ok(f"Added printer {name}", details=[priv.command_for(argv)],
                   note="The queue is created; send a test page to confirm it works.")


def apply(changes: dict) -> dict:
    if any(key.startswith("new_") for key in changes):
        return _add(changes)
    return base.ok("Nothing to change")


def action(name: str, args: dict) -> dict:
    queue = str(args.get("name") or "").strip()

    if name == "printers.remove":
        if not queue:
            return base.fail("No printer given")
        argv = ["lpadmin", "-x", queue]
        result = priv.run_priv(argv)
        if not result.ok:
            return base.denied((result.err or result.out).strip() or "lpadmin failed",
                               priv.command_for(argv))
        return base.ok(f"Removed printer {queue}", details=[priv.command_for(argv)])

    if name in ("printers.default", "printers.test"):
        if not queue:
            return base.fail("No printer given")
        if name == "printers.default":
            argv = ["lpadmin", "-d", queue]
            result = priv.run_priv(argv)
            if not result.ok:
                return base.denied((result.err or result.out).strip() or "lpadmin failed",
                                   priv.command_for(argv))
            return base.ok(f"{queue} is the default printer",
                           details=[priv.command_for(argv)])
        argv = ["lp", "-d", queue, TEST_PAGE]
        result = util.run(argv, timeout=30)
        if not result.ok:
            return base.fail((result.err or result.out).strip() or "lp failed")
        return base.ok(f"Sent a test page to {queue}", details=[" ".join(argv)])

    if name == "printers.open_cups":
        if not util.spawn(["xdg-open", CUPS_URL]):
            return base.fail("Could not open a browser")
        return base.ok("Opened the CUPS web interface", details=[CUPS_URL])

    return base.fail(f"unknown action {name!r}")
