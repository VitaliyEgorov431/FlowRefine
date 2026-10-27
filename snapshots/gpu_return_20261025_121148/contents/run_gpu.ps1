[CmdletBinding()]
param([switch]$SkipSmoke, [string]$RunDir = 'runs/gpu_vlm_v1')
$ErrorActionPreference = 'Stop'
$previousPythonPath = $env:PYTHONPATH
Push-Location -LiteralPath $PSScriptRoot
try {
    $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
    $env:PYTHONUTF8 = '1'
    $pythonExe = Join-Path $PSScriptRoot '.venv-gpu/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Run 01_SETUP_GPU.cmd first.' }
    New-Item -ItemType Directory -Force -Path 'gpu_logs' | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    Start-Transcript -Path "gpu_logs/run_$stamp.txt" | Out-Null
    try {
        if (-not $SkipSmoke) {
            Write-Host 'Checking one saved DEVELOPMENT chart before the 15 test charts.'
            $ErrorActionPreference = 'Continue'
            & $pythonExe -u -m flowrefine.gpu_experiment --phase all --baseline runs/development_3b_v1 --output runs/gpu_vlm_smoke --limit 1
            $code = $LASTEXITCODE
            $ErrorActionPreference = 'Stop'
            if ($code -ne 0) { throw 'Development smoke failed. See gpu_logs. No main test started.' }
        }
        Write-Host 'Starting frozen 15-task VLM comparison. Existing completed tasks are reused.'
        $ErrorActionPreference = 'Continue'
        & $pythonExe -u -m flowrefine.gpu_experiment --phase all --baseline runs/test_v1 --output $RunDir
        $code = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($code -ne 0) { throw 'Experiment stopped; partial results preserved. See GPU_EXPERIMENT_RU.md for resuming.' }
    }
    finally { Stop-Transcript | Out-Null }
    & $pythonExe runtime_setup/collect_gpu_results.py --run $RunDir
    if ($LASTEXITCODE -ne 0) { throw 'Result archive failed.' }
    Write-Host "Finished. View $RunDir/COMPARISON.md and $RunDir/index.html. Send back GPU_RESULTS_*.zip."
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    Pop-Location
}
