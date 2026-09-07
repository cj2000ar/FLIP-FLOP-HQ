$ErrorActionPreference="Stop"
$Root="C:\FLIP_FLOP_HQ"
$Script=Join-Path $Root "07_TOOLS\x10_3c_r12_session_mapper\x10_3c_r12_session_mapper.py"
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){
  $Cmd=Get-Command python.exe -ErrorAction SilentlyContinue
  if(-not $Cmd){throw "Python not found."}
  $Python=$Cmd.Source
}
& $Python $Script
if($LASTEXITCODE -ne 0){throw "X10.3C-R1.2 session mapper failed."}
$Txt="C:\FLIP_FLOP_HQ\06_REPORTS\forensic\x10_3c_target_ceiling\r12_session_mapper\LATEST_X10_3C_R12_SESSION_MAPPER_SUMMARY.txt"
if(-not (Test-Path $Txt)){throw "R1.2 passed but report TXT missing."}
Start-Process notepad.exe -ArgumentList "`"$Txt`""
