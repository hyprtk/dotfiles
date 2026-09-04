# hyprtk-menu

A Whisker-style application menu for Hyprland, written in Python (GTK3 +
gtk-layer-shell). Opens as a floating overlay popup styled with your pywal
glass aesthetic — searchable launcher with category sidebar, pinned favorites,
recents, and power buttons.

## Features

- Instant live app search (name, generic name, comment, keywords)
- Category sidebar (All, Favorites, Recently Used, Accessories, Development,
  Education, Games, Graphics, Internet, Multimedia, Office, Science, Settings,
  System)
- Pin/unpin favorites (right-click an app)
- Recently used tracking (max 10, configurable)
- Power buttons (lock, logout, reboot, shutdown, suspend — commands configurable)
- pywal-driven frosted glass theme (`~/.cache/wal/colors.sh`)
- **Live color updates** — polls the pywal cache every 2s; when a wallpaper
  change regenerates colors while the menu is open, the theme re-applies in
  place without closing or restarting
- **Follows the active bar theme** — reads `~/.cache/.themestyle.sh` and
  applies a matching profile (hyprtk dark frosted, hyprtk-aero glass,
  hyprtk-light, hyprtk-clear, hyprtk-glass, hyprtk-inverse, hyprtk-reverse,
  hyprtk-negative). Switching the bar theme while the menu is open re-themes
  it live and re-anchors it if the bar moved, resized, or re-aligned. Pywal
  colors drive all accents.
- Single instance; toggle from anywhere via `hyprtk-menu --toggle` (SIGUSR1)

## Install

```bash
./install.sh
# uninstall
./install.sh --uninstall
```

Installs to `~/.local/share/hyprtk-menu/` and `~/.local/bin/hyprtk-menu`.

## Usage

```bash
hyprtk-menu              # open (or toggle if already running)
hyprtk-menu --toggle     # toggle visibility
```

### Hyprland

```ini
# keybind
bind = SUPER, SPACE, exec, hyprtk-menu --toggle

# backdrop blur (in decoration or monitor section)
layerrule = blur, hyprtk-menu
```

### hyprtk-bar button

The bar's start button opens the menu (`start_command: "hyprtk-menu"` in
`~/.config/hyprtk-bar/config.json`). To launch it from anywhere, bind a key:

```ini
bind = SUPER, SPACE, exec, hyprtk-menu --toggle
```

## Configuration

`~/.config/hyprtk-menu/config.json` (auto-created, optional):

```json
{
  "position": "auto",
  "align": "left",
  "layout": "whisker",
  "width": 920,
  "height": 580,
  "sidebar_width": 180,
  "recents_width": 230,
  "show_recents": true,
  "max_recents": 10,
  "favorites": [],
  "recents": [],
  "power": {
    "lock": "pidof hyprlock || hyprlock",
    "logout": "hyprshutdown",
    "reboot": "systemctl reboot",
    "shutdown": "systemctl poweroff",
    "suspend": "systemctl suspend"
  }
}
```

Positions:
- `position: "auto"` (default) — follows **hyprtk-bar**: reads
  `~/.config/hyprtk-bar/config.json` and anchors the menu on the bar's edge
  (bar `position: "top"` → menu appears below the top bar; `"bottom"` → menu
  appears above the bottom bar). The menu's `align` is applied relative to
  the bar's horizontal extent (computed from the bar's `width` + `align`), so
  a partial-width bar places the menu at the bar's left edge, center, or right
  edge — not the screen edges — and the menu sits just clear of the bar's
  `height`. Re-detected every time the menu opens, and live while open if the
  bar config changes.
- `align: "left" | "center" | "right"` — horizontal placement used with
  `position: "auto"`. Change it from the alignment icon in the menu's power
  bar (next to the "hyprtk-menu" label); an open menu repositions live.
- Explicit overrides: `top-left` / `top-center` / `top-right` /
  `bottom-left` / `bottom-center` / `bottom-right` — these ignore `align`.
- `center` — centered on screen.

The menu is a pure overlay (no exclusive zone), so it never pushes windows —
it floats above them like a popup, just clear of hyprtk-bar.

## Layouts

`layout` selects the menu style — `whisker` (default), `win7`, `win11`, or
`plasma`. All layouts share the same Whisker structure (search, category
sidebar, app list, favorites, recents, power bar); each is a visual theme
(layout-*.css) scoped under a root class. Click the layout button in the power
bar (next to the alignment button) to cycle through them — the change applies
live and is saved to config.

## Resizing

- Drag the corner grip (bottom-right of the power bar) to resize the window
  freely; size is persisted to `width` / `height` on release.
- Drag the thin dividers between the columns to widen the categories list,
  the app list, or the recents panel; positions persist to `sidebar_width` /
  `recents_width`.
- The recents panel has a **Clear** button next to its title to wipe the
  recently-used list.

## Requirements

- python3, python-gobject (PyGObject)
- gtk3, gtk-layer-shell (Python bindings)

## Structure

```
hyprtk_menu/
├── app.py        # entry, single-instance lockfile, SIGUSR1 toggle
├── menu.py       # layer-shell window, layout, navigation, power
├── apps.py       # .desktop scan, category map, search, launch
├── config.py     # config persistence
└── theme.py      # CSS assembly (pywal + base)
assets/style.css  # base GTK CSS
```

## Notes

- Requires gtk-layer-shell (Hyprland implements the protocol natively)
- The menu is transparent; enable `layerrule = blur, hyprtk-menu` in
  Hyprland for real backdrop blur
