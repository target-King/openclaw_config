$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "[bootstrap] Repo root: $RepoRoot"

try {
    & (Join-Path $RepoRoot "scripts\doctor.ps1") -RepoRoot $RepoRoot
    & (Join-Path $RepoRoot "scripts\install.ps1") -RepoRoot $RepoRoot
    & (Join-Path $RepoRoot "scripts\backup.ps1") -RepoRoot $RepoRoot
    & (Join-Path $RepoRoot "scripts\sync.ps1") -RepoRoot $RepoRoot
    Write-Host "[bootstrap] Done."
}
catch {
    Write-Error $_
    exit 1
}
