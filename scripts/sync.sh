#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
SKIP_PUSH_CHECK="${SKIP_PUSH_CHECK:-false}"
SERVER_PULL="${SERVER_PULL:-false}"

# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/lib/common.sh"

OPENCLAW_HOME_DIR="$(get_openclaw_home)"

# ── Step 0: 仓库健康检查 ──
echo ""
echo "=== Step 0: Repo health check ==="
doctor_script="$REPO_ROOT/scripts/doctor.sh"
if [[ -x "$doctor_script" ]]; then
    bash "$doctor_script" "$REPO_ROOT"
else
    echo "[warn] doctor.sh not found, skipping health check" >&2
fi

# ── Step 1: 推送前检查 ──
if [[ "$SKIP_PUSH_CHECK" != "true" ]]; then
    echo ""
    echo "=== Step 1: Pre-push check ==="

    cd "$REPO_ROOT"

    # 检查是否有未提交的修改
    status_output="$(git status --porcelain 2>&1)" || true
    if [[ -n "$status_output" ]]; then
        echo "[warn] Uncommitted changes detected:" >&2
        echo "$status_output" | sed 's/^/  /' >&2
        echo "[error] Please commit all changes before syncing. Aborting." >&2
        exit 1
    fi
    echo "[sync] Working tree is clean."

    # 检查是否有未推送的提交
    git fetch origin 2>/dev/null || true
    unpushed="$(git log "origin/HEAD..HEAD" --oneline 2>/dev/null)" || \
    unpushed="$(git log "origin/main..HEAD" --oneline 2>/dev/null)" || \
    unpushed="$(git log "origin/master..HEAD" --oneline 2>/dev/null)" || \
    unpushed=""

    if [[ -n "$unpushed" ]]; then
        echo "[warn] Unpushed commits detected:" >&2
        echo "$unpushed" | sed 's/^/  /' >&2
        echo "[error] Please push all commits to remote before syncing. Aborting." >&2
        exit 1
    fi
    echo "[sync] All commits are pushed to remote."
else
    echo ""
    echo "=== Step 1: Pre-push check (skipped) ==="
fi

# ── Step 2: 服务器端拉取 ──
if [[ "$SERVER_PULL" == "true" ]]; then
    echo ""
    echo "=== Step 2: Server-side git pull ==="
    cd "$REPO_ROOT"
    if ! git pull --ff-only 2>&1 | sed 's/^/[pull] /'; then
        echo "[error] git pull failed. Please resolve conflicts manually." >&2
        exit 1
    fi
    echo "[sync] Server repo is up to date."
else
    echo ""
    echo "=== Step 2: Server-side git pull (skipped, set SERVER_PULL=true to enable) ==="
fi

# ── Step 3: 备份 ──
echo ""
echo "=== Step 3: Backup current state ==="
backup_script="$REPO_ROOT/scripts/backup.sh"
if [[ -x "$backup_script" ]]; then
    bash "$backup_script" "$REPO_ROOT"
else
    echo "[warn] backup.sh not found, skipping backup" >&2
fi

# ── Step 4: 执行同步（文件分发） ──
echo ""
echo "=== Step 4: Sync files to .openclaw ==="
echo "[sync] Repo root: $REPO_ROOT"
echo "[sync] OpenClaw home: $OPENCLAW_HOME_DIR"

copy_dir_contents_safe "$REPO_ROOT/_merge" "$OPENCLAW_HOME_DIR"
copy_dir_contents_safe "$REPO_ROOT/managed-config" "$OPENCLAW_HOME_DIR/managed-source"
copy_dir_contents_safe "$REPO_ROOT/skills" "$OPENCLAW_HOME_DIR/skills"
copy_dir_contents_safe "$REPO_ROOT/agents/supervisor" "$OPENCLAW_HOME_DIR/workspace-supervisor"
copy_dir_contents_safe "$REPO_ROOT/agents/coder" "$OPENCLAW_HOME_DIR/workspace-coder"
copy_dir_contents_safe "$REPO_ROOT/agents/reviewer" "$OPENCLAW_HOME_DIR/workspace-reviewer"
copy_dir_contents_safe "$REPO_ROOT/agents/ops" "$OPENCLAW_HOME_DIR/workspace-ops"
copy_dir_contents_safe "$REPO_ROOT/agents/project-analyst" "$OPENCLAW_HOME_DIR/workspace-project-analyst"

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
- workspace-project-analyst

Important:
- Treat this as a prepared local control area.
- Keep sensitive secrets out of Git.
- Keep runtime state separate from source-controlled files.
- All modifications must go through the standard sync workflow:
  local edit -> git push -> server git pull -> scripts/sync.sh
NOTE

echo "[sync] Wrote notice file: $notice_file"

# ── 完成 ──
echo ""
echo "=== Sync completed successfully ==="
echo "[sync] Standard workflow: local edit -> git push -> server git pull -> sync.sh"
