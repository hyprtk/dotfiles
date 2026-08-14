#!/bin/bash
# ── Unified hyprtk installer (gum TUI) ────────────────────────────────────
# Merges the installers of all 11 supported distros (arch, archbang, archcraft,
# archman, bslx, cachy, endeavour, garuda, kiro, manjaro, reborn).
# Per-distro hooks live in installer/steps/<distro>.sh and are sourced here.
# Uses gum for TUI. Password entry remains functional via native sudo prompts.
# ──────────────────────────────────────────────────────────────────────────

# ── Color variables ────────────────────────────────────────────────────────
MAGENTA='\033[35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Script directory detection ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Installation log ──────────────────────────────────────────────────────
LOG_FILE="$SCRIPT_DIR/install.log"
log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" >> "$LOG_FILE"
}

# Initialize log
: > "$LOG_FILE"
log "=== hyprtk installation started ==="
log "Script directory: $SCRIPT_DIR"

# ── Gum setup ──────────────────────────────────────────────────────────────
GUM="$SCRIPT_DIR/installer/standalone/gum"

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

# ── Helpers ────────────────────────────────────────────────────────────────
_box() {
    $GUM style \
        --border-foreground 5 \
        --border double \
        --align center \
        --padding "1 3" \
        --margin "1 0" \
        "$@"
}

_step() {
    clear
    _box "$(printf "${CYAN}%s${NC}" "$1")"
    echo ""
    log "STEP: $1"
}

_ok() {
    echo -e "${CYAN}  ✓ ${WHITE}$1${NC}"
    log "OK: $1"
}

_warn() {
    echo -e "${YELLOW}  ! ${WHITE}$1${NC}"
    log "WARN: $1"
}

_fail() {
    echo -e "${RED}  ✗ ${WHITE}$1${NC}"
    log "FAIL: $1"
}

die() {
    _fail "$1"
    log "FATAL: $1"
    exit 1
}

_spin() {
    local title="$1"
    local cmd="$2"
    local logfile="$3"
    log "SPIN: $title"
    $GUM spin --spinner dot --title "$title" -- bash -c "$cmd >> '$logfile' 2>&1"
    local rc=$?
    if [ $rc -ne 0 ]; then
        log "SPIN FAILED (exit $rc): $title"
    else
        log "SPIN OK: $title"
    fi
    return $rc
}

_run() {
    local title="$1"
    local cmd="$2"
    local logfile="$3"
    log "RUN: $title"
    echo -e "${CYAN}  → ${WHITE}$title${NC}"
    bash -c "$cmd >> '$logfile' 2>&1"
    local rc=$?
    if [ $rc -ne 0 ]; then
        log "RUN FAILED (exit $rc): $title"
    else
        log "RUN OK: $title"
    fi
    return $rc
}

# ── Preflight ──────────────────────────────────────────────────────────────
check_gum
clear

_box \
    "$(printf "${CYAN}HYPRTK DOTFILES${NC}")" \
    "$(printf "${CYAN}Hyprland Desktop Environment Installer${NC}")" \
    "" \
    "$(printf "${RED}DISCLAIMER${NC}")" \
    "$(printf "${WHITE}Installing these dotfiles may alter your system${NC}")" \
    "$(printf "${WHITE}configuration. A clean install is recommended for${NC}")" \
    "$(printf "${WHITE}best results.${NC}")"

echo ""
echo -e "${WHITE}  You will be asked for your Root password to proceed.${NC}"
echo ""

# ── Distro detection ──────────────────────────────────────────────────────
DISTRO=""
DISTRO_NAME=""
DISTRO_VERSION=""

