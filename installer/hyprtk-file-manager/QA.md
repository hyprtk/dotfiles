# QA Matrix — v1.1.3

Automated gate: `make qa` (`scripts/qa.sh`)

| Check | Result |
|---|---|
| Unit tests (listing, places, RPC, ops, journal, preview, search, store, watch, meta, launch, trash, CLI) | 81/81 pass |
| `python3 -m compileall backend` | pass |
| `bash -n install.sh`, `sh -n bin/hyprtk-fm` | pass |
| 10k listing, first page | 43.3 ms (budget 300 ms) |
| 10k listing, cached page | 1.0 ms (budget 50 ms) |
| Installer install + uninstall round-trip in a temp HOME | pass |

End-to-end checks (real UI driven with `wtype`, screenshots reviewed)

| Flow | Result |
|---|---|
| Browse home / project directories | pass |
| Tabs, history, path entry (`Ctrl+L`) | pass |
| Single and dual pane | pass |
| List, grid, compact views; sorting; hidden toggle | pass |
| Copy, move, trash, rename, new folder, new file | pass |
| Conflict dialog: keep both (others unit-tested) | pass |
| Undo: copy, move, trash, rename, mkdir, newfile, batch rename | pass |
| Redo: rename round-trip (undo → redo) | pass |
| Task tray progress and auto-prune | pass |
| Permanent delete confirmation | pass |
| Batch rename with prefix + undo | pass |
| Quick Look: text, image, PDF thumbnails | pass |
| Instant filter | pass |
| Name search and ripgrep content search | pass |
| Command palette → grid view | pass |
| Settings persistence (grid survived relaunch) | pass |
| Session restore (two tabs + `sub` path survived relaunch) | pass |
| Live inotify refresh (external file appeared) | pass |
| Properties metadata + SHA-256 | pass |
| Permissions dialog: `chmod` 644 → 600 | pass |
| Properties: Make executable 644 → 755 | pass |
| Dual pane: `Ctrl+C` in A, `Tab`, `Ctrl+V` in B | pass |
| Context menu: Open Terminal Here spawns Alacritty in the folder | pass |
| Trash place in the sidebar + Trash view | pass (23 items) |
| Trash restore (.trashinfo) | unit-tested |
| Empty Trash (confirm + job) | dialog/job verified; command mocked |
| Show/hide transfers tray (`Ctrl+J`) | pass |
| Drag a file between panes | pass (move journaled; target reveal added) |

Implemented but not automatable in this session (manual gesture check)

| Flow | Status |
|---|---|
| Marquee overlay click pass-through | verified with a PySide6/QTest harness |
| Empty-area right-click menu | implemented; manual mouse check |
| Open as Root (pkexec prompt) | implemented; manual check |
| Marquee selection (drag empty space; Shift+drag from an entry) | implemented; manual gesture check |
| Internal pane-to-pane drag (move) | implemented; manual gesture check |
| Drag-out to another app; external drop-in copy | implemented; manual gesture check |
| Cancel mid-copy (between-item cancellation) | implemented, not exercised |

Remaining deferred

- Open-as-root (pkexec).
- Archive, terminal, tags, git badges, custom actions, compare/dupes/disk usage
  (v1.1 power pass).
- Remote / cloud (v2).
- Release tag (project is not a git repository yet).
