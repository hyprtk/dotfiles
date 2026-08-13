#!/bin/bash
# Unified Hyprland & XFCE Installer
# Merges all 11 distro-specific installers into one
# by hyprtk (Kori Tk) (2026)

set -e

# Source all required scripts
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/installer/scripts/library.sh"

# Gum paths
GUM_PATH="$HOME/hyprtk/installer/standalone/gum"

# Gum styled functions
gum_style_header() {
    local title="$1"
    echo ""
    echo -e "${COLOR_BOLD_CYAN}══════════════════════════════════════════════════════════════════════════════${COLOR_RESET}"
    echo -e "${COLOR_BOLD_MAGENTA}$(printf '%*s' $(( (78 - ${#title}) / 2 )) '')$title${COLOR_RESET}"
    echo -e "${COLOR_BOLD_CYAN}══════════════════════════════════════════════════════════════════════════════${COLOR_RESET}"
    echo ""
}

gum_style_subheader() {
    local title="$1"
    echo ""
    echo -e "${COLOR_BOLD_CYAN}──────────────────────────────────────────────────────────────────────────────${COLOR_RESET}"
    echo -e "${COLOR_BOLD_CYAN}$(printf '%*s' $(( (78 - ${#title} - 6) / 2 )) '')-> $title${COLOR_RESET}"
    echo -e "${COLOR_BOLD_CYAN}──────────────────────────────────────────────────────────────────────────────${COLOR_RESET}"
    echo ""
}

gum_confirm() {
    local message="$1"
    if $GUM_PATH confirm --affirmative "Yes" --negative "No" "$message"; then
        return 0
    else
        return 1
    fi
}

gum_choose() {
    local prompt="$1"
    shift
    local options=("$@")
    $GUM_PATH choose "$prompt" "${options[@]}"
}

gum_spin() {
    local title="$1"
    shift
    local cmd="$*"
    $GUM_PATH spin --spinner dot --title "$title" -- bash -c "$cmd" || true
}

gum_log() {
    local message="$1"
    local style="${2:-info}"
    case $style in
        success)
            echo -e "${COLOR_BOLD_GREEN}✓${COLOR_RESET} $message"
            ;;
        warning)
            echo -e "${COLOR_BOLD_YELLOW}⚠${COLOR_RESET} $message"
            ;;
        error)
            echo -e "${COLOR_BOLD_RED}✗${COLOR_RESET} $message"
            ;;
        *)
            echo -e "${COLOR_BOLD_CYAN}→${COLOR_RESET} $message"
            ;;
    esac
}

# -----------------------------------------------------
# Distro-aware asset selection
# -----------------------------------------------------

# Select the os-release file matching the detected distro
# (falls back to the Arch default when no distro variant exists)
select_os_release() {
    local distro_rel="$HOME/hyprtk/installer/os-release/os-release-$(detect_distro)"
    if [ -f "$distro_rel" ]; then
        echo "$distro_rel"
    else
        echo "$HOME/hyprtk/installer/os-release/os-release"
    fi
}

# Deploy the distro-branded fastfetch logo over the symlinked ascii.txt
# (no-op for distros that share the Arch default)
deploy_fastfetch_logo() {
    local distro_ascii="$HOME/hyprtk/configs/fastfetch/ascii.$(detect_distro)"
    if [ -f "$distro_ascii" ] && [ -f ~/.config/fastfetch/ascii.txt ]; then
        cp "$distro_ascii" ~/.config/fastfetch/ascii.txt
        gum_log "fastfetch logo set for ${DISTRO_NAME}" success
    fi
}

