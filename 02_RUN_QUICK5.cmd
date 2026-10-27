@echo off
cd /d "%~dp0"
".venv-gpu\Scripts\python.exe" -u runtime_setup\run_quick5.py
if errorlevel 1 echo RUN FAILED. Read the error above. Partial results are preserved.
pause
