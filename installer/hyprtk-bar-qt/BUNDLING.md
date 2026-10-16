# Bundling & vendoring

hyprtk-bar-qt is a self-contained vendored app: it vendors the pieces it needs
so a machine with Quickshell/Qt6 installed needs no extra downloads.

## What is bundled

| Item | Path | Installed to |
|------|------|--------------|
| pywal16 (`wal`) | `vendor/pywal16/` | `~/.local/share/hyprtk-bar-qt/vendor/pywal16` (+ a `wal` launcher in the venv, symlinked to `~/.local/bin/wal`) |
| Nerd Font | `assets/fonts/SymbolsNerdFont-Regular.ttf` | `~/.local/share/fonts/` |
| Bar themes | `themes/` | `~/.config/hyprtk-bar-qt/themes/` |
| Clock widget themes | `assets/widgets/clock/` | `~/.config/hyprtk-bar-qt/widget-themes/clock/` |
| Wallpapers | `Wallpapers/` | `~/Pictures/Wallpapers/` (no-clobber) |
| Scripts | `scripts/` | `~/.local/share/hyprtk-bar-qt/scripts/` |
| Default config | `config.json` | `~/.config/hyprtk-bar-qt/config.json` (fresh installs only) |

## pywal16

`vendor/pywal16/` is a verbatim copy of
[pywal16](https://github.com/eylles/pywal16) (fork `hyprtk/pywal16`,
`wal 3.8.15`). It is pure Python (stdlib only) and is run from the bar's venv
via `PYTHONPATH` — no `pip install`, no build, no network. See
`vendor/pywal16/VENDOR.md`. Do not edit the vendored tree; fixes belong in the
bar, not upstream copies.

## Quickshell

Quickshell is **not** bundled — the prebuilt relocatable bundle (bundled Qt) was
~59 MB stripped / 141 MB raw, too large for the GitHub repos. Instead, where the
distro does not package it (Debian/Ubuntu/Mint/Fedora/openSUSE/Void), `install.sh`
(`build_quickshell_from_source`) installs the build deps and clones + builds it
from source:

```sh
git clone --depth=1 https://github.com/quickshell-mirror/quickshell.git
cmake -S quickshell -B quickshell/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build quickshell/build -j"$(nproc)"
sudo cmake --install quickshell/build && sudo ldconfig
```

It needs **Qt ≥ 6.6** plus private Qt headers, so the build only succeeds where
the system Qt is new enough; on Debian 12 / Ubuntu 24.04 / Mint 22 (Qt 6.4) it
fails with a clear warning. On Arch/Gentoo/Nix the packaged `quickshell` is used
and nothing is built.

## Re-vendoring into hyprtk-multi-distro / merged

The bar is vendored byte-identically:

```sh
git -C <hyprtk-bar-qt checkout> archive HEAD | tar -x -C <tree>/installer/hyprtk-bar-qt
```

(`rm -rf` the destination first so removed files do not linger.)
