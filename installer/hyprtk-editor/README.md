# hyprtk-editor

A fast, theme-aware text editor for the hyprtk desktop — Qt 6 QML on the
front, Python behind it. Opens like a notepad, grows into the parts of Kate
that earn their keep: real tabs, a session, regex search, 600+ syntaxes, a
command palette, line operations and a minimap.

**Current version: 0.1.2** — see [CHANGELOG.md](CHANGELOG.md).

![hyprtk-editor](hyprtk_editor/assets/hyprtk-editor.svg)

## Features

**Documents**
- Tabs with per-tab undo history and scroll position, dirty markers and a close guard
- Session restore (files, caret, scroll, active tab) and autosaved crash-recovery drafts — an unsaved buffer survives a power cut
- Encoding (UTF-8 / UTF-16 LE/BE / ISO-8859-1 / Windows-1252), BOM and LF/CRLF/CR detection, preserved on save
- Atomic saves that keep the file mode; a save refuses to overwrite a file that changed on disk
- External-change detection and *Reload from disk*
- Binary files and very large files open read-only with a banner

**Editing**
- Pygments highlighting for 600+ languages, with a language picker in the palette
- Current-line highlight, bracket matching, line numbers, minimap, word-wrap toggle, zoom
- Duplicate / move / delete line, comment toggle, sort (asc/desc/unique), trim trailing whitespace, join lines, case changes, indent/outdent, tabs ↔ spaces
- Incremental search with case, whole-word and regex modes, match highlighting, previous/next, replace one/all

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
│   ├── bridge.py       the single QML-facing facade (slots, signals, palette)
│   ├── fileio.py       encoding/BOM/EOL detection, atomic writes
│   ├── highlight.py    Pygments spans + the QSyntaxHighlighter
│   ├── languages.py    detection, curated language list, comment tokens
│   ├── palette.py      bar/pywal palette → colours + syntax roles
│   ├── search.py       pure find/replace
│   ├── textops.py      pure line/selection operations
│   ├── settings.py     JSON preferences
│   ├── session.py      session + draft persistence
│   └── qml/            Main, EditorPane, FindBar, CommandPalette, Settings…
├── bin/hyprtk-edit     launcher (sets the Qt platform theme)
├── install.sh
└── tests/              73 unit tests over the pure layers
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
  do not correspond to logical line numbers.
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
