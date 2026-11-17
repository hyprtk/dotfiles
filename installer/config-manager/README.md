# hyprtk-config-manager

> **Part of the hyprtk suite** — [dotfiles](https://github.com/hyprtk/dotfiles) · [bar-qt](https://github.com/hyprtk/hyprtk-bar-qt) · [file manager](https://github.com/hyprtk/hyprtk-file-manager) · [editor](https://github.com/hyprtk/hyprtk-editor) · [config manager](https://github.com/hyprtk/hyprtk-hyprland-config-manager) · [hyprtk-usb](https://github.com/hyprtk/hyprtk-usb) · [ISO creator](https://github.com/hyprtk/Hyprtk-ISO-Creator)

Hyprland configuration manager for the hyprtk desktop suite.
Qt/QML (Quickshell) front end, Python backend, Lua-first (Hyprland 0.55+).

Unlike HyprMod (writes its own override file) and HyprViz (hyprlang only),
this app executes your real `hyprland.lua` module chain to read the *effective*
config, then writes changes back to the file that owns them — with backups and
verification.

See [PLAN.md](PLAN.md) for architecture, milestones, and the bar-qt Animations
move-out.

## Install

```bash
./install.sh --dry-run    # check qs + lua + python
./install.sh              # install to ~/.local/share/hyprtk-config-manager
config-manager            # launch the standalone GUI
config-manager open --overlay   # layer-shell overlay (bar-qt Settings entry)
./install.sh --uninstall  # remove (backups under ~/.config are kept)
```

The installer needs no root: it installs the Quickshell tree + Python backend,
links `config-manager` into `~/.local/bin` (falling back to `/usr/local/bin`
when that directory is not on PATH) and registers a desktop entry. It requires
`qs` (Quickshell) and a Lua interpreter (`lua5.4` or `lua`); both ship with the
hyprtk suite.

## Quick start (from the repo)

```bash
./bin/config-manager --help
./bin/config-manager dump
./bin/config-manager schema
./bin/config-manager validate
qs -p .                      # GUI
python3 -m unittest discover -s tests
```

## Status

M1/M2 in progress: dynamic file sections from the real `require()` chain,
animations editing with a selectable `animations-high`/`animations-low` target,
curves (bézier/spring), per-leaf tree, env editing, pending changes + Apply.
Write tests run against temp copies; the GUI writes to live files on Apply.

---

## Part of the hyprtk suite

hyprtk is one desktop kept in seven repositories: every one of them installs
or configures part of the same pywal-themed, Arch-first Hyprland setup.

| project | what it is |
| --- | --- |
| [**dotfiles**](https://github.com/hyprtk/dotfiles) | the desktop itself: the any-distro installer, the Hyprland Lua config, themes and 60+ scripts |
| [**hyprtk-bar-qt**](https://github.com/hyprtk/hyprtk-bar-qt) | the Qt6/QML (Quickshell) bar and everything it owns: launcher, notifications, tray, quick settings, desktop widgets |
| [**hyprtk-fm**](https://github.com/hyprtk/hyprtk-file-manager) | the Qt6/QML file manager, default for `Super+F` and `inode/directory` |
| [**hyprtk-editor**](https://github.com/hyprtk/hyprtk-editor) | the Qt Quick text editor, default for `text/plain` and `text/markdown` |
| [**config-manager**](https://github.com/hyprtk/hyprtk-hyprland-config-manager) | the Hyprland settings GUI, opened from the bar's Settings |
| [**hyprtk-usb**](https://github.com/hyprtk/hyprtk-usb) | writes a hyprtk ISO to a USB stick, with optional persistence |
| [**ISO creator**](https://github.com/hyprtk/Hyprtk-ISO-Creator) | builds the installable ISO: `airootfs`, package lists, first-run seed |

**This project is the Hyprland settings GUI** in that list; the desktop as a whole lives in
the [dotfiles](https://github.com/hyprtk/dotfiles) repository.
