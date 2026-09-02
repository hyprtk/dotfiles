# Multi-Layout Menu Styles — Design

**Date:** 2026-08-12
**Status:** Approved
**Scope:** hyprtk-menu layout selection (Whisker / Win7 / Win11 / Plasma)

## Overview

Add the ability to choose a menu style layout. All layouts share the same
Whisker widget structure (search, category sidebar, app list, favorites row,
recents pane, power bar). Each layout is a distinct visual theme delivered as
its own CSS file, scoped under a root `.layout-<name>` class, plus a minimal
structural-tweak hook for the few things CSS cannot express.

## Decisions

- **Real structural layouts** — each style rebuilds the window arrangement to
  match its OS, not just a recolor. Verified via screenshots that CSS-only
  recolors were indistinguishable from whisker.
- **Separate CSS files per layout** — each layout gets its own
  `assets/layout-<name>.css`; base `assets/style.css` stays shared.
- **In-menu cycle button** — a layout button in the power bar cycles the
  active layout (mirrors the existing align button), persists to config, and
  re-themes live.
- **Per-layout widget builders in menu.py** — `_build_whisker()`,
  `_build_win7()`, `_build_win11()`, `_build_plasma()` each build their own
  widget tree; `_build_ui()` dispatches on the active layout.

## Layout structures

### Whisker (default, current)
Search top, category sidebar left, favorites row + app list center, recents
right, powerbar bottom. Draggable column panes.

### Win7
- Left pane: app list (programs), favorites pinned at top
- Right pane: "places" (categories list)
- Bottom: search entry + power button (classic Win7 layout)

### Win11
- Centered window (narrower, taller feel)
- Search top, centered
- "Pinned" favorites grid (large icons)
- "Recommended" recents section below
- "All apps" app list below that
- Power buttons bottom-right

### Plasma
- Search top
- Tab row (Favorites / Applications / Computer / Recently Used)
- Favorites tab: favorites grid
- Applications tab: category sidebar + app list
- Recently Used tab: recents list
- Power buttons bottom

## Shared widgets
All layouts reuse: search entry, app row factory (`_make_row`), favorites
buttons (`_refresh_favorites`), recents list (`_refresh_recents`), powerbar +
power actions, layout/align cycle buttons, resize grip. Only the arrangement
differs per layout.

## Configuration

New key in `config.py` `DEFAULT_CONFIG`:

```json
"layout": "whisker"
```

Valid values: `whisker`, `win7`, `win11`, `plasma`. Loaded/saved through the
existing deep-merge + `save_config()` paths.

## CSS Architecture

- `assets/style.css` — unchanged shared base (tokens, panel, panes, powerbar).
- `assets/layout-whisker.css` — current look (extracted as a layout block).
- `assets/layout-win7.css` — aero blue glass: blue-tinted surfaces, Win7 feel.
- `assets/layout-win11.css` — flat acrylic: softer radius, centered-feel
  search, "Recommended"-style recents emphasis.
- `assets/layout-plasma.css` — Breeze translucent: bluish surface, subtle
  borders, KDE feel.

Each layout file scopes its rules under `.layout-<name>` so overrides only
apply when active. Layout CSS may only override base rules — it never
duplicates the full base stylesheet.

### build_css() ordering (theme.py)

1. pywal palette (`_palette_to_css`)
2. base `style.css`
3. waybar theme profile block (`_profile_to_css`)
4. active layout file (read from config)

Signature unchanged. `build_css()` resolves the active layout via
`config.load_config()`.

## Root Class

The window's root widget gets `layout-<name>` added to its style context
(e.g. `.layout-win11`). Applied on startup and whenever the layout changes.

## Cycle Button

- Added to the power bar next to the align button.
- Icon per layout (grid / desktop-style glyphs).
- Click cycles `whisker → win7 → win11 → plasma → whisker`.
- Persists to config, then re-themes live using the same hide → rebuild →
  remap routine as `_check_wal`.

## Structural Tweaks

`apply_layout_tweaks()` in menu.py handles CSS-impossible per-layout behavior
(search placeholder text per layout). Rebuilds of the widget tree happen in
the per-layout builders, so a layout change rebuilds the tree and re-applies
CSS.

## Update Cycle

`_check_wal` already re-applies CSS on any change; the layout button calls the
same re-theme path, so live updates work without new plumbing.

## Files

- `hyprtk_menu/config.py` — add `layout` default
- `hyprtk_menu/theme.py` — append active layout CSS in `build_css()`; add
  layout-name helper
- `hyprtk_menu/menu.py` — root class, layout button, per-layout widget
  builders (`_build_whisker/_build_win7/_build_win11/_build_plasma`),
  `apply_layout_tweaks()`
- `assets/layout-whisker.css`, `assets/layout-win7.css`,
  `assets/layout-win11.css`, `assets/layout-plasma.css` — new
- `install.sh` — copy layout CSS files (currently copies only style.css)
- `README.md` — document layout config + button
