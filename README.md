<div align="center">

# hyprtk dots

A single installer for a fully themed **Hyprland (Wayland)** desktop on any Arch-based Linux distribution — with **XFCE (Xorg)** kept as a safety net.

**11 distros. One install. One pywal-powered theme.**

`Arch` · `Archbang` · `Archcraft` · `Archman` · `BSLX` · `CachyOS` · `EndeavourOS` · `Garuda` · `Kiro` · `Manjaro` · `RebornOS`

---

[Install](#install) · [Features](#features) · [Keybindings](#keybindings) · [Applications](#applications) · [Gallery](#gallery)

</div>

---

## What is this?

A curated, consistent desktop configuration that replaces the default look and feel of Arch Linux with a polished Hyprland setup. One wallpaper drives every colour on screen via **pywal16** — waybar, rofi, the app menu, the lock screen and even your icons all stay in sync.

- **Wayland first** — Hyprland with a floating/split hybrid workflow
- **Xorg fallback** — XFCE stays installed as a safety net
- **Auto-detected distro** — the installer detects your OS and applies the right tweaks
- **No manual colour config** — pywal generates a full palette from your wallpaper

## Install

> Back up your existing `~/.config` before running.

```bash
git clone https://github.com/hyprtk/dotfiles.git ~/hyprtk
cd ~/hyprtk
sh ./1-install.sh
```

The installer is a guided `gum` TUI: it detects your distro, then asks about
package groups, dotfiles and services before installing everything.

> Every Arch-based system is different — results can vary. Review the prompts before accepting.

## Features

| Area | What you get |
| --- | --- |
| **Terminal** | Alacritty + starship prompt |
| **Editor** | Neovim (Vim fallback) |
| **App launcher** | Rofi (plus three bundled GTK menus, see below) |
| **Status bar** | Waybar — 5+ switchable frosted-glass themes |
| **Theming** | pywal16, live, from your wallpaper |
| **Wallpaper** | Matuwall film-strip picker + rofi list + random |
| **Screenshots** | grim & slurp |
| **Screen recording** | wf-recorder |
| **Clipboard** | cliphist |
| **Screen lock** | swaylock-effects |
| **Logout** | hyprlogout |
| **Files** | Thunar |
| **Icons** | Papirus (recolored to match the theme) |
| **Cursor** | Bibata Modern Ice |
| **Browser** | Brave / Chromium |
| **VMs** | QEMU/KVM, VMware |

## Keybindings

`Super` = the Windows key.

### Apps & windows

| Key | Action |
| --- | --- |
| `Super + Return` | Terminal (Alacritty) |
| `Super + Q` | Close window |
| `Super + D` | App menu (rofi) |
| `Super + F` | File manager (Thunar) |
| `Super + B` / `Super + Ctrl + B` | Brave / Chromium |
| `Super + X` | Exit session |
| `Super + M` | Toggle fullscreen |
| `Super + V` | Float / resize / center window |
| `Super + J` / `Super + K` | Toggle / swap split |

### Workspaces

| Key | Action |
| --- | --- |
| `Super + 1..0` | Switch to workspace |
| `Super + Shift + 1..0` | Move window to workspace |

### Wallpaper & themes

| Key | Action |
| --- | --- |
| `Super + W` | Matuwall wallpaper picker |
| `Super + Shift + W` | Random wallpaper |
| `Super + Ctrl + W` | Wallpaper list (rofi) |
| `Super + Ctrl + T` | Switch waybar theme |
| `Super + Shift + B` | Reload waybar |

### Media & system

| Key | Action |
| --- | --- |
| `Super + Print` / `Super + P` | Screenshot |
| `Super + Shift + Print` | Start screen recording |
| `Super + Alt + Print` | Stop screen recording |
| `Super + C` | Color picker (hyprpicker) |
| `Super + Ctrl + Q` | Power menu (hyprlogout) |
| `Super + R` | Reload Hyprland config |

## Applications

Three standalone GTK apps ship with the installer, each with its own project, config and pywal theming:

| App | What it does | Open with |
| --- | --- | --- |
| **theme-gui** | Graphical theme manager — wallpapers, pywal, rofi, waybar, icons, swaylock, SDDM/GRUB | `Super + Alt + T` |
| **hyprtk-menu** | Whisker-style app menu — search, favorites, recents, power buttons | `Super + Space` |
| **hyprtk-arc-menu** | Material-style radial launcher | `Super + Ctrl + M` |

See each app's section below for install and config details.

### theme-gui

A single GTK4 window with sidebar pages for every theming component. Apply a wallpaper and it runs the full pipeline: pywal, waybar restart, icon recolor, swaylock, rofi, matuwall and SDDM/GRUB.

- Config: `~/.config/theme-gui/config.json`

### hyprtk-menu

A floating popup menu with instant search, category sidebar, pinned favorites, recents and a power bar. Four layouts — `whisker`, `win7`, `win11`, `plasma` — switchable from its settings window. Drag the corner to resize, drag the dividers to rebalance columns.

- Config: `~/.config/hyprtk-menu/config.json`

### hyprtk-arc-menu

A FAB-style button that fans its items out on click — 180° at top/bottom center, 90° at corners. Circle or square shapes, transparent mode, live waybar theming. Middle-click anywhere to quit.

- Config: `~/.config/hyprtk-arc-menu/config.json`

## Gallery

| | | |
| --- | --- | --- |
| ![Arch](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/arch1.png) | ![Arch](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/arch2.png) | ![Arch](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/arch3.png) |
| ![EndeavourOS](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/endeavour1.png) | ![EndeavourOS](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/endeavour2.png) | ![EndeavourOS](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/endeavour3.png) |
| ![Garuda](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/garuda1.png) | ![Garuda](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/garuda2.png) | ![Garuda](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/garuda3.png) |

More screenshots per distro live in [`assets/screenshots/`](https://github.com/hyprtk/dotfiles/tree/main/assets/screenshots).

## License

[GPL-2.0](LICENSE)