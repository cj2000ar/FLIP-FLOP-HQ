$ErrorActionPreference = "Stop"
$Python = "C:\FLIP_FLOP_HQ\.venv\Scripts\python.exe"
$Tool = "C:\FLIP_FLOP_HQ\07_TOOLS\cap10_sync_reports_v21\cap10_strategy_reporter_v21.py"
if (-not (Test-Path $Python)) { throw "Quant Lab Python not found." }
if (-not (Test-Path $Tool)) { throw "CAP10 R2.1 reporter missing." }
& $Python $Tool
if ($LASTEXITCODE -ne 0) { throw "CAP10 R2.1 reporter did not complete." }
