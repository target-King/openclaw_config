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
    # 检查 lossless-claw 插件
    $pluginList = openclaw plugins list 2>&1
    if ($pluginList -match "lossless-claw") {
        Write-Host "[install] lossless-claw plugin already installed."
    } else {
        Write-Host "[install] Installing lossless-claw plugin..."
        try {
            openclaw plugins install @martian-engineering/lossless-claw 2>&1 | ForEach-Object { Write-Host "  $_" }
            Write-Host "[install] lossless-claw plugin installed successfully."
        } catch {
            Write-Warning "[install] Failed to install lossless-claw plugin: $_"
            Write-Warning "[install] You can install it manually: openclaw plugins install @martian-engineering/lossless-claw"
        }
    }
}
else {
    Write-Host "[install] OpenClaw command not detected. Directory prep only."
    Write-Host "[install] After installing OpenClaw, run: openclaw plugins install @martian-engineering/lossless-claw"
}
