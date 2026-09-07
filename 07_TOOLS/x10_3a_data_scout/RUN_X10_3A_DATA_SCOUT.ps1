$ErrorActionPreference="Stop"
$Root="C:\FLIP_FLOP_HQ"
$ToolDir=Join-Path $Root "07_TOOLS\x10_3a_data_scout"
$Scorer=Join-Path $ToolDir "x10_3a_data_scout.py"
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){
    $Cmd=Get-Command python.exe -ErrorAction SilentlyContinue
    if(-not $Cmd){throw "Python not found."}
    $Python=$Cmd.Source
}
& $Python $Scorer
if($LASTEXITCODE -ne 0){throw "X10.3A data scout failed."}
$Txt="C:\FLIP_FLOP_HQ\06_REPORTS\forensic\x10_3a_data_scout\X10_3A_DATA_SCOUT_SUMMARY.txt"
if(-not (Test-Path $Txt)){throw "Scout passed but report TXT missing."}
Start-Process notepad.exe -ArgumentList "`"$Txt`""
