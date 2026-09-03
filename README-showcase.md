<div align="center">

# ✨ hyprtk dots

### A complete, themed Hyprland desktop for every Arch-based distro

![GitHub repo](https://img.shields.io/badge/distros-11-%23c084fc?style=for-the-badge)
![Wayland](https://img.shields.io/badge/Wayland-Hyprland-%2322d3ee?style=for-the-badge)
![Theming](https://img.shields.io/badge/theming-pywal16-%23a6e3a1?style=for-the-badge)
![License](https://img.shields.io/badge/license-GPL--2.0-%23cba6f7?style=for-the-badge)

One installer. One wallpaper. A whole desktop that follows your colours.

</div>

---

## 🚀 Features at a glance

| | | |
| --- | --- | --- |
| 🎨 **pywal16 theming** | Every element recolors from one wallpaper — live | |
| 🖥️ **Hyprland + XFCE** | Wayland-first with an Xorg safety net | |
| 📦 **11 distros** | Arch, Archbang, Archcraft, Archman, BSLX, CachyOS, EndeavourOS, Garuda, Kiro, Manjaro, RebornOS | |
| ⚙️ **Guided TUI installer** | gum-based, distro auto-detection | |
| 🧊 **Frosted glass UI** | Switchable waybar themes + matching menus | |
| 📦 **3 bundled apps** | theme-gui, hyprtk-menu, hyprtk-arc-menu | |

---

## ⚡ Quick start

> **Back up your `~/.config` first.**

```bash
git clone https://github.com/hyprtk/dotfiles.git ~/hyprtk
cd ~/hyprtk
sh ./1-install.sh
```

The installer detects your distro, then walks you through package groups,
dotfiles and services. Every prompt is skippable.

---

## 🧰 What's inside

**Core stack**

- **Terminal** — Alacritty
- **Editor** — Neovim
- **Prompt** — Starship
- **Launcher** — Rofi
- **Status bar** — Waybar (5+ frosted-glass themes)
- **Colorscheme** — pywal16 (dynamic)
- **File manager** — Thunar
- **Browser** — Brave / Chromium
- **Icons** — Papirus, recolored to your theme
- **Cursor** — Bibata Modern Ice

**Hyprland extras**

- Screenshots: grim & slurp
- Clipboard: cliphist
- Screen record: wf-recorder
- Screen lock: swaylock-effects
- Logout: hyprlogout
- Wallpapers: matuwall + rofi picker + random
- Virtualization: QEMU/KVM, VMware

---

## ⌨️ Keybindings

`Super` = Windows key.

### Everyday

| Key | Action |
| --- | --- |
| `Super + Return` | Terminal |
| `Super + Q` | Close window |
| `Super + D` | App menu |
| `Super + F` | Files (Thunar) |
| `Super + Space` | hyprtk-menu |
| `Super + Ctrl + M` | hyprtk-arc-menu |

### Wallpaper & themes

| Key | Action |
| --- | --- |
| `Super + W` | Matuwall picker |
| `Super + Shift + W` | Random wallpaper |
| `Super + Ctrl + W` | Rofi wallpaper list |
| `Super + Ctrl + T` | Switch waybar theme |
| `Super + Alt + T` | theme-gui theme manager |

### Media & system

| Key | Action |
| --- | --- |
| `Super + Print` | Screenshot |
| `Super + Shift + Print` | Record screen |
| `Super + Alt + Print` | Stop recording |
| `Super + C` | Color picker |
| `Super + Ctrl + Q` | Power menu |
| `Super + R` | Reload Hyprland |
| `Super + X` | Exit session |

### Workspaces

| Key | Action |
| --- | --- |
| `Super + 1..0` | Switch workspace |
| `Super + Shift + 1..0` | Move window to workspace |

---

## 📦 Bundled applications

### theme-gui — graphical theme manager
One window to theme everything: wallpapers, pywal colors, rofi, waybar, matuwall, swaylock, icons, and SDDM/GRUB.

### hyprtk-menu — modern app menu
Whisker-style popup with search, favorites, recents and power buttons. Four layouts: `whisker`, `win7`, `win11`, `plasma`.

### hyprtk-arc-menu — radial launcher
Material-style FAB that fans apps out on click. Circle or square, transparent mode, pywal + waybar aware.

---

## 🖼️ Gallery

<div align="center">

| Arch | EndeavourOS | Garuda |
| --- | --- | --- |
| ![arch1](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/arch1.png) | ![endeavour1](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/endeavour1.png) | ![garuda1](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/garuda1.png) |

</div>

More screenshots for every distro in [`assets/screenshots/`](https://github.com/hyprtk/dotfiles/tree/main/assets/screenshots).

---

## 🤝 Contributing

Issues and pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

- Keep the pywal pipeline intact — one wallpaper drives all colors.
- Keep both Hyprland **and** XFCE — the Xorg fallback is intentional.

## 📄 License

[GPL-2.0](LICENSE) — free to use, modify and share.