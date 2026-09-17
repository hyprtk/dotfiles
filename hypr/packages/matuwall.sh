# ── matuwall ─────────────────────────────────────────────────────────
#!/bin/bash
echo ""
echo " Matuwall Installer "
echo ""
echo "Installing Matuwall wallpaper picker..."
echo ""

# Matuwall is now a C11 + meson app (upstream moved off Python), so the old
# venv/pip install no longer applies. The AUR `matuwall` package is still the
# old Python/GTK4 app, so build the C version from source.
if ! command -v matuwall >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm base-devel meson ninja git scdoc
    if [ -d "$HOME/.local/share/Matuwall/.git" ]; then
        git -C "$HOME/.local/share/Matuwall" pull --ff-only
    else
        rm -rf "$HOME/.local/share/Matuwall"
        git clone https://github.com/naurissteins/Matuwall.git "$HOME/.local/share/Matuwall"
    fi
    (
        cd "$HOME/.local/share/Matuwall" || exit 1
        [ -d build ] || meson setup build --buildtype=release
        ninja -C build
        sudo ninja -C build install
    )
fi

if command -v matuwall >/dev/null 2>&1; then
    echo " Matuwall installed! "
else
    echo "  ! matuwall is not on PATH — the build failed (see above)" >&2
    exit 1
fi
sleep 2
