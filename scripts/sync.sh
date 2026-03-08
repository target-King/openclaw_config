#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/lib/common.sh"

OPENCLAW_HOME_DIR="$(get_openclaw_home)"
echo "[sync] Repo root: $REPO_ROOT"
echo "[sync] OpenClaw home: $OPENCLAW_HOME_DIR"

copy_dir_contents_safe "$REPO_ROOT/managed-config" "$OPENCLAW_HOME_DIR/managed-source"
copy_dir_contents_safe "$REPO_ROOT/skills" "$OPENCLAW_HOME_DIR/skills"
copy_dir_contents_safe "$REPO_ROOT/agents/supervisor" "$OPENCLAW_HOME_DIR/workspace-supervisor"
copy_dir_contents_safe "$REPO_ROOT/agents/coder" "$OPENCLAW_HOME_DIR/workspace-coder"
copy_dir_contents_safe "$REPO_ROOT/agents/reviewer" "$OPENCLAW_HOME_DIR/workspace-reviewer"
copy_dir_contents_safe "$REPO_ROOT/agents/ops" "$OPENCLAW_HOME_DIR/workspace-ops"

notice_file="$OPENCLAW_HOME_DIR/CONTROL-REPO-NOTICE.txt"
cat > "$notice_file" <<'NOTE'
This directory was prepared by the Git-managed control repo.

Managed source:
- managed-source
- skills
- workspace-supervisor
- workspace-coder
- workspace-reviewer
- workspace-ops

Important:
- Treat this as a prepared local control area.
- Keep sensitive secrets out of Git.
- Keep runtime state separate from source-controlled files.
NOTE

echo "[sync] Wrote notice file: $notice_file"
