# hyprtk-merged — Merge Plan & Build Record

Sources: the 11 distro trees in `/home/hyprtk/Projects/AI-Projects/Source-Files/dots/`
(`arch-dots`, `archbang-dots`, `archcraft-dots`, `archman-dots`, `bslx-dots`,
`cachy-dots`, `endeavour-dots`, `garuda-dots`, `kiro-dots`, `manjaro-dots`, `reborn-dots`).
No reference to any other tree. The 11 source trees are the entire universe of input.

## 1. Baseline finding

`arch-dots` is the natural baseline: every other tree is `arch-dots` plus a small
delta set. All 11 share the same ~45 top-level folders and a ~630-line
`1-install.sh` that differs from arch's by only 5–18 lines per distro.

## 2. Target layout (built)

Four top-level directories keep the parent level clean; only the installer and
docs sit at the root. Paths are relative to the merged repo root (deploys to `~/hyprtk`).

```
hyprtk-merged/
├── 1-install.sh                 # unified installer (single file, top level)
├── CHANGELOG  cheatsheet.md  LICENSE  README.md  .zshrc  .gitattributes   # docs, top level
├── assets/                      # fonts, Wallpapers, themes, papirus-icons, splash, screenshots, thumbnails
├── configs/                     # all app/system configs (alacritty…zshrc, root, dracut, nvidia, grub)
├── hypr/                        # all Hyprland config & settings (lua, conf, scripts, packages)
├── installer/
│   ├── library.sh               # shared helpers
│   ├── os-release/              # os-release-<distro> × 11 + cachyos-branding
│   ├── scripts/                 # helper/utility scripts (+ verify/, build-merged.sh)
│   ├── standalone/              # oh-my-posh, matuwall, awww, papirus-folders, hyprtk-menu, hyprtk-themer, theme-gui
│   ├── hyprtk-menu/             # vendored app (main.py, hyprtk_menu/, assets/)
│   ├── hyprtk-arc-menu/         # vendored app (src/, install.sh, pyproject.toml, .desktop)
│   └── steps/<distro>.sh        # per-distro hooks × 11
└── distro/<name>/               # per-distro overlays (deltas only, mapped paths)
```

### Directory-to-source mapping

| Source top-level | Merged location |
|---|---|
| `fonts/`, `Wallpapers/`, `themes/`, `papirus-icons/`, `splash/`, `screenshots/` | `assets/` |
| `alacritty btop fastfetch figlet gtk hyprlogout hyprpicker matuwall Mousepad nvim ohmyposh oh-my-zsh ranger rofi sddm smb starship swappy swaylock Thunar User-Management vim wal waypaper wob xfce4 zshrc root dracut nvidia grub` | `configs/` |
| `hypr/` | `hypr/` |
| `os-release/`, `scripts/`, `standalone/` | `installer/` |
| top-level files (`1-install.sh`, `CHANGELOG`, `cheatsheet.md`, `default.png`, `.folder.png`, `.gitattributes`, `LICENSE`, `README.md`, `.zshrc`) | top level |

### Top-level file rule

Every top-level file beside `1-install.sh` in the sources stays top level in the
merged repo. `default.png` is additionally mirrored under `assets/Wallpapers/`.

### Sync exclusions

- `configs/gtk/gtk-3.0/bookmarks` — user-local only, never synced across locations
- `PLANNING.md` — merged only, never copied to live or GitHub

## 3. Unified installer design (built)

Single `1-install.sh` = the arch pipeline, with distro divergences extracted into
hooks in `installer/steps/<distro>.sh`. The installer sources the matching steps
file after auto-detecting the distro (with manual fallback) and calls the hook if
defined:

- `pre_install` — package removals:
  - archbang: `pacman -Rns swaylock`
  - bslx: `pacman -Rcs plasma* kde-applications*`
  - kiro: `pacman -Rns xfce4 xfce4-goodies thunar catfish thunar-shares-plugin` + `yay -Rns sddm-git fastfetch-git` + `sleep 5`
