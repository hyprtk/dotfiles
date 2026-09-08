#!/bin/bash
# ── hyprtk-bar least-privilege sudo ───────────────────────────────────────
# Installs /etc/sudoers.d/hyprtk-bar granting the desktop user passwordless
# access ONLY to the exact commands the bar invokes non-interactively (the
# system monitor's dmidecode DIMM readout). Never NOPASSWD: ALL.
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
# Least privilege: only the system monitor's dmidecode DIMM readout runs via
# sudo -n (see monitor_data.fetch_dmidecode). Everything else uses pkexec,
# which still prompts. Installed by setup-sudoers.sh.
#
# Extend this list ONLY with the exact commands the bar actually invokes
# non-interactively; never grant NOPASSWD: ALL.
${TARGET_USER} ALL=(root) NOPASSWD: /usr/bin/dmidecode"

umask 0377
printf '%s\n' "$CONTENT" > "$SUDOERS_D"
chown root:root "$SUDOERS_D"
chmod 440 "$SUDOERS_D"

if ! visudo -c -f "$SUDOERS_D" >/dev/null 2>&1; then
    echo "error: sudoers validation failed; removing invalid drop-in" >&2
    rm -f "$SUDOERS_D"
    exit 1
fi

echo "ok: scoped passwordless sudo configured for '$TARGET_USER' ($SUDOERS_D)"

if sudo -u "$TARGET_USER" sudo -n dmidecode -t 17 < /dev/null >/dev/null 2>&1; then
    echo "ok: passwordless dmidecode verified for '$TARGET_USER'"
else
    echo "warn: could not verify passwordless dmidecode for '$TARGET_USER'"
fi