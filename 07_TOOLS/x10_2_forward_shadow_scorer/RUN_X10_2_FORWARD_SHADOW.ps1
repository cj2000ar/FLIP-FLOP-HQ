$ErrorActionPreference="Stop"
$Root="C:\FLIP_FLOP_HQ"
$ToolDir=Join-Path $Root "07_TOOLS\x10_2_forward_shadow_scorer"
$Scorer=Join-Path $ToolDir "x10_2_dual_hash_championship_scorer.py"
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){
  $Cmd=Get-Command python.exe -ErrorAction SilentlyContinue
  if(-not $Cmd){throw "Python not found."}
  $Python=$Cmd.Source
}
& $Python $Scorer
if($LASTEXITCODE -ne 0){throw "X10.2 dual-hash championship scorer failed."}
$Runs=Join-Path $Root "06_REPORTS\forensic\x10_2_forward_shadow\runs"
$Txt=Get-ChildItem $Runs -Filter "X10_2_CHAMPIONSHIP_SCORE_*.txt" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(-not $Txt){throw "Scorer passed but championship TXT not found."}
Start-Process notepad.exe -ArgumentList "`"$($Txt.FullName)`""
