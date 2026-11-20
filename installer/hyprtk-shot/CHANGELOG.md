# Changelog

## 0.2.1 — 2026-11-20

Pin to screen, the last item from the v0.2 list.

### Added

- **Pin to screen** — the overlay's `Pin` button (or `hyprtk-shot open PATH
  --pin`) keeps the finished crop on screen as a frameless, always-on-top window
  sized to the image, pinned to every workspace by a Hyprland rule. Dismiss with
  a double-click or the close button that appears on hover; a compositor close
  dismisses it too. The file lives in `$XDG_RUNTIME_DIR/hyprtk-shot/` and pin
  files from dead processes are swept on the next pin.
- The pinned window is dragged with the compositor (Super + drag), not by the
  client — Wayland gives an app no way to move its own window.

### Fixed

- **Window titles carried a `" — Screenshot"` suffix** (Qt appends the
  application display name when the title differs), which would have broken the
  window rules that match `^(Screenshot)$` and `^(hyprtk-shot pinned)$`. The
  display name is gone; titles are exactly what the QML sets.
- The process no longer quits when the overlay closes to a pin: the pinned
  window is the thing left on screen, and the single quit decision now lives in
  the `finished` handler (plus a compositor close of the launcher).

## 0.2.0 — 2026-11-20

Placing the selection exactly, and a region that can cross outputs.

### Added

- **Shift locks the box square** while dragging, anchored at the press point.
- **Arrow keys nudge the selection** by 1 px, `Shift` + arrow by 10 px, clamped
  to the image edge (it moves, it never resizes).
- **Cross-output region** — the launcher's "Cross-output" toggle, `--slurp`, or
  `"picker": "slurp"` selects with slurp (which spans every output). The frozen
  overlay stays the default; slurp is the explicit choice.
- **Window picker** — the Window card lists the open windows (focused row first)
  instead of only capturing whichever window happens to have focus;
  `--window ADDRESS` does the same from the command line, and a closed window
  falls back to the focused one.
- **Crop after the fact** — eight grips (corners and edge midpoints) resize a
  selection that already has annotations; the opposite edge stays anchored, and
  annotations are stored in image coordinates so they move with the crop.
- Undo/redo now covers **selection changes and Clear**, not only annotations.

### Changed

- Undo history stores whole-state snapshots (annotations + selection), so a
  mixed history redoes exactly what was on screen at that point.
- `--slurp` / `--overlay` choose the region picker from the command line; the
  no-editor path uses slurp instead of demanding `--region`.

## 0.1.1 — 2026-11-20

### Fixed

- **Closing the launcher ends the process.** The window's `visible` property is
  a binding (`initialMode === "" && ...`), so a compositor close could be
  re-asserted on the next state change and leave a hidden process in the task
  list. The window now quits the application on close.

## 0.1.0 — 2026-11-20

First release. A screenshot tool for the hyprtk desktop: grim capture, a frozen
overlay for selection, in-place annotation, save or copy.

### Added

- **Four capture modes** through `grim`: region (the focused monitor is
  captured, then the box is drawn on the frozen frame), focused window
  (geometry from `hyprctl clients`), focused monitor (`grim -o`), and all
  outputs. No portal, no X11 grab, no screenshot-of-the-overlay bug, and no
  second selection UI.
- **Frozen overlay**: the captured frame is displayed fullscreen, dimmed outside
  the selection, with the selection as the crop.
- **Annotation**: pen, line, arrow, rectangle, ellipse, highlighter, numbered
  step markers, text, blur and pixelate, with colour swatches, stroke width,
  undo, redo and clear. Preview and final render share one painter.
- **Output**: PNG/JPEG/WebP under `~/Pictures/Screenshots`, clipboard via
  `wl-copy`, optional notification, and an append-only history the launcher
  lists (open, copy path, delete).
- **Launcher window**: mode grid, delay, copy/annotate/cursor toggles, save
  directory, recent captures.
- **CLI**: `hyprtk-shot [region|window|output|full|last]`, `--delay`,
  `--copy/--no-copy`, `--save`, `--no-save`, `--stdout`, `--no-edit`,
  `--cursor`, `--json`, `--list-outputs`, `--version`.
- **Desktop integration**: PySide6/QML with the suite's pywal palette, a v09
  suite icon, absolute `Exec=`/`Icon=` desktop entry, `--system` and
  `--uninstall` installers, PyPI-venv fallback for Debian/Ubuntu.
- **Tests**: 94 unit tests (capture argv and geometry, renderer pixel checks,
  store, settings, CLI, docs), `qmllint`, and a headless boot check that drives
  a real capture session.
