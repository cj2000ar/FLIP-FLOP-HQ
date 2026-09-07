$ErrorActionPreference="Stop"
$Python="C:\FLIP_FLOP_HQ\.venv\Scripts\python.exe"
$Tool="C:\FLIP_FLOP_HQ\07_TOOLS\cap10_sync_reports_v22\cap10_final_reporter_r22.py"
& $Python $Tool
if ($LASTEXITCODE -ne 0) { throw "CAP10 final reporter failed." }
$Txt=Get-ChildItem "C:\FLIP_FLOP_HQ\06_REPORTS\cap10\final" -Filter "FLIP_FLOP_CAP10_FINAL_Q1_Q10_*.txt" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $Txt) { throw "Reporter passed but TXT output was not found." }
Start-Process notepad.exe -ArgumentList "`"$($Txt.FullName)`""
