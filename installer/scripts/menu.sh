#!/bin/bash
# menu.sh — shared gum menus for the rofi-free hyprtk scripts.
#
# Hyprland keybinds launch scripts detached (no tty), so gum cannot render.
# Source this file and call menu_choose/menu_filter/menu_confirm: when there is
# no tty the script re-launches itself inside a terminal tagged
# app-id/class "hyprtk-menu" (the dotfiles float it via hypr/windowrules.lua).
#
#   . "$(dirname "$0")/menu.sh"
#   choice=$(printf '%s\n' a b | menu_choose "Pick one")

if [ ! -t 0 ] && [ -z "${HYPRTK_MENU_IN_TERM:-}" ]; then
    export HYPRTK_MENU_IN_TERM=1
    _menu_app="hyprtk-menu"
    _menu_title="Hyprtk Menu"
    if command -v alacritty >/dev/null 2>&1; then
        exec alacritty --class "$_menu_app" -T "$_menu_title" -e "$0" "$@"
    elif command -v kitty >/dev/null 2>&1; then
        exec kitty --class="$_menu_app" -T "$_menu_title" "$0" "$@"
    elif command -v foot >/dev/null 2>&1; then
        exec foot --app-id="$_menu_app" -T "$_menu_title" "$0" "$@"
    elif command -v wezterm >/dev/null 2>&1; then
        exec wezterm start --class "$_menu_app" -- "$0" "$@"
    elif command -v xfce4-terminal >/dev/null 2>&1; then
        exec xfce4-terminal --class="$_menu_app" -T "$_menu_title" --command "$0 $*"
    elif command -v gnome-terminal >/dev/null 2>&1; then
        exec gnome-terminal --class="$_menu_app" --title "$_menu_title" -- "$0" "$@"
    elif command -v konsole >/dev/null 2>&1; then
        exec konsole -p tabtitle="$_menu_title" -e "$0" "$@"
    elif command -v terminator >/dev/null 2>&1; then
        exec terminator -T "$_menu_title" -e "$0" "$@"
    elif command -v x-terminal-emulator >/dev/null 2>&1; then
        exec x-terminal-emulator -T "$_menu_title" -e "$0" "$@"
    elif command -v xterm >/dev/null 2>&1; then
        exec xterm -T "$_menu_title" -e "$0" "$@"
    else
        echo "menu: no terminal emulator found; install alacritty or kitty" >&2
        exit 1
    fi
fi

menu_choose() {
    gum choose --height 14 --header "$1"
}

menu_filter() {
    gum filter --height 16 --header "$1"
}

menu_confirm() {
    gum confirm "$1"
}
