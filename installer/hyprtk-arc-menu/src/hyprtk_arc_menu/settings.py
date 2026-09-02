"""Settings dialog for editing the hyprtk-arc-menu configuration."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")

from gi.repository import Gdk, Gtk, GtkLayerShell

from .arc_menu import load_icon_image
from .config import CORNERS, load, save


def _hex_to_rgba(hex_color: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    if not rgba.parse(hex_color or "#000000"):
        rgba.parse("#000000")
    return rgba


def _rgba_to_hex(rgba: Gdk.RGBA) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
    )


class ItemDialog(Gtk.Dialog):
    """Add/edit a single menu item (icon, command, tooltip)."""

    def __init__(self, parent, item: dict | None = None):
        super().__init__(title="Menu Item", transient_for=parent, modal=True)
        self.set_decorated(False)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_namespace(self, "hyprtk-arc-menu-item")
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Save", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        item = item or {"icon": "", "command": "", "tooltip": ""}
        box = self.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        def field(label: str, value: str) -> Gtk.Entry:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=label, xalign=0)
            lbl.set_size_request(90, -1)
            entry = Gtk.Entry()
            entry.set_text(value or "")
            row.pack_start(lbl, False, False, 0)
            row.pack_start(entry, True, True, 0)
            box.pack_start(row, False, False, 0)
            return entry

        self._icon_entry = field("Icon", item.get("icon", ""))
        self._tooltip_entry = field("Tooltip", item.get("tooltip", ""))
        self._command_entry = field("Command", item.get("command", ""))
        self._action_entry = field("Action", item.get("action", ""))

        hint = Gtk.Label(
            label="Icon: theme icon name (e.g. firefox).\n"
            "Action: 'settings' opens the arc menu settings instead of a command.",
            xalign=0,
            wrap=True,
        )
        hint.set_margin_top(4)
        box.pack_start(hint, False, False, 0)
        self.show_all()

    def get_item(self) -> dict:
        item = {
            "icon": self._icon_entry.get_text().strip(),
            "tooltip": self._tooltip_entry.get_text().strip(),
        }
        action = self._action_entry.get_text().strip()
        command = self._command_entry.get_text().strip()
        if action:
            item["action"] = action
        if command:
            item["command"] = command
        return item


class SettingsDialog(Gtk.Window):
    """Floating, centered layer-shell window to edit the arc menu config."""

    def __init__(self, cfg: dict, on_saved=None):
        super().__init__(title="Arc Menu Settings")
        self._on_saved = on_saved
        self._cfg = cfg
        self._items: list[dict] = [dict(i) for i in cfg.get("items", [])]

        self.set_decorated(False)
        self.set_default_size(560, 620)
        self.set_resizable(True)
        self._init_layer_shell()
        self.connect("key-press-event", self._on_key_press)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)
        self.add(vbox)

        # ── general section ───────────────────────────────────────
        general = Gtk.Frame(label="General")
        gbox = Gtk.Grid(row_spacing=8, column_spacing=12)
        gbox.set_margin_start(12)
        gbox.set_margin_end(12)
        gbox.set_margin_top(8)
        gbox.set_margin_bottom(8)
        general.add(gbox)

        def spinner(value: int, lo: int, hi: int, step: int) -> Gtk.SpinButton:
            adj = Gtk.Adjustment(value=value, lower=lo, upper=hi, step_increment=step)
            spin = Gtk.SpinButton(adjustment=adj)
            return spin

        self._corner_combo = Gtk.ComboBoxText()
        for corner in CORNERS:
            self._corner_combo.append_text(corner)
        self._corner_combo.set_active_id(cfg.get("corner", "bottom-right"))
        # ComboBoxText.set_active_id needs the ids to be the text; use index instead
        for i, corner in enumerate(CORNERS):
            if corner == cfg.get("corner", "bottom-right"):
                self._corner_combo.set_active(i)
                break

        self._radius_spin = spinner(cfg.get("radius", 140), 40, 600, 10)
        self._margin_spin = spinner(cfg.get("margin", 24), 0, 200, 2)
        self._fab_spin = spinner(cfg.get("fab_size", 56), 24, 120, 4)
        self._item_spin = spinner(cfg.get("item_size", 48), 24, 120, 4)
        self._anim_spin = spinner(cfg.get("animation_time", 300), 50, 2000, 25)

        self._pywal_switch = Gtk.Switch()
        self._pywal_switch.set_active(bool(cfg.get("use_pywal", True)))

        self._fab_color = Gtk.ColorButton()
        self._fab_color.set_rgba(_hex_to_rgba(cfg.get("fab_color", "#c084fc")))
        self._item_color = Gtk.ColorButton()
        self._item_color.set_rgba(_hex_to_rgba(cfg.get("item_color", "#22d3ee")))

        rows = [
            ("Corner", self._corner_combo),
            ("Radius (px)", self._radius_spin),
            ("Margin (px)", self._margin_spin),
            ("Menu button size (px)", self._fab_spin),
            ("Item size (px)", self._item_spin),
            ("Animation (ms)", self._anim_spin),
            ("Use pywal colors", self._pywal_switch),
            ("Menu button color", self._fab_color),
            ("Item color", self._item_color),
        ]
        for r, (label, widget) in enumerate(rows):
            gbox.attach(Gtk.Label(label=label, xalign=0), 0, r, 1, 1)
            gbox.attach(widget, 1, r, 1, 1)

        vbox.pack_start(general, False, False, 0)

        # ── items section ─────────────────────────────────────────
        items_frame = Gtk.Frame(label="Menu Items")
        ivbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        ivbox.set_margin_start(12)
        ivbox.set_margin_end(12)
        ivbox.set_margin_top(8)
        ivbox.set_margin_bottom(8)
        items_frame.add(ivbox)

        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._populate_items()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(220)
        scroll.add(self._list)
        ivbox.pack_start(scroll, True, True, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_btn = Gtk.Button(label="Add")
        edit_btn = Gtk.Button(label="Edit")
        remove_btn = Gtk.Button(label="Remove")
        add_btn.connect("clicked", self._on_add)
        edit_btn.connect("clicked", self._on_edit)
        remove_btn.connect("clicked", self._on_remove)
        btn_row.pack_start(add_btn, False, False, 0)
        btn_row.pack_start(edit_btn, False, False, 0)
        btn_row.pack_start(remove_btn, False, False, 0)
        ivbox.pack_start(btn_row, False, False, 0)

        vbox.pack_start(items_frame, True, True, 0)

        # ── bottom buttons ────────────────────────────────────────
        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        cancel = Gtk.Button(label="Cancel")
        save = Gtk.Button(label="Save")
        save.get_style_context().add_class("suggested-action")
        cancel.connect("clicked", lambda _b: self.destroy())
        save.connect("clicked", self._on_save)
        bottom.pack_end(save, False, False, 0)
        bottom.pack_end(cancel, False, False, 0)
        vbox.pack_start(bottom, False, False, 0)

        self.show_all()

    # ── layer shell (floating, centered) ──────────────────────────

    def _init_layer_shell(self) -> None:
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_namespace(self, "hyprtk-arc-menu-settings")
        # No anchors on either axis -> the surface is centered on screen.
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)

    def _on_key_press(self, _widget, event) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    # ── items list ───────────────────────────────────────────────

    def _populate_items(self) -> None:
        for child in self._list.get_children():
            self._list.remove(child)
        for item in self._items:
            row = self._make_item_row(item)
            self._list.add(row)
        self._list.show_all()

    def _make_item_row(self, item: dict) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)
        hbox.set_margin_start(6)
        hbox.set_margin_end(6)
        icon = load_icon_image(item.get("icon", "application-x-executable"), 24, "#000000")
        hbox.pack_start(icon, False, False, 0)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(
            label=item.get("tooltip") or item.get("command") or item.get("action", ""),
            xalign=0,
        )
        sub = Gtk.Label(
            label=(item.get("command") or item.get("action", "no command")),
            xalign=0,
            width_chars=50,
            ellipsize=True,
        )
        sub.get_style_context().add_class("dim-label")
        labels.pack_start(title, False, False, 0)
        labels.pack_start(sub, False, False, 0)
        hbox.pack_start(labels, True, True, 0)
        row.add(hbox)
        return row

    def _selected_index(self) -> int | None:
        row = self._list.get_selected_row()
        if row is None:
            return None
        return row.get_index()

    def _on_add(self, _btn) -> None:
        dlg = ItemDialog(self)
        if dlg.run() == Gtk.ResponseType.OK:
            self._items.append(dlg.get_item())
            self._populate_items()
        dlg.destroy()

    def _on_edit(self, _btn) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        dlg = ItemDialog(self, self._items[idx])
        if dlg.run() == Gtk.ResponseType.OK:
            self._items[idx] = dlg.get_item()
            self._populate_items()
        dlg.destroy()

    def _on_remove(self, _btn) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        del self._items[idx]
        self._populate_items()

    # ── save ─────────────────────────────────────────────────────

    def _on_save(self, _btn) -> None:
        corner_list = list(CORNERS)
        self._cfg["corner"] = corner_list[self._corner_combo.get_active()]
        self._cfg["radius"] = self._radius_spin.get_value_as_int()
        self._cfg["margin"] = self._margin_spin.get_value_as_int()
        self._cfg["fab_size"] = self._fab_spin.get_value_as_int()
        self._cfg["item_size"] = self._item_spin.get_value_as_int()
        self._cfg["animation_time"] = self._anim_spin.get_value_as_int()
        self._cfg["use_pywal"] = self._pywal_switch.get_active()
        self._cfg["fab_color"] = _rgba_to_hex(self._fab_color.get_rgba())
        self._cfg["item_color"] = _rgba_to_hex(self._item_color.get_rgba())
        self._cfg["items"] = self._items
        save(self._cfg)
        if self._on_saved:
            self._on_saved()
        self.destroy()