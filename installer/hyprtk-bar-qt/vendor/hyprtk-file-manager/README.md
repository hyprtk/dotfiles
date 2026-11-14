# hyprtk-file-manager

A fast, keyboard-first file manager for the hyprtk desktop — Qt 6 QML
(Quickshell) on the front, a Python backend behind it. Clean like Nautilus,
with the power of Dolphin/Yazi one shortcut away. It follows the suite's live
pywal theme and ships as the default `Super+F` / `inode/directory` handler.

**Current version: 1.8.1** — see [CHANGELOG.md](CHANGELOG.md).

## Features

**Browsing**
- Async, virtualized listings that never freeze (10k-file directories are fine)
- Icon grid, details list and compact views; sortable, dirs-first, hidden toggle
- Type-aware Papirus icons per file (MIME/extension, exact names) and special
  folders (Desktop, Documents, Downloads, `.git`, cloud folders…)
- Tabs with per-tab history, back/forward/up, breadcrumb (Home and mount paths
  read as names, click to type a path) and `Ctrl+L` path entry
- Single pane by default, optional dual pane (`Tab` switches)
- Single/ctrl/shift selection, marquee select, and cross-pane drag and drop

**File operations**
- Copy, cut, paste, move, rename, new folder/file, trash and permanent delete
- Shared desktop clipboard: file selections use the Wayland
  `x-special/gnome-copied-files` format, so the bar's cliphist history and other
  file managers see the same copy/cut selection
- Conflict dialog: replace / skip / keep both / apply to all
- Docked task queue with progress, cancel and partial-failure reporting
- Multi-level undo **and** redo for move/copy/trash/rename (`Ctrl+Z` /
  `Ctrl+Shift+Z`)
- Batch rename with find/replace, numbering, prefix/suffix, case and live preview
- Undo journal persisted alongside session state

**Preview and inspection**
- Grid thumbnails for images, video and PDF (cached; toggle in Settings)
- Spacebar Quick Look: images, video, PDF, text/code and metadata
- Properties dialog with permissions and checksums
- Open-with via `xdg-open`; **Open With…** picks any registered application
  (default first, then recommended), can set it as the default, and opens a
  terminal (or a root terminal) in the cwd

**Places and devices**
- Places sidebar from XDG dirs + GTK bookmarks (shared with Thunar), reorderable
  with **Move Up** / **Move Down** (saved with the rest of the settings)
- Devices via `lsblk`/UDisks2: mount, open, eject (unmount-only, by design);
  boot/EFI/recovery partitions hidden, internal-first grouping
- Network: auto-scan for SMB/NFS/AFP hosts (shown by machine name via NetBIOS/DNS,
  e.g. `192.168.0.230` → **NAS**), enumerate shares through GVfs, real credential
  auth saved to the keyring, mount `smb://host/share`, and add shares/folders to
  Places as reconnectable URIs

**Search and keyboard**
- Instant filename filter (`Ctrl+F`) plus recursive name/content search
  (`Ctrl+Shift+F`, ripgrep for content when installed)
- Command palette over every action (`Ctrl+K`), plus a settings dialog
  (`Ctrl+,`) for every preference, including a right-click menu editor
- Full keyboard operation; see the shortcut table below

## Requirements

Required:

| | |
|---|---|
| **Quickshell** | `qs` on `PATH` (Qt 6 QML runtime) |
| **Python** | 3.10+ |
| **Python packages** | PyGObject (`python-gobject`) for network shares / GVfs |
| **GIO** | `gio` for trash and GVfs mounts |
| **UDisks2** | `udisks2` for device mount/eject |

Optional — features degrade gracefully without them:

| Tool | Enables |
|---|---|
| `rg` (ripgrep) | recursive content search |
| `smbclient` | SMB share listing fallback |
| `showmount` (nfs-utils) | NFS export listing |
| `avahi-browse` | mDNS host discovery |
| `vipsthumbnail` (libvips) | fast image thumbnails |
| `ffmpeg` | video thumbnails |
| `pdftoppm` (poppler) | PDF thumbnails |
| `xdg-open` | open files with their default app |
| `pkexec` | open terminal as root |

A terminal is needed for the “open terminal” action: `alacritty`, `kitty`,
`foot` or `wezterm`, or set `$TERMINAL`.

## Install

Full details, per-distro package commands and troubleshooting are in
[INSTALL.md](INSTALL.md).

