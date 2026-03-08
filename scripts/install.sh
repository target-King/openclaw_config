#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/lib/common.sh"

OPENCLAW_HOME_DIR="$(get_openclaw_home)"
echo "[install] Target home: $OPENCLAW_HOME_DIR"

for dir in \
  "$OPENCLAW_HOME_DIR" \
  "$OPENCLAW_HOME_DIR/managed-source" \
  "$OPENCLAW_HOME_DIR/skills" \
  "$OPENCLAW_HOME_DIR/workspace-supervisor" \
  "$OPENCLAW_HOME_DIR/workspace-coder" \
  "$OPENCLAW_HOME_DIR/workspace-reviewer" \
  "$OPENCLAW_HOME_DIR/workspace-ops" \
  "$OPENCLAW_HOME_DIR/backups" \
  "$OPENCLAW_HOME_DIR/logs"; do
  ensure_dir "$dir"
done

if command -v openclaw >/dev/null 2>&1; then
  echo "[install] OpenClaw command detected: $(command -v openclaw)"
  # 检查 lossless-claw 插件
  if openclaw plugins list 2>/dev/null | grep -q "lossless-claw"; then
    echo "[install] lossless-claw plugin already installed."
  else
    echo "[install] Installing lossless-claw plugin..."
    if openclaw plugins install @martian-engineering/lossless-claw 2>&1 | sed 's/^/  /'; then
      echo "[install] lossless-claw plugin installed successfully."
    else
      echo "[warn] Failed to install lossless-claw plugin." >&2
      echo "[warn] Install manually: openclaw plugins install @martian-engineering/lossless-claw" >&2
    fi
  fi
else
  echo "[install] OpenClaw command not detected. Directory prep only."
  echo "[install] After installing OpenClaw, run: openclaw plugins install @martian-engineering/lossless-claw"
fi
