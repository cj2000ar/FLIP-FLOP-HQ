# Guardian V2 Bootstrap - Windows PowerShell
# Stages and verifies package before launching V2 application
# Authority: ZERO
# Exit Code: 78 on Guardian verification failure
# Date: 2026-09-07

param(
    [Parameter(Mandatory=$true)]
    [string]$ManifestPath,
    [Parameter(Mandatory=$false)]
    [string]$BrowserUrl = "http://localhost:3000"
)

# Set error action to stop on first error
$ErrorActionPreference = "Stop"

Write-Host "[Guardian V2] Bootstrap starting..."
Write-Host "[Guardian V2] Manifest: $ManifestPath"
Write-Host "[Guardian V2] Browser URL: $BrowserUrl"

# Verify manifest exists
if (-not (Test-Path $ManifestPath)) {
    Write-Error "[Guardian V2] Manifest not found: $ManifestPath"
    exit 78
}

# Set script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Change to engine directory
Set-Location (Split-Path -Parent $scriptDir)

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[Guardian V2] Activating Python venv..."
    & venv\Scripts\Activate.ps1
}

# Launch V2 launcher with Python
Write-Host "[Guardian V2] Invoking V2 launcher..."
$launcherScript = Join-Path $scriptDir "guardian_v2_launcher.py"

python $launcherScript $ManifestPath $BrowserUrl
$exitCode = $LASTEXITCODE

if ($exitCode -eq 78) {
    Write-Host "[Guardian V2] Verification failed. Exit code: 78"
    exit 78
}

if ($exitCode -eq 0) {
    Write-Host "[Guardian V2] Bootstrap successful."
    exit 0
} else {
    Write-Host "[Guardian V2] Unexpected exit code: $exitCode"
    exit $exitCode
}
