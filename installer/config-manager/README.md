<div align="center">

<img src="docs/branding/banner.png" alt="hyprtk-config-manager — part of the hyprtk suite" width="100%" />

[![suite](https://img.shields.io/badge/suite-hyprtk-02DEDE?style=flat-square&labelColor=05060B)](https://github.com/hyprtk)
[![version](https://img.shields.io/badge/version-0.2.5-FD4FB6?style=flat-square&labelColor=05060B)](CHANGELOG.md)
[![license](https://img.shields.io/badge/license-GPL--3.0-5FB8F5?style=flat-square&labelColor=05060B)](LICENSE)

</div>

# hyprtk-config-manager

> **Part of the hyprtk suite** — [dotfiles](https://github.com/hyprtk/dotfiles) · [bar-qt](https://github.com/hyprtk/hyprtk-bar-qt) · [file manager](https://github.com/hyprtk/hyprtk-file-manager) · [editor](https://github.com/hyprtk/hyprtk-editor) · [terminal](https://github.com/hyprtk/hyprtk-term) · [calculator](https://github.com/hyprtk/hyprtk-calc) · [screenshot](https://github.com/hyprtk/hyprtk-shot) · [recorder](https://github.com/hyprtk/hyprtk-rec) · [system manager](https://github.com/hyprtk/hyprtk-system-manager) · [config manager](https://github.com/hyprtk/hyprtk-hyprland-config-manager) · [hyprtk-usb](https://github.com/hyprtk/hyprtk-usb) · [ISO creator](https://github.com/hyprtk/Hyprtk-ISO-Creator)

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

## Branding

<img src="docs/branding/palette.png" alt="hyprtk palette: cyan #02DEDE, magenta #FD4FB6, navy #000044, ink #05060B, white #F2F6FF, muted #8A93A6" width="100%" />

The mark is the suite's **v09** direction: an oversized `ht` monogram on an ink
field, a gradient ring, and the component glyph in a badge. The wordmark is
**KoblenzSerial Bold**, converted to outlines so no font install is needed.
The banner, icon and palette are generated from the brand kit described in the
[dotfiles README](https://github.com/hyprtk/dotfiles#branding).

---

## Part of the hyprtk suite

hyprtk is one desktop kept in twelve repositories: every one of them installs
or configures part of the same pywal-themed, Arch-first Hyprland setup.

| project | what it is |
| --- | --- |
| [**dotfiles**](https://github.com/hyprtk/dotfiles) | the desktop itself: the any-distro installer, the Hyprland Lua config, themes and 60+ scripts |
| [**hyprtk-bar-qt**](https://github.com/hyprtk/hyprtk-bar-qt) | the Qt6/QML (Quickshell) bar and everything it owns: launcher, notifications, tray, quick settings, desktop widgets |
| [**hyprtk-fm**](https://github.com/hyprtk/hyprtk-file-manager) | the Qt6/QML file manager, default for `Super+F` and `inode/directory` |
| [**hyprtk-editor**](https://github.com/hyprtk/hyprtk-editor) | the Qt Quick text editor, default for `text/plain` and `text/markdown` |
| [**hyprtk-term**](https://github.com/hyprtk/hyprtk-term) | the Qt Quick terminal: libvterm core, tabs, scrollback search, pywal palette |
| [**hyprtk-calc**](https://github.com/hyprtk/hyprtk-calc) | the Qt Quick calculator: exact decimal arithmetic, three modes |
| [**hyprtk-shot**](https://github.com/hyprtk/hyprtk-shot) | the screenshot tool: frozen overlay, crop grips, annotations, window picker, pin to screen |
| [**hyprtk-rec**](https://github.com/hyprtk/hyprtk-rec) | the screen recorder: wf-recorder/wl-screenrec, mixed audio, GIF, trim, HUD |
| [**hyprtk-system-manager**](https://github.com/hyprtk/hyprtk-system-manager) | the suite's System Settings: 25 searchable panels for hardware, users, appearance and the apps |
| [**config-manager**](https://github.com/hyprtk/hyprtk-hyprland-config-manager) | the Hyprland settings GUI, opened from the bar's Settings |
| [**hyprtk-usb**](https://github.com/hyprtk/hyprtk-usb) | writes a hyprtk ISO to a USB stick, with optional persistence |
| [**ISO creator**](https://github.com/hyprtk/Hyprtk-ISO-Creator) | builds the installable ISO: `airootfs`, package lists, first-run seed |

**This project is the Hyprland settings GUI** in that list; the desktop as a whole lives in
the [dotfiles](https://github.com/hyprtk/dotfiles) repository.
