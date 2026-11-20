# Changelog

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