- `install_os_release` — default: `os-release-<distro>` → `/usr/lib/`
  - archbang: → `/etc/`
  - cachy: `/usr/lib/` + `/run/systemd/propagate/.os-release-stage/` + `/run/user/$UID/...` + cachyos-branding hook
- `install_boot` — arch only: splash → `/usr/share/systemd/bootctl/` + `mkinitcpio -P`
- `grudupdater` — kiro: guarded no-op (script has no source in any of the 11 trees)
- `grub_wallpaper` — bslx: copy `current-wallpaper.png` to `/boot/grub/`
- `wal_init` — archcraft: `wal -i ~/.cache/current-wallpaper.png`
- `pre_hypr_symlink` — all but arch: `mv ~/.config/hypr ~/.config/hypr-old`
- `setup_sudoers` — reborn: multiline sudoers

Distro detection: reads `/etc/os-release` ID, maps (arch, archbang, archcraft,
archman, bluestar/bslx, cachyos/cachy, endeavour/endeavouros, garuda, kiro,
manjaro, reborn/rebornos), with an interactive fallback.

### Shebangs

All `.sh` files use correct shebangs (`#!/bin/bash` or `#!/bin/sh`). Fixed from
`#/bin/bash` (missing `!`) which caused silent failures when invoked via `./script.sh`.

### Intentionally removed (excluded from completeness check)

User removed the following from the merged tree; `verify-completeness.sh` excludes
them via `REMOVED_EXCLUDE` (see `installer/scripts/verify/verify-completeness.sh`):

- `configs/root/.local/share/themes/Arc-Azure-dodger-blue*` — 3 GTK themes (large)
- `configs/root/.config/nwg-look/` + `configs/root/.local/share/nwg-look/`
- `configs/waybar/` (and the source waybar theme set) — removed outright:
  hyprtk-bar is the taskbar and owns the notification daemon.
  `hypr/scripts/generate-aero-colors.sh` (only used by the waybar launcher) is
  gone too.

### Standalone wrappers

All standalone scripts in `installer/standalone/` use `$HOME` instead of hardcoded
paths to work on any user account:

- `hyprtk-menu` → `$HOME/.local/share/hyprtk-menu/main.py`
- `theme-gui` → `$HOME/.local/share/theme-gui/venv/bin/python3`
- `hyprtk-themer` → calls `theme-gui` (no path needed)

`hyprtk-arc-menu` does **not** use a `standalone/` wrapper — its own
`installer/hyprtk-arc-menu/install.sh` writes `~/.local/bin/hyprtk-arc-menu` and
`hyprtk-arc-menu-toggle` directly (full paths, so they work even when
Hyprland's exec PATH lacks `~/.local/bin`).

### hyprtk-menu (added, not in the 11 sources)

The app menu launcher. Vendored as `installer/hyprtk-menu/` (main.py, hyprtk_menu/,
assets/) and deployed by `installer/scripts/hyprtk-menu-install.sh`, invoked from
`1-install.sh` right after the standalone symlink step. The PATH wrapper lives at
`installer/standalone/hyprtk-menu` (symlinked to `~/.local/bin` by
`_installSymLink standalone`); it execs `$HOME/.local/share/hyprtk-menu/main.py`.
Waybar module `custom/hyprtk-menu` calls `$HOME/.local/bin/hyprtk-menu --toggle`.

### theme-gui + hyprtk-themer (added, not in the 11 sources)

GTK4/Adwaita theme manager. Installed to `~/.local/share/theme-gui/` via
`installer/theme-gui/install.sh`. Standalone wrapper at `installer/standalone/theme-gui`
symlinked to `~/.local/bin`. `hyprtk-themer` is a thin wrapper that calls `theme-gui`.
Keybinding: `SUPER+ALT+T` → `theme-gui`.

### hyprtk-arc-menu (added, not in the 11 sources)

Material-style radial/arc menu (GTK3 + gtk-layer-shell). A FAB-style button sits
in a configurable screen position and fans its items out on click — 180° at the
top/bottom center, 90° at corners — each item launching a command. Middle-click
anywhere on the menu quits the app.

Vendored as `installer/hyprtk-arc-menu/` (src/, install.sh, pyproject.toml,
hyprtk-arc-menu.desktop) and installed by `1-install.sh` via its own
`install.sh`, exactly like theme-gui. Config at
`~/.config/hyprtk-arc-menu/config.json`:

```json
{
  "position": "bottom-right",
  "shape": "circle",
  "transparent": false,
  "follow_waybar": true,
  "margin": 24,
  "radius": 140,
  "fab_size": 56,
  "item_size": 48,
  "animation_time": 300,
  "items": [
    { "icon": "firefox", "command": "firefox", "tooltip": "Firefox" }
  ]
}
```

Theming: mirrors the active waybar theme's glass + text color live (watches
`~/.cache/.themestyle.sh`), keeps pywal `color5`/`color6` accents, and supports
`shape: square` (items encircle the button on a square perimeter) and
`transparent: true` (icons only). The in-menu Settings item opens a dialog to
edit everything, including the item list (add/edit/remove, move up/down, and
search installed apps).

