# Installing hyprtk-file-manager

This document covers a standalone install, the suite/vendored install, and how
to make the file manager the desktop default. It applies to version 1.6.0.

## Quick start

```sh
git clone https://github.com/hyprtk/hyprtk-file-manager.git
cd hyprtk-file-manager
./install.sh
hyprtk-fm
```

`install.sh` copies the app to
`${XDG_DATA_HOME:-$HOME/.local/share}/hyprtk-file-manager`, creates the
`~/.local/bin/hyprtk-fm` symlink and installs the **Files** desktop entry.
It refuses to run without `qs` (Quickshell) or `python3`.

## Requirements

### Required

| | |
|---|---|
| **Quickshell** | the `qs` binary on `PATH` (Qt 6 QML runtime) |
| **Python** | 3.10 or newer |
| **PyGObject** | `python-gobject` / `python3-gi` — network shares and GVfs |
| **GIO** | the `gio` command — trash and GVfs mounts |
| **UDisks2** | device mount/eject (`udisksctl`) |

Only `qs` and `python3` are checked by the installer; the rest are runtime
requirements. The app starts without them, but the corresponding features
(trash, devices, network) will report errors.

### Optional

| Tool | Enables |
|---|---|
| `rg` (ripgrep) | recursive content search; without it search is name-only |
| `smbclient` | SMB share listing fallback |
| `showmount` (nfs-utils / nfs-common) | NFS export listing |
| `avahi-browse` | mDNS host discovery on the local network |
| `vipsthumbnail` (libvips) | fast image thumbnails |
| `ffmpeg` | video thumbnails |
| `pdftoppm` (poppler) | PDF thumbnails |
| `xdg-open` (xdg-utils) | open files in their default application |
| `pkexec` (polkit) | “Open terminal as root” |
| a terminal | open-terminal action: `alacritty`, `kitty`, `foot`, `wezterm`, or `$TERMINAL` |

Set `QT_QPA_PLATFORMTHEME=gtk3` in the environment so Qt picks up the icon
theme; the `hyprtk-fm` launcher and `make run` set it for you.

## Per-distro dependencies

Install the required set, then any optional tools you want.

### Arch and derivatives

```sh
sudo pacman -S --needed python python-gobject gvfs gvfs-smb gvfs-nfs udisks2 \
    xdg-utils
# optional
sudo pacman -S --needed ripgrep samba nfs-utils avahi libvips ffmpeg poppler
```

Quickshell must provide `qs` (normally the `quickshell` package; if your
mirror lacks it, use the AUR `quickshell-git`).

### Debian and Ubuntu

```sh
sudo apt install python3 python3-gi gvfs-backends udisks2 xdg-utils
# optional
sudo apt install ripgrep smbclient nfs-common avahi-utils libvips-tools \
    ffmpeg poppler-utils
```

`quickshell` is not in older Debian/Ubuntu archives; install it from your
distro's package, a PPA, or build it. Without `qs` on `PATH` the installer
aborts.

### Fedora

```sh
sudo dnf install python3 python3-gobject gvfs gvfs-smb gvfs-nfs udisks2 \
    xdg-utils
# optional
sudo dnf install ripgrep samba-client nfs-utils avahi-tools vips-tools \
    ffmpeg poppler-utils
```

Install `quickshell` from the Fedora package/COPR if it is not already present.

### openSUSE

```sh
sudo zypper install python3 python3-gobject gvfs gvfs-backends udisks2 \
    xdg-utils
# optional
sudo zypper install ripgrep samba nfs-client avahi libvips-tools ffmpeg \
    poppler-tools
```

### Void Linux

```sh
sudo xbps-install -S python3 python3-gobject gvfs gvfs-smb udisks2 xdg-utils
# optional
sudo xbps-install -S ripgrep samba nfs-utils avahi libvips ffmpeg poppler
```

### Alpine

```sh
sudo apk add python3 py3-gobject3 gvfs udisks2 xdg-utils
# optional
sudo apk add ripgrep samba-client nfs-utils avahi-tools vips-tools ffmpeg \
    poppler-utils
```

## Install options

### Standalone (this repository)

```sh
./install.sh              # install
./install.sh --uninstall  # remove
HYPRTK_DRYRUN=1 ./install.sh   # show what would be installed, change nothing
```

