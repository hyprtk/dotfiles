#!/usr/bin/env bash
#
# ██       ██
#░██      ░██            ██   ██ ██████            ██████
#░██   █  ░██  ██████   ░░██ ██ ░██░░░██  ██████  ░██░░░██  █████  ██████
#░██  ███ ░██ ░░░░░░██   ░░███  ░██  ░██ ░░░░░░██ ░██  ░██ ██░░░██░░██░░█
#░██ ██░██░██  ███████    ░██   ░██████   ███████ ░██████ ░███████ ░██ ░
#░████ ░░████ ██░░░░██    ██    ░██░░░   ██░░░░██ ░██░░░  ░██░░░░  ░██
#░██░   ░░░██░░████████  ██     ░██     ░░████████░██     ░░██████░███
#░░       ░░  ░░░░░░░░  ░░      ░░       ░░░░░░░░ ░░       ░░░░░░ ░░░
#
# by hyprtk (Kori Tk) (2026)
####################################
#
if [ -f /usr/bin/waypaper ]; then
    echo ":: Launching waypaper in /usr/bin"
    waypaper $1 &
elif [ -f $HOME/.local/bin/waypaper ]; then
    echo ":: Launching waypaper in $HOME/.local/bin"
    $HOME/.local/bin/waypaper $1 &
else
    echo ":: waypaper not found"
fi
