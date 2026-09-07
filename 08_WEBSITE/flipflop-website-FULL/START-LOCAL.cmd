@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Instala Node.js 22.13 o posterior y vuelve a abrir este archivo.
  pause
  exit /b 1
)
if not exist "node_modules\vinext\package.json" (
  call npm ci
  if errorlevel 1 exit /b 1
)
call npm run dev
