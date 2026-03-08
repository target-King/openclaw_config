#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[bootstrap] Repo root: $REPO_ROOT"

bash "$REPO_ROOT/scripts/doctor.sh" "$REPO_ROOT"
bash "$REPO_ROOT/scripts/install.sh" "$REPO_ROOT"
bash "$REPO_ROOT/scripts/backup.sh" "$REPO_ROOT"
bash "$REPO_ROOT/scripts/sync.sh" "$REPO_ROOT"

echo "[bootstrap] Done."
