@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\local-app.ps1" -Action Stop
if errorlevel 1 pause
