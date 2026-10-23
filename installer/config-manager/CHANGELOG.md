# Changelog

## 0.2.2 — 2026-10-23 (live monitor output/mode pickers)

- New `monitors.list` RPC: reads every connected output and its
  `availableModes` from `hyprctl -j monitors all` — the same source
  nwg-displays uses — normalizes them, removes duplicates and marks active
  outputs.
- Monitors page now offers an **Output** dropdown (all connected outputs with
  make/model/serial, active/inactive and an `auto` entry) and a **Mode**
  dropdown listing every available WxH@Hz for the selected output. `preferred`
  and existing custom modes are preserved; without Hyprland the page falls back
  to the old text fields.
- 60 tests (monitor parsing/dedup/current-mode coverage).

## 0.2.1 — 2026-10-23 (bar-qt integration)

- The UI now lives in `surface/App.qml`, shared by two window roots:
  `Main.qml` (standalone `FloatingWindow`, still SUPER-draggable) and
  `Overlay.qml` (layer-shell Overlay, used by bar-qt Settings).
- `config-manager open --overlay` (or `HYPR_CM_OVERLAY=1`) opens the overlay
  variant, which sits above the bar-qt Settings dialogue (Top layer) while
  remaining an independent process.
- Loader-based entry point picks the root at startup; standalone behaviour,
  config/animations editing and backend RPC are unchanged.

## 0.2.0 — 2026-10-23 (M1 sections + M2 animations editing)

### Sections from the real tree
- Every `*.lua` file is now a sidebar section, ordered by the actual
  `require()` chain; files not loaded by `hyprland.lua` appear as inactive.
- `hyprland.lua` is a read-only "Load order" page; `animations-*` are collapsed
  into the Animations page.
- Options are assigned by provenance, so each setting appears under the file
  that owns it; extra known options can be added from curated metadata.
- Non-config modules show their discovered calls: env, binds, rules, monitors,
  exec and unknown `hl.*` calls.
- `hyprlock`/`hypridle` stay out of scope (bar themer owns them).

### Animations
- File dropdown targets `animations-high.lua` or `animations-low.lua`; edits are
  read from and written to the selected file (active file shown as a badge).
- "Make active" flips the `require("animations-*")` line.
- Editable curve list: bézier points or spring (mass/stiffness/damping), with a
  live preview; editable tree: enabled, speed, curve and style per leaf.
- Animation/curve verification probes the target file, so editing an inactive
  module cannot silently verify against the effective tree.
- Env values are editable per module (`hl.env`), adding the call when missing.

### UI
- Settings window is now a FloatingWindow (normal toplevel) that self-floats
  and centres via Hyprland IPC, so SUPER+LMB window drag/resize work normally.
  Fixed at 1020×720 via min/max size hints.
- Real dropdown component (QtQuick Controls Basic popup) for all combos.
- File/active badges and discovered lists on module pages; pending-changes bar
  accepts mixed config, animation, curve and env edits.
- Layout pass: one fixed 200px control column per row, aligned left labels,
  32px controls, compact inline spin steppers, consistent 44×24 toggles,
  and a realigned animation tree/curve editor.
- Theme now resolves identically to hyprtk-bar-qt: pywal `special.background`
  /`foreground`, `color5` accent, `color6` accent2, `color8` dim, `color1`
  error, `color3` warn, the bar's `theme.source` manual overrides, its
  `opacity`/`border_width`/`border_animation` settings and `font.size`.
  Watches both `colors.json` and the bar `config.json`, so wallpaper/theme
  swaps apply live. Window chrome now uses the bar's animated accent border,
  accent-filled selected nav, accent2-tinted fields/buttons and cards.
- The window also self-sets `opacity`/`opacity_inactive` to 1.0 so
  `inactive_opacity 0.7` cannot wash it out when unfocused.
- Sidebar sections are sorted alphabetically by display name.
- Unified chrome with the hyprtk-bar-qt settings dialogue: flush 150px
  sidebar with left-rounded panel corners, 32px nav items, flat label rows
  (fixed 170px label column), grouped cards only for complex animation
  sections, and a footer carrying status, Reload, Revert/Apply and Close.
  Window resized to 900×640 with the bar's 140ms reveal animation.
- Keybind rows now show the actual dispatch expression (exec_cmd target,
  window.close, focus direction=left, …) instead of null.

### Inline editing & saving
- Environment/NVIDIA variables are editable in place, with an **Add variable**
  row (key + value) that appends to the page's module.
- Autostart commands (`hl.exec*`) are editable inline.
- Keybindings show editable **Keys** and **Dispatcher** fields per bind, plus an
  **Add binding** row.
- Monitors and window/layer/workspace rules expose every scalar field as an
  editable inline control (monitor output/mode/position/scale, rule
  match/props/float/size…).
- Load order exposes each `require()` as an editable module name with an
  active toggle, plus **Add module**.
- New writers: `set_exec`, `set_bind`, `set_call_field` (nested table keys),
  `set_require`, `add_require`; apply verification checks the resulting bind,
  exec or require state and re-probes the effective tree.
- Footer **Save configuration** applies all pending changes and runs
  `hyprctl reload`; Revert clears them. Ctrl+S also saves. Raw file editing UI
  was removed.

### Installer
- `install.sh` (+ `Makefile` targets): atomic install into
  `~/.local/share/hyprtk-config-manager`, `config-manager` launcher on PATH,
  desktop entry, dependency check, `--dry-run` and `--uninstall` (backups kept).
  No root or system-package changes required.
- `config-manager open` now detaches Quickshell into its own session so the
  launcher can exit cleanly.

### Tests
- 44 tests: dynamic sections, provenance assignment, inactive animation-file
  targeting, standalone module probing, env edit/add, live-tree build.

## 0.1.0 — 2026-10-22 (M0 scaffold)

Initial scaffold for the hyprtk Hyprland configuration manager.

### Read path
- Recording `hl` prelude: executes the real `hyprland.lua` require chain,
  captures every call with file/line provenance, tolerates unknown API
  namespaces (`hl.dsp.*`).
- Normalized model: config, curves, animations, binds, monitors, window/layer/
  workspace rules, gestures, env, exec, unknown calls.

### Write path
- Comment/string-aware Lua scanner: call spans, nested key paths, inline and
  multi-line insertion.
- Editors: `set_config`, `set_animation`, `set_curve` (bézier + spring),
  `set_animations_mode` (flips the active `require("animations-*")`).
- `Session`: sequential edits, per-file backups, atomic writes, one-probe
  semantic verification, byte-identical rollback.
- Backups under `~/.config/hyprtk-config-manager/backups/<stamp>/`.

### Interfaces
- CLI: `dump`, `get`, `set [--dry-run]`, `apply`, `validate`, `schema`,
  `backup list|restore`, `bar get|set`, `serve`, `open`.
- JSON-lines RPC for the GUI.
- Quickshell window: sidebar, schema-driven option pages with pending changes
  and Apply, Animations page with curve preview, animation tree, bar mirror.

### Tests
- 37 unit/integration tests (probe, scan, edit, schema, session, real tree).
- Integration apply verified on a temp copy of `hyprtk-merged/hypr`.

### Notes
- `hyprtk-bar-qt` Animations move-out is planned for M3; this release only reads
  its animation keys.
