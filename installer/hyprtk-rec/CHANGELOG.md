# Changelog

## 0.2.2 — 2026-11-20

The settings sheet, for the things the daily panel has no room for.

### Added

- **Settings sheet** — "Settings" in the window header opens a panel with the
  save folder (editable, `~` expanded and validated, with an Open action),
  notifications on/off, the length of the recent list (6/12/24), the encoder
  backend (auto / wf-recorder / wl-screenrec) with what is actually installed,
  and **Reset** back to the shipped defaults.

- **Replay buffer** — `--replay N` (or Replay buffer in Settings) keeps the last
  N seconds in memory with `wl-screenrec --history`; "Save replay" flushes them
  with `SIGUSR1` and keeps recording. Available only where `wl-screenrec` is
  installed — the setting is dimmed with the reason otherwise, and asking for a
  replay without it is a start error rather than a silent normal recording.
  **Not live-tested on this machine**: the AUR `wl-screenrec` (0.3.2 and -git)
  does not build against Arch's ffmpeg 8 — its `ffmpeg-next` crate has
  non-exhaustive matches for new `AVSampleFormat`/`AVPixelFormat`/`AVCodecID`
  variants — so the code path is argv- and signal-tested only.

### Changed

- `Bridge.resetConfig()` now re-reads the file (what its name says); the new
  `resetDefaults()` is the one that writes the defaults back. `Settings.reset()`
  does the write.
## 0.2.1 — 2026-11-20

The last two audio and encoder items from the v0.2 list.

### Added

- **Mixed audio ("Both")** — system audio and the microphone in one track. It is
  a real mix: a null sink (`hyprtk-rec-mix`) fed by two loopbacks (the default
  sink's monitor and the default input), recorded from that sink's monitor. The
  module ids live in the state file, so a stop from another process — or a
  recovery after a crash — unloads them instead of leaving a sink behind.
  Available as `--audio mix` and as the "Both" option in the window.
- **VAAPI encoding (opt-in)** — `--vaapi` or Encoder → VAAPI in the window, for
  `wf-recorder` with h264 or hevc. Availability is **probed**, not assumed: a
  `renderD*` node can exist and still fail `vaInitialize` (it does on this
  machine), so the probe initialises the device and the window shows the
  reason instead of offering a button that cannot work. A failed probe is a
  start error, never a silent fall back to the CPU.

- **Recording HUD** — a small pinned window (240x56, top-left) with the elapsed
  timer, Pause/Resume and Stop, shown for as long as a recording is active. It
  never takes focus, so showing it does not pull the keyboard away from the app
  being recorded, and it appears for a recording started by a keybinding in
  another process as well as one started from the window.
- The window and the HUD are positioned by two Hyprland window rules (matched on
  their exact titles); a recording started with `--toggle` has no HUD, because
  there is no long-lived process to draw one.

### Fixed

- **The window only polled the state while it was already recording**, so a
  recording started from a keybinding was invisible to an open window (no
  timer, no HUD). The poll now runs always: once a second when idle, twice a
  second while recording, and only emits when the state actually changed.
- **Window titles carried a " — Screen Recorder" suffix**, so the window rules
  that match on `^(Screen Recorder|Recording)$` matched nothing. The application
  display name is gone and the titles are exactly what the QML sets.
- Closing the window left a hidden process behind; it now quits. The encoder
  keeps running in its own session and the state file still answers `stop`, the
  same as a keybinding-started recording.

### Changed

- `Recorder.status()` reports `vaapi` alongside `container`, and the recording
  state carries the device it used.
## 0.2.0 — 2026-11-20

Output formats, a window picker and a notification that can act.

### Added

- **GIF output** — `--container gif` or Format → GIF in the window. The file is
  written by `wf-recorder` (`-c gif -x rgb8`), frame rate capped at 30 because a
  live GIF above that is unplayable and enormous. `wl-screenrec` cannot write a
  GIF, so the backend falls back to `wf-recorder` instead of failing late.
- **Window picker in the window** — the Window source now records the window you
  pick, not only the focused one. The choice is stored as a Hyprland client
  address and self-heals when that window closes. `--window ADDRESS` does the
  same from the command line.
- **Trim** — `hyprtk-rec trim PATH --from 12 --to 30` (or `--last`) cuts a
  finished file with `-c copy`, so it is instant and lossless. `--reencode` is
  the frame-accurate option; `--replace` overwrites the original instead of
  writing a `-trimmed` sibling. Times accept seconds, `MM:SS` or `HH:MM:SS`.
- **Crash recovery** — a state file whose encoder is gone now hands back the
  partial recording (`Recorder.recover()`); the window adds it to the recent
  list and notifies, instead of silently dropping an interrupted capture. The
  file was always written under its final name, so nothing needs renaming.
- **Notification actions** — the "Recording saved" notification carries
  "Open folder" and "Copy path". The waiter is a detached `hyprtk-rec
  notify-saved PATH` process, because notify-send only reports the pressed
  button while the notification is on screen.

### Changed

- The recording state now carries its container, so `status --json` says what
  was written and a stale state file cannot produce a `.gif` claim for an MP4.
- Container lists live in one place (`recorder.CONTAINERS`); `store.make_name()`
  can no longer refuse a container the recorder can write.

## 0.1.0 — 2026-11-20

First release. A screen recorder for the hyprtk desktop: pick a source, choose
audio, record, and get a finished file.

### Added

- **Three sources** — focused (or named) monitor, a region from `slurp`, or the
  focused window's `hyprctl` geometry.
- **Two backends** — `wf-recorder` (default, already a suite dependency) and
  `wl-screenrec` (GPU-encoded, used automatically when installed). Per-codec
  CRF/bitrate mapping for `low`/`medium`/`high`.
- **Audio** — off, the default sink's monitor (system audio), the default
  microphone, or any named source; resolved through `pactl`.
- **Process control** — start, SIGINT stop with container finalization, SIGSTOP
  pause and SIGCONT resume, a JSON state file in `$XDG_RUNTIME_DIR` that makes
  `status`/`stop`/`toggle` work from any process, and stale-state cleanup.
- **Window** — state card with elapsed timer, source/audio/fps/codec/quality/
  countdown controls, output directory, recent recordings with duration and
  size.
- **CLI** — `start`, `stop`, `toggle`, `pause`, `resume`, `status`, `sources`,
  with every setting as a flag and `--json` output.
- **Desktop integration** — PySide6/QML with the suite's pywal palette, a v09
  suite icon, absolute `Exec=`/`Icon=` desktop entry, `--system` and
  `--uninstall` installers, PyPI-venv fallback for Debian/Ubuntu.
- **Tests**: 94 unit tests (argv builders, state lifecycle, audio parsing,
  sources, stores, settings, CLI, docs), `qmllint`, and a headless boot check
  that drives a full record/pause/stop cycle.
