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
Write-Host "[install] Target home: $OpenClawHome"

$dirs = @(
    $OpenClawHome,
    (Join-Path $OpenClawHome "managed-source"),
    (Join-Path $OpenClawHome "skills"),
    (Join-Path $OpenClawHome "workspace-supervisor"),
    (Join-Path $OpenClawHome "workspace-coder"),
    (Join-Path $OpenClawHome "workspace-reviewer"),
    (Join-Path $OpenClawHome "workspace-ops"),
    (Join-Path $OpenClawHome "backups"),
    (Join-Path $OpenClawHome "logs")
)

foreach ($dir in $dirs) {
    Ensure-Dir $dir
}

$openclawCmd = Get-Command openclaw -ErrorAction SilentlyContinue
if ($null -ne $openclawCmd) {
    Write-Host "[install] OpenClaw command detected: $($openclawCmd.Source)"
}
else {
    Write-Host "[install] OpenClaw command not detected. This is okay. Directory prep only."
}
