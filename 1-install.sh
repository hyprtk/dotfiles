#!/bin/bash
echo ""
echo " Welcome to the Hyprland & XFCE installer "
echo " I have chosen as my preference to install both, if you choose No on either Environments the installer will fail and close "
echo " I chose it this way so if 1 Enviroment has problems i still have the other to boot too, enjoy"
echo ""
echo " You will now be asked to enter your Root password to proceed with the installation process"
echo ""
sleep 2

# ── Unified hyprtk installer ─────────────────────────────────────────────
# Merges the installers of all 11 supported distros (arch, archbang, archcraft,
# archman, bslx, cachy, endeavour, garuda, kiro, manjaro, reborn).
# Per-distro hooks live in installer/steps/<distro>.sh and are sourced here.
# ──────────────────────────────────────────────────────────────────────────
DISTRO="${DISTRO:-}"
if [ -z "$DISTRO" ]; then
    if [ -f /etc/os-release ]; then
        DISTRO_ID=$(grep -E '^ID=' /etc/os-release | head -1 | cut -d= -f2 | tr -d '"')
        case "$DISTRO_ID" in
            arch)        DISTRO=arch ;;
            archbang)    DISTRO=archbang ;;
            archcraft)   DISTRO=archcraft ;;
            archman)     DISTRO=archman ;;
            bluestar|bslx) DISTRO=bslx ;;
            cachyos|cachy) DISTRO=cachy ;;
            endeavour|endeavouros) DISTRO=endeavour ;;
            garuda)      DISTRO=garuda ;;
            kiro)        DISTRO=kiro ;;
            manjaro)     DISTRO=manjaro ;;
            reborn|rebornos) DISTRO=reborn ;;
        esac
    fi
fi
if [ -z "$DISTRO" ]; then
    echo "Could not auto-detect distro. Available:"
    echo "  arch archbang archcraft archman bslx cachy endeavour garuda kiro manjaro reborn"
    while [ -z "$DISTRO" ]; do
        read -p "Enter your distro name: " DISTRO
    done
fi
# Normalise: accept "*-dots" style input
DISTRO="${DISTRO%-dots}"
# Validate
case "$DISTRO" in
    arch|archbang|archcraft|archman|bslx|cachy|endeavour|garuda|kiro|manjaro|reborn) ;;
    *) echo "ERROR: unsupported distro '$DISTRO'" >&2; exit 1 ;;
esac
echo "Detected distro: $DISTRO"
STEPS="$(dirname "$0")/installer/steps/$DISTRO.sh"
if [ -f "$STEPS" ]; then
    source "$STEPS"
fi

