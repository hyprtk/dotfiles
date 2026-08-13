#!/bin/bash
ROOT=/home/hyprtk/Projects/AI-Projects/hyprtk-merged
cd "$ROOT"
TMP=$(mktemp -d)
find "$ROOT" -type f \
  -not -path "*/assets/papirus-icons/*" \
  -not -name "PLANNING.md" \
  -not -name "1-install.sh" \
  -print0 2>/dev/null | while IFS= read -r -d '' f; do
    grep -hoE "~/hyprtk/[A-Za-z0-9._/-]+" "$f" 2>/dev/null
  done | sed 's|/*$||' | sort -u > "$TMP/refs.txt"

while IFS= read -r ref; do
  rel="${ref#\~/hyprtk}"
  case "$rel" in
    /.zshrc|/.bashrc|/README.md|/CHANGELOG|/cheatsheet.md|/LICENSE|/default.png|/.folder.png|/.gitattributes|/1-install.sh)
      [ -e "$ROOT${rel}" ] || echo "  MISSING(TOP): $ref"
      continue ;;
    /configs/qtile/*|/configs/picom/*)
      echo "  [dead-alias] $ref (no qtile/picom source — matches live)"
      continue ;;
  esac
  [ -e "$ROOT${rel}" ] || echo "  MISSING: $ref"
done < "$TMP/refs.txt"
echo "=== total unique refs: $(wc -l < "$TMP/refs.txt") ==="
rm -rf "$TMP"
