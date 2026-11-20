#!/bin/bash
# hyprtk-pkglist
# ── media ─────────────────────────────────────────────────────────
_PKGDIR="$(cd "$(dirname "$0")" && pwd)"
. "$_PKGDIR/../../installer/scripts/pkgmanager.sh"

# hyprtk-shot needs grim (capture), slurp (cross-output region selection) and
# wl-clipboard (copy); hyprtk-rec needs wf-recorder (already here) and pactl
# (pipewire-pulse). notify-send comes from the libnotify package below.
case "$HYPRTK_PM" in
pacman)
    PKGS=(xclip pamixer wf-recorder grim slurp wl-clipboard libnotify
          pavucontrol tumbler vlc mpv ffmpeg cava)
    AUR=(hyprquickframe-git)
    ;;
apt)
    PKGS=(xclip pamixer wf-recorder grim slurp wl-clipboard libnotify-bin
          pavucontrol tumbler vlc mpv ffmpeg cava)
    ;;
dnf)
    PKGS=(xclip pamixer wf-recorder grim slurp wl-clipboard libnotify
          pavucontrol tumbler vlc mpv ffmpeg-free cava)
    ;;
zypper)
    PKGS=(xclip pamixer wf-recorder grim slurp wl-clipboard libnotify-tools
          pavucontrol tumbler vlc mpv ffmpeg cava)
    ;;
xbps)
    PKGS=(xclip pamixer wf-recorder grim slurp wl-clipboard libnotify
          pavucontrol tumbler vlc mpv ffmpeg cava)
    ;;
apk)
    PKGS=(xclip pamixer wf-recorder grim slurp wl-clipboard libnotify
          pavucontrol tumbler vlc mpv ffmpeg cava)
    ;;
esac

if [ "${1:-}" = "--list" ]; then printf '%s ' "${PKGS[@]}" "${AUR[@]}"; echo; exit 0; fi

echo " Media Packages "
pkg_install "${PKGS[@]}"
aur_install "${AUR[@]}"
echo ""
