# Bootstrap FlipFlop HQ Production (Windows)
# Run as Administrator

$FLIPFLOP_HOME = "C:\Program Files\FlipFlop"
$FLIPFLOP_DATA = "$FLIPFLOP_HOME\data"
$FLIPFLOP_DB = "$FLIPFLOP_HOME\databases"
$FLIPFLOP_LOGS = "C:\ProgramData\FlipFlop\logs"
$SECRETS_DIR = "C:\ProgramData\FlipFlop\secrets"
$VENV_PATH = "$FLIPFLOP_HOME\venv"
$TaskName = "FlipFlop-Scheduler"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FlipFlop HQ Production Bootstrap" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Create directories
Write-Host "`n[1/6] Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $FLIPFLOP_DATA -Force | Out-Null
New-Item -ItemType Directory -Path $FLIPFLOP_DB -Force | Out-Null
New-Item -ItemType Directory -Path $FLIPFLOP_LOGS -Force | Out-Null
New-Item -ItemType Directory -Path $SECRETS_DIR -Force | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green

# 2. Create virtual environment
Write-Host "`n[2/6] Creating Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path $VENV_PATH)) {
    & python -m venv $VENV_PATH
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
}

# 3. Install dependencies
Write-Host "`n[3/6] Installing Python dependencies..." -ForegroundColor Yellow
& "$VENV_PATH\Scripts\pip.exe" install -q alpaca-trade-api psutil requests python-dotenv 2>$null
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# 4. Setup credentials
Write-Host "`n[4/6] Setting up credentials..." -ForegroundColor Yellow
$env_file = "$SECRETS_DIR\market-api.env"
if (-not (Test-Path $env_file)) {
    @"
ALPACA_API_KEY=
ALPACA_API_SECRET=
"@ | Set-Content $env_file
    Write-Host "⚠ Created $env_file - UPDATE WITH YOUR CREDENTIALS" -ForegroundColor Yellow
} else {
    Write-Host "✓ Credentials file exists" -ForegroundColor Green
}

# 5. Create Scheduled Task
Write-Host "`n[5/6] Creating Windows Scheduled Task..." -ForegroundColor Yellow
$scriptWrapper = "$FLIPFLOP_HOME\run_scheduler.ps1"
@"
`$env:Path = "$VENV_PATH\Scripts;`$env:Path"
cd "$FLIPFLOP_HOME"
python -u scheduler_service.py
"@ | Set-Content $scriptWrapper

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptWrapper`""
$Trigger = New-ScheduledTaskTrigger -AtStartup

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -RunLevel Highest -Description "FlipFlop HQ Scheduler" | Out-Null
Write-Host "✓ Scheduled Task created" -ForegroundColor Green

# 6. Start scheduler
Write-Host "`n[6/6] Starting scheduler..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3
$task = Get-ScheduledTask -TaskName $TaskName
if ($task.State -eq "Running") {
    Write-Host "✓ Scheduler running" -ForegroundColor Green
} else {
    Write-Host "⚠ Scheduler queued to start" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Bootstrap Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nNext steps:"
Write-Host "1. Edit credentials: $env_file"
Write-Host "2. Verify running: Get-ScheduledTask -TaskName 'FlipFlop-Scheduler'"
Write-Host "3. Check health: curl http://localhost:8080/health"
Write-Host "`nAuthority: ZERO"
Write-Host "Live: OFF"