_detect_distro() {
    local distro_id="" distro_name="" distro_version="" distro_pretty=""

    if [ -f /etc/os-release ]; then
        distro_id=$(grep -E '^ID=' /etc/os-release | head -1 | cut -d= -f2 | tr -d '"')
        distro_name=$(grep -E '^NAME=' /etc/os-release | head -1 | cut -d= -f2 | tr -d '"')
        distro_version=$(grep -E '^VERSION_ID=' /etc/os-release | head -1 | cut -d= -f2 | tr -d '"')
        distro_pretty=$(grep -E '^PRETTY_NAME=' /etc/os-release | head -1 | cut -d= -f2 | tr -d '"')
    fi

    # Handle "Hyprtk on (Arch Linux)" format — extract the distro name
    local clean_name="${distro_pretty:-$distro_name}"
    clean_name="${clean_name#Hyprtk on }"
    clean_name="${clean_name#Hyprtk on }"
    clean_name="${clean_name#(}"
    clean_name="${clean_name%)}"
    clean_name=$(echo "$clean_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Map ID to internal distro name
    DISTRO=""
    case "$distro_id" in
        arch)                  DISTRO=arch ;;
        archbang)              DISTRO=archbang ;;
        archcraft)             DISTRO=archcraft ;;
        archman)               DISTRO=archman ;;
        bluestar|bslx)         DISTRO=bslx ;;
        cachyos|cachy)         DISTRO=cachy ;;
        endeavour|endeavouros) DISTRO=endeavour ;;
        garuda)                DISTRO=garuda ;;
        kiro)                  DISTRO=kiro ;;
        manjaro)               DISTRO=manjaro ;;
        reborn|rebornos)       DISTRO=reborn ;;
    esac

    DISTRO_NAME="$clean_name"
    DISTRO_VERSION="${distro_version:-N/A}"
}

_detect_distro

# Show detection result if found
if [ -n "$DISTRO" ]; then
    _box \
        "$(printf "${CYAN}DISTRO DETECTED${NC}")" \
        "" \
        "$(printf "${WHITE}Name:     ${CYAN}%s${NC}" "$DISTRO_NAME")" \
        "$(printf "${WHITE}ID:       ${CYAN}%s${NC}" "$DISTRO")" \
        "$(printf "${WHITE}Version:  ${CYAN}%s${NC}" "$DISTRO_VERSION")"
    echo ""
    log "Distro detected: $DISTRO_NAME ($DISTRO) v$DISTRO_VERSION"
fi

# Manual selection if auto-detect failed
if [ -z "$DISTRO" ]; then
    _warn "Could not auto-detect distro from /etc/os-release"
    echo ""

    DISTROS=(
        "Arch Linux"
        "ArchBANG Linux"
        "Archcraft Linux"
        "Archman Linux"
        "BlueStar Linux"
        "CachyOS"
        "EndeavourOS"
        "Garuda Linux"
        "Kiro Linux"
        "Manjaro Linux"
        "RebornOS"
    )

    $GUM style --foreground 5 --bold --padding "1 0" "Select your distribution:"

    SELECTED=$($GUM choose \
        --height=13 \
        --cursor.foreground=5 \
        --selected.foreground=0 \
        --selected.background=5 \
        --item.foreground=6 \
        "${DISTROS[@]}")

    if [[ -z "$SELECTED" ]]; then
        echo -e "${MAGENTA}  Installation cancelled.${NC}"
        log "Installation cancelled by user"
        exit 0
    fi

    case "$SELECTED" in
        "Arch Linux")       DISTRO=arch ;;
        "ArchBANG Linux")   DISTRO=archbang ;;
        "Archcraft Linux")  DISTRO=archcraft ;;
        "Archman Linux")    DISTRO=archman ;;
        "BlueStar Linux")   DISTRO=bslx ;;
        "CachyOS")          DISTRO=cachy ;;
        "EndeavourOS")      DISTRO=endeavour ;;
        "Garuda Linux")     DISTRO=garuda ;;
        "Kiro Linux")       DISTRO=kiro ;;
        "Manjaro Linux")    DISTRO=manjaro ;;
        "RebornOS")         DISTRO=reborn ;;
    esac
    DISTRO_NAME="$SELECTED"
fi

# Normalise: accept "*-dots" style input
DISTRO="${DISTRO%-dots}"

