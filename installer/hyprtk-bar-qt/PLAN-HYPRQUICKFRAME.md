# HyprQuickFrame vendoring — plan & requirements

Status: **Phases 1–4 done.** Optional bar action deferred; NVIDIA hardware and
fractional-scale validation still pending.
Created 2026-10-19.

Goal: ship [HyprQuickFrame](https://github.com/Ronin-CK/HyprQuickFrame) as the
hyprtk screenshot overlay, installed and maintained by `hyprtk-bar-qt`, working
on every distro family `hyprtk-merged` supports (Arch, Debian/Ubuntu/Mint,
Fedora, openSUSE, Void, Alpine) and on AMD / Intel / NVIDIA GPUs.

This complements `PLAN.md` (the GTK-parity remediation plan); it does not
replace it.

---

## 1. What the utility is

A one-shot Quickshell overlay, separate from the bar shell:

- Freezes every monitor with `ScreencopyView` (`Quickshell.Wayland`).
- Region / window / full-screen selection (`QtQuick.Shapes`, a `.qsb` shader).
- Captures with external `grim`, copies with `wl-copy`, notifies with
  `notify-send`; optional editor (`satty`/`gradia`), optional KDE Connect share,
  optional post-save hook.
- Invoked as `qs -p <dir> -n`; exits after the capture.

Upstream: MIT (JamDon2, Ronin-CK). Pinned commit **`a411411`** (2026-09-20;
same code as the AUR's `57f0629`, only README changed). Upstream tags stop at
`v1.1.0` (May 2026), so **pin a commit, not a tag**.

Vendored tree: `vendor/hyprquickframe/` (byte-identical `git archive`), with
provenance in `vendor/hyprquickframe.SOURCE.md`. Never patch it in place: make
changes upstream or carry a documented patch and re-vendor.

---

## 2. Runtime requirements

### Hard

| Requirement | Why | Notes |
|---|---|---|
| Quickshell ≥ **0.3.0** | overlay, screencopy | prebuilt bundle **v0.3.0 + bundled Qt 6.8.3** verified to load the overlay on AMD |
| Hyprland ≥ 0.55 | Hyprland IPC + Lua config | merged already enforces this |
| `grim` | actual capture | **not currently installed by merged**; add to bar EXTRAS |
| `wl-clipboard` (`wl-copy`) | clipboard | already in bar EXTRAS |
| `libnotify` (`notify-send`) | notifications | already in bar EXTRAS; name varies (`libnotify-bin`, `libnotify-tools`) |
| `sh`, `coreutils` (`timeout`, `mkdir`, `rm`), `hyprctl` | pipeline | present |

### Optional

- **Editor**: upstream supports `satty`/`gradia`. `satty` is **not packaged** on
  Debian (bookworm/trixie), Ubuntu (24.04/26.04), Mint, Fedora, openSUSE.
  hyprtk already installs `swappy` everywhere (source-built where unpackaged),
  so Phase 3 adds a `swappy` mode instead of making `satty` mandatory.
- **KDE Connect share**: `kdeconnect-cli`; package names/availability vary
  (Arch/Void/Debian/Ubuntu OK; Fedora/openSUSE/Alpine differ). Must degrade to
  "share toggle hidden/disabled", and the current `grep -oP` extraction is
  GNU-only (breaks on BusyBox).
- **ImageMagick**: listed by upstream but not referenced by the QML; already
  installed by the bar, keep as-is (not a new hard dep).

### Distro availability (container-checked)

| Package | Arch | Debian/Ubuntu/Mint | Fedora | openSUSE | Void | Alpine |
|---|---|---|---|---|---|---|
| grim | OK | OK | OK | OK | OK | OK |
| wl-clipboard | OK | OK | OK | OK | OK | OK |
| notify-send | OK | OK | OK | OK | OK | OK |
| swappy | OK | 12/24.04/Mint MISS, 13/26.04 OK | OK | OK | OK | MISS |
| satty | OK | **MISS** | **MISS** | **MISS** | OK | OK |
| kdeconnect-cli | OK | OK | name varies | name varies | OK | MISS |

Quickshell itself: packaged on Arch/Fedora/openSUSE/Void/Alpine; Debian/Ubuntu/
Mint use the prebuilt **v0.3.0** bundle (Qt < 6.6) or a source build (Qt ≥ 6.6).
The bundle is `x86_64`/`aarch64` only.

---

## 3. GPU requirements

The GPU-sensitive part is the frozen overlay (`ScreencopyView`), not `grim`:

| Path | AMD | Intel | NVIDIA |
|---|---|---|---|
| `grim` (wlr-screencopy) | works | works (Mesa) | works |
| `ScreencopyView` freeze | works (tested locally) | expected (Mesa) | usually works; known Quickshell ICC/dual-GPU races |

Known NVIDIA risks (upstream Quickshell / Hyprland):

- Quickshell #897: ICC screencopy context race on **dual-GPU NVIDIA** during
  session lock (not our path, but shows fragility).
- caelestia #1814: capturing a screen not backed by a live Wayland output can
  crash Hyprland ≤ 0.56.2; guard `captureSource`.
- Hyprland #16126: direct-scanout latch after a one-shot capture (perf, not
  failure) on recent Hyprland.
- Hyprland #14256: region capture fails at fractional scale when the scaled
  region is non-integer.

Mitigation (Phase 2): if `ScreencopyView` produces no frame within ~1–2 s, close
the overlay and fall back to a **no-freeze** `grim` + `slurp` + `swappy` path,
with a notification. Keep the overlay for AMD/Intel; offer an explicit
NVIDIA fallback and an opt-in overlay override.

NVIDIA hardware validation is still required; containers/AMD cannot prove it.

---

## 4. Integration design

- **Vendor** in `hyprtk-bar-qt/vendor/hyprquickframe/`, pinned as above.
- **Install** to `~/.local/share/hyprtk-bar-qt/hyprquickframe/`; launch with
  `qs -p <dir> -n`, never via `/etc/xdg` or `-c`.
- **Launcher**: `bin/hyprtk-screenshot` → installed as `~/.local/bin/hyprtk-screenshot`
  by the existing `bin/*` loop. Resolves `qs`/`quickshell`/`~/.local/bin/qs`
  (same PATH lesson as the bar launcher), preflights `grim`, forwards
  `HQF_MODE` / `HQF_ACTION` and args.
- **Deps**: add `grim` to bar `EXTRAS` for all families. Optional tools are not
  installed.
- **Uninstall**: `INSTALL_DIR` removal removes the vendored tree; the `bin/*`
  loop removes the launcher.
- **Merged wiring** (Phase 4): replace the `ssdetect.sh` NVIDIA/AMD split
  (currently NVIDIA → `screenshot.sh`/grimblast, which merged does not install)
  with the single `hyprtk-screenshot` entrypoint + fallback.
- **Theme** (Phase 4): pywal template → `~/.config/hyprquickframe/theme.toml`
  (accent/background/foreground, bar radius, bottom margin).

---

## 5. Phases

### Phase 1 — vendor + installer + `grim` + launcher  *(in progress)*

- [x] Vendor upstream `a411411` into `vendor/hyprquickframe/` via `git archive`.
- [x] Add `vendor/hyprquickframe.SOURCE.md` (repo, commit, date, license).
- [x] `install.sh`: copy the vendored tree to `$INSTALL_DIR/hyprquickframe`.
- [x] `install.sh`: add `grim` to `EXTRAS` for pacman/apt/dnf/zypper/xbps/apk/
      emerge/nix.
- [x] `bin/hyprtk-screenshot`: PATH-safe launcher, `grim` preflight, `qs -p`.
- [x] Verify with `install.sh --no-deps` + real overlay run (AMD).
- [x] Add `slurp` to EXTRAS for the no-freeze fallback.

### Phase 2 — capture fallback / NVIDIA robustness  *(implemented on AMD)*

- [x] Patch the vendored watchdog: on no `ScreencopyView` frame, run a
      no-freeze `grim`+`slurp` selector and notify instead of quitting silently.
- [x] Guard `captureSource` against non-capturable/stale screens.
- [x] Decide NVIDIA default (overlay first, automatic fallback) and add
      `HQF_FORCE_FALLBACK=1` / `HQF_FALLBACK_GEOM` overrides.
- [ ] Test fractional scaling (1.25) region capture; round/fallback if needed.
- [ ] Validate on real NVIDIA (single + hybrid).
- [x] Verified on AMD by forcing a no-frame `ScreencopyView` (temporary
      `captureSource: null`): watchdog → fallback → clipboard PNG, plus
      `HQF_FORCE_FALLBACK=1` save/temp with `HQF_FALLBACK_GEOM`.
- [x] `slurp` added to EXTRAS (verified packaged on all six families).
- [x] Local patch recorded: `vendor/patches/hyprquickframe-no-freeze-fallback.patch`.

### Phase 3 — editor + optional features  ✅ done

- [x] Add `swappy` mode (universal in hyprtk; upstream only has satty/gradia).
- [x] Hide/disable the edit toggle when no supported editor exists
      (`satty`/`swappy`/`gradia` probed at startup; theme preference honoured).
- [x] Hide/disable share when `kdeconnect-cli` is absent; POSIX-safe `awk`
      parsing instead of GNU `grep -oP`.
- [x] Fix the gradia path's `hyprctl dispatch exec --` (broken on Hyprland
      0.55+ Lua dispatch) — launch detached via `setsid`.
