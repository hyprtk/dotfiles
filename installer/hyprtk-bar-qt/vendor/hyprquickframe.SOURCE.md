# Vendored source: HyprQuickFrame

- Upstream: https://github.com/Ronin-CK/HyprQuickFrame
- Pinned commit: `a41141195e7c918ac6f57fa41a89d4caca212003`
  (2026-09-20, "Merge pull request #39 from nathan-havens/main")
- License: MIT — see `hyprquickframe/LICENSE` (JamDon2, Ronin-CK)
- Vendored: 2026-10-19 with
  `git archive <commit> | tar -x -C vendor/hyprquickframe`

The directory `hyprquickframe/` is the upstream tracked tree at that commit plus
the documented patch set in `vendor/patches/`:

- `hyprquickframe-hyprtk.patch` — cumulative hyprtk patch:
  - no-freeze `grim` + `slurp` fallback when `ScreencopyView` produces no frame
    (NVIDIA/screencopy failures), forced via `HQF_FORCE_FALLBACK=1`; guards
    `captureSource` against stale outputs; falls back to the focused output when
    geometry is unavailable;
  - editor capability probe + `swappy` mode (satty/gradia optional), edit tab
    hidden when no editor is installed;
  - share toggle hidden when `kdeconnect-cli` is absent, POSIX `awk` device-id
    parsing (no GNU `grep -P`);
  - gradia launch detached without `hyprctl dispatch exec --` (broken on
    Hyprland 0.55+ Lua dispatch).

Do not edit the vendored tree without regenerating the patch and updating this
file. Upstreaming these changes is preferred; re-vendor from the new commit once
accepted.

Installed by `hyprtk-bar-qt`'s `install.sh` to
`~/.local/share/hyprtk-bar-qt/hyprquickframe/` and launched by
`bin/hyprtk-screenshot` (`qs -p <dir> -n`).

Plan / requirements: `PLAN-HYPRQUICKFRAME.md`.