# Validate
case "$DISTRO" in
    arch|archbang|archcraft|archman|bslx|cachy|endeavour|garuda|kiro|manjaro|reborn) ;;
    *) die "unsupported distro '$DISTRO'" ;;
esac

_ok "Target distro: $DISTRO_NAME ($DISTRO)"

# Confirm before proceeding
if ! $GUM confirm --prompt.foreground=5 "Proceed with $DISTRO installation?"; then
    echo -e "${MAGENTA}  Installation cancelled.${NC}"
    log "Installation cancelled by user"
    exit 0
fi

# Source distro-specific hooks
STEPS="$SCRIPT_DIR/installer/steps/$DISTRO.sh"
if [ -f "$STEPS" ]; then
    source "$STEPS"
    log "Sourced distro hooks: $STEPS"
fi

# ── Pre-install (distro-specific cleanup) ─────────────────────────────────
_step "Removing leftover Packages"
if type pre_install >/dev/null 2>&1; then
    pre_install
else
    sudo pacman -Rns plasma-meta kde-applications-meta --noconfirm 2>/dev/null
    sudo pacman -Rns plasma kde-applications --noconfirm 2>/dev/null
fi
_ok "Leftover packages removed"

# ── Load libraries ────────────────────────────────────────────────────────
_step "Loading Installation Libraries"
source "$SCRIPT_DIR/installer/scripts/library.sh"
_ok "Library loaded"

# ── Timezone ──────────────────────────────────────────────────────────────
echo ""
sh "$SCRIPT_DIR/installer/scripts/set-timezone.sh" 2>/dev/null
_ok "Timezone configured"

# ── Install Yay ───────────────────────────────────────────────────────────
_step "Installing Yay"
if sudo pacman -Qs yay > /dev/null 2>&1; then
    _ok "yay already installed"
else
    _spin "Installing yay..." "_installPackagesPacman base-devel && git clone https://aur.archlinux.org/yay-git.git ~/Downloads/yay-git && cd ~/Downloads/yay-git && makepkg -si --noconfirm && cd $SCRIPT_DIR" "$LOG_FILE"
    _ok "yay installed"
fi

# ── Confirm start ─────────────────────────────────────────────────────────
if ! $GUM confirm --prompt.foreground=5 "Start the installation now?"; then
    echo -e "${MAGENTA}  Installation cancelled.${NC}"
    log "Installation cancelled by user"
    exit 0
fi

# ── Graphics card ─────────────────────────────────────────────────────────
_step "Graphics Card Setup"
_spin "Configuring graphics card..." "sh $SCRIPT_DIR/hypr/packages/graphics-card.sh" "$LOG_FILE"
_ok "Graphics card configured"

# ── Confirm core apps ────────────────────────────────────────────────────
if ! $GUM confirm --prompt.foreground=5 "Install core apps now?"; then
    echo -e "${MAGENTA}  Installation aborted.${NC}"
    log "Installation aborted by user"
    exit 0
fi

# ── Core packages ─────────────────────────────────────────────────────────
_step "Installing Core Packages"
for pkg in hyprland xfce4 filetools webtools printers network media terminaltools systemtools system hyprviz sddm-check sddmgrub matuwall; do
    _spin "Installing $pkg..." "sh $SCRIPT_DIR/hypr/packages/$pkg.sh" "$LOG_FILE"
    _ok "$pkg installed"
done

_spin "Installing awww wrapper..." "sh $SCRIPT_DIR/installer/scripts/awww-wrapper.sh" "$LOG_FILE"
_ok "awww wrapper installed"

if type grudupdater >/dev/null 2>&1; then
    _spin "Running grub updater..." "grudupdater" "$LOG_FILE"
fi

# ── Pywal16 ───────────────────────────────────────────────────────────────
_step "Installing Pywal16"
if [ -f /usr/bin/wal ]; then
    _ok "pywal16 already installed"