# Main installation function
main() {
    # Show main header
    print_main_header
    
    # Detect distro
    DISTRO=$(detect_distro)
    DISTRO_NAME=$(get_distro_name $DISTRO)
    
    # Show detected distro
    print_distro_header "$DISTRO_NAME"
    
    # Check if distro is supported
    if ! is_supported_distro "$DISTRO"; then
        print_error "Unsupported distribution: $DISTRO_NAME"
        print_info "Supported distributions: Arch, Garuda, CachyOS, Manjaro, EndeavourOS, Archcraft, Archman, ArchBang, BSLX, Kiro, RebornOS"
        exit 1
    fi
    
    # Welcome message
    print_info_box "Welcome to the Hyprland & XFCE installer"
    echo -e "${COLOR_WHITE}I have chosen as my preference to install both, if you choose No on either${COLOR_RESET}"
    echo -e "${COLOR_WHITE}Environments the installer will fail and close.${COLOR_RESET}"
    echo -e "${COLOR_WHITE}I chose it this way so if 1 Environment has problems I still have the other to boot too, enjoy.${COLOR_RESET}"
    echo -e "${COLOR_WHITE}You will now be asked to enter your Root password to proceed with the installation process${COLOR_RESET}"
    
    # Removing leftover packages
    print_section_header "Removing leftover Packages"
    
    # Remove distro-specific packages if installed
    get_distro_removal_command $DISTRO
    
    # Starting Installation Process
    print_section_header "Starting Installation Process"
    
    # Load Installation Libraries
    print_section_header "Load Installation Libraries"
    sh ~/hyprtk/installer/scripts/set-timezone.sh
    
    # Installation Libraries loaded
    print_section_header "Installation Libraries loaded"
    
    # Install Yay
    print_section_header "Install Yay"
    if sudo pacman -Qs yay > /dev/null ; then
        gum_log "yay is installed. You can proceed with the installation" success
    else
        gum_log "yay is not installed and will be installed now!" warning
        _installPackagesPacman "base-devel"
        git clone https://aur.archlinux.org/yay-git.git ~/Downloads/yay-git
        cd ~/Downloads/yay-git
        makepkg -si
        cd ~/hyprtk/
    fi
    
    # Yay is Installed
    print_section_header "Yay is Installed"
    
    # Confirm start of installation
    gum_confirm "DO YOU WANT TO START THE INSTALLATION NOW?" || exit 1
    
    # Graphics card detection
    sh ~/hyprtk/hypr/packages/graphics-card.sh
    
    # Confirm core apps installation
    gum_confirm "DO YOU WANT TO INSTALL THE CORE APPS NOW?" || exit 1
    
    # Core Apps section
    print_section_header "Installing required Packages"
    
    gum_spin "Installing Hyprland..." sh ~/hyprtk/hypr/packages/hyprland.sh
    gum_spin "Installing XFCE4..." sh ~/hyprtk/hypr/packages/xfce4.sh
    gum_spin "Installing File Tools..." sh ~/hyprtk/hypr/packages/filetools.sh
    gum_spin "Installing Web Tools..." sh ~/hyprtk/hypr/packages/webtools.sh
    gum_spin "Installing Printers..." sh ~/hyprtk/hypr/packages/printers.sh
    gum_spin "Installing Network..." sh ~/hyprtk/hypr/packages/network.sh
    gum_spin "Installing Media..." sh ~/hyprtk/hypr/packages/media.sh
    gum_spin "Installing Terminal Tools..." sh ~/hyprtk/hypr/packages/terminaltools.sh
    gum_spin "Installing System Tools..." sh ~/hyprtk/hypr/packages/systemtools.sh
    gum_spin "Installing System..." sh ~/hyprtk/hypr/packages/system.sh
    gum_log "Installing HyprViz..." info
    _checkAndInstallHyprviz
    gum_spin "Installing SDDM..." sh ~/hyprtk/hypr/packages/sddm-check.sh
    gum_spin "Installing SDDM/GRUB..." sh ~/hyprtk/hypr/packages/sddmgrub.sh
    gum_log "Installing Matuwall..." info
    _checkAndInstallMatuwall
    gum_spin "Installing AWWW..." sh ~/hyprtk/installer/scripts/awww-wrapper.sh
    
    # Distro-specific: Kiro needs grudupdater
    if needs_grudupdater "$DISTRO"; then
        if [ -f ~/hyprtk/installer/scripts/grudupdater.sh ]; then
            gum_spin "Installing grudupdater..." sh ~/hyprtk/installer/scripts/grudupdater.sh
        else
            gum_log "grudupdater.sh not found - skipping" warning
        fi
    fi
    
    gum_log "Installed required Packages" success
    
    # Install Pywal16
    print_section_header "Install Pywal16"
    if [ -f /usr/bin/wal ]; then
        gum_log "pywal16 already installed." success
    else
        gum_spin "Installing Pywal16..." yay --noconfirm -S python-pywal16-git
    fi
    gum_log "Pywal16 Installed" success
    
    # Install Theme GUI
    print_section_header "Install Theme GUI"
    if [ -f "$HOME/.local/bin/theme-gui" ]; then
        gum_log "Theme GUI already installed." success
    else
        gum_spin "Installing Theme GUI..." bash ~/hyprtk/configs/theme-gui/install.sh
    fi
    gum_log "Theme GUI Installed" success
    
    # Install Hyprtk Menu
    print_section_header "Install Hyprtk Menu"
    if [ -f "$HOME/.local/bin/hyprtk-menu" ]; then
        gum_log "Hyprtk Menu already installed." success
    else
        gum_spin "Installing Hyprtk Menu..." bash ~/hyprtk/configs/hyprtk-menu/install.sh
    fi
    gum_log "Hyprtk Menu Installed" success
    
    # Install Wallpapers
    print_section_header "Install Wallpapers"
    sh ~/hyprtk/hypr/packages/wallpapers.sh
    gum_log "Wallpapers Installed" success
    
    # Install Fonts
    print_section_header "Install Fonts"
    sh ~/hyprtk/hypr/packages/fonts.sh
    gum_log "Fonts Installed" success
    
    # Install Icons Root
    print_section_header "Install Icons Root"
    gum_log "Installing to root user" info
    gum_spin "Installing Icons..." wget -qO- https://raw.githubusercontent.com/PapirusDevelopmentTeam/papirus-icon-theme/master/install.sh | DESTDIR="/root/.local/share/icons" sh
    gum_log "Icons Installed" success
    
    # Initiating Pywal16
    print_section_header "Initiating Pywal16"
    gum_log "Init pywal16" info
    
    # Distro-specific: Archcraft uses cache wallpaper path
    if uses_cache_wallpaper "$DISTRO"; then
        wal -i ~/.cache/current-wallpaper.png
    else
        wal -i ~/hyprtk/assets/Wallpapers/default.png
    fi
    
    gum_log "pywal16 initiated." success
    gum_log "Copy default wallpaper to .cache" info
    cp ~/hyprtk/assets/Wallpapers/default.png ~/.cache/current-wallpaper.png
    sudo cp ~/.cache/current-wallpaper.png /root/.cache/current-wallpaper.png
    
    # Distro-specific: BSLX needs grub wallpaper
    if needs_grub_wallpaper "$DISTRO"; then
        sudo cp ~/.cache/current-wallpaper.png /boot/grub/current-wallpaper.png
    fi
    
    xdg-user-dirs-update --force
    xdg-user-dirs-gtk-update --force
    gum_log "default wallpaper copied." success
    gum_log "Pywal16 Initiated" success
    
    # Hyprland section
    print_section_header "Hyprland Installation"
    echo -e "${COLOR_BOLD_WHITE} by Kori Tk (2026) ${COLOR_RESET}"
    echo -e "${COLOR_BOLD_WHITE} ------------------------------------------------------------------- ${COLOR_RESET}"
    
    # Confirm Hyprland installation
    gum_confirm "DO YOU WANT TO START THE INSTALLATION NOW?" || exit 1
    
    # Launch Thunar to generate xfconf
    print_section_header "Launch Thunar to generate xfconf"
    gum_log "Launching Thunar to populate xfconf" info
    thunar &
    sleep 3
    gum_log "Closing Thunar" info
    killall thunar
    
    # Enabling Bluetooth
    print_section_header "Enabling Bluetooth"
    gum_spin "Enabling Bluetooth..." bash -c "sudo systemctl start bluetooth && sudo systemctl enable bluetooth"
    
    # Enabling Cockpit
    print_section_header "Enabling Cockpit"
    sudo cp "$(select_os_release)" /usr/lib/os-release
    
    # Distro-specific: CachyOS needs extra branding
    if has_cachyos_branding "$DISTRO"; then
        sudo cp "$(select_os_release)" /run/systemd/propagate/.os-release-stage/
        sudo cp "$(select_os_release)" /run/user/$UID/systemd/propagate/.os-release-stage/
        sudo cp ~/hyprtk/installer/os-release/cachyos-branding /usr/share/libalpm/scripts/
        sudo bash /usr/share/libalpm/scripts/cachyos-branding
    fi
    
    # Restore boot splash + rebuild initramfs (required for Arch installs)
    if [ -f ~/hyprtk/configs/splash/splash-arch.bmp ]; then
        sudo cp ~/hyprtk/configs/splash/splash-arch.bmp /usr/share/systemd/bootctl/
        update_initramfs
    else
        gum_log "splash-arch.bmp not found - skipping boot splash" warning
    fi
    
    sudo cp ~/hyprtk/configs/User-Management/manage-users.desktop /usr/share/applications/
    gum_spin "Enabling Cockpit..." bash -c "sudo systemctl enable --now cockpit.socket && sudo systemctl start cockpit.socket"
    
    # Enabling Samba
    print_section_header "Enabling Samba"
    sudo cp ~/hyprtk/configs/smb/smb.conf /etc/samba/
    gum_spin "Enabling Samba..." bash -c "sudo systemctl enable smb nmb && sudo systemctl start smb nmb && sudo systemctl restart smb nmb"
    gum_log "Please update the interfaces section of /etc/samba/smb.conf with your IP address" warning
    
    # Graphics Card Information
    print_warning_box "IMPORTANT Graphic Card Information"
    echo -e "${COLOR_WHITE}If you installed an NVIDIA Graphics Card please follow the instructions in the${COLOR_RESET}"
    echo -e "${COLOR_WHITE}nvidia.conf file located ~/hyprtk/hypr/nvidia.lua${COLOR_RESET}"
    
    # Dotfiles installation section
    print_section_header "hyprtk Dotfiles Installation"
    echo -e "${COLOR_BOLD_WHITE} by Kori Tk (2026) ${COLOR_RESET}"
    echo -e "${COLOR_BOLD_WHITE} ------------------------------------------------------------------- ${COLOR_RESET}"
    echo -e "${COLOR_WHITE}The script will ask for permission to remove existing directories and files from ~/.config/${COLOR_RESET}"
    echo -e "${COLOR_WHITE}Symbolic links will then be created from ~/hyprtk into your ~/.config/ directory.${COLOR_RESET}"
    echo -e "${COLOR_WHITE}But you can decide to keep your personal versions by answering with No (Nn).${COLOR_RESET}"
    
    # Confirm dotfiles installation
    print_section_header "Confirm dotfiles files Install"
    gum_confirm "DO YOU WANT TO START THE INSTALLATION NOW?" || exit 1
    
    # Check .config directory exists
    print_section_header "Check .config directory exists"
    gum_log "Check if .config folder exists" info
    
    if [ -d ~/.config ]; then
        gum_log ".config folder already exists." success
    else
        mkdir ~/.config
        gum_log ".config folder created." info
    fi
    
    # Create Symbolic Links
    print_section_header "Create Symbolic Links"
    gum_style_subheader "Install general hyprtk"
    
    _installSymLink alacritty ~/.config/alacritty ~/hyprtk/configs/alacritty/ ~/.config
    _installSymLink ranger ~/.config/ranger ~/hyprtk/configs/ranger/ ~/.config
    _installSymLink vim ~/.config/vim ~/hyprtk/configs/vim/ ~/.config
    _installSymLink nvim ~/.config/nvim ~/hyprtk/configs/nvim/ ~/.config
    _installSymLink starship ~/.config/starship.toml ~/hyprtk/configs/starship/starship.toml ~/.config/starship.toml
    _installSymLink rofi ~/.config/rofi ~/hyprtk/configs/rofi/ ~/.config
    _installSymLink dunst ~/.config/dunst ~/hyprtk/configs/dunst/ ~/.config
    _installSymLink wal ~/.config/wal ~/hyprtk/configs/wal/ ~/.config
    _installSymLink btop ~/.config/btop ~/hyprtk/configs/btop/ ~/.config
    
    # Re-Initiating Pywal16
    print_section_header "Re-Initiating Pywal16"
    
    # Distro-specific: Archcraft uses cache wallpaper path
    if uses_cache_wallpaper "$DISTRO"; then
        wal -i ~/.cache/current-wallpaper.png
    else
        wal -i ~/hyprtk/assets/Wallpapers/default.png
    fi
    
    gum_log "Pywal16 templates initiated!" success
    gum_log "Pywal16 Initiated" success
    
    # Install GTK
    gum_style_subheader "Install GTK hyprtk"
    _installSymLink gtk-3.0 ~/.config/gtk-3.0 ~/hyprtk/configs/gtk/gtk-3.0/ ~/.config/
    _installSymLink gtk-4.0 ~/.config/gtk-4.0 ~/hyprtk/configs/gtk/gtk-4.0/ ~/.config/
    _installSymLink themes ~/.local/share/themes ~/hyprtk/assets/themes ~/.local/share/
    _installSymLink icons ~/.local/share/icons ~/hyprtk/configs/papirus-icons/icons ~/.local/share/
    
    # Install Xfce
    gum_style_subheader "Install Xfce hyprtk"
    _installSymLink xfce4 ~/.config/xfce4 ~/hyprtk/configs/xfce4 ~/.config/
    _installSymLink Thunar ~/.config/Thunar ~/hyprtk/configs/Thunar ~/.config/
    _installSymLink Mousepad ~/.config/Mousepad ~/hyprtk/configs/Mousepad ~/.config/
    
    # Install Hyprland
    gum_style_subheader "Install Hyprland hyprtk"
    
    # Distro-specific: Some distros need hypr config backup
    if needs_hypr_backup "$DISTRO"; then
        mv ~/.config/hypr ~/.config/hypr-old
    fi
    
    _installSymLink hypr ~/.config/hypr ~/hyprtk/hypr/ ~/.config
    _installSymLink fastfetch ~/.config/fastfetch ~/hyprtk/configs/fastfetch/ ~/.config
    deploy_fastfetch_logo
    _installSymLink waybar ~/.config/waybar ~/hyprtk/configs/waybar/ ~/.config
    _installSymLink swaylock ~/.config/swaylock ~/hyprtk/configs/swaylock/ ~/.config
    _installSymLink swappy ~/.config/swappy ~/hyprtk/configs/swappy/ ~/.config
    _installSymLink hyprlogout ~/.config/hyprlogout ~/hyprtk/configs/hyprlogout/ ~/.config
    _installSymLink waypaper ~/.config/waypaper ~/hyprtk/configs/waypaper/ ~/.config
    _installSymLink zshrc ~/.config/zshrc ~/hyprtk/configs/zshrc/ ~/.config
    _installSymLink ohmyposh ~/.config/ohmyposh ~/hyprtk/configs/ohmyposh/ ~/.config
    _installSymLink matuwall ~/.config/matuwall ~/hyprtk/configs/matuwall/ ~/.config
    _installSymLink wob ~/.config/wob ~/hyprtk/configs/wob/ ~/.config
    mkdir -p ~/.local/bin
    
    # Install ZSH
    gum_style_subheader "Install ZSH"
    sudo pacman -S zsh --noconfirm
    _checkAndInstallOhMyZsh
    
    # Install ZSH Plugins
    gum_style_subheader "Install ZSH Plugins"
    _installZshPlugin "zsh-autosuggestions" "https://github.com/zsh-users/zsh-autosuggestions"
    _installZshPlugin "zsh-syntax-highlighting" "https://github.com/zsh-users/zsh-syntax-highlighting.git"
    _installZshPlugin "fast-syntax-highlighting" "https://github.com/zdharma-continuum/fast-syntax-highlighting.git"
    
    # Update .zshrc
    print_section_header "Update .zshrc"
    gum_log "Install .zshrc" info
    _installSymLink .zshrc ~/.zshrc ~/hyprtk/.zshrc ~/.zshrc
    
    # Reset terminal state (gum can leave the tty in raw mode) so password
    # prompts render visibly, then change the ROOT shell to zsh.
    stty sane 2>/dev/null || true
    echo ""
    echo "A password prompt will now appear to change the ROOT shell to zsh."
    echo "Enter your sudo password when prompted."
    sudo chsh -s /bin/zsh
    
    # Change the current user's shell to zsh (prompts for the login password).
    stty sane 2>/dev/null || true
    echo ""
    echo "A password prompt will now appear to change your user shell to zsh."
    echo "Enter your login password when prompted."
    chsh -s /bin/zsh
    gum_log ".zshrc Updated" success
    _installSymLink standalone ~/.local/bin ~/hyprtk/installer/standalone/ ~/.local/bin
    _installSymLink oh-my-zsh ~/.oh-my-zsh/oh-my-zsh.sh ~/hyprtk/configs/oh-my-zsh/oh-my-zsh.sh ~/.oh-my-zsh
    [ -d "$HOME/dotfiles" ] && rm -R $HOME/dotfiles
    
    # Setup Root User Config
    gum_style_subheader "Setup Root User Config"
    sudo cp -r ~/hyprtk/configs/root /
    gum_log "Copying Config and Themes to ROOT User" info
    echo -e 'Defaults env_reset,pwfeedback'| sudo tee -a /etc/sudoers
    gum_log "Setup Password Feedback when entering SUDO password" info
    
    # Congratulations
    print_success_box "Setup Complete"
    echo -e "${COLOR_BOLD_GREEN}DONE!${COLOR_RESET}"
    echo -e "${COLOR_WHITE}NEXT: Update the keyboard layout in ~/hyprtk/hypr/input.lua${COLOR_RESET}"
    echo -e "${COLOR_WHITE}NEXT: Update the screen resolution in ~/hyprtk/hypr/monitors.lua${COLOR_RESET}"
    echo -e "${COLOR_WHITE}Now proceed with rebooting your system and Enjoy!!!${COLOR_RESET}"
    
    # Main footer
    print_main_footer
}

# Run the main function
main "$@"
