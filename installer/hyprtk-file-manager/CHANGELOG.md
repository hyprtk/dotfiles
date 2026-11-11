# Changelog

## 1.6.4 — 2026-11-11

### Added

- **Real thumbnails in grid view.** Images, videos and PDFs now show preview
  tiles (image/video frames and the first PDF page) instead of only their type
  icon. Tiles are generated on demand for visible items, cached on disk, and
  fall back to the type icon while loading. A new **Grid thumbnails** setting
  turns them off.

### Changed

- **Type-aware file icons.** Files and folders now get their real freedesktop
  MIME icon from the active theme (Papirus) instead of one generic glyph:
  source code, documents, images, audio, video, archives/packages, fonts,
  certificates/keys, 3D models, disk images, executables and more. Exact
  names (Makefile, CMakeLists.txt, README, LICENSE, CHANGELOG, PKGBUILD,
  shell rc files) and well-known/XDG folders (Desktop, Documents, Downloads,
  Music, Pictures, Videos, Projects, `.git`, cloud folders) get their own
  icons. Extensionless executables/scripts and Qt Linguist `.ts` files are
  detected from content; `.ts` otherwise shows the TypeScript icon.

## 1.6.3 — 2026-11-11

### Fixed

- **Copy/paste pasted older items.** Arrow keys only moved the cursor while
  leaving a previous selection in place, so `Ctrl+C` copied the previously
  clicked item (or a whole earlier selection) instead of the item under the
  cursor. Arrow keys now move the selection with the cursor; `Ctrl`+arrows move
  the cursor while keeping the selection for multi-select.
- **Stale selection across navigation.** Back/forward (and tab/path changes) now
  clear the selection, and a selection that points outside the current folder is
  pruned before it can be copied.

## 1.6.2 — 2026-11-11

### Changed

- **Cleaner right-click menu.** Items are now grouped into sections (Open,
  Edit, Create, Trash, Organize, Tools, Properties) separated by thin dividers,
  and actions that do not apply to the current selection are hidden instead of
  shown greyed out. Every action is still available, the per-user show/hide and
  reorder settings still apply, and the menu is noticeably shorter in normal
  use.

## 1.6.1 — 2026-11-11

### Changed

- **Settings dialog version.** The dialog shows the running
  hyprtk-file-manager version in its bottom-left corner.

## 1.6.0 — 2026-11-11

### Changed

- **Repository hygiene.** Planning docs, QA notes, benchmarks and test suites
  are no longer tracked or published; they stay local for development.

### Added

- **Editable right-click menu.** Settings now has a **Right-click menu** editor:
  toggle any context-menu item on or off and move it up or down. The order and
  visibility apply to both file and blank-area menus, are saved with the rest of
  the configuration, and can be reset to defaults.

## 1.5.1 — 2026-11-11

### Changed

- **Sidebar typography.** The Places, Devices and Network section headings now
  use the item font size instead of a smaller label size, and network host rows
  match it too.

## 1.5.0 — 2026-11-11

### Added

- **Settings dialog.** A gear at the top of the sidebar (also `Ctrl+,` and the
  command palette) opens settings for every editable preference: view mode,
  icon size, sort key, descending order, folders first, hidden files, dual
  pane, preview panel and the transfers tray. Changes apply immediately and are
  saved automatically.

## 1.4.0 — 2026-11-11

### Added

- **Open With.** Right-clicking a file now offers **Open With…**, a dialog that
  lists every application registered for the file's content type — the default
  app first, then recommended apps, then the rest alphabetically. Pick one with
  the mouse or arrow keys and Enter; the file opens in it without changing the
  system default. Applications come from Gio/GVfs, with a `.desktop`-file
  fallback when PyGObject is unavailable.
- 117 tests.

### Changed

- **Open as Root now opens an elevated file manager.** The blank-area menu item
  launches `hyprtk-fm` through `pkexec` (forwarding the Wayland/Qt session and
  pywal theme environment) instead of a root terminal. The previous behaviour
  is still available as **Open Terminal as Root**.
- **Root warning banner.** A window running as root now shows a red bar under
  the address bar — "Running as root — file operations affect the whole
  system" — so an elevated instance is never mistaken for a normal one.
- **Sidebar navigation.** Back, forward and up moved from the start of the
  address bar to the top of the sidebar, joined by a Home button. The address
  bar now spans the full toolbar width.

### Fixed

- **View and sort buttons.** The toolbar's view-mode and sort-key buttons called
  `Config.cycleView()` / `Config.cycleSort()`, which were missing from the
  settings singleton, so both clicks failed silently. Both cyclers are restored.
- **Papirus folder colors in every view.** Icons were requested at their display
  size, so 16px rows (compact view, sidebar) picked Papirus' monochrome
  symbolic variant and the grid could pick a blue fallback. Icons now request a
  64px source and scale down, so the recolored full-color variants are used
  consistently in list, grid and compact views.

## 1.3.0 — 2026-11-10

### Added

- **Network browsing that actually authenticates.** Selecting a host now asks
  for credentials and then enumerates the server's shares through GVfs (Gio),
  listing them under the host. With a single share it mounts straight away.
  Before, the backend "mounted" the server root, which GVfs treats as an
  already-mounted browse location — so credentials were never validated and no
  path appeared.
- **Share mounts are real.** Clicking a share mounts `smb://host/share` (or
  `nfs://host/export`) and opens it. Credentials are saved to the keyring
  (`PasswordSave.PERMANENTLY`); a silent keyring attempt runs first, and the
  dialog only appears when a password is actually required.