else
    _spin "Installing pywal16..." "yay --noconfirm -S python-pywal16-git" "$LOG_FILE"
    _ok "pywal16 installed"
fi

# ── Wallpapers ────────────────────────────────────────────────────────────
_step "Installing Wallpapers"
_spin "Installing wallpapers..." "sh $SCRIPT_DIR/hypr/packages/wallpapers.sh" "$LOG_FILE"
_ok "Wallpapers installed"

# ── Fonts ─────────────────────────────────────────────────────────────────
_step "Installing Fonts"
_spin "Installing fonts..." "sh $SCRIPT_DIR/hypr/packages/fonts.sh" "$LOG_FILE"
_ok "Fonts installed"

# ── Icons root ────────────────────────────────────────────────────────────
_step "Installing Icons (root)"
_spin "Installing Papirus icons for root..." "wget -qO- https://raw.githubusercontent.com/PapirusDevelopmentTeam/papirus-icon-theme/master/install.sh | DESTDIR=/root/.local/share/icons sh" "$LOG_FILE"
_ok "Icons installed for root"

# ── Init pywal16 ─────────────────────────────────────────────────────────
_step "Initiating Pywal16"
_spin "Initializing pywal16..." "wal -i $SCRIPT_DIR/assets/Wallpapers/default.png" "$LOG_FILE"
_ok "pywal16 initiated"

_spin "Setting default wallpaper..." "cp $SCRIPT_DIR/assets/Wallpapers/default.png ~/.cache/current-wallpaper.png && sudo cp ~/.cache/current-wallpaper.png /root/.cache/current-wallpaper.png" "$LOG_FILE"
if type grub_wallpaper >/dev/null 2>&1; then
    _spin "Updating grub wallpaper..." "grub_wallpaper" "$LOG_FILE"
fi
_spin "Updating user directories..." "xdg-user-dirs-update --force && xdg-user-dirs-gtk-update --force" "$LOG_FILE"
_ok "Default wallpaper set"

# ── Confirm Hyprland config ──────────────────────────────────────────────
if ! $GUM confirm --prompt.foreground=5 "Configure Hyprland now?"; then
    echo -e "${MAGENTA}  Hyprland configuration skipped.${NC}"
    log "Hyprland configuration skipped by user"
