$ErrorActionPreference="Stop"
$Root="C:\FLIP_FLOP_HQ"
$Scorer=Join-Path $Root "07_TOOLS\x10_3b_quant_core\x10_3b_quant_core.py"
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){
  $Cmd=Get-Command python.exe -ErrorAction SilentlyContinue
  if(-not $Cmd){throw "Python not found."}
  $Python=$Cmd.Source
}
& $Python $Scorer
if($LASTEXITCODE -ne 0){throw "X10.3B quant core failed."}
$Txt="C:\FLIP_FLOP_HQ\06_REPORTS\forensic\x10_3b_quant_core\LATEST_X10_3B_QUANT_CORE_SUMMARY.txt"
if(-not (Test-Path $Txt)){throw "X10.3B passed but latest TXT missing."}
Start-Process notepad.exe -ArgumentList "`"$Txt`""
