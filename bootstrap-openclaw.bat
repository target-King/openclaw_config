@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap-openclaw.ps1"
if errorlevel 1 (
  echo.
  echo Bootstrap failed.
  pause
  exit /b 1
)
echo.
echo Bootstrap completed.
pause
