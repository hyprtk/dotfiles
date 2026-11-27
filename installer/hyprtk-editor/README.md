<div align="center">

<img src="docs/branding/banner.png" alt="hyprtk-editor — part of the hyprtk suite" width="100%" />

[![suite](https://img.shields.io/badge/suite-hyprtk-02DEDE?style=flat-square&labelColor=05060B)](https://github.com/hyprtk)
[![version](https://img.shields.io/badge/version-0.2.7-FD4FB6?style=flat-square&labelColor=05060B)](CHANGELOG.md)
[![wiki](https://img.shields.io/badge/wiki-editor-C084FC?style=flat-square&labelColor=05060B)](https://github.com/hyprtk/hyprtk-editor/wiki)
[![license](https://img.shields.io/badge/license-MIT-5FB8F5?style=flat-square&labelColor=05060B)](LICENSE)

</div>

# hyprtk-editor

> **Part of the hyprtk suite** — [dotfiles](https://github.com/hyprtk/dotfiles) · [bar-qt](https://github.com/hyprtk/hyprtk-bar-qt) · [file manager](https://github.com/hyprtk/hyprtk-file-manager) · [editor](https://github.com/hyprtk/hyprtk-editor) · [terminal](https://github.com/hyprtk/hyprtk-term) · [calculator](https://github.com/hyprtk/hyprtk-calc) · [screenshot](https://github.com/hyprtk/hyprtk-shot) · [recorder](https://github.com/hyprtk/hyprtk-rec) · [system manager](https://github.com/hyprtk/hyprtk-system-manager) · [config manager](https://github.com/hyprtk/hyprtk-hyprland-config-manager) · [hyprtk-usb](https://github.com/hyprtk/hyprtk-usb) · [ISO creator](https://github.com/hyprtk/Hyprtk-ISO-Creator)

A fast, theme-aware text editor for the hyprtk desktop — Qt 6 QML on the
front, Python behind it. Opens like a notepad, grows into the parts of Kate
that earn their keep: real tabs, a session, regex search, 600+ syntaxes, a
command palette, line operations and a minimap.

**Current version: 0.2.7** — see [CHANGELOG.md](CHANGELOG.md).

## Features

**Documents**
- Tabs with per-tab undo history and scroll position, dirty markers and a close guard; drag to reorder, middle-click to close, wheel to cycle
- Session restore (files, caret, scroll, active tab) and autosaved crash-recovery drafts — an unsaved buffer survives a power cut
- Encoding (UTF-8 / UTF-16 LE/BE / ISO-8859-1 / Windows-1252), BOM and LF/CRLF/CR detection, preserved on save
- Atomic saves that keep the file mode; a save refuses to overwrite a file that changed on disk
- External-change detection and *Reload from disk*
- Binary files and very large files open read-only with a banner
- **Git diff gutter** — added, modified and deleted lines against HEAD, in a
  stripe that survives wrap mode and the line-number toggle

**Editing**
- Pygments highlighting for 600+ languages, with a language picker in the palette
- Current-line highlight, bracket matching, line numbers, minimap, word-wrap toggle, zoom
- Duplicate / move / delete line, comment toggle, sort (asc/desc/unique), trim trailing whitespace, join lines, case changes, indent/outdent, tabs ↔ spaces
- Incremental search with case, whole-word and regex modes, match highlighting, previous/next, replace one/all — **per tab**, so each file keeps its own query and replace text
- Quick open (`Ctrl+P`) over open documents, recent files and the current folder, ranked by a fuzzy subsequence score
- **Print and export to PDF** (`Ctrl+K → Print…` / `Export as PDF…`): a separate
  light-theme document, so a dark editor prints as black text on paper with a
  light syntax palette

**Interface**
- Command palette (`Ctrl+K`) over every action — including language, encoding and line endings, so no menu hunting
- Follows the bar's pywal palette; the syntax theme is derived from the same 16 colours, so it matches the wallpaper
- Keyboard-first, with a status bar for line/column, selection, language, encoding, EOL and line count
- Suite integration: open the containing folder in **hyprtk-fm**, open a terminal here, copy the file path
- Drag and drop files onto the window

## Requirements

| | |
|---|---|
| **Python** | 3.10+ |
| **PySide6** | 6.6+ (Qt 6.12 tested) |
| **Pygments** | 2.14+ |

PySide6 and Pygments are already suite dependencies for hyprtk-usb and
hyprtk-iso-creator, so a normal hyprtk install has both. Quickshell is **not**
needed; this is a plain Qt app like the USB/ISO front ends.

## Install

```sh
./install.sh                  # tree in ~/.local/share/hyprtk-editor, launcher in ~/.local/bin
./install.sh --set-default    # also become the default text/plain handler
./install.sh --uninstall
```

Then `hyprtk-edit [FILE ...]`, or launch **Text Editor** from the app menu.
`HYPRTK_DRYRUN=1 ./install.sh` prints what it would do.

## Keyboard

| Action | Shortcut |
|---|---|
| New / open / save / save as | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S` |
| Close tab / next tab / previous tab | `Ctrl+W` / `Ctrl+Tab` / `Ctrl+Shift+Tab` |
| Find / replace | `Ctrl+F` / `Ctrl+H` |
| Find next / previous | `F3` / `Shift+F3` |
| Go to line | `Ctrl+G` |
| Quick open | `Ctrl+P` |
| Command palette | `Ctrl+K` or `Ctrl+Shift+P` |
| Preferences | `Ctrl+,` |
| Duplicate / delete line | `Ctrl+Shift+D` / `Ctrl+Shift+K` |
| Move line up / down | `Alt+Up` / `Alt+Down` |
| Toggle comment | `Ctrl+/` |
| Toggle word wrap | `Alt+Z` |
| Zoom in / out / reset | `Ctrl+=` / `Ctrl+-` / `Ctrl+0` |
| Indent / outdent | `Tab` / `Shift+Tab` |

## Architecture

```
hyprtk-editor/
├── hyprtk_editor/
│   ├── app.py          QApplication + QML engine + Bridge
│   ├── bridge.py       the single QML-facing facade (slots, signals, palette, tokenising worker)
│   ├── fileio.py       encoding/BOM/EOL detection, atomic writes
│   ├── gitdiff.py      git diff --unified=0 → gutter marks
│   ├── printdoc.py     light-theme print/PDF document
│   ├── highlight.py    Pygments spans + the QSyntaxHighlighter
│   ├── languages.py    detection, curated language list, comment tokens
│   ├── palette.py      bar/pywal palette → colours + syntax roles
│   ├── search.py       pure find/replace + fuzzy ranking
│   ├── textops.py      pure line/selection operations
│   ├── settings.py     JSON preferences
│   ├── session.py      session + draft persistence
│   └── qml/            Main, EditorPane, FindBar, QuickOpen, CommandPalette…
├── bin/hyprtk-edit     launcher (sets the Qt platform theme)
├── install.sh
└── tests/              147 unit tests over the pure layers
```

### The highlighting constraint (why it is viewport-scoped)

Measured on this stack, with a QML `TextArea`:

| Lines | `QSyntaxHighlighter.rehighlight()` | Plain edit + repaint |
|---|---|---|
| 300 | 21 ms | 2 ms |
| 1,500 | 158 ms | 2 ms |
| 6,000 | 2.4 s | 2 ms |
| 24,000 | 40 s | 8 ms |

Every block formatted by `QSyntaxHighlighter` emits a document change that
QML's text node honours, so a whole-document pass is quadratic. Pygments
tokenises 6,000 lines in 135 ms, so the design is: tokenise once into per-line
spans, then push only the **visible blocks plus the edited block** through
`rehighlightBlock` (0.8–3.4 ms per block). Editing stays at 2–8 ms even in a
24,000-line file. Bulk `QTextLayout.setFormats` is fast but QQuickTextEdit does
not paint formats applied that way, so it is not an option.

### Palette plumbing

QML singletons cannot read context properties (verified), and PySide6's
singleton registration is unusable in this build, so the palette is exposed as
the notifying `Bridge.palette` property. Its values are converted to real
`QColor` objects in Python: a `QVariantMap` with hex strings reaches QML as
strings, where `color.r` is `undefined` and alpha helper functions silently
produce black.

## Limits (honest ones)

- QML's text engine lays out the whole document. Above ~400 KB highlighting and
  the minimap switch off; above 2 MB the file opens read-only.
- The line-number gutter is hidden while word wrap is on — wrapped visual lines
  do not correspond to logical line numbers. The git stripe is a separate
  column for exactly that reason.
- The git gutter marks the working tree against HEAD. A file outside a
  repository, or in a repository git cannot answer for within two seconds, just
  has no marks.
- Printed output has no syntax-error squiggles or search highlights: the print
  document is rebuilt from the plain text, not copied from the live one.
- Highlighting colours only what is on screen; off-screen text is coloured as it
  scrolls in. This is deliberate, and invisible in normal use.
- No LSP, multi-cursor, split view or markdown preview yet — see
  [PLAN.md](PLAN.md).

## Development

```sh
make test              # unit tests
make qa                # tests + qmllint + headless boot + installer round-trip
make run               # launch from the source tree
python3 scripts/screenshot.py shot.png   # offscreen render for visual checks
```

See [RESEARCH.md](RESEARCH.md) for the editor survey and [PLAN.md](PLAN.md) for
the roadmap and suite-integration checklist.

## License

MIT — see [LICENSE](LICENSE).

---

## Branding

<img src="docs/branding/palette.png" alt="hyprtk palette: cyan #02DEDE, magenta #FD4FB6, navy #000044, ink #05060B, white #F2F6FF, muted #8A93A6" width="100%" />

The mark is the suite's **v09** direction: an oversized `ht` monogram on an ink
field, a gradient ring, and the component glyph in a badge. The wordmark is
**KoblenzSerial Bold**, converted to outlines so no font install is needed.
The banner, icon and palette are generated from the brand kit described in the
[dotfiles README](https://github.com/hyprtk/dotfiles#branding).

---

## Part of the hyprtk suite

hyprtk is one desktop kept in nine repositories: every one of them installs
or configures part of the same pywal-themed, Arch-first Hyprland setup.

| project | what it is |
| --- | --- |
| [**dotfiles**](https://github.com/hyprtk/dotfiles) | the desktop itself: the any-distro installer, the Hyprland Lua config, themes and 60+ scripts |
| [**hyprtk-bar-qt**](https://github.com/hyprtk/hyprtk-bar-qt) | the Qt6/QML (Quickshell) bar and everything it owns: launcher, notifications, tray, quick settings, desktop widgets |
| [**hyprtk-fm**](https://github.com/hyprtk/hyprtk-file-manager) | the Qt6/QML file manager, default for `Super+F` and `inode/directory` |
| [**hyprtk-editor**](https://github.com/hyprtk/hyprtk-editor) | the Qt Quick text editor, default for `text/plain` and `text/markdown` |
| [**hyprtk-term**](https://github.com/hyprtk/hyprtk-term) | the Qt Quick terminal: libvterm core, tabs, scrollback search, pywal palette |
| [**hyprtk-calc**](https://github.com/hyprtk/hyprtk-calc) | the Qt Quick calculator: exact decimal arithmetic, three modes |
| [**config-manager**](https://github.com/hyprtk/hyprtk-hyprland-config-manager) | the Hyprland settings GUI, opened from the bar's Settings |
| [**hyprtk-usb**](https://github.com/hyprtk/hyprtk-usb) | writes a hyprtk ISO to a USB stick, with optional persistence |
| [**ISO creator**](https://github.com/hyprtk/Hyprtk-ISO-Creator) | builds the installable ISO: `airootfs`, package lists, first-run seed |

**This project is the text editor** in that list; the desktop as a whole lives in
the [dotfiles](https://github.com/hyprtk/dotfiles) repository.