else
    # ── Thunar xfconf ────────────────────────────────────────────────────
    _step "Launching Thunar to generate xfconf"
    _spin "Generating xfconf..." "thunar & sleep 3 && killall thunar" "$LOG_FILE"
    _ok "Thunar xfconf generated"

    # ── Bluetooth ────────────────────────────────────────────────────────
    _step "Enabling Bluetooth"
    _spin "Enabling bluetooth..." "sudo systemctl start bluetooth && sudo systemctl enable bluetooth" "$LOG_FILE"
    _ok "Bluetooth enabled"

    # ── Cockpit / os-release ─────────────────────────────────────────────
    _step "Enabling Cockpit"
    if type install_os_release >/dev/null 2>&1; then
        _spin "Installing os-release..." "install_os_release" "$LOG_FILE"
    else
        _spin "Copying os-release..." "sudo cp $SCRIPT_DIR/installer/os-release/os-release-$DISTRO /usr/lib/" "$LOG_FILE"
    fi
    if type install_boot >/dev/null 2>&1; then
        _spin "Installing boot splash..." "install_boot" "$LOG_FILE"
    fi
    _spin "Enabling cockpit..." "sudo cp $SCRIPT_DIR/configs/User-Management/manage-users.desktop /usr/share/applications/ && sudo systemctl enable --now cockpit.socket && sudo systemctl start cockpit.socket" "$LOG_FILE"
    _ok "Cockpit enabled"

    # ── Samba ────────────────────────────────────────────────────────────
    _step "Enabling Samba"
    _spin "Enabling samba..." "sudo cp $SCRIPT_DIR/configs/smb/smb.conf /etc/samba/ && sudo systemctl enable smb nmb && sudo systemctl start smb nmb && sudo systemctl restart smb nmb" "$LOG_FILE"
    _warn "Update interfaces in /etc/samba/smb.conf with your IP address"
    _ok "Samba enabled"

    # ── NVIDIA info ──────────────────────────────────────────────────────
    _step "NVIDIA Information"
    echo -e "${WHITE}  If you installed an NVIDIA card, follow the instructions in:${NC}"
    echo -e "${CYAN}  ~/hyprtk/hypr/nvidia.lua${NC}"
    $GUM input --placeholder "Press Enter to continue..."

    # ── Confirm dotfiles ────────────────────────────────────────────────
    if ! $GUM confirm --prompt.foreground=5 "Install dotfiles now?"; then
        echo -e "${MAGENTA}  Dotfile installation skipped.${NC}"
        log "Dotfile installation skipped by user"
    else
        # ── .config directory ───────────────────────────────────────────
        _step "Checking .config Directory"
        if [ -d ~/.config ]; then
            _ok ".config folder exists"
        else
            mkdir ~/.config
            _ok ".config folder created"
        fi

        # ── General symlinks ───────────────────────────────────────────
        _step "Installing General Configs"
        _spin "Installing alacritty..." "_installSymLink alacritty ~/.config/alacritty $SCRIPT_DIR/configs/alacritty/ ~/.config" "$LOG_FILE"
        _spin "Installing ranger..." "_installSymLink ranger ~/.config/ranger $SCRIPT_DIR/configs/ranger/ ~/.config" "$LOG_FILE"
        _spin "Installing vim..." "_installSymLink vim ~/.config/vim $SCRIPT_DIR/configs/vim/ ~/.config" "$LOG_FILE"
        _spin "Installing nvim..." "_installSymLink nvim ~/.config/nvim $SCRIPT_DIR/configs/nvim/ ~/.config" "$LOG_FILE"
        _spin "Installing starship..." "_installSymLink starship ~/.config/starship.toml $SCRIPT_DIR/configs/starship/starship.toml ~/.config/starship.toml" "$LOG_FILE"
        _spin "Installing rofi..." "_installSymLink rofi ~/.config/rofi $SCRIPT_DIR/configs/rofi/ ~/.config" "$LOG_FILE"
        _spin "Installing dunst..." "_installSymLink dunst ~/.config/dunst $SCRIPT_DIR/configs/dunst/ ~/.config" "$LOG_FILE"
        _spin "Installing wal..." "_installSymLink wal ~/.config/wal $SCRIPT_DIR/configs/wal/ ~/.config" "$LOG_FILE"
        _spin "Installing btop..." "_installSymLink btop ~/.config/btop $SCRIPT_DIR/configs/btop/ ~/.config" "$LOG_FILE"
        _ok "General configs installed"

        # ── Re-init pywal16 ───────────────────────────────────────────
        _step "Re-Initiating Pywal16"
        if type wal_init >/dev/null 2>&1; then
            _spin "Running wal_init..." "wal_init" "$LOG_FILE"
        else
            _spin "Initializing pywal16..." "wal -i $SCRIPT_DIR/assets/Wallpapers/default.png" "$LOG_FILE"
        fi
        _ok "Pywal16 templates initiated"

        # ── GTK ───────────────────────────────────────────────────────
        _step "Installing GTK Configs"
        _spin "Installing GTK 3.0..." "_installSymLink gtk-3.0 ~/.config/gtk-3.0 $SCRIPT_DIR/configs/gtk/gtk-3.0/ ~/.config/" "$LOG_FILE"
        _spin "Installing GTK 4.0..." "_installSymLink gtk-4.0 ~/.config/gtk-4.0 $SCRIPT_DIR/configs/gtk/gtk-4.0/ ~/.config/" "$LOG_FILE"
        _spin "Installing themes..." "_installSymLink themes ~/.local/share/themes $SCRIPT_DIR/assets/themes ~/.local/share/" "$LOG_FILE"
        _spin "Installing icons..." "_installSymLink icons ~/.local/share/icons $SCRIPT_DIR/assets/papirus-icons/icons ~/.local/share/" "$LOG_FILE"
        _ok "GTK configs installed"

        # ── Xfce ──────────────────────────────────────────────────────
        _step "Installing Xfce Configs"
        _spin "Installing xfce4..." "_installSymLink xfce4 ~/.config/xfce4 $SCRIPT_DIR/configs/xfce4 ~/.config/" "$LOG_FILE"
        _spin "Installing Thunar..." "_installSymLink Thunar ~/.config/Thunar $SCRIPT_DIR/configs/Thunar ~/.config/" "$LOG_FILE"
        _spin "Installing Mousepad..." "_installSymLink Mousepad ~/.config/Mousepad $SCRIPT_DIR/configs/Mousepad ~/.config/" "$LOG_FILE"
        _ok "Xfce configs installed"

        # ── Hyprland ──────────────────────────────────────────────────
        _step "Installing Hyprland Configs"
        if type pre_hypr_symlink >/dev/null 2>&1; then
            _spin "Running pre_hypr_symlink..." "pre_hypr_symlink" "$LOG_FILE"
        fi
        _spin "Installing hypr..." "_installSymLink hypr ~/.config/hypr $SCRIPT_DIR/hypr/ ~/.config" "$LOG_FILE"
        _spin "Installing fastfetch..." "_installSymLink fastfetch ~/.config/fastfetch $SCRIPT_DIR/configs/fastfetch/ ~/.config" "$LOG_FILE"
        _spin "Installing waybar..." "_installSymLink waybar ~/.config/waybar $SCRIPT_DIR/configs/waybar/ ~/.config" "$LOG_FILE"
        _spin "Installing swaylock..." "_installSymLink swaylock ~/.config/swaylock $SCRIPT_DIR/configs/swaylock/ ~/.config" "$LOG_FILE"
        _spin "Installing swappy..." "_installSymLink swappy ~/.config/swappy $SCRIPT_DIR/configs/swappy/ ~/.config" "$LOG_FILE"
        _spin "Installing hyprlogout..." "_installSymLink hyprlogout ~/.config/hyprlogout $SCRIPT_DIR/configs/hyprlogout/ ~/.config" "$LOG_FILE"
        _spin "Installing waypaper..." "_installSymLink waypaper ~/.config/waypaper $SCRIPT_DIR/configs/waypaper/ ~/.config" "$LOG_FILE"
        _spin "Installing zshrc..." "_installSymLink zshrc ~/.config/zshrc $SCRIPT_DIR/configs/zshrc/ ~/.config" "$LOG_FILE"
        _spin "Installing ohmyposh..." "_installSymLink ohmyposh ~/.config/ohmyposh $SCRIPT_DIR/configs/ohmyposh/ ~/.config" "$LOG_FILE"
        _spin "Installing matuwall..." "_installSymLink matuwall ~/.config/matuwall $SCRIPT_DIR/configs/matuwall/ ~/.config" "$LOG_FILE"
        _spin "Installing wob..." "_installSymLink wob ~/.config/wob $SCRIPT_DIR/configs/wob/ ~/.config" "$LOG_FILE"
        _spin "Creating ~/.local/bin..." "mkdir -p ~/.local/bin" "$LOG_FILE"
        _ok "Hyprland configs installed"

        # ── ZSH ──────────────────────────────────────────────────────
        _step "Installing ZSH"
        _spin "Installing zsh..." "sudo pacman -S zsh --noconfirm" "$LOG_FILE"
        _spin "Installing oh-my-zsh..." "sh -c \"\$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)\" \"\" --unattended" "$LOG_FILE"
        _ok "ZSH installed"

        _step "Installing ZSH Plugins"
        _spin "Installing zsh-autosuggestions..." "git clone https://github.com/zsh-users/zsh-autosuggestions \${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions 2>/dev/null" "$LOG_FILE"
        _spin "Installing zsh-syntax-highlighting..." "git clone https://github.com/zsh-users/zsh-syntax-highlighting.git \${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting 2>/dev/null" "$LOG_FILE"
        _spin "Installing fast-syntax-highlighting..." "git clone https://github.com/zdharma-continuum/fast-syntax-highlighting.git \${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fast-syntax-highlighting 2>/dev/null" "$LOG_FILE"
        _ok "ZSH plugins installed"

        # ── .zshrc ────────────────────────────────────────────────────
        _step "Updating .zshrc"
        _spin "Installing .zshrc..." "_installSymLink .zshrc ~/.zshrc $SCRIPT_DIR/.zshrc ~/.zshrc" "$LOG_FILE"
        _spin "Setting default shell..." "sudo chsh -s /bin/zsh && chsh -s /bin/zsh" "$LOG_FILE"
        _ok ".zshrc updated"

        # ── Standalone apps ──────────────────────────────────────────
        _step "Installing Standalone Apps"
        _spin "Installing standalone binaries..." "_installSymLink standalone ~/.local/bin $SCRIPT_DIR/installer/standalone/ ~/.local/bin" "$LOG_FILE"
        _spin "Installing oh-my-zsh..." "_installSymLink oh-my-zsh ~/.oh-my-zsh/oh-my-zsh.sh $SCRIPT_DIR/configs/oh-my-zsh/oh-my-zsh.sh ~/.oh-my-zsh" "$LOG_FILE"
        _ok "Standalone apps installed"

        # ── hyprtk-menu ──────────────────────────────────────────────
        _step "Installing hyprtk-menu"
        _spin "Installing hyprtk-menu..." "sh $SCRIPT_DIR/installer/scripts/hyprtk-menu-install.sh" "$LOG_FILE"
        _ok "hyprtk-menu installed"

        # ── theme-gui ────────────────────────────────────────────────
        _step "Installing theme-gui"
        _spin "Installing theme-gui..." "bash $SCRIPT_DIR/installer/theme-gui/install.sh" "$LOG_FILE"
        _ok "theme-gui installed"

        # ── Root user config ─────────────────────────────────────────
        _step "Setting Up Root User Config"
        _spin "Copying root config..." "sudo cp -r $SCRIPT_DIR/configs/root /" "$LOG_FILE"
        _ok "Root user config copied"

        # ── Sudoers ──────────────────────────────────────────────────
        if type setup_sudoers >/dev/null 2>&1; then
            _spin "Configuring sudoers..." "setup_sudoers" "$LOG_FILE"
        else
            _spin "Configuring sudoers..." "echo 'Defaults env_reset,pwfeedback' | sudo tee -a /etc/sudoers > /dev/null" "$LOG_FILE"
        fi
        _ok "Sudoers configured"
    fi
fi

# ── Cleanup ────────────────────────────────────────────────────────────────
rm -rf "$HOME/dotfiles" 2>/dev/null

# ── Completion ─────────────────────────────────────────────────────────────
log "=== hyprtk installation completed ==="
clear
_box \
    "$(printf "${CYAN}INSTALLATION COMPLETE${NC}")" \
    "" \
    "$(printf "${WHITE}Done!${NC}")" \
    "" \
    "$(printf "${WHITE}Installation log:${NC}")" \
    "$(printf "${CYAN}%s${NC}" "$LOG_FILE")" \
    "" \
    "$(printf "${WHITE}Next steps:${NC}")" \
    "$(printf "${CYAN}1. Update keyboard layout${NC}")" \
    "$(printf "${CYAN}   in ~/hyprtk/hypr/input.lua${NC}")" \
    "$(printf "${CYAN}2. Update screen resolution${NC}")" \
    "$(printf "${CYAN}   in ~/hyprtk/hypr/monitors.lua${NC}")" \
    "$(printf "${WHITE}3. Reboot your system${NC}")" \
    "" \
    "$(printf "${CYAN}github.com/hyprtk/dotfiles${NC}")"

echo ""
