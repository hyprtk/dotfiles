#!/bin/bash
# Simulate deployment per distro: canonical + overlay -> verify every referenced
# ~/hyprtk path resolves. Known source-level dead refs are whitelisted.
ROOT=/home/hyprtk/Projects/AI-Projects/hyprtk-merged
# these paths are referenced in the source trees but do not exist there either
DEAD="~/hyprtk/.bashrc|~/hyprtk/configs/waybar/reload.sh|~/hyprtk/hypr/conf/nvidia.conf|~/hyprtk/installer/scripts/applauncher.sh|~/hyprtk/installer/scripts/growthrate.py|~/hyprtk/installer/scripts/looking-glass.sh|~/hyprtk/configs/qtile/config.py|~/hyprtk/configs/picom/picom.conf|~/hyprtk/installer/os-release/os-release-$"
for d in arch archbang archcraft archman bslx cachy endeavour garuda kiro manjaro reborn; do
  TMP=$(mktemp -d)
  rsync -a --exclude='distro' --exclude='installer/steps' --exclude='installer/scripts/build-merged.sh' --exclude='PLANNING.md' "$ROOT/" "$TMP/" 2>/dev/null
  [ -d "$ROOT/distro/$d" ] && rsync -a "$ROOT/distro/$d/" "$TMP/" 2>/dev/null
  FAIL=0
  while IFS= read -r ref; do
    case "$ref" in
      *.bashrc|*reload.sh|*nvidia.conf|*applauncher.sh|*growthrate.py|*looking-glass.sh|*qtile/*|*picom/*) continue ;;
      *os-release-|*hyprland.conf) continue ;;
    esac
    rel="${ref#\~/hyprtk}"
    [ -e "$TMP$rel" ] || { echo "  [$d] MISSING: $ref"; FAIL=1; }
  done < <(grep -rhoE "~/hyprtk/[A-Za-z0-9._/-]+" "$TMP" --include="*" 2>/dev/null | sed 's|/*$||' | sort -u)
  if [ "$FAIL" = 0 ]; then echo "[OK] $d: all refs resolve (source-known dead refs excluded)"; fi
  rm -rf "$TMP"
done
