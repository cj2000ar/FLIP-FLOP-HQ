$ErrorActionPreference = "Stop"
$Python = "C:\FLIP_FLOP_HQ\.venv\Scripts\python.exe"
$Tool = "C:\FLIP_FLOP_HQ\07_TOOLS\stage3h4_forward_blackbox_v1\stage3h4_forward_blackbox.py"

if (-not (Test-Path $Python)) { exit 2 }
if (-not (Test-Path $Tool)) { exit 3 }

& $Python $Tool score *> "C:\FLIP_FLOP_HQ\08_LOGS\stage3h4\last_scorer_console.txt"
exit $LASTEXITCODE
