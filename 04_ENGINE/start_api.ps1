# FlipFlop HQ Private Read API - Startup Script
# Starts API with auto-restart on crash, health monitoring, logging
# Usage: powershell -ExecutionPolicy Bypass -File start_api.ps1

param(
    [string]$Port = "8000",
    [string]$Host = "127.0.0.1",
    [string]$LogFile = "api.log",
    [int]$RestartDelaySeconds = 5,
    [int]$HealthCheckIntervalSeconds = 30
)

$ErrorActionPreference = "Continue"
$ProcessName = "Private Read API"
$PythonScript = "private_read_api.py"
$HealthEndpoint = "http://$Host`:$Port/health"

Write-Host "=========================================="
Write-Host "FlipFlop HQ Private Read API"
Write-Host "Port: $Port | Host: $Host | Log: $LogFile"
Write-Host "=========================================="

function Start-API {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Starting API..." -ForegroundColor Green

    $env:PYTHONUNBUFFERED = 1
    $env:PORT = $Port

    # Start uvicorn server
    & python -m uvicorn private_read_api:app --host $Host --port $Port --reload 2>&1 | Tee-Object -FilePath $LogFile -Append
}

function Check-Health {
    try {
        $response = Invoke-WebRequest -Uri $HealthEndpoint -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            return $true
        }
    }
    catch {
        return $false
    }
}

function Monitor-API {
    $job = Start-Job -ScriptBlock ${function:Start-API} -Name $ProcessName

    while ($true) {
        Start-Sleep -Seconds $HealthCheckIntervalSeconds

        if ($job.State -ne "Running") {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] API process died! Restarting in ${RestartDelaySeconds}s..." -ForegroundColor Red
            Start-Sleep -Seconds $RestartDelaySeconds
            $job = Start-Job -ScriptBlock ${function:Start-API} -Name $ProcessName
        }
        elseif (-not (Check-Health)) {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Health check failed! Restarting..." -ForegroundColor Yellow
            Stop-Job -Job $job -Force
            Start-Sleep -Seconds $RestartDelaySeconds
            $job = Start-Job -ScriptBlock ${function:Start-API} -Name $ProcessName
        }
        else {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Health check OK" -ForegroundColor Green
        }
    }
}

# Trap Ctrl+C to gracefully shutdown
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Shutting down API..." -ForegroundColor Yellow
}

# Start monitoring
Monitor-API