Installed layout:

| Path | Content |
|---|---|
| `~/.local/share/hyprtk-file-manager/` | application tree (`shell.qml`, `backend/`, `surface/`, …) |
| `~/.local/bin/hyprtk-fm` | launcher symlink |
| `~/.local/share/applications/hyprtk-file-manager.desktop` | Files desktop entry |
| `~/.local/state/hyprtk-file-manager/` | created at runtime: session and undo journal |
| `~/.cache/hyprtk-file-manager/thumbs/` | created at runtime: thumbnail cache |

Ensure `~/.local/bin` is on your `PATH`.

### Suite install (hyprtk desktop)

On a hyprtk system, install from the main installer in `hyprtk-merged`:

```sh
cd hyprtk-merged
./1-install.sh
```

The suite installs `config-manager` and the bar first, then the file manager
from `installer/hyprtk-file-manager/`. It also exports `FILEMANAGER=hyprtk-fm`
for the session, registers the XDG `inode/directory` handler, and keeps Thunar
as a fallback. The suite package lists already include the network/GVfs
packages.

### Bar-only install

The bar (`hyprtk-bar-qt`) ships a vendored copy and its `install.sh` provisions
the app, `hyprtk-fm` and the Files entry alongside HyprQuickFrame/pywal16.
`--dry-run` reports it; `--uninstall` leaves the file manager in place. A
bar-only install does **not** add the file manager's system dependencies — the
distro packages above still apply, or device/network features will be limited.

## Make it the default

The suite sets this automatically. For a manual install:

```sh
xdg-mime default hyprtk-file-manager.desktop inode/directory
```

Bind `Super+F` in your Hyprland config (the suite does this) to
`hyprtk-fm`, and optionally add it to the bar's quick links.

## Verify the install

```sh
hyprtk-fm version                    # prints the version
hyprtk-fm places                     # JSON places/bookmarks/drives
hyprtk-fm ~/Downloads                # opens the window
gio list smb://<host>/               # GVfs sees the network stack
```

From the source tree, `make qa` runs the unit tests, syntax checks, the
performance budget and an installer round-trip in a temporary `HOME`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `qs (Quickshell) is required` | install Quickshell so `qs` is on `PATH`, then re-run `./install.sh` |
| Icons render as placeholders | Qt has no icon theme: export `QT_QPA_PLATFORMTHEME=gtk3` (the launcher does this) |
| Trash says the location is not supported | `gio trash` refuses system-internal mounts (e.g. `/tmp`, `/proc`); use permanent delete there |
| Network shows no hosts | check ports 445/139/2049/548 on the LAN and that `avahi-browse` is installed; rescan from the Network header |
| Host lists “No shares found” | credentials or share permissions; SMB needs `smbclient`/GVfs, NFS needs `showmount` and the server's exports |
| Share click asks for a password every time | the keyring is unavailable — unlock/login to the keyring so `PasswordSave.PERMANENTLY` can store the credential |
| Unmount/eject does nothing | `udisks2` missing or polkit refused the action; eject is intentionally unmount-only (no power-off) |
| No image/video/PDF thumbnails | install `libvips` (`vipsthumbnail`), `ffmpeg`, and `poppler` (`pdftoppm`) |
| Open terminal fails | no supported terminal found; install one or export `TERMINAL=…` |
| Root terminal asks for nothing / fails | `pkexec` missing or no polkit agent; the suite normally runs one |
| Window closes but the process stays | quit with `Ctrl+Q`; closing via the compositor can leave `qs` alive |
| Keys go to another window after a dialog | focus the pane and retry; hidden inputs reclaim focus only for the active pane |

## Uninstall

```sh
./install.sh --uninstall
```

This removes the application tree, the `hyprtk-fm` symlink and the desktop
entry. Session state (`~/.local/state/hyprtk-file-manager/`) and the thumbnail
cache (`~/.cache/hyprtk-file-manager/`) are left behind; delete them manually
if desired.

If you installed through the suite, remove it with the suite installer or
simply delete `~/.local/share/hyprtk-file-manager/` and the two launcher/entry
files listed above.

## License

GPL-3.0. See [LICENSE](LICENSE).
