param(
  [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

Write-Host "[doctor] Checking repo structure..."

$requiredDirs = @(
    "managed-config",
    "agents",
    "skills",
    "scripts",
    "templates",
    "memory-spec",
    "data"
)

$requiredFiles = @(
    "README.md",
    ".gitignore",
    ".env.example",
    "bootstrap-openclaw.bat",
    "bootstrap-openclaw.ps1",
    "bootstrap-openclaw.sh",
    "_merge\settings.json5",
    "managed-config\openclaw.json5",
    "managed-config\agents.json5",
    "managed-config\skills.json5",
    "managed-config\channels.json5",
    "scripts\install.ps1",
    "scripts\sync.ps1",
    "scripts\backup.ps1",
    "scripts\doctor.ps1",
    "scripts\install.sh",
    "scripts\sync.sh",
    "scripts\backup.sh",
    "scripts\doctor.sh",
    "scripts\lib\common.sh",
    "scripts\memory\init_db.py",
    "scripts\memory\ingest_chat.py",
    "scripts\memory\retrieve_context.py",
    "scripts\memory\summarize_topic.py",
    "scripts\memory\compact_memory.py"
)

$missing = @()

foreach ($dir in $requiredDirs) {
    $full = Join-Path $RepoRoot $dir
    if (-not (Test-Path $full)) {
        $missing += $dir
    }
}

foreach ($file in $requiredFiles) {
    $full = Join-Path $RepoRoot $file
    if (-not (Test-Path $full)) {
        $missing += $file
    }
}

$agentNames = @("supervisor", "coder", "reviewer", "ops", "project-analyst", "scheduler")
foreach ($agent in $agentNames) {
    foreach ($fileName in @("AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md")) {
        $full = Join-Path $RepoRoot ("agents\" + $agent + "\" + $fileName)
        if (-not (Test-Path $full)) {
            $missing += ("agents\" + $agent + "\" + $fileName)
        }
    }
}

$skillNames = @("memory-retrieve", "memory-summarize", "topic-router", "repo-health", "git-sync")
foreach ($skill in $skillNames) {
    $full = Join-Path $RepoRoot ("skills\" + $skill + "\SKILL.md")
    if (-not (Test-Path $full)) {
        $missing += ("skills\" + $skill + "\SKILL.md")
    }
}

if ($missing.Count -gt 0) {
    Write-Error ("[doctor] Missing required paths:`n- " + ($missing -join "`n- "))
}

Write-Host "[doctor] Repo structure looks good."

# ── Runtime plugin check (optional) ──
$openclawCmd = Get-Command openclaw -ErrorAction SilentlyContinue
if ($null -ne $openclawCmd) {
    $pluginList = openclaw plugins list 2>&1
    if ($pluginList -match "lossless-claw") {
        Write-Host "[doctor][runtime] lossless-claw plugin is installed."
    } else {
        Write-Warning "[doctor][runtime] lossless-claw plugin not found. Run: openclaw plugins install @martian-engineering/lossless-claw"
    }
}
