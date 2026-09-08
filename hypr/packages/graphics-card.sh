#!/bin/bash

echo "
#########################################################
#                                                       #
#            Which Graphics Card do you have?           #
#                                                       #
#########################################################

1) Intel
2) AMD
3) Nvidia
Defaults to AMD if you choose
something else
"
echo ""
read -r GRAPHICSCARD
case "$GRAPHICSCARD" in
1)
  sudo pacman -S --noconfirm xf86-video-intel mesa vulkan-intel vulkan-intel;;
2|*)
  sudo pacman -S --noconfirm xf86-video-amdgpu mesa vulkan-radeon vdpauinfo corectrl libvdpau vdpauinfo
  sudo sed -i 's/MODULES=()/MODULES=(amdgpu)/' /etc/mkinitcpio.conf 2>/dev/null || true
  sudo mkinitcpio --config /etc/mkinitcpio.conf --generate /boot/initramfs-custom.img 2>/dev/null || true;;
3)
  sudo sed -i 's/GRUB_CMDLINE_LINUX="[^"]*"/GRUB_CMDLINE_LINUX="rootfstype=ext4 nvidia_drm.modeset=1 rd.driver.blacklist=nouveau modprob.blacklist=nouveau"/' /etc/default/grub 2>/dev/null || true
  if command -v grub-mkconfig >/dev/null 2>&1; then
    sudo grub-mkconfig -o /boot/grub/grub.cfg
  fi
  sudo sed -i 's/MODULES=()/MODULES=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)/' /etc/mkinitcpio.conf 2>/dev/null || true
  echo -e "options nvidia-drm modeset=1" | sudo tee -a /etc/modprobe.d/nvidia.conf > /dev/null 2>&1 || true
  sudo pacman -S --noconfirm nvidia-open-dkms nvidia-utils nvidia-settings qt5-wayland qt5ct qt6-wayland qt6ct libva && yay --noconfirm -S libva-nvidia-driver-git
  sudo mkinitcpio --config /etc/mkinitcpio.conf --generate /boot/initramfs-custom.img 2>/dev/null || true;;
esac
echo ""
clear
echo "
#########################################################
#                                                       #
#         Your Graphics Card has been installed         #
#                                                       #
#########################################################
"