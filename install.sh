#!/usr/bin/env bash

MAGENTA='\033[35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GUM="$SCRIPT_DIR/standalone/gum"

gum() {
    "$GUM" "$@"
}

check_gum() {
    if [ -x "$GUM" ]; then
        return
    fi
    if command -v gum &>/dev/null; then
        GUM="$(command -v gum)"
        return
    fi
    echo -e "${CYAN}gum not found. Installing...${NC}"
    sudo pacman -S --noconfirm gum
    GUM="$(command -v gum)"
}

check_gum
clear

gum style \
    --border-foreground 5 \
    --border double \
    --align center \
    --padding "1 3" \
    --margin "1 0" \
    "$(printf "${CYAN}HYPRTK DOTFILES${NC}")" \
    "$(printf "${CYAN}Hyprland Desktop Environment Installer${NC}")" \
    "" \
    "$(printf "${RED}DISCLAIMER${NC}")" \
    "$(printf "${WHITE}Installing these dotfiles may alter your system${NC}")" \
    "$(printf "${WHITE}configuration. A clean install is recommended for${NC}")" \
    "$(printf "${WHITE}best results.${NC}")"

gum style --foreground 5 --bold --padding "1 0" "Select your distribution:"

DISTROS=(
    "1) Arch Linux"
    "2) ArchBANG Linux"
    "3) Archcraft Linux"
    "4) Archman Linux"
    "5) BlueStar Linux"
    "6) CachyOS"
    "7) EndeavourOS"
    "8) Garuda Linux"
    "9) Kiro Linux (ArcoLinux Rebrand)"
    "10) Manjaro Linux"
    "11) My Personal Dotfiles"
    "12) RebornOS"
    "13) Exit"
)

SELECTED=$(gum choose \
    --height=13 \
    --cursor.foreground=5 \
    --selected.foreground=0 \
    --selected.background=5 \
    --item.foreground=6 \
    "${DISTROS[@]}")

if [[ -z "$SELECTED" || "$SELECTED" == "13) Exit" ]]; then
    printf '\033[1A\033[K'
    echo -e "${MAGENTA}Installation cancelled.${NC}"
    exit 0
fi

DOTS="${SELECTED%%)*}"

if ! gum confirm --prompt.foreground=5 "Proceed with installation?"; then
    echo -e "${MAGENTA}Installation cancelled.${NC}"
    exit 0
fi

case $DOTS in
1)  REPO="arch-dots" ;;
2)  REPO="archbang-dots" ;;
3)  REPO="archcraft-dots" ;;
4)  REPO="archman-dots" ;;
5)  REPO="bslx-dots" ;;
6)  REPO="cachy-dots" ;;
7)  REPO="endeavour-dots" ;;
8)  REPO="garuda-dots" ;;
9)  REPO="kiro-dots" ;;
10) REPO="manjaro-dots" ;;
11) REPO="my-dots" ;;
12) REPO="reborn-dots" ;;
*)  REPO="arch-dots" ;;
esac

gum spin --spinner dot --title "Cloning $REPO..." -- git clone "https://github.com/hyprtk/$REPO.git" ~/hyprtk
cd ~/hyprtk
sh ./1-install.sh

echo
gum style \
    --foreground 6 \
    --border-foreground 5 \
    --border double \
    --padding "1 3" \
    --margin "1 0" \
    "Installation complete" \
    "github.com/hyprtk/dotfiles"
