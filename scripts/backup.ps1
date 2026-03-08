param(
  [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
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


$OpenClawHome = Get-OpenClawHome
Ensure-Dir $OpenClawHome

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $OpenClawHome ("backups\" + $timestamp)
Ensure-Dir $backupRoot

$targets = @(
    "managed-source",
    "skills",
    "workspace-supervisor",
    "workspace-coder",
    "workspace-reviewer",
    "workspace-ops",
    "workspace-project-analyst"
)

$copied = $false
foreach ($name in $targets) {
    $src = Join-Path $OpenClawHome $name
    if (Test-Path $src) {
        $dst = Join-Path $backupRoot $name
        Copy-Item $src $dst -Recurse -Force
        Write-Host "[backup] $src -> $dst"
        $copied = $true
    }
}

if (-not $copied) {
    Write-Host "[backup] Nothing to back up yet."
}
