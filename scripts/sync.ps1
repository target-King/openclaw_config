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
Write-Host "[sync] Repo root: $RepoRoot"
Write-Host "[sync] OpenClaw home: $OpenClawHome"

$managedSource = Join-Path $RepoRoot "managed-config"
$skillsSource = Join-Path $RepoRoot "skills"

Copy-DirSafe $managedSource (Join-Path $OpenClawHome "managed-source")
Copy-DirSafe $skillsSource (Join-Path $OpenClawHome "skills")

$agentMappings = @(
    @{ Source = (Join-Path $RepoRoot "agents\supervisor"); Target = (Join-Path $OpenClawHome "workspace-supervisor") },
    @{ Source = (Join-Path $RepoRoot "agents\coder");      Target = (Join-Path $OpenClawHome "workspace-coder") },
    @{ Source = (Join-Path $RepoRoot "agents\reviewer");   Target = (Join-Path $OpenClawHome "workspace-reviewer") },
    @{ Source = (Join-Path $RepoRoot "agents\ops");        Target = (Join-Path $OpenClawHome "workspace-ops") }
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

Important:
- Treat this as a prepared local control area.
- Keep sensitive secrets out of Git.
- Keep runtime state separate from source-controlled files.
"@ | Set-Content -Path $noticeFile -Encoding UTF8

Write-Host "[sync] Wrote notice file: $noticeFile"
