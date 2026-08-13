"""Layer-shell menu window for hyprtk-menu."""

import json
import os
import re
import subprocess
import pwd

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell, Pango

from . import apps, config as cfg, theme
from .theme import apply_css, build_css

# Win7-style places entries (label, icon_name, command_or_path)
WIN7_PLACES = [
    ("Documents", "folder-documents", None),
    ("Pictures", "folder-pictures", None),
    ("Music", "folder-music", None),
    ("Games", "applications-games", None),
    ("Computer", "computer", ""),
    ("Control Panel", "preferences-system", None),
    ("Devices and Printers", "drive-multidisk", None),
    ("Default Programs", "applications-system", None),
    ("Help and Support", "help-browser", None),
]

POWER_ICONS = {
    "lock": "system-lock-screen",
    "logout": "system-log-out",
    "reboot": "system-reboot",
    "shutdown": "system-shutdown",
    "suspend": "system-suspend",
    "hibernate": "system-suspend-hibernate",
}

POWER_PNG = {
    "lock": "lock.png",
    "logout": "logout.png",
    "reboot": "reboot.png",
    "shutdown": "shutdown.png",
    "suspend": "suspend.png",
    "hibernate": "hibernate.png",
}

POWER_ICON_SIZE = 16

ALIGN_ICONS = {
    "left": "\uf036",
    "center": "\uf037",
    "right": "\uf038",
}
ALIGN_ORDER = ["left", "center", "right"]

LAYOUT_ICONS = theme.LAYOUT_ICONS
LAYOUT_ORDER = theme.LAYOUT_ORDER


class MenuWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.config = cfg.load_config()
        self.apps = apps.scan_apps()
        self.pinned = set(self.config.get("favorites", []))
        self.recents = list(self.config.get("recents", []))
        self.current_category = "All"

        self.set_title("hyprtk-menu")
        width = int(self.config.get("width", 920))
        height = int(self.config.get("height", 580))
        self.set_size_request(600, 400)
        self.set_default_size(width, height)
        self.set_resizable(True)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_accept_focus(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

        screen = Gdk.Screen.get_default()
        if screen.get_rgba_visual():
            self.set_visual(screen.get_rgba_visual())
        self.set_app_paintable(True)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        GtkLayerShell.set_namespace(self, "hyprtk-menu")
        # Pure overlay — no exclusive zone, so windows are never pushed.
        GtkLayerShell.set_exclusive_zone(self, 0)
        self._apply_position()

        apply_css(build_css())
        self.get_style_context().add_class("menu-root")
        self._apply_layout_class()

        self._wal_mtime = theme.wal_mtime()
        self._themestyle_prev = theme.themestyle_mtime()
        GLib.timeout_add_seconds(2, self._check_wal)

        self._build_ui()

        self.connect("key-press-event", self._on_window_key)
        self.connect("destroy", Gtk.main_quit)

    # -- layer shell ------------------------------------------------------

    def _detect_waybar_edge(self):
        """Return 'top' or 'bottom' based on the active waybar theme."""
        theme_name = ""
        theme_file = os.path.expanduser("~/.cache/.themestyle.sh")
        try:
            with open(theme_file, encoding="utf-8") as f:
                theme_name = f.read().split(";")[0].strip().strip("/")
        except OSError:
            pass
        if theme_name.endswith("-bottom"):
            return "bottom"
        if theme_name.endswith("-top"):
            return "top"
        if theme_name:
            config_path = os.path.expanduser(
                "~/hyprtk/configs/waybar/themes/%s/config" % theme_name
            )
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = json.loads(re.sub(r"//.*", "", f.read()))
                position = data.get("position", "top")
                return "bottom" if position == "bottom" else "top"
            except (OSError, ValueError):
                pass
        return None

    def _apply_position(self):
        position = self.config.get("position", "auto")
        edge = "top"
        horizontal = "left"
        if position == "auto":
            edge = self._detect_waybar_edge() or "top"
            align = self.config.get("align", "left")
            horizontal = align if align in ("left", "center", "right") else "left"
        elif position == "center":
            edge = "center"
        else:
            parts = position.split("-")
            edge = parts[0] if parts[0] in ("top", "bottom") else "top"
            horizontal = parts[1] if len(parts) > 1 else "left"

        top = GtkLayerShell.Edge.TOP
        bottom = GtkLayerShell.Edge.BOTTOM
        left = GtkLayerShell.Edge.LEFT
        right = GtkLayerShell.Edge.RIGHT

        if edge == "center":
            # No anchors on any edge → the surface is centered on the output.
            for anchor in (top, bottom, left, right):
                GtkLayerShell.set_anchor(self, anchor, False)
            return

        GtkLayerShell.set_anchor(self, top, edge == "top")
        GtkLayerShell.set_anchor(self, bottom, edge == "bottom")
        # Horizontal: anchor only the chosen side; unanchored → centered.
        GtkLayerShell.set_anchor(self, left, horizontal == "left")
        GtkLayerShell.set_anchor(self, right, horizontal == "right")

        margin = 5
        GtkLayerShell.set_margin(self, top, margin if edge == "top" else 0)
        GtkLayerShell.set_margin(self, bottom, margin if edge == "bottom" else 0)
        GtkLayerShell.set_margin(self, left, 5 if horizontal == "left" else 0)
        GtkLayerShell.set_margin(self, right, 5 if horizontal == "right" else 0)

    # -- UI construction --------------------------------------------------

    def _build_ui(self):
        self._layout_initialized = False
        self._resizing = False
        layout = self.config.get("layout", "whisker")
        if layout not in LAYOUT_ORDER:
            layout = "whisker"
        builder = getattr(self, "_build_%s" % layout, None)
        if builder is None:
            layout = "whisker"
            builder = self._build_whisker
        root = builder()
        self._root = root
        self.add(root)

    def _rebuild_ui(self):
        """Tear down and rebuild the widget tree for a new layout."""
        child = self.get_child()
        if child is not None:
            self.remove(child)
        self._build_ui()
        self._refresh_favorites()
        self._refresh_apps()
        self._refresh_recents()
        self.show_all()
        self.present()
        GLib.idle_add(self.search.grab_focus)

    def _apply_saved_layout(self):
        """Restore saved window size and pane positions (first show only)."""
        self.set_size_request(
            int(self.config.get("width", 920)), int(self.config.get("height", 580))
        )
        if hasattr(self, "pane_main"):
            GLib.idle_add(self._apply_pane_positions)
        return False

    def _apply_pane_positions(self):
        window_w = self.get_allocated_width() or int(self.config.get("width", 920))
        sidebar_w = int(self.config.get("sidebar_width", 180))
        recents_w = int(self.config.get("recents_width", 230))
        self.pane_main.set_position(sidebar_w)
        if hasattr(self, "pane_right"):
            self.pane_right.set_position(max(window_w - sidebar_w - recents_w, 120))

    def _save_layout(self):
        window_w = self.get_allocated_width()
        window_h = self.get_allocated_height()
        if window_w and window_h:
            self.config["width"] = window_w
            self.config["height"] = window_h
        if hasattr(self, "pane_main"):
            sidebar_w = self.pane_main.get_position()
            if sidebar_w > 0:
                self.config["sidebar_width"] = sidebar_w
        if hasattr(self, "pane_right"):
            right_pos = self.pane_right.get_position()
            if right_pos > 0 and window_w:
                self.config["recents_width"] = max(window_w - sidebar_w - right_pos, 120)
        cfg.save_config(self.config)

    def _on_paned_changed(self, _paned):
        self._save_layout()

    # -- shared widgets ---------------------------------------------------

    def _make_search(self):
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search applications...")
        self.search.get_style_context().add_class("search")
        self.search.connect("search-changed", self._on_search_changed)
        self.search.connect("key-press-event", self._on_search_key)
        return self.search

    def _build_sidebar(self, store=True):
        scroll = Gtk.ScrolledWindow()
        scroll.get_style_context().add_class("sidebar-scroll")
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        sidebar = Gtk.ListBox()
        sidebar.get_style_context().add_class("sidebar")
        sidebar.set_selection_mode(Gtk.SelectionMode.NONE)
        sidebar.set_activate_on_single_click(True)
        for category in apps.CATEGORY_ORDER:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("cat-row")
            label = Gtk.Label(label=category, xalign=0)
            label.get_style_context().add_class("cat-label")
            row.add(label)
            row.category = category
            if category == "All":
                row.get_style_context().add_class("selected")
            sidebar.add(row)
        sidebar.connect("row-activated", self._on_category_activated)
        scroll.add(sidebar)
        if store:
            self.sidebar = sidebar
        return scroll

    def _make_app_list(self):
        scroll = Gtk.ScrolledWindow()
        scroll.get_style_context().add_class("app-list-scroll")
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.app_list = Gtk.ListBox()
        self.app_list.get_style_context().add_class("app-list")
        self.app_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.app_list.set_activate_on_single_click(True)
        self.app_list.connect("row-activated", self._on_app_activated)
        self.app_list.connect("button-press-event", self._on_app_button)
        scroll.add(self.app_list)
        return scroll

    def _make_favorites(self, klass="favorites"):
        self.fav_row = Gtk.FlowBox()
        self.fav_row.get_style_context().add_class(klass)
        self.fav_row.set_selection_mode(Gtk.SelectionMode.NONE)
        self.fav_row.set_max_children_per_line(100)
        return self.fav_row

    def _make_center(self, with_favorites=True):
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.get_style_context().add_class("center-pane")
        if with_favorites:
            center.pack_start(self._make_favorites(), False, False, 0)
        center.pack_start(self._make_app_list(), True, True, 0)
        return center

    def _build_recents(self, title="Recently Used", klass="recents-pane"):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.get_style_context().add_class(klass)
        box.set_size_request(int(self.config.get("recents_width", 230)), -1)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label=title, xalign=0)
        label.get_style_context().add_class("pane-title")
        header.pack_start(label, True, True, 0)

        clear_btn = Gtk.Button(label="Clear")
        clear_btn.get_style_context().add_class("clear-btn")
        clear_btn.set_tooltip_text("Clear recently used apps")
        clear_btn.connect("clicked", self._on_clear_recents)
        header.pack_end(clear_btn, False, False, 0)

        box.pack_start(header, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.recents_list = Gtk.ListBox()
        self.recents_list.get_style_context().add_class("recents-list")
        self.recents_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.recents_list.set_activate_on_single_click(True)
        self.recents_list.connect("row-activated", self._on_app_activated)
        scroll.add(self.recents_list)
        box.pack_start(scroll, True, True, 0)
        return box

    # -- layout builders --------------------------------------------------

    def _build_whisker(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("menu")
        root.pack_start(self._make_search(), False, False, 0)

        self.pane_right = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.pane_right.get_style_context().add_class("pane")
        self.pane_right.pack1(self._make_center(), True, True)
        if self.config.get("show_recents", True):
            self.pane_right.pack2(self._build_recents(), False, False)

        self.pane_main = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.pane_main.get_style_context().add_class("pane")
        self.pane_main.pack1(self._build_sidebar(), False, False)
        self.pane_main.pack2(self.pane_right, True, True)

        self.pane_main.connect("accept-position", self._on_paned_changed)
        self.pane_right.connect("accept-position", self._on_paned_changed)

        root.pack_start(self.pane_main, True, True, 0)
        root.pack_end(self._build_powerbar(), False, False, 0)
        return root

    def _build_win7(self):
        """Windows 7 Start Menu — user+apps left, places+search right."""
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("menu")

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.get_style_context().add_class("pane")

        # ── Left pane: user profile + favorites + app list ──
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.get_style_context().add_class("win7-left")

        # User profile bar
        profile = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        profile.get_style_context().add_class("win7-profile")
        avatar = Gtk.Image.new_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
        avatar.get_style_context().add_class("win7-avatar")
        profile.pack_start(avatar, False, False, 0)
        username = Gtk.Label(label=pwd.getpwuid(os.getuid()).pw_name, xalign=0)
        username.get_style_context().add_class("win7-username")
        profile.pack_start(username, False, False, 0)
        left.pack_start(profile, False, False, 0)

        # Favorites
        left.pack_start(self._make_favorites(), False, False, 0)

        # App list (fills remaining space)
        left.pack_start(self._make_app_list(), True, True, 0)

        # All Programs row at bottom of left pane
        allprog = Gtk.ListBoxRow()
        allprog.get_style_context().add_class("win7-allprograms")
        allprog_label = Gtk.Label(label="All Programs  ▸", xalign=0)
        allprog_label.get_style_context().add_class("win7-allprograms-label")
        allprog.add(allprog_label)
        allprog.connect("activated", self._on_win7_allprograms)
        left.pack_end(allprog, False, False, 0)

        paned.pack1(left, True, True)

        # ── Right pane: places + search ──
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.get_style_context().add_class("win7-right")

        places_scroll = Gtk.ScrolledWindow()
        places_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        places_scroll.set_vexpand(True)
        places = Gtk.ListBox()
        places.get_style_context().add_class("win7-places")
        places.set_selection_mode(Gtk.SelectionMode.NONE)
        places.set_activate_on_single_click(True)
        for label_text, icon_name, cmd in WIN7_PLACES:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("win7-place-row")
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            icon.get_style_context().add_class("win7-place-icon")
            hbox.pack_start(icon, False, False, 0)
            lbl = Gtk.Label(label=label_text, xalign=0)
            lbl.get_style_context().add_class("win7-place-label")
            hbox.pack_start(lbl, True, True, 0)
            row.add(hbox)
            row.place_cmd = cmd
            row.place_label = label_text
            places.add(row)
        places.connect("row-activated", self._on_place_activated)
        places_scroll.add(places)
        right.pack_start(places_scroll, True, True, 0)

        # Search bar at bottom-right
        self._make_search()
        self.search.get_style_context().add_class("win7-search")
        right.pack_end(self.search, False, False, 0)

        paned.pack2(right, False, False)
        self.pane_main = paned
        self.pane_main.connect("accept-position", self._on_paned_changed)
        root.pack_start(self.pane_main, True, True, 0)

        # Bottom bar: shutdown button
        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bottom.get_style_context().add_class("win7-bottom")
        power = self._build_powerbar()
        power.get_style_context().add_class("win7-powerbar")
        bottom.pack_end(power, False, False, 0)
        root.pack_end(bottom, False, False, 0)
        return root

    def _on_place_activated(self, _listbox, row):
        """Open a Win7-style place."""
        cmd = getattr(row, "place_cmd", None)
        label = getattr(row, "place_label", "")
        if cmd is not None:
            # Explicit command
            try:
                subprocess.Popen(cmd, shell=True, start_new_session=True)
            except Exception:
                pass
        elif label:
            # Open in file manager
            path = os.path.expanduser("~/%s" % label)
            if os.path.isdir(path):
                try:
                    subprocess.Popen(["thunar", path], start_new_session=True)
                except Exception:
                    pass
        self.hide_menu()

    def _on_win7_allprograms(self, _row):
        """Switch Win7 to show all apps with category filter."""
        self.current_category = "All"
        if hasattr(self, "sidebar"):
            for child in self.sidebar.get_children():
                if getattr(child, "category", None) == "All":
                    child.get_style_context().add_class("selected")
                else:
                    child.get_style_context().remove_class("selected")
        self._refresh_apps()

    def _build_win11(self):
        """Windows 11 Start Menu — centered search, pinned grid, recommended, user footer."""
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("menu")
        root.set_size_request(
            int(self.config.get("width", 920)), int(self.config.get("height", 580))
        )

        # Search bar (pill-shaped, centered feel)
        self._make_search()
        self.search.get_style_context().add_class("win11-search")
        root.pack_start(self.search, False, False, 0)

        # Pinned section: header + "All apps >" + grid
        pinned_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        pinned_header.get_style_context().add_class("win11-section-header")
        ptitle = Gtk.Label(label="Pinned", xalign=0)
        ptitle.get_style_context().add_class("pane-title")
        pinned_header.pack_start(ptitle, True, True, 0)
        allapps_btn = Gtk.Button(label="All apps  ▸")
        allapps_btn.get_style_context().add_class("win11-allapps-btn")
        allapps_btn.connect("clicked", self._on_win11_allapps)
        pinned_header.pack_end(allapps_btn, False, False, 0)
        root.pack_start(pinned_header, False, False, 0)

        # Pinned grid (6 columns, icon + label tiles)
        pinned_grid = Gtk.Grid()
        pinned_grid.get_style_context().add_class("win11-pinned")
        pinned_grid.set_column_spacing(4)
        pinned_grid.set_row_spacing(4)
        pinned_grid.set_column_homogeneous(True)
        self._win11_pinned_grid = pinned_grid
        root.pack_start(pinned_grid, False, False, 0)

        # Recommended section: header + "More >" + recents
        recents_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        recents_header.get_style_context().add_class("win11-section-header")
        rtitle = Gtk.Label(label="Recommended", xalign=0)
        rtitle.get_style_context().add_class("pane-title")
        recents_header.pack_start(rtitle, True, True, 0)
        more_btn = Gtk.Button(label="More  ▸")
        more_btn.get_style_context().add_class("win11-more-btn")
        recents_header.pack_end(more_btn, False, False, 0)
        root.pack_start(recents_header, False, False, 0)

        recents = self._build_recents(title="", klass="recents-pane win11-recommended")
        recents.set_size_request(-1, int(self.config.get("height", 580)) // 3)
        root.pack_start(recents, False, False, 0)

        # Footer: user avatar (left) + power button (right)
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.get_style_context().add_class("win11-footer")
        avatar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        avatar_box.get_style_context().add_class("win11-user")
        avatar = Gtk.Image.new_from_icon_name("avatar-default", Gtk.IconSize.MENU)
        avatar.get_style_context().add_class("win11-avatar")
        avatar_box.pack_start(avatar, False, False, 0)
        username = Gtk.Label(label=pwd.getpwuid(os.getuid()).pw_name, xalign=0)
        username.get_style_context().add_class("win11-username")
        avatar_box.pack_start(username, False, False, 0)
        footer.pack_start(avatar_box, False, False, 0)
        footer.pack_end(self._build_powerbar(), False, False, 0)
        root.pack_end(footer, False, False, 0)

        return root

    def _refresh_win11_pinned(self):
        """Populate the Win11 pinned grid with favorite app tiles."""
        if not hasattr(self, "_win11_pinned_grid"):
            return
        grid = self._win11_pinned_grid
        for child in grid.get_children():
            grid.remove(child)
        cols = 6
        col = 0
        row = 0
        for entry in self.apps:
            if entry.id not in self.pinned:
                continue
            tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            tile.get_style_context().add_class("win11-tile")
            image = self._make_icon_image(entry, 32)
            image.get_style_context().add_class("win11-tile-icon")
            tile.pack_start(image, False, False, 0)
            label = Gtk.Label(
                label=entry.name,
                ellipsize=Pango.EllipsizeMode.END,
                max_width_chars=8,
            )
            label.get_style_context().add_class("win11-tile-label")
            tile.pack_start(label, False, False, 0)
            btn = Gtk.Button()
            btn.get_style_context().add_class("win11-tile-btn")
            btn.add(tile)
            btn.set_tooltip_text(entry.name)
            btn.connect("clicked", self._on_fav_clicked, entry)
            grid.attach(btn, col, row, 1, 1)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        grid.show_all()

    def _on_win11_allapps(self, _button):
        """Show all apps list (scrollable) in Win11."""
        self.current_category = "All"
        self._refresh_apps()

    def _refresh_recents(self):
        if not hasattr(self, "recents_list"):
            return
        for child in self.recents_list.get_children():
            self.recents_list.remove(child)
        by_id = {entry.id: entry for entry in self.apps}
        for item in self.recents:
            entry = by_id.get(item)
            if entry:
                self.recents_list.add(self._make_row(entry, 26))
        self.recents_list.show_all()

    def _build_plasma(self):
        """KDE Plasma-style menu — icon tabs, favorites grid, places, power footer."""
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("menu")

        # Search bar
        self._make_search()
        root.pack_start(self.search, False, False, 0)

        # Tab row with icons
        tabs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tabs.get_style_context().add_class("plasma-tabs")
        self._plasma_stack = Gtk.Stack()
        self._plasma_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self._plasma_buttons = {}
        tab_defs = [
            ("Favorites", "emblem-favorite"),
            ("Applications", "view-grid"),
            ("Computer", "drive-harddisk"),
            ("Recently Used", "document-open-recent"),
        ]
        for name, icon_name in tab_defs:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            icon.get_style_context().add_class("plasma-tab-icon")
            box.pack_start(icon, False, False, 0)
            label = Gtk.Label(label=name)
            box.pack_start(label, False, False, 0)
            button = Gtk.ToggleButton()
            button.get_style_context().add_class("plasma-tab")
            button.add(box)
            button.connect("clicked", self._on_plasma_tab, name)
            tabs.pack_start(button, True, True, 0)
            self._plasma_buttons[name] = button
        root.pack_start(tabs, False, False, 0)

        # ── Favorites page: large icon grid ──
        fav_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        fav_page.get_style_context().add_class("plasma-page")
        fav_grid = Gtk.Grid()
        fav_grid.get_style_context().add_class("plasma-fav-grid")
        fav_grid.set_column_spacing(8)
        fav_grid.set_row_spacing(8)
        fav_grid.set_column_homogeneous(True)
        self._plasma_fav_grid = fav_grid
        fav_page.pack_start(fav_grid, True, True, 0)
        self._plasma_stack.add_named(fav_page, "Favorites")

        # ── Applications page: category sidebar + app list ──
        app_page = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        app_page.pack1(self._build_sidebar(), False, False)
        app_page.pack2(self._make_center(with_favorites=False), True, True)
        self._plasma_stack.add_named(app_page, "Applications")

        # ── Computer page: places list ──
        comp_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        comp_page.get_style_context().add_class("plasma-page")
        comp_scroll = Gtk.ScrolledWindow()
        comp_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        comp_list = Gtk.ListBox()
        comp_list.get_style_context().add_class("plasma-places")
        comp_list.set_selection_mode(Gtk.SelectionMode.NONE)
        comp_list.set_activate_on_single_click(True)
        places_entries = [
            ("Home", "user-home", os.path.expanduser("~")),
            ("Desktop", "user-desktop", os.path.expanduser("~/Desktop")),
            ("Documents", "folder-documents", os.path.expanduser("~/Documents")),
            ("Downloads", "folder-download", os.path.expanduser("~/Downloads")),
            ("Music", "folder-music", os.path.expanduser("~/Music")),
            ("Pictures", "folder-pictures", os.path.expanduser("~/Pictures")),
            ("Videos", "folder-videos", os.path.expanduser("~/Videos")),
            ("Trash", "user-trash", ""),
            ("Network", "network-workgroup", ""),
        ]
        for lbl, icon_name, path in places_entries:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("plasma-place-row")
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            hbox.pack_start(icon, False, False, 0)
            label = Gtk.Label(label=lbl, xalign=0)
            hbox.pack_start(label, True, True, 0)
            row.add(hbox)
            row.place_path = path
            places_list_rows = comp_list
            row.connect("button-release-event", self._on_plasma_place, path)
            comp_list.add(row)
        comp_scroll.add(comp_list)
        comp_page.pack_start(comp_scroll, True, True, 0)
        self._plasma_stack.add_named(comp_page, "Computer")

        # ── Recently Used page ──
        rec_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        rec_page.get_style_context().add_class("plasma-page")
        rec_scroll = Gtk.ScrolledWindow()
        rec_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.recents_list = Gtk.ListBox()
        self.recents_list.get_style_context().add_class("recents-list")
        self.recents_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.recents_list.set_activate_on_single_click(True)
        self.recents_list.connect("row-activated", self._on_app_activated)
        rec_scroll.add(self.recents_list)
        rec_page.pack_start(rec_scroll, True, True, 0)
        self._plasma_stack.add_named(rec_page, "Recently Used")

        root.pack_start(self._plasma_stack, True, True, 0)

        # Footer: power buttons + align/layout controls
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        footer.get_style_context().add_class("plasma-footer")
        footer.pack_start(self._build_powerbar(), True, True, 0)
        root.pack_end(footer, False, False, 0)

        self._plasma_stack.set_visible_child_name("Favorites")
        self._plasma_buttons["Favorites"].set_active(True)
        return root

    def _on_plasma_place(self, row, event, path):
        """Open a Plasma Computer place."""
        if path and os.path.isdir(path):
            try:
                subprocess.Popen(["thunar", path], start_new_session=True)
            except Exception:
                pass
        self.hide_menu()

    def _refresh_plasma_favorites(self):
        """Populate the Plasma favorites grid with large icon tiles."""
        if not hasattr(self, "_plasma_fav_grid"):
            return
        grid = self._plasma_fav_grid
        for child in grid.get_children():
            grid.remove(child)
        cols = 4
        col = 0
        row = 0
        for entry in self.apps:
            if entry.id not in self.pinned:
                continue
            tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            tile.get_style_context().add_class("plasma-fav-tile")
            image = self._make_icon_image(entry, 48)
            image.get_style_context().add_class("plasma-fav-icon")
            tile.pack_start(image, False, False, 0)
            label = Gtk.Label(
                label=entry.name,
                ellipsize=Pango.EllipsizeMode.END,
                max_width_chars=10,
            )
            label.get_style_context().add_class("plasma-fav-label")
            tile.pack_start(label, False, False, 0)
            btn = Gtk.Button()
            btn.get_style_context().add_class("plasma-fav-btn")
            btn.add(tile)
            btn.set_tooltip_text(entry.name)
            btn.connect("clicked", self._on_fav_clicked, entry)
            grid.attach(btn, col, row, 1, 1)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        grid.show_all()

    def _on_plasma_tab(self, button, name):
        self._plasma_stack.set_visible_child_name(name)
        for key, btn in self._plasma_buttons.items():
            btn.set_active(key == name)

    def _build_powerbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.get_style_context().add_class("powerbar")

        left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left.get_style_context().add_class("power-left")

        title = Gtk.Label(label="hyprtk-menu", xalign=0)
        title.get_style_context().add_class("power-title")
        left.pack_start(title, False, False, 0)

        self.align_button = Gtk.Button()
        self.align_button.get_style_context().add_class("align-btn")
        self.align_button.connect("clicked", self._on_align_clicked)
        self._update_align_button()
        left.pack_start(self.align_button, False, False, 0)

        self.layout_button = Gtk.Button()
        self.layout_button.get_style_context().add_class("layout-btn")
        self.layout_button.connect("clicked", self._on_layout_clicked)
        self._update_layout_button()
        left.pack_start(self.layout_button, False, False, 0)

        bar.pack_start(left, True, True, 0)

        power = self.config.get("power", {})
        for action in ("lock", "logout", "reboot", "shutdown", "suspend", "hibernate"):
            command = power.get(action)
            if not command:
                continue
            button = Gtk.Button()
            button.get_style_context().add_class("power-btn")
            button.set_tooltip_text(action.capitalize())
            image = self._make_power_icon(action)
            button.add(image)
            button.connect("clicked", self._on_power, action)
            bar.pack_end(button, False, False, 0)

        # Corner resize grip
        grip = Gtk.EventBox()
        grip.get_style_context().add_class("resize-grip")
        grip.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        grip.set_tooltip_text("Drag to resize")
        grip_icon = Gtk.Label(label="\u2b0c")
        grip_icon.get_style_context().add_class("resize-grip-icon")
        grip.add(grip_icon)
        grip.connect("button-press-event", self._on_grip_press)
        grip.connect("button-release-event", self._on_grip_release)
        grip.connect("motion-notify-event", self._on_grip_motion)
        bar.pack_end(grip, False, False, 0)
        self.grip = grip
        return bar

    def _on_grip_press(self, _widget, event):
        if event.button == 1:
            self._resizing = True
            self._resize_start_w = self.get_allocated_width()
            self._resize_start_h = self.get_allocated_height()
            self._resize_start_x = event.x_root
            self._resize_start_y = event.y_root
            seat = Gdk.Display.get_default().get_default_seat()
            if seat:
                seat.grab(
                    self.grip.get_window(),
                    Gdk.SeatCapabilities.POINTER,
                    False,
                    None,
                    None,
                    None,
                    None,
                )
            return True
        return False

    def _on_grip_motion(self, _widget, event):
        if not self._resizing:
            return False
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        new_w = max(int(self._resize_start_w + dx), 600)
        new_h = max(int(self._resize_start_h + dy), 400)
        self.set_size_request(new_w, new_h)
        return True

    def _on_grip_release(self, _widget, event):
        if self._resizing:
            self._resizing = False
            seat = Gdk.Display.get_default().get_default_seat()
            if seat:
                seat.ungrab()
            self._save_layout()
            return True
        return False

    def _on_clear_recents(self, _button):
        self.recents = []
        self.config["recents"] = []
        cfg.save_config(self.config)
        self._refresh_recents()
        self._refresh_apps()

    def _update_align_button(self):
        align = self.config.get("align", "left")
        if align not in ALIGN_ICONS:
            align = "left"
        icon = ALIGN_ICONS[align]
        label = Gtk.Label(label=icon)
        label.get_style_context().add_class("align-icon")
        child = self.align_button.get_child()
        if child:
            self.align_button.remove(child)
        self.align_button.add(label)
        self.align_button.set_tooltip_text(
            "Menu alignment: %s (click to cycle)" % align
        )
        self.align_button.show_all()

    def _on_align_clicked(self, _button):
        align = self.config.get("align", "left")
        try:
            index = ALIGN_ORDER.index(align)
        except ValueError:
            index = 0
        next_align = ALIGN_ORDER[(index + 1) % len(ALIGN_ORDER)]
        self.config["align"] = next_align
        cfg.save_config(self.config)
        self._update_align_button()
        self.reposition()

    def _apply_layout_class(self):
        layout = self.config.get("layout", "whisker")
        if layout not in LAYOUT_ORDER:
            layout = "whisker"
        for name in LAYOUT_ORDER:
            self.get_style_context().remove_class("layout-%s" % name)
        self.get_style_context().add_class("layout-%s" % layout)

    def _update_layout_button(self):
        layout = self.config.get("layout", "whisker")
        if layout not in LAYOUT_ICONS:
            layout = "whisker"
        icon = LAYOUT_ICONS[layout]
        label = Gtk.Label(label=icon)
        label.get_style_context().add_class("layout-icon")
        child = self.layout_button.get_child()
        if child:
            self.layout_button.remove(child)
        self.layout_button.add(label)
        self.layout_button.set_tooltip_text("Menu layout: %s (click to cycle)" % layout)
        self.layout_button.show_all()

    def _on_layout_clicked(self, _button):
        layout = self.config.get("layout", "whisker")
        try:
            index = LAYOUT_ORDER.index(layout)
        except ValueError:
            index = 0
        next_layout = LAYOUT_ORDER[(index + 1) % len(LAYOUT_ORDER)]
        self.config["layout"] = next_layout
        cfg.save_config(self.config)
        self._apply_layout_class()
        self._update_layout_button()
        self._apply_layout_tweaks()
        try:
            apply_css(build_css())
        except Exception as exc:
            print("hyprtk-menu: layout css update failed: %s" % exc, flush=True)
        was_visible = self.get_visible()
        if was_visible:
            GLib.idle_add(self._rebuild_ui)
        else:
            self._rebuild_ui()

    def _apply_layout_tweaks(self):
        """CSS-impossible per-layout tweaks. Called on open and layout change."""
        layout = self.config.get("layout", "whisker")
        if layout == "win11":
            self.search.set_placeholder_text("Search for apps, settings, and documents...")
        else:
            self.search.set_placeholder_text("Search applications...")

    # -- helpers ----------------------------------------------------------

    def _make_power_icon(self, action, pixel_size=POWER_ICON_SIZE):
        """Custom PNG power icon (scaled to match system size), else system icon."""
        png = POWER_PNG.get(action)
        if png:
            path = os.path.join(theme.BASE_DIR, "assets", png)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                width = max(pixel_size, 1)
                height = max(int(pixbuf.get_height() * (width / max(pixbuf.get_width(), 1))), 1)
                scaled = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
                image = Gtk.Image.new_from_pixbuf(scaled)
                image.get_style_context().add_class("power-icon")
                return image
            except (GLib.Error, OSError):
                pass
        return Gtk.Image.new_from_icon_name(
            POWER_ICONS.get(action, "system-run"), Gtk.IconSize.MENU
        )

    def _make_icon_image(self, entry, pixel_size):
        icon = entry.icon
        if icon is None:
            return Gtk.Image.new_from_icon_name(
                "application-x-executable", Gtk.IconSize.DND
            )
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DND)
        image.set_pixel_size(pixel_size)
        return image

    def _make_row(self, entry, icon_size=32):
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("app-row")
        row.entry = entry

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        image = self._make_icon_image(entry, icon_size)
        image.get_style_context().add_class("app-icon")
        hbox.pack_start(image, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name = Gtk.Label(
            label=entry.name,
            xalign=0,
            ellipsize=Pango.EllipsizeMode.END,
        )
        name.get_style_context().add_class("app-name")
        vbox.pack_start(name, False, False, 0)
        if entry.comment:
            desc = Gtk.Label(
                label=entry.comment,
                xalign=0,
                ellipsize=Pango.EllipsizeMode.END,
            )
            desc.get_style_context().add_class("app-desc")
            vbox.pack_start(desc, False, False, 0)
        hbox.pack_start(vbox, True, True, 0)
        row.add(hbox)
        return row

    def _visible_apps(self):
        query = self.search.get_text().strip()
        if query:
            return [entry for entry in self.apps if entry.matches(query)]

        category = self.current_category
        if category == "Favorites":
            return [entry for entry in self.apps if entry.id in self.pinned]
        if category == "Recently Used":
            by_id = {entry.id: entry for entry in self.apps}
            return [by_id[item] for item in self.recents if item in by_id]

        if category == "All":
            return list(self.apps)
        return [entry for entry in self.apps if category in entry.categories]

    # -- refresh ----------------------------------------------------------

    def _refresh_favorites(self):
        if not hasattr(self, "fav_row"):
            return
        for child in self.fav_row.get_children():
            self.fav_row.remove(child)
        for entry in self.apps:
            if entry.id not in self.pinned:
                continue
            button = Gtk.Button()
            button.get_style_context().add_class("fav-btn")
            image = self._make_icon_image(entry, 26)
            button.add(image)
            button.set_tooltip_text(entry.name)
            button.connect("clicked", self._on_fav_clicked, entry)
            self.fav_row.add(button)
        self.fav_row.set_visible(bool(self.pinned))
        self.fav_row.show_all()
        # Win11 pinned grid + Plasma fav grid
        if hasattr(self, "_win11_pinned_grid"):
            self._refresh_win11_pinned()
        if hasattr(self, "_plasma_fav_grid"):
            self._refresh_plasma_favorites()

    def _refresh_apps(self):
        if not hasattr(self, "app_list"):
            return
        for child in self.app_list.get_children():
            self.app_list.remove(child)
        for entry in self._visible_apps():
            self.app_list.add(self._make_row(entry))
        self.app_list.show_all()
        if self.app_list.get_children():
            self.app_list.select_row(self.app_list.get_row_at_index(0))

    # -- actions ----------------------------------------------------------

    def _launch(self, entry):
        if apps.launch_app(entry):
            self.recents = [entry.id] + [
                item for item in self.recents if item != entry.id
            ]
            self.recents = self.recents[: int(self.config.get("max_recents", 10))]
            self.config["recents"] = self.recents
            cfg.save_config(self.config)
        self.hide_menu()

    def _toggle_pin(self, entry):
        if entry.id in self.pinned:
            self.pinned.discard(entry.id)
        else:
            self.pinned.add(entry.id)
        self.config["favorites"] = sorted(self.pinned)
        cfg.save_config(self.config)
        self._refresh_favorites()
        self._refresh_apps()

    # -- signals ----------------------------------------------------------

    def _on_search_changed(self, _widget):
        self._refresh_apps()

    def _on_search_key(self, _widget, event):
        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
            rows = self.app_list.get_children()
            if not rows:
                return True
            selected = self.app_list.get_selected_row()
            index = rows.index(selected) if selected in rows else 0
            if event.keyval == Gdk.KEY_Down:
                index = (index + 1) % len(rows)
            else:
                index = (index - 1) % len(rows)
            self.app_list.select_row(rows[index])
            self.app_list.scroll_to_row(rows[index])
            return True
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            row = self.app_list.get_selected_row()
            if row:
                entry = getattr(row, "entry", None)
                if entry:
                    self._launch(entry)
            return True
        return False

    def _on_window_key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_menu()
            return True
        if event.keyval == Gdk.KEY_F and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.search.grab_focus()
            self.search.select_region(0, -1)
            return True
        return False

    def _on_category_activated(self, _sidebar, row):
        category = getattr(row, "category", None)
        if not category:
            return
        self.current_category = category
        if hasattr(self, "sidebar"):
            for child in self.sidebar.get_children():
                if child is row:
                    child.get_style_context().add_class("selected")
                else:
                    child.get_style_context().remove_class("selected")
        self._refresh_apps()

    def _on_app_activated(self, _listbox, row):
        entry = getattr(row, "entry", None)
        if entry:
            self._launch(entry)

    def _on_app_button(self, _widget, event):
        if event.button == 3:  # right-click: pin/unpin
            row = self.app_list.get_row_at_y(int(event.y))
            if row:
                entry = getattr(row, "entry", None)
                if entry:
                    self._toggle_pin(entry)
            return True
        return False

    def _on_fav_clicked(self, _button, entry):
        self._launch(entry)

    def _on_power(self, _button, action):
        command = self.config.get("power", {}).get(action)
        if command:
            try:
                subprocess.Popen(command, shell=True, start_new_session=True)
            except Exception:
                pass
        self.hide_menu()

    # -- show / hide ------------------------------------------------------

    def _check_wal(self):
        """Live-update pywal colors and waybar-theme profile while open."""
        changed = False
        wal_mtime = theme.wal_mtime()
        if wal_mtime and wal_mtime != self._wal_mtime:
            self._wal_mtime = wal_mtime
            changed = True
        theme_mtime = theme.themestyle_mtime()
        if theme_mtime != self._themestyle_prev:
            self._themestyle_prev = theme_mtime
            changed = True
        if not changed:
            return True

        was_visible = self.get_visible()
        if was_visible:
            # Hide first so re-anchoring happens on an unmapped surface.
            self.hide()
        try:
            apply_css(build_css())
        except Exception as exc:
            print("hyprtk-menu: theme css update failed: %s" % exc, flush=True)
        else:
            print("hyprtk-menu: theme updated", flush=True)
        # The waybar edge (top/bottom) may have changed too — re-anchor.
        self._apply_position()
        if was_visible:
            GLib.idle_add(self._remap_after_update)
        return True

    def _remap_after_update(self):
        self.hide()
        self.show_all()
        self.present()
        GLib.idle_add(self.search.grab_focus)
        return False

    def show_menu(self):
        self._apply_position()
        self._apply_layout_tweaks()
        self._refresh_favorites()
        self._refresh_apps()
        self._refresh_recents()
        self.show_all()
        self.present()
        if not self._layout_initialized:
            self._layout_initialized = True
            GLib.idle_add(self._apply_saved_layout)
        GLib.idle_add(self.search.grab_focus)

    def hide_menu(self):
        self.hide()
        self.search.set_text("")
        self.current_category = "All"
        if hasattr(self, "sidebar"):
            for child in self.sidebar.get_children():
                if getattr(child, "category", None) == "All":
                    child.get_style_context().add_class("selected")
                else:
                    child.get_style_context().remove_class("selected")

    def toggle(self):
        if self.get_visible():
            self.hide_menu()
        else:
            self.show_menu()

    def reposition(self):
        """Re-apply anchoring after the user changes alignment."""
        self.config = cfg.load_config()
        was_visible = self.get_visible()
        self._apply_position()
        if was_visible:
            GLib.idle_add(self._remap_after_update)
