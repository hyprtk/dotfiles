#!/bin/bash
# ── hyprtk-bar passwordless sudo ──────────────────────────────────────────
# Installs /etc/sudoers.d/hyprtk-bar granting the desktop user passwordless
# sudo so the system monitor's DIMM readout (and other privileged bar
# actions) never need an interactive pkexec/sudo prompt.
#
# Usage (as the desktop user, or as root):
#   sudo bash setup-sudoers.sh
#
# Idempotent. The drop-in is validated with visudo before it is kept.
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail

SUDOERS_D="/etc/sudoers.d/hyprtk-bar"

if [ "$(id -u)" -ne 0 ]; then
    echo "error: this script must run as root (e.g. sudo bash setup-sudoers.sh)" >&2
    exit 1
fi

# Resolve the desktop user: the sudo invoker, a pkexec caller, else $USER.
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    TARGET_USER="$SUDO_USER"
elif [ -n "${PKEXEC_UID:-}" ]; then
    TARGET_USER="$(id -nu "$PKEXEC_UID" 2>/dev/null || true)"
else
    TARGET_USER="${USER:-$(id -un)}"
fi
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    echo "error: cannot determine the desktop user (run it via sudo as that user)" >&2
    exit 1
fi

CONTENT="# hyprtk-bar: passwordless sudo for the desktop user.
# Used by the system monitor (dmidecode DIMM readout) and other privileged
# bar actions. Installed by setup-sudoers.sh.
#
# To restrict to only the monitor's hardware readout instead of full sudo,
# replace the final line with:
#   ${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/dmidecode
#
${TARGET_USER} ALL=(ALL) NOPASSWD: ALL"

umask 0377
printf '%s\n' "$CONTENT" > "$SUDOERS_D"
chown root:root "$SUDOERS_D"
chmod 440 "$SUDOERS_D"

if ! visudo -c -f "$SUDOERS_D" >/dev/null 2>&1; then
    echo "error: sudoers validation failed; removing invalid drop-in" >&2
    rm -f "$SUDOERS_D"
    exit 1
fi

echo "ok: passwordless sudo configured for '$TARGET_USER' ($SUDOERS_D)"

if sudo -u "$TARGET_USER" sudo -n true 2>/dev/null; then
    echo "ok: passwordless sudo verified for '$TARGET_USER'"
else
    echo "warn: could not verify passwordless sudo for '$TARGET_USER'"
fi