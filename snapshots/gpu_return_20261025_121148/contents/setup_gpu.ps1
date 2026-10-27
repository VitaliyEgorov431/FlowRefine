[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Test-Path '.venv-gpu/Scripts/python.exe')) {
        & py -3.12 -m venv .venv-gpu
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 from python.org (with Python Launcher), then rerun.' }
    }
    $pythonExe = Join-Path $PSScriptRoot '.venv-gpu/Scripts/python.exe'
    & $pythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'pip setup failed.' }
    & $pythonExe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu126
    if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch installation failed.' }
    & $pythonExe -m pip install --only-binary=llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu -r runtime_setup/requirements-gpu.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Compiler is not required; inspect CPU wheel availability.' }
    & $pythonExe runtime_setup/check_gpu.py
    if ($LASTEXITCODE -ne 0) { throw 'GPU/runtime check failed.' }
    & $pythonExe runtime_setup/download_gpu_models.py
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed; rerun setup to resume downloads.' }
    Write-Host 'Setup complete. Run 02_RUN_EXPERIMENT.cmd'
}
finally { Pop-Location }
