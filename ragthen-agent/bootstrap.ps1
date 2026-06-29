param(
    [string]$LibrariesPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = "$env:USERPROFILE\.ragthen"
$ScriptsDir = "$env:USERPROFILE\AppData\Roaming\Python\Python313\Scripts"

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  Ragthen Bootstrap"                    -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# 0. Ensure Python Scripts is in PATH
Write-Host "[0/6] Ensuring Python Scripts in PATH ..." -ForegroundColor Yellow
$currentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentUserPath -notlike "*$ScriptsDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentUserPath;$ScriptsDir", "User")
    Write-Host "  Added to user PATH: $ScriptsDir"
    $env:PATH = "$env:PATH;$ScriptsDir"
} else {
    Write-Host "  Already in PATH, skipping."
}

# 1. Create ~/.ragthen directory with config and libraries
Write-Host "[1/6] Setting up $AppDir ..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$AppDir\libraries" -Force | Out-Null

$configPath = "$AppDir\config.json"
if (-not (Test-Path $configPath)) {
    $defaultConfig = @{
        backend_mode = "local"
        remote_url   = "http://localhost:8000"
        libraries_path = "$AppDir\libraries"
        chunk_size   = 1200
        chunk_overlap = 250
        llm_model    = "gpt-4o"
    }
    $defaultConfig | ConvertTo-Json -Depth 3 | Set-Content -Path $configPath -Encoding UTF8
    Write-Host "  Created default config.json"
} else {
    Write-Host "  Config already exists, skipping."
}

# 2. Install ragthen-core in development mode
Write-Host "[2/6] Installing ragthen-core (editable) ..." -ForegroundColor Yellow
$coreDir = Join-Path $Root "..\ragthen-core"
if (Test-Path $coreDir) {
    pip install -e $coreDir
    if ($?) {
        Write-Host "  ragthen-core installed successfully."
    } else {
        Write-Host "  WARNING: pip install failed. Check dependencies manually." -ForegroundColor Red
    }
} else {
    Write-Host "  ERROR: ragthen-core not found at $coreDir" -ForegroundColor Red
    exit 1
}

# 3. Install ragthen-agent in development mode
Write-Host "[3/6] Installing ragthen-agent (editable) ..." -ForegroundColor Yellow
pip install -e $Root
if ($?) {
    Write-Host "  ragthen-agent installed successfully."
} else {
    Write-Host "  WARNING: pip install failed. Check dependencies manually." -ForegroundColor Red
}

# 4. Verify the CLI works
Write-Host "[4/6] Verifying installation ..." -ForegroundColor Yellow
$cliResult = ragthen --help 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ragthen CLI is ready!"
} else {
    Write-Host "  WARNING: ragthen command not found. Try restarting your terminal." -ForegroundColor Red
}

# 5. Done
Write-Host "[5/6] Bootstrap complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Your libraries directory: $AppDir\libraries" -ForegroundColor Cyan
Write-Host "Config file:             $AppDir\config.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "To switch to remote mode, edit config.json and set:" -ForegroundColor Cyan
Write-Host '  "backend_mode": "remote"' -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Add PDFs to ~/.ragthen/libraries/<name>/" -ForegroundColor White
Write-Host "  2. Run: ragthen ingest -l <name>" -ForegroundColor White
Write-Host "  3. Run: ragthen search -l <name> \"your query\"" -ForegroundColor White
Write-Host ""
Write-Host "For the agent: add .opencode/agents/ragthen.md to your project." -ForegroundColor Cyan

# 6. Deploy agent to opencode global config
Write-Host "[6/6] Deploying agent to opencode config ..." -ForegroundColor Yellow
$agentSource = Join-Path $Root ".opencode\agents\Ragthen.md"
$agentDest = "$env:USERPROFILE\.config\opencode\agents\ragthen.md"
if (Test-Path $agentSource) {
    New-Item -ItemType Directory -Path (Split-Path $agentDest -Parent) -Force | Out-Null
    Copy-Item -Path $agentSource -Destination $agentDest -Force
    Write-Host "  Agent deployed to: $agentDest"
} else {
    Write-Host "  WARNING: Agent source not found at $agentSource" -ForegroundColor Red
}
