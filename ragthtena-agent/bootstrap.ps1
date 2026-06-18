param(
    [string]$LibrariesPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = "$env:USERPROFILE\.ragthtena"

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  Raghtena Bootstrap"                    -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# 1. Create ~/.ragthtena directory with config and libraries
Write-Host "[1/5] Setting up $AppDir ..." -ForegroundColor Yellow
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

# 2. Install ragthtena-core in development mode
Write-Host "[2/5] Installing ragthtena-core (editable) ..." -ForegroundColor Yellow
$coreDir = Join-Path $Root "..\ragthtena-core"
if (Test-Path $coreDir) {
    pip install -e $coreDir
    if ($?) {
        Write-Host "  ragthtena-core installed successfully."
    } else {
        Write-Host "  WARNING: pip install failed. Check dependencies manually." -ForegroundColor Red
    }
} else {
    Write-Host "  ERROR: ragthtena-core not found at $coreDir" -ForegroundColor Red
    exit 1
}

# 3. Install ragthtena-agent in development mode
Write-Host "[3/5] Installing ragthtena-agent (editable) ..." -ForegroundColor Yellow
pip install -e $Root
if ($?) {
    Write-Host "  ragthtena-agent installed successfully."
} else {
    Write-Host "  WARNING: pip install failed. Check dependencies manually." -ForegroundColor Red
}

# 4. Verify the CLI works
Write-Host "[4/5] Verifying installation ..." -ForegroundColor Yellow
$cliResult = ragthtena --help 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ragthtena CLI is ready!"
} else {
    Write-Host "  WARNING: ragthtena command not found. Try restarting your terminal." -ForegroundColor Red
}

# 5. Done
Write-Host "[5/5] Bootstrap complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Your libraries directory: $AppDir\libraries" -ForegroundColor Cyan
Write-Host "Config file:             $AppDir\config.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "To switch to remote mode, edit config.json and set:" -ForegroundColor Cyan
Write-Host '  "backend_mode": "remote"' -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Add PDFs to ~/.ragthtena/libraries/<name>/" -ForegroundColor White
Write-Host "  2. Run: ragthtena ingest -l <name>" -ForegroundColor White
Write-Host "  3. Run: ragthtena search -l <name> \"your query\"" -ForegroundColor White
Write-Host ""
Write-Host "For the agent: add .opencode/agents/ragthtena.md to your project." -ForegroundColor Cyan
