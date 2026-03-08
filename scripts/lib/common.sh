#!/usr/bin/env bash
set -euo pipefail

get_openclaw_home() {
  if [[ -n "${OPENCLAW_HOME:-}" ]]; then
    printf '%s\n' "$OPENCLAW_HOME"
  else
    printf '%s\n' "$HOME/.openclaw"
  fi
}

ensure_dir() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    mkdir -p "$path"
    echo "[mkdir] $path"
  fi
}

copy_dir_contents_safe() {
  local source="$1"
  local target="$2"
  ensure_dir "$target"
  if [[ ! -d "$source" ]]; then
    echo "[skip] Source not found: $source" >&2
    return 0
  fi
  # copy contents, including dotfiles, but not the source dir itself
  cp -a "$source"/. "$target"/
  echo "[sync] $source -> $target"
}
