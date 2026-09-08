# Bootstrap FlipFlop HQ Production (Windows)
# Run as Administrator: powershell -ExecutionPolicy Bypass -File bootstrap_production.ps1

#Requires -RunAsAdministrator

$FLIPFLOP_HOME = "C:\Program Files\FlipFlop"
$FLIPFLOP_DATA = "$FLIPFLOP_HOME\data"
$FLIPFLOP_DB = "$FLIPFLOP_HOME\databases"
$FLIPFLOP_LOGS = "C:\ProgramData\FlipFlop\logs"
$SECRETS_DIR = "C:\ProgramData\FlipFlop\secrets"
$VENV_PATH = "$FLIPFLOP_HOME\venv"

Write-Host "🚀 FlipFlop HQ Production Bootstrap"
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Create directories
Write-Host "[1/7] Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $FLIPFLOP_DATA -Force | Out-Null
New-Item -ItemType Directory -Path $FLIPFLOP_DB -Force | Out-Null
New-Item -ItemType Directory -Path $FLIPFLOP_LOGS -Force | Out-Null
New-Item -ItemType Directory -Path $SECRETS_DIR -Force | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green

# 2. Create virtual environment
Write-Host "[2/7] Creating Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path $VENV_PATH)) {
    & python -m venv $VENV_PATH
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
}

# 3. Install dependencies
Write-Host "[3/7] Installing Python dependencies..." -ForegroundColor Yellow
& "$VENV_PATH\Scripts\pip.exe" install -q alpaca-trade-api psutil requests python-dotenv 2>$null
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# 4. Setup credentials
Write-Host "[4/7] Setting up credentials..." -ForegroundColor Yellow
$env_file = "$SECRETS_DIR\market-api.env"
if (-not (Test-Path $env_file)) {
    @"
# Set these environment variables
ALPACA_API_KEY=
ALPACA_API_SECRET=
"@ | Set-Content $env_file
    Write-Host "⚠ Created $env_file - UPDATE WITH YOUR CREDENTIALS" -ForegroundColor Yellow
} else {
    Write-Host "✓ Credentials file exists" -ForegroundColor Green
}

# 5. Create Windows Scheduled Task
Write-Host "[5/7] Creating Windows Scheduled Task..." -ForegroundColor Yellow

$TaskName = "FlipFlop-Scheduler"
$TaskDescription = "FlipFlop HQ Autonomous Scheduler (24/7)"
$ActionScript = @"
$env:Path = "$VENV_PATH\Scripts;`$env:Path"
cd "$FLIPFLOP_HOME"
python -u scheduler_service.py
"@

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -Command $ActionScript"
$Trigger = New-ScheduledTaskTrigger -AtStartup

try {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -RunLevel Highest `
        -Description $TaskDescription | Out-Null

    Write-Host "✓ Scheduled Task created" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create task: $_" -ForegroundColor Red
    exit 1
}

# 6. Start scheduler
Write-Host "[6/7] Starting scheduler..." -ForegroundColor Yellow
try {
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 3
    $task = Get-ScheduledTask -TaskName $TaskName
    if ($task.State -eq "Running") {
        Write-Host "✓ Scheduler running" -ForegroundColor Green
    } else {
        Write-Host "✗ Scheduler not running" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Failed to start scheduler: $_" -ForegroundColor Red
    exit 1
}

# 7. Verify health
Write-Host "[7/7] Verifying health..." -ForegroundColor Yellow
$healthScript = @"
import sys
sys.path.insert(0, r'$FLIPFLOP_HOME')
from health_check import HealthChecker
hc = HealthChecker(r'$FLIPFLOP_DB')
result = hc.check_all()
print(f"Status: {result['status']}")
if result['status'] != 'HEALTHY':
    print(f"Warnings: {result['failed_checks']}")
"@

& "$VENV_PATH\Scripts\python.exe" -c $healthScript

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ FlipFlop Bootstrap Complete" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Update credentials: $env_file"
Write-Host "2. Monitor task: Get-ScheduledTask -TaskName 'FlipFlop-Scheduler' | Get-ScheduledTaskInfo"
Write-Host "3. View logs: Get-EventLog -LogName System -Source FlipFlop-Scheduler"
Write-Host ""
Write-Host "Authority: ZERO"
Write-Host "Live: OFF"
