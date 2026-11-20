# Changelog

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
