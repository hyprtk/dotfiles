#!/bin/bash
# kiro distro steps — removes xfce4 + sddm-git + fastfetch-git,
# os-release to /usr/lib/ (no splash/bootctl), backs up existing hypr config.
# grudupdater.sh is NOT shipped in any source tree — omitted (guarded no-op).

pre_install() {
    sudo pacman -Rns plasma-meta kde-applications-meta --noconfirm
    sudo pacman -Rns plasma kde-applications --noconfirm
    sudo pacman -Rns xfce4 xfce4-goodies thunar catfish thunar-shares-plugin --noconfirm
    yay -Rns sddm-git fastfetch-git --noconfirm
    sleep 5
}

pre_hypr_symlink() {
    [ -e ~/.config/hypr ] && mv ~/.config/hypr ~/.config/hypr-old
    return 0
}

grudupdater() {
    # Kiro's original installer ran ~/hyprtk/installer/scripts/grudupdater.sh here, but that
    # script has no source in any of the 11 distro trees. Skipped by design.
    :
}
