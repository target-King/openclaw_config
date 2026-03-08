param(
  [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
  [switch]$SkipPushCheck,
  [switch]$ServerPull
)

$ErrorActionPreference = "Stop"

function Get-OpenClawHome {
    if ($env:OPENCLAW_HOME -and $env:OPENCLAW_HOME.Trim() -ne "") {
        return $env:OPENCLAW_HOME
    }
    return (Join-Path $env:USERPROFILE ".openclaw")
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Host "[mkdir] $Path"
    }
}

function Copy-DirSafe([string]$Source, [string]$Target) {
    Ensure-Dir $Target
    if (-not (Test-Path $Source)) {
        Write-Warning "[skip] Source not found: $Source"
        return
    }
    Copy-Item -Path (Join-Path $Source "*") -Destination $Target -Recurse -Force
    Write-Host "[sync] $Source -> $Target"
}

# ── Step 0: 仓库健康检查 ──
Write-Host ""
Write-Host "=== Step 0: Repo health check ==="
$doctorScript = Join-Path $PSScriptRoot "doctor.ps1"
if (Test-Path $doctorScript) {
    & $doctorScript -RepoRoot $RepoRoot
} else {
    Write-Warning "[sync] doctor.ps1 not found, skipping health check"
}

# ── Step 1: 推送前检查 ──
if (-not $SkipPushCheck) {
    Write-Host ""
    Write-Host "=== Step 1: Pre-push check ==="

    Push-Location $RepoRoot
    try {
        # 检查是否有未提交的修改
        $status = git status --porcelain 2>&1
        if ($status) {
            Write-Warning "[sync] Uncommitted changes detected:"
            $status | ForEach-Object { Write-Host "  $_" }
            Write-Error "[sync] Please commit all changes before syncing. Aborting."
        }
        Write-Host "[sync] Working tree is clean."

        # 检查是否有未推送的提交
        git fetch origin 2>&1 | Out-Null
        $unpushed = git log "origin/HEAD..HEAD" --oneline 2>&1
        if ($LASTEXITCODE -ne 0) {
            # fallback: try origin/main or origin/master
            $unpushed = git log "origin/main..HEAD" --oneline 2>&1
            if ($LASTEXITCODE -ne 0) {
                $unpushed = git log "origin/master..HEAD" --oneline 2>&1
            }
        }
        if ($unpushed) {
            Write-Warning "[sync] Unpushed commits detected:"
            $unpushed | ForEach-Object { Write-Host "  $_" }
            Write-Error "[sync] Please push all commits to remote before syncing. Aborting."
        }
        Write-Host "[sync] All commits are pushed to remote."
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "=== Step 1: Pre-push check (skipped) ==="
}

# ── Step 2: 服务器端拉取 ──
if ($ServerPull) {
    Write-Host ""
    Write-Host "=== Step 2: Server-side git pull ==="
    Push-Location $RepoRoot
    try {
        git pull --ff-only 2>&1 | ForEach-Object { Write-Host "[pull] $_" }
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[sync] git pull failed. Please resolve conflicts manually."
        }
        Write-Host "[sync] Server repo is up to date."
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "=== Step 2: Server-side git pull (skipped, use -ServerPull to enable) ==="
}

# ── Step 3: 备份 ──
Write-Host ""
Write-Host "=== Step 3: Backup current state ==="
$backupScript = Join-Path $PSScriptRoot "backup.ps1"
if (Test-Path $backupScript) {
    & $backupScript -RepoRoot $RepoRoot
} else {
    Write-Warning "[sync] backup.ps1 not found, skipping backup"
}

# ── Step 4: 执行同步（文件分发） ──
Write-Host ""
Write-Host "=== Step 4: Sync files to .openclaw ==="

$OpenClawHome = Get-OpenClawHome
Write-Host "[sync] Repo root: $RepoRoot"
Write-Host "[sync] OpenClaw home: $OpenClawHome"

$mergeSource = Join-Path $RepoRoot "_merge"
$managedSource = Join-Path $RepoRoot "managed-config"
$skillsSource = Join-Path $RepoRoot "skills"

Copy-DirSafe $mergeSource $OpenClawHome
Copy-DirSafe $managedSource (Join-Path $OpenClawHome "managed-source")
Copy-DirSafe $skillsSource (Join-Path $OpenClawHome "skills")

$agentMappings = @(
    @{ Source = (Join-Path $RepoRoot "agents\supervisor"); Target = (Join-Path $OpenClawHome "workspace-supervisor") },
    @{ Source = (Join-Path $RepoRoot "agents\coder");      Target = (Join-Path $OpenClawHome "workspace-coder") },
    @{ Source = (Join-Path $RepoRoot "agents\reviewer");   Target = (Join-Path $OpenClawHome "workspace-reviewer") },
    @{ Source = (Join-Path $RepoRoot "agents\ops");              Target = (Join-Path $OpenClawHome "workspace-ops") },
    @{ Source = (Join-Path $RepoRoot "agents\project-analyst"); Target = (Join-Path $OpenClawHome "workspace-project-analyst") }
)

foreach ($mapping in $agentMappings) {
    Copy-DirSafe $mapping.Source $mapping.Target
}

$noticeFile = Join-Path $OpenClawHome "CONTROL-REPO-NOTICE.txt"
@"
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
  local edit -> git push -> server git pull -> scripts/sync.ps1
"@ | Set-Content -Path $noticeFile -Encoding UTF8

Write-Host "[sync] Wrote notice file: $noticeFile"

# ── 完成 ──
Write-Host ""
Write-Host "=== Sync completed successfully ==="
Write-Host "[sync] Standard workflow: local edit -> git push -> server git pull -> sync.ps1"
