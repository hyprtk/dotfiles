<div align="center">

<img src="docs/branding/banner.png" alt="hyprtk-system-manager — part of the hyprtk suite" width="100%" />

[![suite](https://img.shields.io/badge/suite-hyprtk-02DEDE?style=flat-square&labelColor=05060B)](https://github.com/hyprtk)
[![version](https://img.shields.io/badge/version-0.7.2-FD4FB6?style=flat-square&labelColor=05060B)](CHANGELOG.md)
[![wiki](https://img.shields.io/badge/wiki-system-manager-C084FC?style=flat-square&labelColor=05060B)](https://github.com/hyprtk/hyprtk-system-manager/wiki)
[![license](https://img.shields.io/badge/license-MIT-5FB8F5?style=flat-square&labelColor=05060B)](LICENSE)

</div>

# hyprtk-system-manager

> **Part of the hyprtk suite** — [dotfiles](https://github.com/hyprtk/dotfiles) · [bar-qt](https://github.com/hyprtk/hyprtk-bar-qt) · [file manager](https://github.com/hyprtk/hyprtk-file-manager) · [editor](https://github.com/hyprtk/hyprtk-editor) · [terminal](https://github.com/hyprtk/hyprtk-term) · [calculator](https://github.com/hyprtk/hyprtk-calc) · [screenshot](https://github.com/hyprtk/hyprtk-shot) · [recorder](https://github.com/hyprtk/hyprtk-rec) · [system manager](https://github.com/hyprtk/hyprtk-system-manager) · [config manager](https://github.com/hyprtk/hyprtk-hyprland-config-manager) · [hyprtk-usb](https://github.com/hyprtk/hyprtk-usb) · [ISO creator](https://github.com/hyprtk/Hyprtk-ISO-Creator)

One searchable settings application for the whole hyprtk desktop and the Linux
system under it: displays, appearance, fonts, users, date and time, input,
network, power, storage, services, updates, privacy and every suite app.

**Current version: 0.7.2** — see [CHANGELOG.md](CHANGELOG.md),
[PLAN.md](PLAN.md) and the survey in [RESEARCH.md](RESEARCH.md).

![System Settings](docs/main.png)

![Users & Groups](docs/users.png)

## Why a suite settings app

GNOME Settings, KDE System Settings and XFCE Settings Manager each solve part of
this problem well: GNOME has the best single-window language, KDE the best
module metadata and privilege model, XFCE the fastest navigation. None of them
knows about a Hyprland Lua tree, a pywal palette, a Quickshell bar or the eight
hyprtk applications sitting next to them.

hyprtk-system-manager borrows the good parts and drops the rest:

- **One window, one page stack, one apply model.** Grouped sidebar, global
  row-level search, pending-change footer, explicit Apply/Revert.
- **Declared panels, one renderer.** A panel is a Python module that returns a
  JSON form model; `FormPage.qml` renders the twelve row types. Bespoke QML is
  reserved for genuinely spatial pages (monitors, accounts).
- **Honest capability reporting.** Every panel declares `functional`, `live`,
  `partial`, `read only`, `external` or `planned`, derived from real probes, and
  the UI shows it as a pill.
- **Privilege is visible.** Root work goes through `sudo -n` or `pkexec`; the
  app shows the exact command and never runs a hidden root daemon.
- **Transactional writes.** Any file change is snapshotted under
  `~/.config/hyprtk-system-manager/backups/` and can be restored.
- **The suite is first-class.** The Apps group lists every hyprtk application
  with its installed version, live state and a link to its own settings, and
  writes the same bar config keys the bar's own Settings window writes.

## Panels

| System | Hardware | Network | Personalisation |
|---|---|---|---|
| About · Date & Time · Region & Language · Users & Groups · Services · Snapshots · Profiles · Updates | Displays · Graphics · Sound · Input Devices · Power · Bluetooth · Printers · Storage | Network | Appearance · Fonts · Notifications |

| Desktop | Applications | Security | Accessibility |
|---|---|---|---|
| Bar · Hyprland · Keyboard Shortcuts · Autostart | Default Applications · hyprtk Suite | Privacy & Security | Accessibility |

Fully implemented: **About, Date & Time, Users & Groups, Displays, Sound,
Printers, Appearance, Fonts, Autostart, hyprtk Suite, Power, Storage, Privacy,
Bar, Hyprland, Snapshots, Profiles**. Accessibility and Input stay
`partial` by design: the keyboard aids need a settings daemon this desktop does
not ship, and per-device overrides belong to config-manager. See
[PLAN.md](PLAN.md).

Apply is previewable: **Preview** shows a unified diff of every file an Apply
would change and writes nothing. Panels that act on the system instead of a file
say so. Other apps can deep-link to a row with
`hyprtk-settings open --page power --row "Charge limit"`.

## Architecture

```
Quickshell (QML)                        Python backend
────────────────                        ──────────────
shell.qml                               system_manager.cli serve
  └ MainWindow / Overlay                  ├ rpc.py     JSON-lines
      └ App.qml                           ├ catalog.py panel registry
          ├ Sidebar.qml                   ├ form.py    form model
          ├ pages/FormPage.qml            ├ panels/*   probe/apply/action
          ├ pages/DisplaysPage.qml        ├ priv.py    sudo/pkexec
          └ pages/UsersPage.qml           └ state.py   snapshots
```

The UI and the backend talk one JSON object per line over stdio, the same
pattern as the file manager and config-manager.

## Install

```sh
./install.sh              # user install: ~/.local/share/hyprtk-system-manager
./install.sh --dry-run    # report dependencies, change nothing
./install.sh --system     # /usr/local, used by the ISO
./install.sh --uninstall  # remove the app, keep backups
```

Requirements: `python3` and Quickshell (`qs`). Everything else is detected at
runtime; missing tools degrade a panel, never the app.

## Run

```sh
hyprtk-settings                  # open the window
hyprtk-settings --page displays  # open a specific panel
hyprtk-settings --overlay        # layer-shell panel (bar hand-off)
```

The window is a layer-shell panel centred on the focused screen, like the
bar's Settings and Quick Settings. Layer surfaces are not decorated by the
compositor, so the app's animated accent border is the only edge — no second
border, shadow or compositor rounding.

Bind it in Hyprland:

```lua
hl.bind("SUPER + I", hl.dsp.exec_cmd("hyprtk-settings"))
```

## CLI

```sh
hyprtk-settings panels                 # list panels and their status
hyprtk-settings panel displays         # print a panel's form model (JSON)
hyprtk-settings doctor                 # probe all 25 panels, report contract breaks
hyprtk-settings apply datetime timezone=Europe/Paris ntp=true
hyprtk-settings action users create --args '{"username":"kori","shell":"/usr/bin/zsh"}'
hyprtk-settings backups list
hyprtk-settings backups restore 20261123-163000-123
```

`doctor` is the CI check: it fails if any panel returns an invalid form model.

## Scope and safety

- **Never edits the Hyprland Lua tree** except a clearly delimited managed block
  in `monitors.lua` written by the Displays panel. Everything else in the
  compositor belongs to config-manager.
- **Never automates a system upgrade.** The Updates panel reports, copies the
  command and cleans the cache; the upgrade itself needs a visible terminal.
- **Never stores a password.** `chpasswd` receives it on stdin once.
- **Never silently escalates.** Every root action reports its command in the
  result details.

## Development

```sh
make test    # 137 unit tests
make doctor  # probe every panel on this machine
make qa      # tests + compile + qmllint + off-screen boot + installer round-trip
```

Documentation screenshots are rendered, not captured from a live session:

```sh
python3 scripts/screenshot.py            # docs/main.png, docs/users.png
python3 scripts/screenshot.py displays   # any page, off-screen, deterministic
```

The off-screen boot check runs `qs -p .` for one page of each kind and asserts
the backend answered, so a broken QML file cannot hide behind a green unit run.

## License

MIT — see [LICENSE](LICENSE).
