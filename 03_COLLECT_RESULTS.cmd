@echo off
cd /d "%~dp0"
".venv-gpu\Scripts\python.exe" runtime_setup\collect_gpu_results.py
pause
