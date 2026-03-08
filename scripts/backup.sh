#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/lib/common.sh"

OPENCLAW_HOME_DIR="$(get_openclaw_home)"
ensure_dir "$OPENCLAW_HOME_DIR"

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_root="$OPENCLAW_HOME_DIR/backups/$timestamp"
ensure_dir "$backup_root"

copied=false
for name in managed-source skills workspace-supervisor workspace-coder workspace-reviewer workspace-ops workspace-project-analyst; do
  src="$OPENCLAW_HOME_DIR/$name"
  if [[ -e "$src" ]]; then
    dst="$backup_root/$name"
    if [[ -d "$src" ]]; then
      mkdir -p "$dst"
      cp -a "$src"/. "$dst"/
    else
      mkdir -p "$(dirname "$dst")"
      cp -a "$src" "$dst"
    fi
    echo "[backup] $src -> $dst"
    copied=true
  fi
done

# 备份 settings.json5
settings_file="$OPENCLAW_HOME_DIR/settings.json5"
if [[ -f "$settings_file" ]]; then
  cp -a "$settings_file" "$backup_root/settings.json5"
  echo "[backup] $settings_file -> $backup_root/settings.json5"
  copied=true
fi

if [[ "$copied" == false ]]; then
  echo "[backup] Nothing to back up yet."
fi