Keybinding: `SUPER+CTRL+M` → `hyprtk-arc-menu-toggle`.

## 4. Verification (all PASSED)

1. **Completeness diff** — every file in all 11 source trees is accounted for in
   the canonical core or its `distro/<name>/` overlay. `COMPLETENESS: ALL 11
   DISTROS FULLY ACCOUNTED`.
2. **Reference audit** — every `~/hyprtk/...` path in the merged tree resolves.
   Known dead refs (reload.sh, nvidia.conf, hyprland.conf, applauncher.sh,
   growthrate.py, grudupdater.sh, looking-glass.sh, qtile/picom, .bashrc,
   os-release-) are whitelisted in `audit-references.sh`.
3. **bash -n** — all shell scripts pass.
4. **Dry-run** — for each distro, canonical+overlay deployed to sandbox; all
   referenced paths resolve. All 11 pass.
5. **os-release** — all 11 `installer/os-release/os-release-<distro>` byte-match
   sources; cachyos-branding matches.
6. **Installer hooks** — each distro's steps file exports exactly the hooks its
   original installer diverged with.

### Verification scripts

Located in `installer/scripts/verify/`:
- `verify-completeness.sh` — checks all source files accounted for
- `audit-references.sh` — checks all `~/hyprtk/` refs resolve (dead refs whitelisted)
- `audit-installer.sh` — checks installer commands covered
- `dryrun.sh` — simulates per-distro deployment, checks all refs resolve

Both `audit-references.sh` and `dryrun.sh` auto-detect ROOT via `$(dirname "$0")`
and centralize dead refs in a `DEAD_REFS` array.

Rebuild script: `installer/scripts/build-merged.sh` (recreates canonical tree +
overlays from the 11 sources). NOTE: it `rm -rf`s the target — run with care.

## 5. Location sync

Three copies of the installer exist:

| Location | Purpose |
|----------|---------|
| `~/Projects/AI-Projects/hyprtk-merged/` | Source of truth (merged build) |
| `~/hyprtk/` | Live install (symlinked to `~/.local/bin`) |
| `~/Documents/GitHub/dotfiles/` | GitHub push target |

Sync flow: merged → live → GitHub. All verified via `md5sum` and `diff -rq`.

## 6. Recent tweaks & additions (2026-09-02)

- **hyprtk-arc-menu project added** — new standalone app vendored at
  `installer/hyprtk-arc-menu/`, wired into `1-install.sh` (step mirrors
  theme-gui). See the project section above.
- **hypr config additions** (in `hypr/`, same in merged + live):
  - `keybindings.lua` — added
    `hl.bind(mainMod .. " + CTRL + M", hl.dsp.exec_cmd("$HOME/.local/bin/hyprtk-arc-menu-toggle"))`
  - `autostart.lua` — added `hl.exec_cmd("hyprtk-arc-menu")`
- **README.md** — added an **Applications** section documenting the three
  bundled apps (theme-gui, hyprtk-menu, hyprtk-arc-menu) with their config
  JSON and theming notes.
- **Sync note** — `README.md` and the app bundles are kept identical across
  merged / live / GitHub. `PLANNING.md` remains merged-only (see sync
  exclusions).
