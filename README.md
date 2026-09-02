# Hyprland Dots

This is the configuration for Arch Linux, Arcolinux, Garuda, Manjaro based installations of Hyprland (Wayland) and/or XFCE (Xorg).

This will work on most flavours of Arch.


## Common Packages

- Terminal: alacritty
- Editor: nvim/ nano
- Prompt: starship
- Icons: Font Awesome
- Menus: Rofi
- Colorscheme: pywal16 (dynamic)
- Browsers: chromium (brave optional)
- Filemanager: Thunar
- Cursor: Bibata Modern Ice
- Icons: Papirus-Icon-Theme
- Virtual Machine: qemu/kvm, vmware workstation, winboat

## Hyprland

- Status Bar: waybar
- Screenshots: grim & slurp
- Clipboard Manager: cliphist
- Logout: hyprlogout
- Screenlock: swaylock-effects
- Screen Capture: wf-recorder

## Templating

Hyprland: Included is a pywal16 configuration that changes the color scheme based on a randomly selected wallpaper. 

	Keybinding SuperKey + Shift + w you can change the wallpaper.

	Keybinding SuperKey + Ctrl + w opens rofi with a list of installed wallpapers.

	Keybinding SuperKey + w opens matuwall to display all wallpapers on a film roll (Editable)

See also the .zshrc and the key bindings on Hyprland and XFCE for more alias definitions.

Hyprland: In addition, you can switch the Waybar Template

	Keybinding SUPER + CTRL + T or by pressing the _ icon under the picture icon in waybar.

The templates are available in ~/dotfiles/waybar/themes. You can add your own personal themes into this folder. The script will read in the folder structure.

## Applications

The dotfiles bundle three standalone applications, all installed from
`installer/` by `1-install.sh`. Each is a separate project that reads its own
config from `~/.config/<name>/` and is themed by pywal / the active waybar
theme.

### theme-gui

GTK4/Adwaita graphical theme manager for the Hyprland desktop. A single window
with sidebar pages for: Wallpaper, Pywal Colors, Rofi Themes, Waybar Themes,
Matuwall, Swaylock, Icons, and SDDM & GRUB.

- **Install**: `installer/theme-gui/install.sh` → `~/.local/share/theme-gui/`,
  launchers `theme-gui` / `hyprtk-themer`
- **Open**: `theme-gui` (keybind `SUPER + ALT + T`)
- **Config**: `~/.config/theme-gui/config.json`

  ```json
  {
    "last_page": "wallpaper",
    "window_width": 1100,
    "window_height": 700,
    "wallpaper_dir": "~/Pictures/Wallpapers",
    "pywal_backend": "wal"
  }
  ```

- **Theming**: applies pywal colors across the whole desktop — runs pywal,
  restarts waybar with the selected theme, recolors papirus icons, and syncs
  swaylock, rofi, matuwall, and SDDM/GRUB. Each page targets one component.

### hyprtk-menu

Whisker-style application menu (GTK3 + layer-shell) that floats over the
desktop as a popup — instant search, category sidebar, pin favorites, recents,
and power buttons.

- **Install**: `installer/hyprtk-menu/install.sh` → `~/.local/share/hyprtk-menu/`,
  launcher `hyprtk-menu`
- **Open**: `hyprtk-menu` or `hyprtk-menu --toggle` (keybind `SUPER + SPACE`)
- **Config**: `~/.config/hyprtk-menu/config.json` (auto-created)

  ```json
  {
    "position": "auto",
    "align": "left",
    "layout": "whisker",
    "width": 920,
    "height": 580,
    "sidebar_width": 180,
    "recents_width": 230,
    "show_recents": true,
    "max_recents": 10,
    "power": {
      "lock": "pidof hyprlock || hyprlock",
      "logout": "hyprshutdown",
      "reboot": "systemctl reboot",
      "shutdown": "systemctl poweroff",
      "suspend": "systemctl suspend"
    }
  }
  ```

- **Theming**: frosted glass theme driven by pywal (`~/.cache/wal/colors.sh`)
  with live color updates on wallpaper change. Matches the active waybar theme
  (reads `~/.cache/.themestyle.sh`) — dark frosted, aero glass, light, clear,
  glass, inverse, reverse, negative profiles — and re-anchors top↔bottom with
  the bar. Layouts: `whisker`, `win7`, `win11`, `plasma`.
- **Resize**: drag the corner grip to resize; drag the column dividers to
  rebalance the categories/app list/recents widths.

### hyprtk-arc-menu

Material-style radial/arc menu (GTK3 + layer-shell). A FAB-style button sits in
a configurable screen position and fans its items out on click — 180° at the
top/bottom center, 90° at corners — each item launching a command. Middle-click
anywhere on it quits the app.

- **Install**: `installer/hyprtk-arc-menu/install.sh` → `~/.local/share/hyprtk-arc-menu/`,
  launchers `hyprtk-arc-menu` (+ `-toggle`)
- **Open**: `hyprtk-arc-menu` (keybind `SUPER + CTRL + M`); toggle with
  `hyprtk-arc-menu-toggle`
- **Config**: `~/.config/hyprtk-arc-menu/config.json`

  ```json
  {
    "position": "bottom-right",
    "shape": "circle",
    "transparent": false,
    "follow_waybar": true,
    "margin": 24,
    "radius": 140,
    "fab_size": 56,
    "item_size": 48,
    "animation_time": 300,
    "items": [
      { "icon": "firefox", "command": "firefox", "tooltip": "Firefox" }
    ]
  }
  ```

- **Theming**: mirrors the active waybar theme's glass + text color and updates
  live on theme switch; keeps pywal `color5`/`color6` accents for the button and
  items even while following waybar. Options: `shape: square` (items encircle
  the button on a square perimeter), `transparent: true` (icons only, no
  backgrounds).
- **Settings**: the in-menu Settings item opens a dialog to edit everything —
  position, shape, radius/margin/sizes, animation, pywal / follow-waybar /
  transparent toggles, colors, and the item list (add/edit/remove, move
  up/down, search installed apps).

## Getting started

To make it easy for you to get started with my garuda-dots, here's a list of recommended next steps.

PLEASE BACKUP YOUR EXISTING .config WITH YOUR DOTFILES BEFORE STARTING THE SCRIPTS.


# Make sure that you're in your home directory

	git clone https://github.com/hyprtk/dotfiles.git ~/hyprtk
	cd ~/hyprtk
	sh ./1-install.sh

#Please note that every Arch Linux system is different and I cannot guarantee that everything works fine on your system.
## Screenshots & Video

Arch Linux
![MODEL](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/arch1.png)
![Model](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/arch2.png)
![Model](https://github.com/hyprtk/dotfiles/blob/main/assets/screenshots/arch3.png)
