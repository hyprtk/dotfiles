# Changelog

All notable changes to hyprtk-menu are documented in this file.
Dates are in YYYY-MM-DD format.

## [0.1.3] - 2026-09-05

### Changed

- **Theming now shares hyprtk-bar's theming model** — the menu reads the
  bar's `theme.source` (pywal / waybar / manual) + `waybar_theme` from
  `~/.config/hyprtk-bar/config.json` and resolves the **same palette** the bar
  uses (new `waybar_theme.py` port of the bar's parser, pointed at the bar's
  imported themes dir). The hardcoded theme-profile table and the
  `.themestyle.sh` watcher were dropped; the menu re-themes live on pywal
  colors, bar config, or theme changes.
- **2px menu panel border** on all four layouts (base style.css + win7 / win11
  / plasma layout overrides).

## [0.1.2] - 2026-09-04

### Changed

- `position: "auto"` now follows hyprtk-bar's **geometry**, not just its edge:
  reads `width` + `align` + `margin` + `height` from
  `~/.config/hyprtk-bar/config.json` and positions the menu's `align`
  relative to the bar's horizontal extent (left edge / center / right edge of
  the bar) instead of the screen edges. The menu also clears the bar's full
  height (`height` + 2*`margin` + gap) and re-anchors live while open when
  the bar config changes.
- Menu auto-position now follows hyprtk-bar's **gap_in/gap_out** geometry
  (the bar's exclusive-zone push), not just its edge; zero gaps are honored.
- Settings dialogue gained a **Spacing section** (Gap in = menu↔bar, Gap out =
  menu↔screen edge) replacing the hardcoded margins; zero is a valid gap.

## [0.1.1] - 2026-09-04

### Changed

- `position: "auto"` now follows **hyprtk-bar** instead of waybar: reads
  `~/.config/hyprtk-bar/config.json` and anchors the menu on the bar's edge
  (`position: "top"` → below the bar, `"bottom"` → above the bar). Waybar
  theme-config parsing removed.
- Settings dialogue "Auto (follow waybar)" renamed to
  "Auto (follow hyprtk-bar)"; theme-profile comments/docs updated to
  reference the bar theme.

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