- [x] Keep the post-save hook, documented as `sh -c` (user config).
- [x] Verified on AMD: edit tab present, `HQF_ACTION=edit` active, no share
      toggle without kdeconnect; swappy capture → Ctrl+S → clipboard round-trip.

### Phase 4 — merged wiring + theming  *(implemented)*

- [x] `ssdetect.sh` → `hyprtk-screenshot` for all GPUs; detached launch so the
      keybind returns, then resets the screenshot submap. `sshot.sh` is now an
      alias. No NVIDIA/grimblast split.
- [x] pywal template `configs/wal/templates/hyprquickframe-theme.toml`; installer
      symlinks `~/.config/hyprquickframe/theme.toml` to the rendered file.
- [ ] Optional bar quicklink/IPC action for screenshots — deferred (the keybind
      flow is complete; the overlay is a one-shot Quickshell config, not IPC).
- [x] Package audit: `grim`/`slurp` are in EXTRAS; optional `satty`/`kdeconnect`
      documented in §2.
- [x] Verified: template renders under an isolated `XDG_CONFIG_HOME`; the
      overlay logs the pywal theme path; `ssdetect.sh` returns in ~6 ms and
      starts `qs -p .../hyprquickframe` detached.

### Phase 5 — portability + release

- [ ] Confirm the prebuilt Quickshell v0.3.0 bundle path (old-Qt distros) and a
      Qt ≥ 6.6 source build both run the overlay.
