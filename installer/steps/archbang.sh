#/bin/bash
# archbang distro steps — removes swaylock, installs os-release to /etc/,
# no splash/bootctl step, backs up existing hypr config.

pre_install() {
    sudo pacman -Rns plasma-meta kde-applications-meta --noconfirm
    sudo pacman -Rns plasma kde-applications --noconfirm
    sudo pacman -Rns swaylock --noconfirm
}

install_os_release() {
    sudo cp ~/hyprtk/installer/os-release/os-release-$DISTRO /etc/
}

pre_hypr_symlink() {
    [ -e ~/.config/hypr ] && mv ~/.config/hypr ~/.config/hypr-old
}