sudo pacman -S figlet --noconfirm
sudo cp ~/hyprtk/configs/figlet/fonts/* /usr/share/figlet/fonts/
figlet -f 3d "Install"
echo "

by hyprtk (Kori Tk) (2026)
#########################################################
"
sleep 2
echo ""
clear
echo "
#########################################################
#                                                       #
#             Removing leftover Packages                #
#                                                       #
#########################################################
"
sleep 2
if type pre_install >/dev/null 2>&1; then
    pre_install
else
    sudo pacman -Rns plasma-meta kde-applications-meta --noconfirm
    sudo pacman -Rns plasma kde-applications --noconfirm
fi
echo ""
clear
echo "
#########################################################
#                                                       #
#             Starting Installation Process             #
#                                                       #
#########################################################
"
sleep 2
echo ""
clear
echo "
#########################################################
#                                                       #
#              Load Installation Libraries              #
#                                                       #
#########################################################
"
echo ""
source $(dirname "$0")/installer/scripts/library.sh
echo ""
echo ""
sh ~/hyprtk/installer/scripts/set-timezone.sh
echo ""
sleep 2
clear
echo "
#########################################################
#                                                       #
#            Installation Libraries loaded              #
#                                                       #
#########################################################
"
echo ""
sleep 2
clear
echo "
#########################################################
#                                                       #
#                     Install Yay                       #
#                                                       #
#########################################################
"
echo ""
if sudo pacman -Qs yay > /dev/null ; then
    echo "yay is installed. You can proceed with the installation"
else
    echo "yay is not installed and will be installed now!"
    _installPackagesPacman "base-devel"
    git clone https://aur.archlinux.org/yay-git.git ~/Downloads/yay-git
    cd ~/Downloads/yay-git
    makepkg -si
    cd ~/hyprtk/
    clear
fi
echo ""
clear
echo "
#########################################################
#                                                       #
#                    Yay is Installed                   #
#                                                       #
#########################################################
"
sleep 2
echo ""
echo ""
while true; do
    read -p "DO YOU WANT TO START THE INSTALLATION NOW? (Yy/Nn): " yn
    case $yn in
        [Yy]* )
            echo "Installation started."
        break;;
        [Nn]* ) 
            exit;
        break;;
        * ) echo "Please answer yes or no.";;
    esac
done
echo ""
echo ""
sleep 2
echo ""
clear
sh ~/hyprtk/hypr/packages/graphics-card.sh
sleep 2
clear
while true; do
    read -p "DO YOU WANT TO INSTALL THE CORE APPS NOW? (Yy/Nn): " yn
    case $yn in
        [Yy]* )
            echo "Installation started."
        break;;
        [Nn]* ) 
            echo "Installation is Aborted"
            exit;
        break;;
        * ) echo "Please answer yes or no.";;
    esac
done
echo ""
figlet -f 3d "Core Apps"
echo ""
echo "
#########################################################
#                                                       #
#             Installing required Packages              #
#                                                       #
#########################################################
"

echo ""
sh ~/hyprtk/hypr/packages/hyprland.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/xfce4.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/filetools.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/webtools.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/printers.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/network.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/media.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/terminaltools.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/systemtools.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/system.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/hyprviz.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/sddm-check.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/sddmgrub.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/hypr/packages/matuwall.sh
echo ""
sleep 2
echo ""
sh ~/hyprtk/installer/scripts/awww-wrapper.sh
echo ""
if type grudupdater >/dev/null 2>&1; then
    grudupdater
fi
echo "
#########################################################
#                                                       #
#              Installed required Packages              #
#                                                       #
#########################################################
"
echo ""
clear
echo "
#########################################################
#                                                       #
#                    Install Pywal16                    #
#                                                       #
#########################################################
"
if [ -f /usr/bin/wal ]; then
    echo "pywal16 already installed."
else
    yay --noconfirm -S python-pywal16-git
fi
echo ""
echo "
#########################################################
#                                                       #
#                    Pywal16 Installed                  #
#                                                       #
#########################################################
"
echo ""
clear
echo ""
echo "
#########################################################
#                                                       #
#                   Install Wallpapers                  #
#                                                       #
#########################################################
"
echo ""
echo ""
sh ~/hyprtk/hypr/packages/wallpapers.sh
echo ""
sleep 2
echo "
#########################################################
#                                                       #
#                 Wallpapers Installed                  #
#                                                       #
#########################################################
"
echo ""
clear
echo "
#########################################################
#                                                       #
#                     Install Fonts                     #
#                                                       #
#########################################################
"
echo ""
echo ""
sh ~/hyprtk/hypr/packages/fonts.sh
echo ""
sleep 2
echo "
#########################################################
#                                                       #
#                    Fonts Installed                    #
#                                                       #
#########################################################
"
echo ""
clear
echo ""
echo "
#########################################################
#                                                       #
#                   Install Icons Root                  #
#                                                       #
#########################################################
"
echo ""
echo "-> Installing to root user"
wget -qO- https://raw.githubusercontent.com/PapirusDevelopmentTeam/papirus-icon-theme/master/install.sh | DESTDIR="/root/.local/share/icons" sh

echo "
#########################################################
#                                                       #
#                    Icons Installed                    #
#                                                       #
#########################################################
"
echo ""
clear
echo ""
echo "
#########################################################
#                                                       #
#                   Initiating Pywal16                  #
#                                                       #
#########################################################
"
echo ""
echo "-> Init pywal16"
wal -i ~/hyprtk/assets/Wallpapers/default.png
echo "pywal16 initiated."
echo ""
echo ""
echo "-> Copy default wallpaper to .cache"
cp ~/hyprtk/assets/Wallpapers/default.png ~/.cache/current-wallpaper.png
sudo cp ~/.cache/current-wallpaper.png /root/.cache/current-wallpaper.png
if type grub_wallpaper >/dev/null 2>&1; then
    grub_wallpaper
fi
xdg-user-dirs-update --force
xdg-user-dirs-gtk-update --force   
echo "default wallpaper copied."
echo ""
echo "
#########################################################
#                                                       #
#                    Pywal16 Initiated                  #
#                                                       #
#########################################################
"
echo ""
sleep 2
clear
echo ""
figlet -f 3d "Hyprland"
echo ""
echo " by hyprtk (Kori Tk) (2026) "
echo " ------------------------------------------------------------------- "
echo ""
echo ""
while true; do
    read -p "DO YOU WANT TO START THE INSTALLATION NOW? (Yy/Nn): " yn
    case $yn in
        [Yy]* )
            echo "Installation started."
        break;;
        [Nn]* ) 
            echo "Installation is Aborted"
            exit;
        break;;
        * ) echo "Please answer yes or no.";;
    esac
done
echo ""
echo ""
echo "
#########################################################
#                                                       #
#            Launch Thunar to generate xfconf           #
#                                                       #
#########################################################
"
echo ""
echo "-> Launching Thunar to populate xfconf"
thunar &
sleep 3
echo ""
echo ""
echo "-> Closing Thunar"
killall thunar
echo ""
clear
echo "
#########################################################
#                                                       #
#                   Enabling Bluetooth                  #
#                                                       #
#########################################################
"
sudo systemctl start bluetooth
sudo systemctl enable bluetooth
echo ""
echo ""
clear
echo "
#########################################################
#                                                       #
#                   Enabling Cockpit                    #
#                                                       #
#########################################################
"
if type install_os_release >/dev/null 2>&1; then
    install_os_release
else
    sudo cp ~/hyprtk/installer/os-release/os-release-$DISTRO /usr/lib/
fi
if type install_boot >/dev/null 2>&1; then
    install_boot
fi
sudo cp ~/hyprtk/configs/User-Management/manage-users.desktop /usr/share/applications/
sudo systemctl enable --now cockpit.socket
sudo systemctl start cockpit.socket
echo ""
echo ""
clear
echo "
#########################################################
#                                                       #
#                   Enabling Samba                      #
#                                                       #
#########################################################
"
sudo cp ~/hyprtk/configs/smb/smb.conf /etc/samba/
sudo systemctl enable smb nmb
sudo systemctl start smb nmb
sudo systemctl restart smb nmb
echo "Please update the interfaces section of /etc/samba/smb.conf with your IP address"
sleep 3
clear
echo "
#########################################################
#                                                       #
#           IMPORTANT Graphic Card Information          #
#                                                       #
#########################################################
"
echo ""
echo ""
echo "If you installed an NVIDIA Graphics Card please follow the instructions in the"
echo "nvidia.conf file located ~/hyprtk/hypr/conf/nvidia.conf"
echo ""
sleep 5
clear
figlet -f 3d "hyprtk"
echo ""
echo " by hyprtk (Kori Tk) (2026) "
echo " ------------------------------------------------------------------- "
echo ""
echo "The script will ask for permission to remove existing directories and files from ~/.config/"
echo "Symbolic links will then be created from ~/hyprtk into your ~/.config/ directory."
echo "But you can decide to keep your personal versions by answering with No (Nn)."
echo ""
sleep 5
clear
echo ""
echo "
#########################################################
#                                                       #
#              Confirm dotfile files Install            #
#                                                       #
#########################################################
"
while true; do
    read -p " DO YOU WANT TO START THE INSTALLATION NOW? (Yy/Nn): " yn
    case $yn in
        [Yy]* )
            echo "Installation started."
        break;;
        [Nn]* ) 
            exit;
        break;;
        * ) echo "Please answer yes or no.";;
    esac
done
echo ""
clear
echo "
#########################################################
#                                                       #
#             Check .config directory exists            #
#                                                       #
#########################################################
"
echo ""
echo "-> Check if .config folder exists"

if [ -d ~/.config ]; then
    echo ".config folder already exists."
else
    mkdir ~/.config
    echo ".config folder created."
fi
echo ""
sleep 3
clear
echo "
#########################################################
#                                                       #
#                 Create Symbolic Links                 #
#                                                       #
#########################################################
"
# name symlink source target
echo ""
echo ""
echo "-------------------------------------"
echo "-> Install general hyprtk"
echo "-------------------------------------"
echo ""
echo ""
_installSymLink alacritty ~/.config/alacritty ~/hyprtk/configs/alacritty/ ~/.config
_installSymLink ranger ~/.config/ranger ~/hyprtk/configs/ranger/ ~/.config
_installSymLink vim ~/.config/vim ~/hyprtk/configs/vim/ ~/.config
_installSymLink nvim ~/.config/nvim ~/hyprtk/configs/nvim/ ~/.config
_installSymLink starship ~/.config/starship.toml ~/hyprtk/configs/starship/starship.toml ~/.config/starship.toml
_installSymLink rofi ~/.config/rofi ~/hyprtk/configs/rofi/ ~/.config
_installSymLink dunst ~/.config/dunst ~/hyprtk/configs/dunst/ ~/.config
_installSymLink wal ~/.config/wal ~/hyprtk/configs/wal/ ~/.config
_installSymLink btop ~/.config/btop ~/hyprtk/configs/btop/ ~/.config
echo ""
clear
echo "
#########################################################
#                                                       #
#                  Re-Initiating Pywal16                #
#                                                       #
#########################################################
"
echo ""
if type wal_init >/dev/null 2>&1; then
    wal_init
else
    wal -i ~/hyprtk/assets/Wallpapers/default.png
fi
echo "Pywal16 templates initiated!"
echo ""
echo ""
echo "
#########################################################
#                                                       #
#                    Pywal16 Initiated                  #
#                                                       #
#########################################################
"
echo ""
clear
echo "-------------------------------------"
echo "-> Install GTK hyprtk"
echo "-------------------------------------"
echo ""
_installSymLink gtk-3.0 ~/.config/gtk-3.0 ~/hyprtk/configs/gtk/gtk-3.0/ ~/.config/
_installSymLink gtk-4.0 ~/.config/gtk-4.0 ~/hyprtk/configs/gtk/gtk-4.0/ ~/.config/
_installSymLink themes ~/.local/share/themes ~/hyprtk/assets/themes ~/.local/share/
_installSymLink icons ~/.local/share/icons ~/hyprtk/assets/papirus-icons/icons ~/.local/share/
echo ""
clear
echo "-------------------------------------"
echo "-> Install Xfce hyprtk"
echo "-------------------------------------"
echo ""
_installSymLink xfce4 ~/.config/xfce4 ~/hyprtk/configs/xfce4 ~/.config/
_installSymLink Thunar ~/.config/Thunar ~/hyprtk/configs/Thunar ~/.config/
_installSymLink Mousepad ~/.config/Mousepad ~/hyprtk/configs/Mousepad ~/.config/
echo ""
clear
echo "-------------------------------------"
echo "-> Install Hyprland hyprtk"
echo "-------------------------------------"
echo ""
if type pre_hypr_symlink >/dev/null 2>&1; then
    pre_hypr_symlink
fi
_installSymLink hypr ~/.config/hypr ~/hyprtk/hypr/ ~/.config
_installSymLink fastfetch ~/.config/fastfetch ~/hyprtk/configs/fastfetch/ ~/.config
_installSymLink waybar ~/.config/waybar ~/hyprtk/configs/waybar/ ~/.config
_installSymLink swaylock ~/.config/swaylock ~/hyprtk/configs/swaylock/ ~/.config
_installSymLink swappy ~/.config/swappy ~/hyprtk/configs/swappy/ ~/.config
_installSymLink hyprlogout ~/.config/hyprlogout ~/hyprtk/configs/hyprlogout/ ~/.config
_installSymLink waypaper ~/.config/waypaper ~/hyprtk/configs/waypaper/ ~/.config
_installSymLink zshrc ~/.config/zshrc ~/hyprtk/configs/zshrc/ ~/.config
_installSymLink ohmyposh ~/.config/ohmyposh ~/hyprtk/configs/ohmyposh/ ~/.config
_installSymLink matuwall ~/.config/matuwall ~/hyprtk/configs/matuwall/ ~/.config
_installSymLink wob ~/.config/wob ~/hyprtk/configs/wob/ ~/.config
mkdir ~/.local/bin
echo ""
clear
echo ""
echo ""
echo "-------------------------------------"
echo "-> Install ZSH"
echo "-------------------------------------"
echo ""
sudo pacman -S zsh --noconfirm
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
echo ""
echo ""
echo "-------------------------------------"
echo "-> Install ZSH Plugins"
echo "-------------------------------------"
echo ""
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
git clone https://github.com/zdharma-continuum/fast-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/fast-syntax-highlighting
echo ""
echo "
#########################################################
#                                                       #
#                      Update .zshrc                    #
#                                                       #
#########################################################
"
echo ""
echo "-> Install .zshrc"
echo ""
_installSymLink .zshrc ~/.zshrc ~/hyprtk/.zshrc ~/.zshrc
echo ""
sudo chsh -s /bin/zsh
chsh -s /bin/zsh
echo "
#########################################################
#                                                       #
#                    .zshrc Updated                     #
#                                                       #
#########################################################
"
echo ""
_installSymLink standalone ~/.local/bin ~/hyprtk/installer/standalone/ ~/.local/bin
_installSymLink oh-my-zsh ~/.oh-my-zsh/oh-my-zsh.sh ~/hyprtk/configs/oh-my-zsh/oh-my-zsh.sh ~/.oh-my-zsh
echo ""
echo "-> Install hyprtk-menu"
echo ""
sh ~/hyprtk/installer/scripts/hyprtk-menu-install.sh
echo ""
echo "-> Install theme-gui"
echo ""
bash ~/hyprtk/installer/theme-gui/install.sh
echo ""
rm -R $HOME/dotfiles
clear
echo ""
echo ""
echo "-------------------------------------"
echo "-> Setup Root User Config"
echo "-------------------------------------"
echo ""
sudo cp -r ~/hyprtk/configs/root /
echo " Copying Config and Themes to ROOT User "
echo ""
sleep 3
if type setup_sudoers >/dev/null 2>&1; then
    setup_sudoers
else
    echo -e 'Defaults env_reset,pwfeedback'| sudo tee -a /etc/sudoers
fi
echo " Setup Password Feedback when entering SUDO password "
echo ""
sleep 3
clear
echo ""
echo ""
echo "-------------------------------------"
echo "-> Congratulations Setup Complete"
echo "-------------------------------------"
echo ""
echo "DONE!"
echo ""
echo "NEXT: Update the keyboard layout and screen resolution in ~/hyprtk/hypr/hyprland.conf"
echo "Now proceed with rebooting your system and Enjoy!!!"
echo ""