- [ ] Test Alpine (BusyBox) boot: launcher + grim, no GNU-only paths on the
      default flow.
- [ ] Run T1 package matrix + T2 dry-run + audit; update CHANGELOG/README.
- [ ] Bump version, vendor into merged, `push-all`; tag the bar release.

---

## 6. Acceptance criteria

- Fresh install on each supported family yields a working
  `~/.local/bin/hyprtk-screenshot` (given a Wayland session + Hyprland).
- `hyprtk-screenshot` opens the overlay without a terminal-only PATH; region,
  window, full-screen and temp modes save/copy as expected on AMD and Intel.
- On NVIDIA, the utility either shows the overlay correctly or automatically
  falls back to a functional no-freeze capture.
- No new hard dependency that a supported family cannot install (satty and
  kdeconnect stay optional; downstream tools degrade cleanly).
- Vendored tree stays byte-identical to the pinned upstream commit (aside from
  the documented SOURCE file outside it).

## 7. Open questions

- Which NVIDIA behaviour do we default to: attempt overlay with fallback, or
  skip the freeze on NVIDIA until validated?
- Do we want `swappy` as the only editor (recommended) or best-effort
  satty/gradia/swappy?
- Should the screenshot action also appear in the bar (quicklink/module), or
  stay keybind-only?
