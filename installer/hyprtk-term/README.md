<div align="center">

<img src="docs/branding/banner.png" alt="hyprtk-term — part of the hyprtk suite" width="100%" />

[![suite](https://img.shields.io/badge/suite-hyprtk-02DEDE?style=flat-square&labelColor=05060B)](https://github.com/hyprtk)
[![version](https://img.shields.io/badge/version-0.2.7-FD4FB6?style=flat-square&labelColor=05060B)](CHANGELOG.md)
[![wiki](https://img.shields.io/badge/wiki-term-C084FC?style=flat-square&labelColor=05060B)](https://github.com/hyprtk/hyprtk-term/wiki)
[![license](https://img.shields.io/badge/license-MIT-5FB8F5?style=flat-square&labelColor=05060B)](LICENSE)

</div>

# hyprtk-term

> **Part of the hyprtk suite** — [dotfiles](https://github.com/hyprtk/dotfiles) · [bar-qt](https://github.com/hyprtk/hyprtk-bar-qt) · [file manager](https://github.com/hyprtk/hyprtk-file-manager) · [editor](https://github.com/hyprtk/hyprtk-editor) · [terminal](https://github.com/hyprtk/hyprtk-term) · [calculator](https://github.com/hyprtk/hyprtk-calc) · [screenshot](https://github.com/hyprtk/hyprtk-shot) · [recorder](https://github.com/hyprtk/hyprtk-rec) · [system manager](https://github.com/hyprtk/hyprtk-system-manager) · [config manager](https://github.com/hyprtk/hyprtk-hyprland-config-manager) · [hyprtk-usb](https://github.com/hyprtk/hyprtk-usb) · [ISO creator](https://github.com/hyprtk/Hyprtk-ISO-Creator)

A fast, theme-aware terminal emulator for the hyprtk desktop — Qt Quick/QML on
the front, Python in the middle and **libvterm** (Neovim's emulator core)
underneath. It follows the wallpaper, opens in a few hundred milliseconds and
keeps a real shell honest: alt screen, truecolor, wide characters, scrollback,
mouse reporting and bracketed paste all work.

**Current version: 0.2.7** — see [CHANGELOG.md](CHANGELOG.md) and [PLAN.md](PLAN.md).

![hyprtk-term rendering a shell](docs/probe.png)
![scrollback search](docs/search.png)

## Why another terminal

The suite already ships Alacritty and Kitty. Neither knows about the bar's
theme, neither can be extended with the suite's own QML, and both are another
distro package to carry. hyprtk-term is ~2,000 lines, depends on libvterm (in
every supported archive) and paints a grid on the CPU — which the benchmarks in
[RESEARCH.md](RESEARCH.md) show is not the disadvantage it sounds like.

## Features

**Emulation**
- libvterm core: ECMA-48 / xterm, DEC private modes, alt screen, scroll regions, reflow on resize
- 16-colour palette from pywal, 256-colour cube, 24-bit truecolor
- Bold, italic, underline (single/double/curly), strike, reverse, conceal, blink
- Wide (CJK) and combining characters, emoji fallback through the system font
- **Box drawing and block elements are drawn, not typed**: every code point in
  U+2500-U+259F is painted as rectangles, lines and arcs inside its cell, so
  frames, rules and block art stay seamless whatever the font contains
- OSC 52 clipboard (both directions), OSC 0/2 window title, bracketed paste
- Mouse reporting (click, drag, any-motion) for TUI apps, with Shift to override

**Window**
- Tabs with the running program's title, middle-click to close, bell indicator
- Scrollback (10,000 lines by default) with wheel scroll and jump-to-bottom
- **Scrollback search** (`Ctrl+Shift+F`): plain or regex, case toggle, match
  count, next/previous, active match highlighted
- Linear selection, double-click word select, select-all, copy/paste
- Right-click menu, font zoom, settings sheet (`Ctrl+,`)

**Suite**
- Palette resolved from the same pywal/bar source as the editor, the file
  manager and the bar; a wallpaper change reloads every open tab
- Symbols Nerd Font chrome, v09 suite icon, `hyprtk-term.desktop`

## Install

**Arch**

```bash
sudo pacman -S libvterm python-pyside6
./install.sh
```

**Debian / Ubuntu** — `sudo apt install libvterm0 python3-pyside6.qml`
(Debian 12 and Ubuntu 24.04 package PySide6 without the QML modules; the
installer falls back to a private venv for those).

**Fedora** `sudo dnf install libvterm python3-pyside6`, **openSUSE**
`sudo zypper in libvterm0 python3-pyside6`, **Void** `sudo xbps-install libvterm
python3-PySide6`, **Alpine** `apk add libvterm py3-pyside6`.

The installer copies a tree to `~/.local/share/hyprtk-term`, links
`~/.local/bin/hyprtk-term`, writes the desktop entry with absolute paths and
registers the icon. `--system` installs under `/usr/local` for the live ISO,
`--uninstall` removes it again.

## Usage

```bash
hyprtk-term                     # login shell in ~
hyprtk-term -e btop             # run a command instead
hyprtk-term -d ~/Projects       # start somewhere else
```

| Keys | Action |
|---|---|
| `Ctrl+Shift+T` | New tab |
| `Ctrl+Shift+W` | Close tab |
| `Ctrl+Shift+N` / `Ctrl+Shift+P`, `Alt+←` / `Alt+→` | Next / previous tab |
| `Ctrl+Shift+C` / `Ctrl+Shift+V` | Copy / paste |
| `Ctrl+=` / `Ctrl+-` | Zoom |
| `Ctrl+Shift+F` | Search scrollback |
| `Ctrl+Shift+G` / `Shift+F3` | Next match |
| `Ctrl+,` | Settings |
| `Ctrl+Shift+Q` | Quit |
| `Shift`+drag | Select even when the app wants the mouse |

## Configuration

`~/.config/hyprtk-term/config.json`, written by the settings sheet:

| Key | Default | Meaning |
|---|---|---|
| `font_family` | `JetBrainsMono Nerd Font Mono` | Any installed monospace family |
| `font_size` | `11.0` | Points |
| `line_height` | `1.18` | Cell height multiplier |
| `opacity` | `0.98` | Background alpha; `< 1` makes the window translucent |
| `padding` | `6` | Pixels around the grid |
| `scrollback` | `10000` | Lines kept in history (0 disables) |
| `shell` | `""` | Blank uses `$SHELL` |
| `login_shell` | `true` | Pass `-l` to shells that support it |
| `cursor_blink` | `true` | |
| `copy_on_select` | `false` | Copy as soon as the mouse is released |

## How it works

```
PTY (pty.fork)  ->  libvterm (ctypes)  ->  row runs  ->  QPainter  ->  QML
```

- `hyprtk_term/vtcapi.py` — every libvterm signature and struct in one dict, so
  no call can be added with a missing `restype` (that bug segfaults).
- `hyprtk_term/vt.py` — the emulator: feed, damage-tracked row cache,
  scrollback ring of raw cells, key/mouse encoders, OSC 52 hooks.
- `hyprtk_term/ptyproc.py` — fork/exec, winsize, non-blocking reads.
- `hyprtk_term/terminal.py` — one QT object per tab, PTY watched by a
  `QSocketNotifier` on the GUI thread.
- `hyprtk_term/view.py` — the painted grid, selection, mouse, keys.
- `hyprtk_term/boxdraw.py` — geometry for box drawing and block elements,
  emitted through a small canvas protocol so it needs no Qt and is unit tested
  against a recording canvas.
- `hyprtk_term/qml/` — tabs, settings, theme.

Measured on this machine: 12 MB/s parse throughput, ~2 ms to re-read an 80x24
grid, ~3 ms to paint it. Numbers and method in [RESEARCH.md](RESEARCH.md).

## Development

```bash
make test     # 122 unit tests, no display needed
make qa       # tests + qmllint + headless boot + installer round-trip
make shot     # offscreen screenshot to docs/probe.png
make run
```

## License

MIT. Part of the hyprtk suite.

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

hyprtk is one desktop kept in nine repositories: every one of them installs
or configures part of the same pywal-themed, Arch-first Hyprland setup.

| project | what it is |
| --- | --- |
| [**dotfiles**](https://github.com/hyprtk/dotfiles) | the desktop itself: the any-distro installer, the Hyprland Lua config, themes and 60+ scripts |
| [**hyprtk-bar-qt**](https://github.com/hyprtk/hyprtk-bar-qt) | the Qt6/QML (Quickshell) bar and everything it owns: launcher, notifications, tray, quick settings, desktop widgets |
| [**hyprtk-fm**](https://github.com/hyprtk/hyprtk-file-manager) | the Qt6/QML file manager, default for `Super+F` and `inode/directory` |
| [**hyprtk-editor**](https://github.com/hyprtk/hyprtk-editor) | the Qt Quick text editor, default for `text/plain` and `text/markdown` |
| [**hyprtk-term**](https://github.com/hyprtk/hyprtk-term) | the Qt Quick terminal: libvterm core, tabs, scrollback search, pywal palette |
| [**hyprtk-calc**](https://github.com/hyprtk/hyprtk-calc) | the Qt Quick calculator: exact decimal arithmetic, three modes |
| [**config-manager**](https://github.com/hyprtk/hyprtk-hyprland-config-manager) | the Hyprland settings GUI, opened from the bar's Settings |
| [**hyprtk-usb**](https://github.com/hyprtk/hyprtk-usb) | writes a hyprtk ISO to a USB stick, with optional persistence |
| [**ISO creator**](https://github.com/hyprtk/Hyprtk-ISO-Creator) | builds the installable ISO: `airootfs`, package lists, first-run seed |

**This project is the terminal** in that list; the desktop as a whole lives in
the [dotfiles](https://github.com/hyprtk/dotfiles) repository.
