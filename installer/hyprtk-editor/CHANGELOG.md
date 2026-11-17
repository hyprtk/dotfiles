# Changelog

## 0.1.2 — 2026-11-17

- Installer: `--system` installs under `/usr/local` (share + bin + desktop
  entry) for the live ISO, so every user gets the editor without a per-user
  install. Per-user remains the default.

## 0.1.1 — 2026-11-17

- Installer: fall back to a private PyPI venv when the distro's PySide6 lacks
  the QML bindings (Debian 12, Ubuntu 24.04) or Pygments is missing. The
  launcher prefers `venv/bin/python` when it exists.

## 0.1.0 — 2026-11-16

First working scaffold of the suite's text editor.

### Added
- Tabs with per-tab undo history, dirty markers, close guard and session restore
- Autosaved crash-recovery drafts with a recovery flow
- Open/save/save-as with atomic writes, mode preservation and stale-file protection
- Encoding (UTF-8, UTF-16 LE/BE, ISO-8859-1, Windows-1252), BOM and LF/CRLF/CR
  detection, preserved on save; binary and huge files open read-only
- Pygments syntax highlighting for 600+ languages, detected by extension or
  shebang, painted per visible block; language picker in the palette
- Current-line highlight, bracket matching, line numbers, minimap, word wrap,
  zoom, status bar
- Incremental find with case/whole-word/regex modes, live match painting,
  replace one/all
- Command palette over every action, including language, encoding and line endings
- Line operations: duplicate, move, delete, comment toggle, sort asc/desc/unique,
  trim trailing whitespace, join, case changes, indent/outdent, tabs↔spaces
- pywal/bar palette with palette-derived syntax colours and live reload
- File watching + reload, drag and drop, hyprtk-fm/terminal/clipboard integration
- Installer, desktop entry, icon, 73 unit tests and a QA script
