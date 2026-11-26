# Changelog

## Unreleased — documentation

- README: v09 suite banner, palette badges and the twelve-repository suite
  list (screenshot, recorder and system manager were missing).

## 0.2.5 — 2026-11-26

### Fixed

- **Every CLI flag that matters was dropped on the editor path.** `run()`
  builds a fresh `Settings` from disk, so `--delay`, `--cursor` and `--picker`
  were set on an object nobody read: `hyprtk-shot region --slurp` documented in
  the README never used slurp. They are passed as overrides now.
- **`--save PATH` wrote nothing when the config had `save: false`**, and still
  exited 0. An explicit `--save` now wins.
- **A failed clipboard copy reported success.** The JSON payload echoed the
  intent (`"copied": true`) and the exit status was 0; it now reports the real
  result and returns 1.
- **A second pin in one process reused the same file** and then unlinked it,
  leaving a blank pin window that `unpin()` could not clear. Pin files carry a
  serial number.
- **Pin files could be world-readable.** With no `XDG_RUNTIME_DIR` the pin dir
  fell back to `/tmp` at 0755 with 0644 PNGs; it is 0700/0600 now.
- **`--window ADDRESS` for a window that closed captured whatever had focus**
  instead of failing.
- **The annotation ratio was wrong for a named output or a mixed-scale/stacked
  layout** (ratio 1.0, or the sum of the monitor widths), so strokes and text in
  the saved file were the wrong weight. It is taken from the captured output and
  from the union of the monitors.
- **`deleteCapture`/`openPath` acted on any path from history.jsonl**, so an
  edited entry could unlink an arbitrary file. Both require the path to live in
  the screenshots folder.

## 0.2.4 — 2026-11-23

### Fixed

- **`--save PATH` was ignored by the region overlay.** The flag only reached the
  no-editor capture path, so `hyprtk-shot region -s /tmp/shot.png` still wrote
  into the configured screenshot folder under a generated name. The overlay now
  honours a file name, a directory (a name is generated inside it, `/` suffix
  included) and a path without a suffix (the format is appended), and never
  overwrites an existing file. Found by driving the overlay with injected input.

## 0.2.3 — 2026-11-20

### Fixed

- **The window picker offered windows from other workspaces.** Capturing a
  window is a geometry crop of the current screen, so a window that is not on
  screen produces somebody else's pixels. The list is now the active
  workspace's windows, focused first, and the bridge self-heals a pick that
  leaves the workspace. (A tiled or maximised window *is* its tile, so its
  capture looks like the workspace — that is the window, not a bug.)
- **A delayed capture gave no sign it was waiting.** The delay hid the launcher
  and then froze the screen, and the frozen frame looks exactly like the live
  desktop, so starting the drag during the delay lost the press and nothing
  could be selected. A 200×200 countdown window now runs for the delay and is
  hidden 120 ms before `grim`, so the number is never in the capture.
- **A leftover annotation tool ate the first drag.** The overlay now starts a
  selection on any press while nothing is chosen (full frame), whatever tool is
  active; the tool applies once a box exists.

### Changed

- **Region capture is two phases.** The overlay freezes with only the selection
  active — no annotation toolbar, just "Drag to select a region" — and the
  toolbar appears once a box exists, with the Select tool active so the box can
  be moved or resized first. `Enter` (and Save/Copy) only work once a region has
  been chosen; right-click or `Ctrl+A` count as choosing the whole screen, so an
  accidental `Enter` can no longer capture everything.

## 0.2.2 — 2026-11-20

### Fixed

- **A region capture saved the whole monitor.** The overlay opens with the
  whole frame selected. Pressing inside that selection started a *move*, and a
  full-frame selection cannot move — it is already at every edge — so the
  selection never changed and the saved file was the entire screenshot.
  A press on the untouched full-frame selection now starts a new box; moving
  still works once a box exists, and the eight grips still resize.
  Right-click or `Ctrl+A` still selects everything.

### Tests

- `selection.is_full_frame()` (unit) and a bootcheck drag that drives the real
  canvas handlers: press 100,100 → 300,250 must leave a 200x150 selection, and
  it fails on the old behaviour.

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
