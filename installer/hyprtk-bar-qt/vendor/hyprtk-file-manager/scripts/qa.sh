#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

echo "== unit tests =="
PYTHONPATH=backend python3 -m unittest discover -s tests

echo "== syntax =="
python3 -m compileall -q backend
bash -n install.sh
sh -n bin/hyprtk-fm

echo "== performance =="
python3 scripts/perf.py

echo "== installer round-trip =="
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
HOME="$TMP" XDG_DATA_HOME="$TMP/.local/share" ./install.sh >/dev/null
test -x "$TMP/.local/bin/hyprtk-fm"
test -f "$TMP/.local/share/applications/hyprtk-file-manager.desktop"
HOME="$TMP" XDG_DATA_HOME="$TMP/.local/share" ./install.sh --uninstall >/dev/null
test ! -e "$TMP/.local/share/hyprtk-file-manager"

echo "QA PASS"