- **Network places.** Shares and folders inside a mount can be added to Places.
  GTK bookmarks now support `smb://` and `nfs://` URIs (shown with a
  `folder-remote` icon) and reconnect on click. Add to Places converts a GVfs
  mount path back to its URI so it survives reboots.
- **Clicking a host toggles its shares.** A host with listed shares now shows a
  caret and collapses/expands on click; hosts without shares connect as before.
- **NFS exports** are listed with `showmount -e` when available.
- **Network discovery runs automatically** when the window opens; scanning now
  probes ports and mDNS in parallel.

### Fixed

- GVfs share directory names are matched case-insensitively, so a `Documents`
  share maps to `smb-share:server=host,share=documents`.
- 108 tests.

## 1.2.9 — 2026-11-10

### Changed

- **Devices now matches Thunar.** EFI System (GPT and MBR `0xef`), Microsoft
  Reserved, Windows Recovery, and BIOS boot partitions are hidden, along with
  anything mounted under `/boot` or `/efi` — so a Ventoy stick no longer shows
  its `VTOYEFI` partition.
- Internal unmounted data volumes are shown again (reverts the 1.2.2 hide rule);
  unlabelled volumes use Thunar-style names like `531 GB Volume` (decimal GB,
  rounded).
- Device rows are grouped like Thunar: internal volumes first, then
  removable/external, with File System first.
- 102 tests.

## 1.2.8 — 2026-11-10

### Fixed

- **Section headings now actually inset 16px.** The previous `x` values were
  ignored because the headings sit inside QML positioners; using `leftPadding`
  makes Places, Devices, and Network align with the row icon edge instead of the
  window border.
- 100 tests.

## 1.2.7 — 2026-11-10

### Fixed

- **Section headings align to the Devices row inset (16px).** Places, Devices,
  and Network no longer hug the window border; all three share the same left
  edge as the device/place row icons.
- 100 tests.

## 1.2.6 — 2026-11-10

### Fixed

- **Places, Devices, Network headings share one left inset**, so Places and
  Network align with Devices instead of hugging the window border.
- 100 tests.

## 1.2.5 — 2026-11-10

### Changed

- Removed the **+** button from the Places heading. Adding a folder to Places is
  still available from the folder context menu (**Add to Places**).
- 100 tests.

## 1.2.4 — 2026-11-10

### Changed

- **Eject now unmounts only.** Ejecting a mounted external device leaves it in
  Devices as an inactive row with a **mount** action instead of powering the
  disk off and removing the row. This matches the expected “inactive, not
  removed” behavior. The eject icon disappears once it is unmounted.
- 100 tests.

## 1.2.3 — 2026-11-10

### Added

- **File System** entry in Devices, always first, opening the root (`/`) like
  Thunar.
- **Eject** button on mounted external volumes. Right-click a device for
  **Eject Media** as well. Eject unmounts the volume and powers off its disk
  when the hardware supports it; if power-off is unsupported the volume still
  unmounts. Browsing inside an ejected mount moves the pane home.
- 100 tests.

### Changed

- **Places / Devices / Network** section headings align to the sidebar's left
  edge (items stay indented).
## 1.2.2 — 2026-11-10

### Changed

- **Devices hides internal unmounted volumes.** A volume is treated as external
  when its disk reports `rm`, a USB/MMC/SDIO/FireWire transport, or when it is
  mounted. Internal, non-removable volumes that are not mounted (for example
  spare NVMe partitions) are hidden. Transport and removable flags are inherited
  from the parent disk, so an external USB drive that is currently unmounted
  stays visible with a mount action.
- Combined with the fstab filter, Devices shows only removable/external or
  mounted volumes.
- 96 tests.

## 1.2.1 — 2026-11-10

### Fixed

- **Devices no longer lists fstab-backed volumes.** `/etc/fstab` (and
  `/etc/fstab.d/*`) is parsed and entries are matched by mountpoint, `/dev`
  path, UUID, LABEL, PARTUUID, and PARTLABEL. Auto-mounted systems and `/mnt`
  drives disappear from Devices; non-fstab volumes (USB, spare partitions)
  remain.

### Added

- **Network login dialogue.** Opening a network host/share now asks for
  username, password, and workgroup/domain (plus **Guest**). The mount goes
  through Gio's `MountOperation` with the supplied credentials, so GVfs does not
  prompt separately.
- 94 tests.

## 1.2.0 — 2026-11-10

### Added

- Thunar-style sidebar: **Places**, **Devices**, **Network** (the old Bookmarks
  group is merged into Places).
- Places: defaults plus GTK bookmarks (shared with Thunar); a **+** button and
  the pane's **Add to Places** action add the current/selected folder, and
  custom entries can be removed from the right-click menu.
- Devices: every block volume from `lsblk` (mounted or not, incl. USB), with
  click-to-mount through `udisksctl` and a mount hint on unmounted volumes.
- Network: local `/24` port scan plus Avahi for SMB/NFS/AFP hosts; guest SMB
  shares are listed; clicking a host or share mounts it through GVfs and browses
  the mount point.
- Command palette entries for **Add to Places** and **Scan Network**.
- 91 tests.

### Notes

- NFS exports are not enumerated without `showmount`; NFS hosts are detected.
- SMB share listing may need credentials; click the host to authenticate through
  GVfs.

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
