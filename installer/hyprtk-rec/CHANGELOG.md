# Changelog

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