```sh
git clone https://github.com/hyprtk/hyprtk-file-manager.git
cd hyprtk-file-manager
./install.sh
```

This copies the app to `${XDG_DATA_HOME:-~/.local/share}/hyprtk-file-manager`,
symlinks `~/.local/bin/hyprtk-fm` and installs the *Files* desktop entry.
`~/.local/bin` must be on your `PATH`.

Uninstall:

```sh
./install.sh --uninstall
```

## Run

```sh
hyprtk-fm              # open at $HOME
hyprtk-fm ~/Downloads  # open at a path
```

Environment variables:

| Variable | Meaning |
|---|---|
| `HYPRTK_FM_START` | initial directory (default `$HOME`) |
| `HYPRTK_FM_VIEW` | `list` (default), `grid` or `compact` |
| `HYPRTK_FM_DUAL` | `1` starts with dual pane |
| `QT_QPA_PLATFORMTHEME` | set to `gtk3` for the icon theme (the launchers do this) |

View mode, hidden files, sorting, pane layout and panels are also editable in
the app and persisted automatically.

## Keyboard shortcuts

| Keys | Action |
|---|---|
| `Ctrl+L` | edit path |
| `Backspace` | go up |
| `Alt+Left` / `Alt+Right` | back / forward |
| `F5` | reload |
| `Ctrl+H` | toggle hidden files |
| `Ctrl+T` / `Ctrl+W` | new tab / close tab |
| `Tab` | switch active pane (dual pane) |
| `Up`/`Down`, `Home`/`End` | move selection |
| `Ctrl+Up`/`Ctrl+Down`, `Ctrl+Home`/`Ctrl+End` | move cursor, keep selection |
| `Return` | open |
| `Space` | toggle preview (Quick Look) |
| `Ctrl+Space` | toggle selection |
| `Ctrl+A` | select all |
| `Ctrl+F` | instant filter |
| `Ctrl+C` / `Ctrl+X` / `Ctrl+V` | copy / cut / paste |
| `F2` | rename |
| `Ctrl+Shift+N` / `Ctrl+Alt+N` | new folder / new file |
| `Ctrl+Shift+E` | empty trash (in Trash) |
| `Ctrl+Z` / `Ctrl+Shift+Z` | undo / redo |
| `Alt+Return` | properties |
| `Ctrl+Shift+F` | recursive search |
| `Ctrl+K` | command palette |
| `Ctrl+J` | toggle transfers panel |
| `Ctrl+Q` | quit |
| `Escape` | close dialog / cancel edit |

## CLI

```sh
hyprtk-fm open [path]   # open the GUI (default)
hyprtk-fm serve         # JSON-lines RPC over stdio
hyprtk-fm places        # dump places, bookmarks and drives as JSON
hyprtk-fm version
```

## Development

```sh
make run     # launch from the source tree
make test    # Python unit tests
make qa      # tests + syntax checks + perf budget + installer round-trip
```

Layout:

- `shell.qml`, `surface/` — window, panes, dialogs and panels
- `data/` — QML singletons bridging the backend (Backend, Ui, Jobs, Preview…)
- `components/`, `theme/`, `config/` — shared widgets, pywal theme, settings
- `backend/hyprtk_file_manager/` — Python: listing, ops, journal/undo, search,
  preview, trash, places/devices, network, RPC and CLI
- `tests/` — unittest suite; `spike/` — performance benchmarks and results

Notes and gotchas for contributors:

- QML needs `QT_QPA_PLATFORMTHEME=gtk3` for the icon theme; `make run` sets it.
- QML positioners ignore child `x`; use `leftPadding` for alignment.
- Trash uses real `gio trash`; system-internal mounts (e.g. `/tmp`) are refused.
- Never mount the SMB server root — enumerate shares, then mount
  `smb://host/share` (GVfs reports the root as already mounted).
- Eject is intentionally unmount-only; do not add power-off.
- Session state lives in `~/.local/state/hyprtk-file-manager/`; thumbnails in
  `~/.cache/hyprtk-file-manager/thumbs/`.

## Part of the hyprtk suite

Vendored into the suite installer and used as the default file manager (the
bar's **Files** quick link, `Super+F`, XDG `inode/directory`), with Thunar kept
as a fallback. This repository remains the source of truth; update it first,
then re-vendor.

## License

GPL-3.0. See [LICENSE](LICENSE).
