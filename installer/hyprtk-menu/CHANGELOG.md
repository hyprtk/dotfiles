# Changelog

All notable changes to hyprtk-menu are documented in this file.
Dates are in YYYY-MM-DD format.

## [0.1.0] - 2026-09-03

Initial release. Whisker-style application menu for Hyprland (GTK3 +
gtk-layer-shell) with four layouts.

### Added

- Instant live app search across name, generic name, comment, and keywords
- Category sidebar (All, Favorites, Recently Used, Accessories, Development,
  Education, Games, Graphics, Internet, Multimedia, Office, Science, Settings,
  System)
- Pin/unpin favorites (right-click), recently-used tracking (max 10)
- Power bar with lock / logout / reboot / shutdown / suspend
- Four layouts: whisker (default), win7, win11, plasma — cycled from the power
  bar, applied live, saved to config
- Plasma Computer tab: two-pane in-menu file browser (persistent places sidebar
  + content pane, Back/Up/path nav), Trash manager (list, restore with
  `name.1.ext` dedup, Empty Trash)
- Settings cog: floating frameless draggable window — theme radio list,
  position "Auto (follow waybar)" + monitor corner/center grid; stays open on
  Apply
- pywal-driven frosted glass theme with live 2s polling of the pywal cache —
  re-themes in place while open
- Follows the active waybar theme (`~/.cache/.themestyle.sh`) — re-themes and
  re-anchors live when the bar moves top/bottom
- `position: auto` detects the waybar edge and anchors the menu on the same
  edge
- Resizable: corner grip + draggable column dividers, persisted to config
- Single instance with SIGUSR1 toggle (`hyprtk-menu --toggle`)
- `install.sh` (install / uninstall) to `~/.local/share/hyprtk-menu/` and
  `~/.local/bin/hyprtk-menu`, creates `~/Games`