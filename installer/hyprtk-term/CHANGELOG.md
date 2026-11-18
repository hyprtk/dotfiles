# Changelog

## 0.2.2 — 2026-11-18

### Fixed

- **The scrollback-search screenshot in the README renders again.**
  `docs/search.png` was added to the README while `.gitignore` still ignored
  `docs/*.png` (only `probe.png` was un-ignored), so the file existed locally,
  in the vendored copy and on disk — just never in the repository. GitHub showed
  a broken image. The ignore rule is gone and the image is regenerated against
  the current UI.
- New `tests/test_docs.py`: every relative link and image in the markdown must
  exist, and every image the README shows must be tracked by git (the second
  half is what actually catches this class of bug).

## 0.2.1 — 2026-11-18

### Fixed

- **Tabs no longer move while you click them.** A tab's width was derived from
  its title, so every OSC title change (zsh sets one on each prompt) resized the
  tab and pushed everything to its right along — the second tab shifted by up to
  129 px. Fixed width (150 px), title elided; the active tab's full title is in
  the window title.
- **The settings sheet's "+" buttons sit inside the card.** Label, value and the
  two 26 px pills summed past the card's content width, so the right-hand pill
  hung outside the sheet (and could not be clicked).

### Changed

- Tabs are stored in a `ListModel` and updated with `setProperty`, so adding,
  closing or re-labelling a tab no longer destroys and recreates every delegate
  mid-click.
- The headless gate now checks both: tab geometry must survive a title change,
  clicking each tab must activate it, and every stepper button must fit its card.

## 0.2.0 — 2026-11-18## 0.2.0 — 2026-11-18

### Added

- **Scrollback search.** `Ctrl+Shift+F` opens a find bar over the active tab:
  plain or regex, case toggle, match counter, next/previous (`Ctrl+Shift+G` /
  `Shift+F3`), `Esc` to close. Matches are collected over history *and* the live
  screen, the active one is highlighted stronger, and the view scrolls so the
  match lands about a third down.
  Scrollback lines cache their plain text when they are pushed, so searching a
  10,000-line history costs one pass over strings instead of re-reading 800,000
  cells through ctypes.
- **Correct paint order.** Row backgrounds, then selection and search tints,
  then glyphs. Highlights no longer dim the text they cover.

### Changed

- `VTerminal.line_text()` for cheap per-line text (cached for history, built on
  demand for screen rows); `set_scrollback()` keeps the text cache aligned.
- Search state is dropped on resize, where absolute line numbers would go stale.

## 0.1.0 — 2026-11-18

First scaffold. A real shell in a real window, with the parts that make it
usable daily and an honest list of what is not there yet (see PLAN.md).

### Added

- **libvterm core through ctypes.** xterm/DEC parsing, alt screen, reflow,
  scroll regions, 256-colour and truecolor, bold/italic/underline/strike/
  reverse/conceal/blink, wide and combining characters.
- **Theme-following palette.** The 16 ANSI slots come from pywal through the
  bar's theme, the same loader the editor and file manager use. A wallpaper
  change reloads every open tab.
- **Damage-tracked rendering.** libvterm reports damaged rows, the rows are
  re-read through ctypes and cached as styled runs, and QPainter draws runs
  instead of cells. A full 80x24 grid paints in ~3 ms.
- **Scrollback.** A ring of raw `VTermScreenCell` bytes (10,000 lines by
  default) so `sb_popline` can hand libvterm its own cells back; wheel scroll,
  jump to bottom, clear.
- **Tabs** with the OSC title, middle-click close, bell indicator, and one PTY
  per tab.
- **Input.** libvterm's key encoder (arrows, Home/End/Ins/Del/PgUp/PgDn, F1–F12,
  modifiers, control characters, alt prefix), bracketed paste, IME commits,
  mouse reporting with Shift override.
- **Selection and clipboard.** Linear and word selection, select-all, copy/paste,
  and OSC 52 in both directions.
- **Settings sheet** (`Ctrl+,`) for font, size, opacity, scrollback, cursor
  blink and copy-on-select, saved to `~/.config/hyprtk-term/config.json`.
- **Suite integration scaffolding.** v09 icon (`term` glyph added to the brand
  kit), installer with `--system`/`--uninstall`/`--set-default`, desktop entry,
  Symbols Nerd Font chrome.

### Notes

- 93 unit tests, `qmllint` clean, headless boot check, installer round-trip;
  `make qa` runs the lot.
- Not in 0.1: splits, scrollback search, OSC 8 hyperlinks, inline images,
  ligature clamping, session restore. Each is scheduled in PLAN.md.

## Unreleased

- Nothing yet.
