# hyprtk dots

A themed **Hyprland** desktop for Arch-based Linux, with **XFCE** as a fallback. One installer, 11 distros, one pywal-powered color scheme.

## Install

```bash
git clone https://github.com/hyprtk/dotfiles.git ~/hyprtk
cd ~/hyprtk
sh ./1-install.sh
```

Back up `~/.config` first. The installer auto-detects your distro and guides you through the rest.

## Includes

- Waybar (switchable themes) · Rofi · Alacritty · Neovim · Starship
- pywal16 dynamic theming · Matuwall wallpaper picker
- grim/slurp · cliphist · wf-recorder · swaylock-effects · hyprlogout
- Thunar · Papirus icons · Bibata cursor · Brave / Chromium
- QEMU/KVM · VMware

## Apps

| App | Purpose | Open |
| --- | --- | --- |
| theme-gui | Theme manager (wallpapers, colors, waybar, icons, SDDM/GRUB) | `Super + Alt + T` |
| hyprtk-menu | App menu (4 layouts) | `Super + Space` |
| hyprtk-arc-menu | Radial launcher | `Super + Ctrl + M` |

## Keybinds

`Super` = Windows key.

| Key | Action |
| --- | --- |
| `Super + Return` | Terminal |
| `Super + D` | App menu |
| `Super + Q` | Close window |
| `Super + F` | File manager |
| `Super + W` | Wallpaper picker |
| `Super + Shift + W` | Random wallpaper |
| `Super + Ctrl + W` | Wallpaper list |
| `Super + Ctrl + T` | Switch waybar theme |
| `Super + Print` | Screenshot |
| `Super + Shift + Print` | Screen record |
| `Super + Ctrl + Q` | Power menu |
| `Super + 1..0` | Workspaces (`Shift` to move window) |

## License

[GPL-2.0](LICENSE)