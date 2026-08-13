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
├── assets/                      # fonts, Wallpapers, themes, papirus-icons, splash, screenshots
├── configs/                     # all app/system configs (alacritty…zshrc, root, dracut, nvidia, grub)
├── hypr/                        # all Hyprland config & settings (lua, conf, scripts, packages)
├── installer/
│   ├── library.sh               # shared helpers
│   ├── os-release/              # os-release-<distro> × 11 + cachyos-branding
│   ├── scripts/                 # helper/utility scripts (+ verify/, build-merged.sh)
│   ├── standalone/              # oh-my-posh, matuwall, awww, papirus-folders, hyprtk-menu
│   ├── hyprtk-menu/             # vendored app (main.py, hyprtk_menu/, assets/)
│   └── steps/<distro>.sh        # per-distro hooks × 11
└── distro/<name>/               # per-distro overlays (deltas only, mapped paths)
```

### Directory-to-source mapping

| Source top-level | Merged location |
|---|---|
| `fonts/`, `Wallpapers/`, `themes/`, `papirus-icons/`, `splash/`, `screenshots/` | `assets/` |
| `alacritty btop dunst fastfetch figlet gtk hyprlogout hyprpicker matuwall Mousepad nvim ohmyposh oh-my-zsh ranger rofi sddm smb starship swappy swaylock Thunar User-Management vim wal waybar waypaper wob xfce4 zshrc root dracut nvidia grub` | `configs/` |
| `hypr/` | `hypr/` |
| `os-release/`, `scripts/`, `standalone/` | `installer/` |
| top-level files (`1-install.sh`, `CHANGELOG`, `cheatsheet.md`, `default.png`, `.folder.png`, `.gitattributes`, `LICENSE`, `README.md`, `.zshrc`) | top level |

### Top-level file rule

Every top-level file beside `1-install.sh` in the sources stays top level in the
merged repo. `default.png` is additionally mirrored under `assets/Wallpapers/`.

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

### Intentionally removed (excluded from completeness check)

User removed the following from the merged tree; `verify-completeness.sh` excludes
them via `REMOVED_EXCLUDE` (see `installer/scripts/verify/verify-completeness.sh`):

- `configs/root/.local/share/themes/Arc-Azure-dodger-blue*` — 3 GTK themes (large)
- `configs/root/.config/nwg-look/` + `configs/root/.local/share/nwg-look/`
- source waybar theme set (`Bottom`, `Top`, `Bottom-Blur`, `Top-Blur`,
  plain `hyprtk`, `myconfig`, `default/myconfig`) — replaced by the custom
  `hyprtk-*` theme family
- `hypr/scripts/generate-aero-colors.sh` was restored from `old/hyprtk-merged`
  (referenced by `configs/waybar/launch.sh:42`, `wallpaper-colors.sh`,
  `wal-watcher.sh`, `wallpaper-restore.sh`)

### hyprtk-menu (added, not in the 11 sources)

The app menu launcher. Vendored as `installer/hyprtk-menu/` (main.py, hyprtk_menu/,
assets/) and deployed by `installer/scripts/hyprtk-menu-install.sh`, invoked from
`1-install.sh` right after the standalone symlink step. The PATH wrapper lives at
`installer/standalone/hyprtk-menu` (symlinked to `~/.local/bin` by
`_installSymLink standalone`); it execs `~/.local/share/hyprtk-menu/main.py`.
Waybar module `custom/hyprtk-menu` calls `$HOME/.local/bin/hyprtk-menu --toggle`.

## 4. Verification (all PASSED)

1. **Completeness diff** — every file in all 11 source trees is accounted for in
   the canonical core or its `distro/<name>/` overlay. `COMPLETENESS: ALL 11
   DISTROS FULLY ACCOUNTED`.
2. **Reference audit** — every `~/hyprtk/...` path in the merged tree resolves.
   5 source-level dead refs (reload.sh, nvidia.conf, applauncher.sh,
   growthrate.py, looking-glass.sh, qtile/picom, .bashrc) are missing in the
   SOURCES themselves — preserved as-is, matching source.
3. **bash -n** — all shell scripts pass.
4. **Dry-run** — for each distro, canonical+overlay deployed to sandbox; all
   referenced paths resolve. All 11 pass.
5. **os-release** — all 11 `installer/os-release/os-release-<distro>` byte-match
   sources; cachyos-branding matches.
6. **Installer hooks** — each distro's steps file exports exactly the hooks its
   original installer diverged with.

Verification scripts live in `installer/scripts/verify/`:
`verify-completeness.sh`, `audit-references.sh`, `audit-installer.sh`, `dryrun.sh`.

Rebuild script: `installer/scripts/build-merged.sh` (recreates canonical tree +
overlays from the 11 sources). NOTE: it `rm -rf`s the target — run with care.
