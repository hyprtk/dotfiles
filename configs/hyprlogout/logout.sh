#!/bin/bash
#
#
#                                                                        
# by hyprtk (Kori Tk) (2026)
# -----------------------------------------------------
# Power menu (gum). Launched from a keybind, so menu.sh re-opens it in a
# floating terminal tagged "hyprtk-menu" when there is no tty.
. "$HOME/hyprtk/installer/scripts/menu.sh"

uptime="$(uptime -p | sed -e 's/up //g')"

choice=$(printf '%s\n' \
    "Lock" "Suspend" "Log out" "Hibernate" "Reboot" "Shut down" \
    | menu_choose "Power · up $uptime")

[ -n "$choice" ] || exit 0

case "$choice" in
    Lock)
        ~/.config/hypr/scripts/lock.sh
        ;;
    Suspend)
        menu_confirm "Suspend now?" || exit 0
        mpc -q pause 2>/dev/null || true
        amixer set Master mute 2>/dev/null || true
        systemctl suspend
        ;;
    "Log out")
        menu_confirm "End your session?" || exit 0
        hyprctl dispatch 'hl.dsp.exit()'
        ;;
    Hibernate)
        menu_confirm "Hibernate now?" || exit 0
        systemctl hibernate
        ;;
    Reboot)
        menu_confirm "Restart the computer?" || exit 0
        systemctl reboot
        ;;
    "Shut down")
        menu_confirm "Power off the computer?" || exit 0
        systemctl poweroff
        ;;
esac
