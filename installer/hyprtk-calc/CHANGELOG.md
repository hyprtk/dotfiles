# Changelog

## 0.1.1 — 2026-11-26

### Fixed

- **Legal input could hang the UI for minutes.** Live evaluation runs on every
  keystroke, and three paths had no bound: `1e999999` built a 3.3-million-bit
  integer and formatted it in four bases, `ncr(1000000, 500000)` spent 5 s in
  `math.comb`, and `2^100000` formatted a 100 KB binary string. Integers are now
  capped at 4000 digits, `ncr`/`npr` at 100 000 (like `fact()`), and the
  four-base readout is skipped above 40 digits. All three answer in ~0.1 ms.
- **Arithmetic limits were reported as a generic failure.** `cosh(1000)` said
  "could not evaluate"; `OverflowError`/`ValueError`/`ArithmeticError` now carry
  their own message, and an unexpected exception is logged with a traceback
  instead of being hidden behind a user-facing string.
- **History and config writes left a readable `.tmp` behind** on a crash (the
  history can contain pasted secrets). Both use `mkstemp` in the target
  directory, `fsync`, `chmod 0600` and `os.replace`, removing the temp on error.
- **The window title was the raw expression**, so a pasted formula became the
  title (breaking title-based window rules). It is now "Calculator".

## 0.1.0 — 2026-11-18

First release. A calculator for the hyprtk desktop: exact decimals, a live
expression line, and the suite's palette.

### Added

- **Arithmetic core** on `decimal.Decimal`, with a hand-written tokenizer and
  precedence parser (no `ast`, no `eval`): exact literals, implicit
  multiplication, right-associative `^`, postfix `!` and `%`, a bitwise layer
  (`& | xor ~ << >>`), and `0x`/`0b`/`0o`/`1_000` literals.
- **Two precisions**: display digits (3–60, default 12) plus 12 guard digits, so
  `1/3` is exact to what you asked for and `sin(30°)` shows `0.5` instead of
  `0.49999999999999994`.
- **40 functions** (trig/hyperbolic with deg/rad/grad, logs, roots, rounding,
  combinatorics, gcd/lcm, min/max/sign/hypot, factorial) and the constants
  `pi`, `e`, `tau`, `phi`, plus `ans` and named variables.
- **GUI**: live result while typing, Basic/Scientific/Programmer keypads,
  insert-at-cursor, `AC`/`DEL`/`±`, hex digits that open a `0x` literal, a
  four-base programmer readout, and a settings sheet (precision, angle,
  grouping, keypad, live result, always-on-top).
- **History**: append-only JSONL under `~/.config/hyprtk-calc/`, shared with the
  CLI, deduplicated, newest first, click to recall, `↑`/`↓` to walk it.
- **CLI** in the same binary: `hyprtk-calc "2+2*3"`, `-p/--precision`,
  `-a/--angle`, `-b/--base`, `-g/--grouping`, `--all-bases`, `--json`,
  `--history`, `--clear-history`, stdin, exit status 1 on a calculation error.
- **Suite integration of the look**: palette resolved from the bar's pywal
  theme (with derived keypad surfaces, because pywal can return a `color0`
  identical to the background), Symbols Nerd Font chrome, and the v09 suite
  icon with the new `calc` glyph.
- **Installer** with user and `--system` modes, an absolute-path desktop entry,
  and a PyPI-venv fallback for distributions whose PySide6 lacks the QML
  bindings.
- 60 unit tests, `qmllint`, a headless boot check and an installer round-trip in
  `./scripts/qa.sh`.

### Known limits

- Transcendental functions run in double precision (~15 digits) and are then
  rounded to the display precision; `+ − × ÷`, powers and roots are exact
  decimal.
- `%` is a unit (`x/100`), so `100 + 10%` is `100.1`.
- No units, no currency, no plotting, no complex numbers, and no memory keys
  yet — see [PLAN.md](PLAN.md) for the order those arrive in.
