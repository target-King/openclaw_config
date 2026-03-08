#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"

echo "[doctor] Checking repo structure..."

required_dirs=(
  managed-config
  agents
  skills
  scripts
  templates
  memory-spec
  data
)

required_files=(
  README.md
  .gitignore
  .env.example
  bootstrap-openclaw.bat
  bootstrap-openclaw.ps1
  bootstrap-openclaw.sh
  _merge/settings.json5
  managed-config/openclaw.json5
  managed-config/agents.json5
  managed-config/skills.json5
  managed-config/channels.json5
  scripts/install.ps1
  scripts/sync.ps1
  scripts/backup.ps1
  scripts/doctor.ps1
  scripts/install.sh
  scripts/sync.sh
  scripts/backup.sh
  scripts/doctor.sh
  scripts/lib/common.sh
  scripts/memory/init_db.py
  scripts/memory/ingest_chat.py
  scripts/memory/retrieve_context.py
  scripts/memory/summarize_topic.py
  scripts/memory/compact_memory.py
)

missing=()

for dir in "${required_dirs[@]}"; do
  if [[ ! -e "$REPO_ROOT/$dir" ]]; then
    missing+=("$dir")
  fi
done

for file in "${required_files[@]}"; do
  if [[ ! -e "$REPO_ROOT/$file" ]]; then
    missing+=("$file")
  fi
done

for agent in supervisor coder reviewer ops project-analyst scheduler; do
  for file_name in AGENTS.md SOUL.md USER.md TOOLS.md; do
    full="agents/$agent/$file_name"
    if [[ ! -e "$REPO_ROOT/$full" ]]; then
      missing+=("$full")
    fi
  done
done

for skill in memory-retrieve memory-summarize topic-router repo-health git-sync; do
  full="skills/$skill/SKILL.md"
  if [[ ! -e "$REPO_ROOT/$full" ]]; then
    missing+=("$full")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "[doctor] Missing required paths:" >&2
  for item in "${missing[@]}"; do
    echo "- $item" >&2
  done
  exit 1
fi

echo "[doctor] Repo structure looks good."

# ── Runtime plugin check (optional) ──
if command -v openclaw >/dev/null 2>&1; then
  if openclaw plugins list 2>/dev/null | grep -q "lossless-claw"; then
    echo "[doctor][runtime] lossless-claw plugin is installed."
  else
    echo "[warn][runtime] lossless-claw plugin not found. Run: openclaw plugins install @martian-engineering/lossless-claw" >&2
  fi
fi
