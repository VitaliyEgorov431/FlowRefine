@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_gpu.ps1"
if errorlevel 1 echo RUN FAILED. Logs and partial results are preserved.
pause
