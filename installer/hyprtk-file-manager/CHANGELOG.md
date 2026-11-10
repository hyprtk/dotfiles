# Changelog

## 1.1.3 — 2026-11-09

### Added

- **Empty Trash** with confirmation: sidebar right-click on Trash, the Trash
  view's context menu, the command palette, and `Ctrl+Shift+E`. Runs as a job
  (`gio trash --empty`) so the task tray shows progress and panes refresh.
- **Show/hide the transfers tray**: `Ctrl+J`, the tray's Hide button, the pane
  context menu, and the command palette. The choice persists.

### Fixed

- Trash header spacing in the transfers tray.

### Tests

- 81 unit tests.

## 1.1.2 — 2026-11-09

### Fixed

- Drag and drop between panes now uses Qt's Automatic platform drag (the old
  in-view drag was clipped/cancelled at the pane edge). `preventStealing` keeps
  the ListView from taking the drag.
- A drop activates the target pane, refreshes it, and selects/reveals the
  dropped item (paging until found).

### Added

- **Trash** place in the sidebar (home trash).
- **Open Trash** and **Restore from Trash** in the context menu and command
  palette. Restore reads `.trashinfo` and returns the file to its original path.
- 79 unit tests.

## 1.1.1 — 2026-11-09

Fixes from first-run testing.

### Fixed

- Dual pane: clicking a pane now activates it on press; `Tab` switches panes;
  copy/cut/paste across panes verified.
- Right-clicking empty space in a pane opens the context menu (row right-click
  still works).
- Internal drag between panes now carries an explicit path payload, so it no
  longer depends on drag timing; external drops still copy.
- The properties mode field now syncs after a `chmod`.

### Added

- **Open Terminal Here** and **Open as Root** in the context menu and palette.
  Terminal detection: `$TERMINAL`, Alacritty, kitty, foot, WezTerm; root uses
  `pkexec` with the Wayland environment forwarded.
- **Make executable** in the properties dialog (adds `0111`; `Ctrl+E`).
- 77 unit tests.

## 1.1.0 — 2026-11-09

Closed the v1.0 known gaps.

### Added

- Multi-level redo (`Ctrl+Shift+Z`), persisted with the undo journal. New
  operations clear the redo stack.
- Marquee selection in list and grid: drag empty space, `Shift`+drag from an
  entry, `Ctrl` adds to the selection.
- Internal pane-to-pane drag (move) and drag-out (`text/uri-list`); external
  drops copy into the current folder.
- Properties dialog (`Alt+Return`): metadata, symbolic and octal permissions
  with `chmod`, and a SHA-256 checksum.
- Redo and Properties entries in the context menu and command palette.
- 74 unit tests.

### Notes

- Mouse gestures (marquee, drag) were not automatable in the dev session
  (`/dev/uinput` is root-only); they load cleanly and should be checked manually
  on a real session.

## 1.0.0 — 2026-11-09

First release.

### Added

- Persisted settings at `~/.config/hyprtk-file-manager/config.json`: view mode,
  sort key/direction, hidden files, icon size, dual pane, preview.
- Session restore at `~/.local/state/hyprtk-file-manager/session.json`: per-pane
  tabs, active tab, history, and paths.
- Live directory refresh via inotify, one watcher per pane.
- External drag-and-drop copy into the current folder.
- `scripts/qa.sh` (60 tests, syntax, performance gate, installer round-trip) and
  `scripts/perf.py` (10k listing: 44.9 ms first page, 0.8 ms cached).
- `QA.md` with the v1.0 QA matrix.

### Changed

- `Config` now loads and saves over the backend RPC with debounced atomic writes.

### Known limitations

- Marquee selection, internal pane-to-pane drag, and drag-out.
- Redo.
- Properties / permissions / checksum dialogs.
- Archive, terminal, tags, git badges, custom actions, compare/dupes/disk usage
  are v1.1.
- No git tag yet (the project is not a repository).

## 0.3.0 — 2026-11-09

M3 inspect and find.

### Added

- Quick Look preview panel (`Space`): images, video, and PDF thumbnails via
  `vipsthumbnail` / `ffmpeg` / `pdftoppm`, text preview, and metadata.
- Async `preview` and `search` backend methods so the UI stays responsive.
- Instant filename filter (`Ctrl+F`) with debounce.
- Recursive search panel (`Ctrl+Shift+F`): name search and ripgrep content
  search with path, line, and line number; `Ctrl+1` / `Ctrl+2` switch mode.
- Reveal-in-folder from search results.
- Command palette (`Ctrl+K`) with fuzzy matching over 26 actions.
- Batch rename dialog: find/replace, prefix/suffix, numbering, case, live
  preview, collision validation, and undo.
- `Space` opens Quick Look; `Ctrl+Space` toggles selection.
- 55 unit tests.

### Notes

- Name search walks the tree and does not honour `.gitignore`; content search
  uses ripgrep and does.
- Preview thumbnails are cached by path + mtime + size.

## 0.2.0 — 2026-11-09

M2 file operations.

### Added

- Backend job engine: worker threads, stdin-safe event streaming, per-item
  progress, cancel, and partial-failure reporting.
- Operations: copy (recursive, symlink-safe), move, trash (`gio`), permanent
  delete, rename, new folder, new file.
- Conflict handling: replace / skip / keep both / apply-to-all, with a modal
  dialog and `R` / `S` / `K` / `A` shortcuts.
- Multi-level undo for copy, move, trash, rename, mkdir, and new file, with a
  persisted journal at `~/.local/state/hyprtk-file-manager/journal.json`.
- Task tray with progress bars and cancel; finished jobs prune after 8 s.
- Clipboard copy/cut/paste across tabs and panes, plus `Ctrl+C/X/V`, `Ctrl+A`,
  `F2`, `Ctrl+Shift+N`, `Ctrl+Alt+N`, `Ctrl+Z`, `Delete` / `Shift+Delete`.
- Right-click context menu and toolbar overflow menu.
- Confirmation for permanent delete; safe copy-onto-self and
  destination-inside-source rejection.
- 42 unit tests.

### Notes

- `gio trash` follows the XDG spec and refuses system-internal mounts such as
  `/tmp`; the error surfaces in the task tray.
- Redo and batch rename are deferred (batch rename lands in M3).

## 0.1.0 — 2026-11-09

M1 core browser.

### Added

- Quickshell QML front end + Python JSON-lines backend (suite architecture).
- Async paged directory listing with a per-directory name cache and windowed `stat`.
- List, grid, and compact views; name/size/mtime/type sorting; dirs-first; hidden toggle.
- Tabs with per-tab history; back/forward/up; breadcrumb path bar; `Ctrl+L` path entry.
- Optional dual pane with independent panes and tabs.
- Selection: click, Ctrl-toggle, Shift-range; keyboard cursor and open.
- Sidebar: XDG places, GTK bookmarks (deduped), mounted drives from `/proc/mounts`.
- pywal-aware theme with dark-first palette; Papirus icons via the gtk3 platform theme.
- Launcher (`hyprtk-fm`), desktop entry, installer, Makefile.
- 23 unit tests covering listing, sorting, pagination, cache invalidation, places,
  bookmarks, RPC, and the CLI entrypoint.

### Known gaps

- Marquee selection.
- Live inotify refresh (manual `F5`; cache invalidates on directory mtime).
- Drag and drop (manual verification pending).
- No file operations yet (M2: copy/move/trash/rename, conflict dialog, undo).
- Settings are in-memory only (persistence in M4).
