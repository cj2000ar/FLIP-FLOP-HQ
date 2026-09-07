$ErrorActionPreference="Stop"
$Root="C:\FLIP_FLOP_HQ"
$Script=Join-Path $Root "07_TOOLS\x10_3c_target_ceiling\x10_3c_target_ceiling.py"
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){
  $Cmd=Get-Command python.exe -ErrorAction SilentlyContinue
  if(-not $Cmd){throw "Python not found."}
  $Python=$Cmd.Source
}
& $Python $Script
if($LASTEXITCODE -ne 0){throw "X10.3C target ceiling autopsy failed."}
$Txt="C:\FLIP_FLOP_HQ\06_REPORTS\forensic\x10_3c_target_ceiling\LATEST_X10_3C_TARGET_CEILING_SUMMARY.txt"
if(-not (Test-Path $Txt)){throw "X10.3C passed but report TXT missing."}
Start-Process notepad.exe -ArgumentList "`"$Txt`""
