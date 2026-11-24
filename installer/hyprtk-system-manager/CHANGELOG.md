# Changelog

## [0.5.0] — 2026-11-24

The remainder of the P1 backlog: every panel that was read-only or partial now
has a real workflow behind it.

### Added

- **Sound: card profiles.** Each ALSA/PipeWire card exposes its selectable
  profiles (output/input combination and codec), applied with
  `pactl set-card-profile`; the panel re-probes after a change.
- **Network: VPN.** Saved OpenVPN and WireGuard connections are listed with
  Connect/Disconnect/Forget, and `.ovpn`/`.conf` profiles can be imported
  (`nmcli connection import`). The panel checks for the NetworkManager plugin
  first, so it says “OpenVPN support is not installed” instead of surfacing
  *unknown VPN plugin* from nmcli.
- **Displays: bit depth and colour management.** Per-monitor `bitdepth` and `cm`
  are written into the managed block when set; the live buffer format
  (`XRGB8888`, `XRGB2101010`, …) and the current colour preset are shown, and a
  10-bit scanout preselects 10-bit.
- **Accessibility** (expanded): text scaling slider and quick sizes, animations,
  reduced motion, high contrast, always-show-caret, cursor size, sticky / slow /
  bounce / mouse keys, screen-reader and on-screen-keyboard preferences. The
  panel reports whether a settings daemon, Orca or an OSK is actually present and
  offers to launch them, rather than implying the toggles work on their own.
- **Printers**: add a queue (`lpadmin` with a device, a device URI or a driver,
  plus location/description), remove, set the default, send a test page and open
  the CUPS web interface.
- **Region & Language**: generating a locale (`/etc/locale.gen` + `locale-gen`)
  and setting it happen in **one** privileged call, and the console keymap is
  validated against `localectl list-keymaps` before applying.
- **Sidebar: Suggested group** — five everyday panels (Displays, Sound, Network,
  Appearance, Updates), hidden while searching and skipping anything already in
  Recent or currently open.
- `util.spawn()`: detached process launch for GUI helpers, so an RPC action never
  blocks on a window (Orca, OSK, config-manager, CUPS).
- 131 tests, including the new panels, the VPN plugin gate, printer parsing and
  locale generation.

### Changed

- **Network is ordered by what you act on**: Devices → Wi-Fi (radio + actions) →
  Saved networks → VPN → Available networks. A room with twenty access points no
  longer buries the saved list behind the scan results.
- The installer's `network` step includes the OpenVPN plugin on every family
  (`network-manager-openvpn`, `NetworkManager-openvpn`, `networkmanager-openvpn`),
  so VPN import works on a fresh install.

### Fixed

- `locale.parse_localectl()` dropped every indented key, so the panel reported
  “unknown” for the keymap and X11 layout of real `localectl` output.
- The keymap name is validated before the privileged call: an invalid name is
  rejected without an authentication prompt.

## [0.4.0] — 2026-11-24

### Changed

- **Graphics now reports the Vulkan device/ICD separately from the `vulkaninfo`
  tool.** A working RADV stack with `vulkan-tools` absent no longer reads as
  “Vulkan missing”; the panel shows the enumerated device, the ICD file and the
  VA-API driver files.
- The installer's `graphics-card` step now includes `vulkan-tools` for every GPU
  branch (`Vulkan-Tools` on Void), so the diagnostic is present on fresh installs.

### Added

- **Displays**: a drag-to-arrange canvas — monitors are rectangles positioned in
  global pixels, snapped to 8 px, and the cards below follow; plus per-monitor
  **mirroring** (included in the live rule and the persistent block).
- 92 tests: Vulkan summary/ICD parsing, apply through the config,
  last-monitor/disabled guards, mirror in the persistent block, hyprctl error
  detection.

### Fixed

- **Displays: “Apply” silently did nothing.** This Hyprland accepts Lua
  dispatch only, and `hyprctl keyword monitor` answers "unknown request" while
  exiting 0. Apply now writes the managed block and reloads (the only runtime
  path on this build), and `hyprctl` textual errors are treated as failures.
- **The Enabled switch is hidden on a single-monitor setup**, and the backend
  refuses to disable the last enabled output.

## [0.3.0] — 2026-11-24

### Added

- **Network**: join Wi-Fi networks (secured ones prompt for the password),
  disconnect or forget saved connections, and toggle/rescan the radio. The
  password is handed to `nmcli connection up ... passwd-file` through a private
  `0600` file, never in argv or the action result.
- **Input**: save the exposed keyboard, pointer and touchpad settings into a
  delimited block in `input.lua` (Hyprland reloads it), and remove the block
  again. The file is restored if Hyprland rejects the reload.
- **Displays**: per-monitor **variable refresh rate** (off / always /
  fullscreen only), included in the live rule and the persistent block.
- 85 tests: input persist/clear and reload rollback, VRR in the monitor spec.

## [0.2.0] — 2026-11-24

### Changed

- **The RPC server is threaded.** Panel probes no longer run one at a time, so
  a slow probe (Updates can spend a minute in `checkupdates`) cannot freeze the
  rest of the window; apply/action calls stay serialised.
- **Search now finds settings, not just panels.** A background index warms the
  panel probes after startup and matches row labels (`Tap to click`, `Rotation`,
  `Default sink`, …). Results show the matched setting and re-run while the
  index finishes warming.
- **Recent panels** sit above the categories in the sidebar and persist in
  `ui.json`.

### Added

- **Sound**: default **input** volume and mute, plus **per-application
  streams** — each active PipeWire stream gets a volume slider and a mute
  toggle, written with `wpctl set-volume`/`set-mute`.
- **Users**: **Groups** and **Shell** dialogs per account, wired to the existing
  `usermod --groups` / `usermod --shell` actions.
- **Fonts**: **Install a font…** opens the file picker and copies the chosen
  `.ttf/.otf/.ttc/.woff` into `~/.local/share/fonts`, then refreshes the cache.
- 79 tests: out-of-order RPC responses, cached-row search, recent-page state,
  stream parsing and privilege commands, font install.

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
