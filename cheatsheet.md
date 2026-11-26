# Hyprland CheatSheet #

# NVIDIA Users

if you are using an NVIDIA GPU or a laptop with NVIDIA GPU,
please read the ~/hyprtk/hypr/nvidia.lua for setup and configuration of your GPU

# AMDGPU Users

please install the xf86-video-amdgpu drivers and add to the modules section of your /etc/mkinicpio.conf
and run sudo mkinitcpio -P (Please ensure you have your kernels headers installed)

# Quick Keybinds

  Super = Windows Key

# common operations
  Super          Return   *term* (`hyprtk-term`, alacritty fallback)
  Super          q        *quit* (kill focused window)
  Super          d        *show app launcher* (`hyprtk-bar-qt-launcher-toggle`)
  Super   Ctrl   q        *show hyprlogout* (lock/suspend/logout/reboot/shutdown)

# screenshot  (`hyprtk-shot`)
  Super PrintSrc          *region screenshot* — drag on the frozen frame
  Super Shift PrintSrc    *start / stop screen recording* (`hyprtk-rec`)
  Super Alt   PrintSrc    *stop screen recording*

in the overlay: Enter saves+copies, Ctrl+S saves, Ctrl+C copies, Esc cancels,
Ctrl+Z undo, and V/P/L/A/R/E/H/M/T/B/X pick the tools (select, pen, line, arrow,
rect, ellipse, highlight, step, text, blur, pixelate)

screenshots go to ~/Pictures/Screenshots, recordings to ~/Videos/Recordings

# application shortcuts 
  Ctrl    Alt U           *pavucontrol*
  Ctrl    ALT P           *pamac-manager*
  Super   F               *file manager* (`hyprtk-fm`)
  Super   N               *calculator* (`hyprtk-calc`)
  Super   PrintSrc        *screenshot* (`hyprtk-shot`)
  Super Shift PrintSrc    *record screen* (`hyprtk-rec`)
  Super   B               *browser* (`brave`)
  Super   Ctrl B          *browser* (`chromium`)

# container layout
 
  Super   V                   *toggle tiling/floating mode*
  Super   left mouse button   *move window*
  Super   right mouse button  *resize window*

# workspaces
  Super         1 .. 0    *switch to workspace 1 .. 10*
  Super  Shift  1 .. 0    *move container to workspace 1 .. 10*

# notes
  - *Hyprland* configuration files are in `~/.config/hypr/`.
    Read all the files with the editor of your choice.
    More keybindings are included in the config.
  - *hyprtk-bar-qt* is the taskbar (right-click for bar settings / theme).
    Notifications use its built-in center (bell button).
  - *Multimedia keys* - may not work for every keyboard
    may need to hold down the function (`fn`) key
  - Follow the wiki - https://wiki.hyprland.org/
  - Follow the github - https://github.com/hyprwm/Hyprland

# user githubs
  - https://github.com/mylinuxforwork/dotfiles
  - https://github.com/JaKooLit/Hyprland-Dots
  - https://github.com/eldermf/bspwm-hyprland
  - https://github.com/lauroro/hyprland-dots
  - https://github.com/eneshecan/dotfiles

# share your own files on github 
  - so we can all learn
  - and you have a backup
| `monitor-automode --status` | Show what the PiP/PBP mode fallback sees |
