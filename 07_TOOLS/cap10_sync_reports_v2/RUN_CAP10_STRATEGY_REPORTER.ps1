$ErrorActionPreference = "Stop"
$Python = "C:\FLIP_FLOP_HQ\.venv\Scripts\python.exe"
$Tool = "C:\FLIP_FLOP_HQ\07_TOOLS\cap10_sync_reports_v2\cap10_strategy_reporter.py"
if (-not (Test-Path $Python)) { throw "Quant Lab Python not found." }
if (-not (Test-Path $Tool)) { throw "Install CAP10 Sync Reports V2 first." }
& $Python $Tool
if ($LASTEXITCODE -ne 0) { throw "CAP10 reporter did not complete. Read the message above." }
