#!/bin/bash
#
# ─────────────────────────────────────────────────────────────────
#   HYPRTK · Cleanup
#   Part of the Hyprtk desktop suite · github.com/hyprtk
# ─────────────────────────────────────────────────────────────────


yay -Scc
su -c 'pacman -Qtdq | pacman -Rns -'
su -c 'pacman -Qqd | pacman -Rsu -'

