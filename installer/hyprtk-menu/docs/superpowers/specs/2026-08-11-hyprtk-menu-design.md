# hyprtk-menu — Design Spec

**Date:** 2026-08-11
**Status:** Approved
**Stack:** Python 3.14 + PyGObject (GTK3) + gtk-layer-shell

## Purpose

A Whisker-style application menu for Hyprland: a searchable launcher with a
category sidebar, favorites, recents, and power buttons. Opens as a
`gtk-layer-shell` overlay popup, styled with the hyprtk pywal glass aesthetic
(frosted glass, mauve/cyan accents matching the waybar themes).

## Layout (Whisker)

- **Top:** search entry (autofocused on open)
- **Left sidebar:** All, Favorites, Recently Used, then categories
  (Accessories, Development, Education, Games, Graphics, Internet, Multimedia,
  Office, Science, Settings, System)
- **Center:** favorites icon row (pinned) above a scrollable app list filtered
  by category + search
- **Right:** recently used apps list
- **Bottom:** power bar — lock, logout, reboot, shutdown, suspend (commands
  configurable)

## Behavior

- Typing filters apps live (name, generic name, comment, keywords)
- Up/Down navigate the list, Enter/double-click launch, Esc closes
- Right-click an app toggles pin/favorite
- Launched apps move to the top of recents (max 10, configurable)
- Favorites + recents persist in `~/.config/hyprtk-menu/config.json`
- Power commands configurable in the same file
- Single instance; `hyprtk-menu --toggle` sends SIGUSR1 to the running daemon
  (PID in `~/.cache/hyprtk-menu/hyprtk-menu.pid`)

## Launch strategy

- Primary: `Gio.DesktopAppInfo.launch()` (handles field codes)
- Fallback: run the Exec line via `subprocess.Popen` (Terminal=true apps
  wrapped with the detected terminal emulator)

## Theming

- `theme.py` reads `~/.cache/wal/colors.css` (pywal) and prepends it to the
  base CSS; a dark fallback palette is used if pywal is missing
- Base CSS in `assets/style.css` — frosted glass, rounded corners, `@color5`
  (mauve) accents and `@color6` (cyan) highlights
- Hyprland: `layerrule = blur, hyprtk-menu` for real backdrop blur

## Architecture

```
hyprtk_menu/
├── __init__.py
├── app.py        # entry, single-instance lockfile, SIGUSR1 toggle
├── menu.py       # layer-shell window, layout, navigation, power
├── apps.py       # .desktop scan, category map, search, launch
├── config.py     # load/save JSON config
└── theme.py      # CSS assembly + provider
assets/style.css  # base GTK CSS
main.py           # thin entry point
install.sh        # installs to ~/.local/share/hyprtk-menu + ~/.local/bin
README.md
```

## Error handling

- Corrupt config → reset to defaults
- Missing app icons → fallback icon
- Launch failure → silent (menu closes); power command failure → ignored
- Stale PID file → detected via `kill(pid, 0)` and ignored

## Out of scope (YAGNI)

No plugins, no file browser, no autostart editor, no settings GUI.
