# Changelog

All notable changes to hyprtk-system-manager are recorded here. The format is
loosely [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are
independent of the suite tag that carries them.

## [0.1.0] — 2026-11-24

First scaffold: the whole application shape plus eight functional panels.

### Added

- **Quickshell shell**: one window, grouped sidebar with eight categories,
  debounced global search, page header with a capability pill, pending-change
  footer with Apply/Revert, animated accent border, `--overlay` layer-shell mode.
- **Python backend**: JSON-lines RPC (`hello`, `catalog`, `panel`, `apply`,
  `action`, `search`, `fs.list`, `ui.get/set`, `status`), lazy panel registry,
  form-model builders and validation, capability probes, transactional file
  snapshots, `sudo -n`/`pkexec` privilege layer.
- **25 registered panels**, each with real probes:
  - System: About, Date & Time, Region & Language, Users & Groups, Services,
    Updates
  - Hardware: Displays, Graphics, Sound, Input Devices, Power, Bluetooth,
    Printers, Storage
  - Network: Network
  - Personalisation: Appearance, Fonts, Notifications
  - Desktop: Hyprland, Keyboard Shortcuts, Autostart
  - Applications: Default Applications, hyprtk Suite
  - Security: Privacy & Security
  - Accessibility: Accessibility
- **Fully functional panels**:
  - **About** — OS, kernel, CPU/GPU/RAM/disk, compositor, suite versions and a
    copyable diagnostic report.
  - **Date & Time** — timezone list, NTP, local RTC, sync status; writes through
    `timedatectl` under pkexec.
  - **Users & Groups** — account list with badges, create (home, shell, groups,
    admin, password), lock/unlock, delete with typed confirmation, password
    change via `chpasswd` stdin.
  - **Displays** — per-monitor enable/mode/scale/rotation/position, live
    `hyprctl keyword monitor`, and a persistent managed block in `monitors.lua`
    that never touches the rest of the file.
  - **Appearance** — colour source, background/foreground/accent, panel opacity,
    border width/animation, wallpaper through awww + pywal, icon/cursor/GTK
    themes.
  - **Fonts** — interface family and size, monospace resolution, family
    inventory, cache refresh and font installation.
  - **Autostart** — XDG desktop entries, user overrides for system entries,
    enable/disable and open-in-editor.
  - **hyprtk Suite** — version/running state for ten suite apps, settings and
    launch actions, plus inline bar opacity/border/font/animation keys.
- **Generic form renderer** with twelve row types (`info`, `toggle`, `choice`,
  `text`, `number`, `slider`, `color`, `path`, `action`, `list`, `kv`, `note`),
  a custom dropdown/slider/stepper/colour/path control set, inline file picker,
  confirmation and password modals, and a toast.
- **Suite theme**: the bar's exact pywal/config resolution, extended with a
  surface ladder, status colours and a type scale.
- **Tooling**: `hyprtk-settings` launcher, user and `--system` installers,
  desktop entry, v09-style icon, `doctor`, backups CLI, 62 unit tests, QML lint
  pass, off-screen boot check for one page of each kind, installer round-trip,
  and a deterministic off-screen screenshot tool.

### Suite integration (P0)

- Vendored into `hyprtk-merged` (`installer/hyprtk-system-manager/`) and
  installed by `1-install.sh` after config-manager.
- `Super+I` keybinding in `hypr/keybindings.lua`.
- ISO: `--system` install in `customize_airootfs.sh` and a first-run
  `~/.local/bin/hyprtk-settings` launcher link.
- Generated v09 `hyprtk-system-manager` icon (gear badge) and
  `docs/branding/banner.png` + `banner.svg` + `icon.png` with a README header.
- Suite panel no longer offers settings buttons that do not exist; fm/term/
  editor show their in-app `Ctrl+,` hint, and USB/ISO versions are read from the
  zipapp and the venv package.
- 68 tests: zipapp/venv/glob version lookup and settings-entrypoint guards.

### Fixed

- **Double edge around the window.** The standalone window was a `FloatingWindow`,
  so Hyprland added its own border, 10px rounding and drop shadow around the
  app's 14px rounded accent border. It is now a layer-shell `PanelWindow` like
  the bar's Settings and Quick Settings: layer surfaces are not decorated, so
  the app's animated border is the only edge, with one radius and no shadow.
  Off-screen QA and screenshots use a `FloatingWindow` host (`TestWindow.qml`).
- **Square sidebar corner.** The sidebar rail painted a square corner outside
  the panel's rounded border; it now rounds its top-left and bottom-left
  corners, as the bar's Settings sidebar does.

### Changed

- **Retheme to the bar-qt dialog language.** Every surface now uses the exact
  tokens from `hyprtk-bar-qt/components`: 30px controls on a 60% background
  fill with `accent2` borders, accent2-tinted 30px buttons, 16px slider handles,
  the 46×24 pill toggle, 8px cards with accent section titles, a 200px sidebar
  with the black-on-accent selection, 0.96 panel opacity and the animated accent
  border. The previous card-and-uppercase look, the right-aligned value column
  and the 34px controls are gone.

### Notes

- The Hyprland configuration stays owned by config-manager; the Hyprland panel
  links to it and Displays writes only its managed block.
- Panels that depend on absent tooling report `Unavailable` instead of failing.
- Known gaps and the roadmap are in [PLAN.md](PLAN.md): network join flow,
  per-app volume, power profiles, accessibility breadth, printer queues, and
  full row-level search.
