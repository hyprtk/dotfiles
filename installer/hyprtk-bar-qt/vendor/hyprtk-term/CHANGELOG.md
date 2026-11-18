# Changelog

## 0.2.6 — 2026-11-18

### Fixed

- **No stray `%` above the prompt.** zsh's `PROMPT_SP` prints a bold reverse
  `%` after output that did not end in a newline, fills the rest of the line
  with `COLUMNS - 1` spaces, then erases the mark with `CR`, space, `CR`. If a
  grid resize lands in the middle of that sequence and the shell still believes
  the previous, wider `COLUMNS`, the fill wraps onto the next line, the erase
  lands there instead, and the `%` is stranded on screen. The startup layout was
  doing exactly that: the view was constructed with the *default* settings and
  spawned the shell at the wrong grid, then resized it four times in 130 ms
  (103 → 132 → 272 → 271) as the real font loaded and the compositor tiled the
  window — the last of those a one-column *shrink*, which is the dangerous
  direction.
  - The saved settings are now loaded at construction, so the font and the grid
    are right the first time.
  - The shell is spawned only once the window has stopped being laid out
    (80 ms settle), so its startup sees no resizes at all.
  - Grid resizes are coalesced (40 ms), so a layout burst reaches the shell once
    instead of four times.
- `Terminal.resize()` returns whether the grid changed. It returned `None`, so
  the "drop search matches on resize" branch in the view never ran.

`scripts/bootcheck.py` gained a gate for the coalescing: a two-step resize must
reach the shell exactly once (it reached it four times before).

## 0.2.5 — 2026-11-18

### Fixed

- **Block art and box drawing render correctly with any font.** The default
  `JetBrainsMono Nerd Font Mono` ships only U+2588 out of the whole U+2500-U+259F
  range, so Qt fell back to a proportional face for the rest: `opencode`'s logo
  came out as scattered squares and its frame as a dashed line, while the same
  screen was correct in alacritty (which uses FiraCode). Every code point in that
  range is now painted as rectangles, lines and arcs inside its cell — half and
  full blocks tile exactly, light/heavy/double frames join without crossing,
  dashes, rounded corners and diagonals are drawn to size. `boxdraw.py` is
  Qt-free and covered by `tests/test_boxdraw.py`, including an assertion that
  nothing is drawn outside its cell for all 160 code points.
- `vt.py` now splits a row into one run per geometric cell, so the painter can
  address the cell exactly; `row_runs` and scrollback runs are otherwise
  unchanged.

## 0.2.4 — 2026-11-18

### Fixed

- **The window is one surface again.** The tab strip painted the theme
  background at `max(0.75, opacity)` while the grid painted it at `opacity`, so
  below 100% the two halves showed different amounts of wallpaper and the grid
  never matched the strip. Both now use the configured opacity, and the headless
  gate samples a strip pixel against a grid pixel at 58% to prove it.
- **The right-click menu is themed, not GTK.** It was a `QtQuick.Controls`
  `Menu`, which takes its palette from QQuickTheme (the platform theme, i.e.
  GTK) and ignores pywal entirely — a white box with black text. Replaced with
  `components/ContextMenu.qml`: a `Popup` that supplies only the window/dismiss
  behaviour, with our own surface, rows, hover tint, disabled state, separator
  and focus return to the terminal.

## 0.2.3 — 2026-11-18

### Added

- **The settings sheet shows the app version** in its bottom-left corner
  (`hyprtk-term 0.2.3`), captured once at startup so the label cannot break at
  teardown. The headless gate asserts the text matches `hyprtk_term.__version__`,
  so a stale or empty label fails the build.

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
