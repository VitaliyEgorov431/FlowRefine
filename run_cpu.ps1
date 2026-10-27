[CmdletBinding()]
param(
    [ValidateSet('development', 'test')][string]$Split = 'test',
    [ValidateSet('generate', 'critique', 'repair', 'all')][string]$Phase = 'all',
    [string]$RunDir = 'runs/test_v1',
    [string]$AnalysisDir = 'analysis/test_v1',
    [string]$GalleryPath = 'demo/index.html',
    [string]$TextModel = 'models/qwen2.5-3b-instruct-q4_k_m.gguf',
    [string]$VisionModel = 'models/SmolVLM-256M-Instruct-Q8_0.gguf',
    [string]$VisionProjector = 'models/mmproj-SmolVLM-256M-Instruct-f16.gguf',
    [ValidateRange(1, 64)][int]$Threads = 4,
    [ValidateRange(100, 2048)][int]$MaxTokens = 900,
    [ValidateRange(20, 1024)][int]$VisionMaxTokens = 180,
    [ValidateRange(1, 20)][int]$Limit,
    [switch]$ReplayOnly
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'src/flowrefine/cli.py') -PathType Leaf)) {
    throw 'Run this script from the intact FlowRefine project; src/flowrefine/cli.py is missing.'
}
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw 'Project .venv/Scripts/python.exe is missing. Prepare the environment first; this script does not install packages.'
}
$previousPythonPath = $env:PYTHONPATH
Push-Location -LiteralPath $projectRoot
try {
    $env:PYTHONPATH = Join-Path $projectRoot 'src'
    & $pythonExe -c 'import PIL, matplotlib'
    if ($LASTEXITCODE -ne 0) { throw 'Pillow/matplotlib are unavailable in the project environment.' }

    if (-not $ReplayOnly) {
        & $pythonExe -c 'import llama_cpp; from llama_cpp.llama_chat_format import MTMDChatHandler; print(llama_cpp.__version__)'
        if ($LASTEXITCODE -ne 0) { throw 'CPU llama-cpp-python with MTMD is unavailable. No packages were installed.' }
        foreach ($modelFile in @($TextModel, $VisionModel, $VisionProjector)) {
            if (-not (Test-Path -LiteralPath $modelFile -PathType Leaf)) {
                throw "Missing model file: $modelFile. See runtime_setup/HANDOFF.md. No automatic download is performed."
            }
        }
        $runArguments = @('-m', 'flowrefine.cli', 'run', '--split', $Split,
            '--output', $RunDir, '--model', $TextModel, '--vision-model', $VisionModel,
            '--vision-projector', $VisionProjector, '--vision-backend', 'mtmd',
            '--phase', $Phase, '--threads', "$Threads", '--max-tokens', "$MaxTokens",
            '--vision-max-tokens', "$VisionMaxTokens")
        if ($PSBoundParameters.ContainsKey('Limit')) { $runArguments += @('--limit', "$Limit") }
        Write-Host 'Starting CPU inference. Existing immutable runs are resumed only if their manifest matches tasks, settings and source hashes.'
        # Native MTMD diagnostics use stderr even on success. Windows PowerShell
        # must not convert these diagnostic lines into terminating exceptions.
        $inferenceErrorPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & $pythonExe @runArguments
            $inferenceExitCode = $LASTEXITCODE
        }
        finally { $ErrorActionPreference = $inferenceErrorPreference }
        if ($inferenceExitCode -ne 0) {
            throw 'Inference stopped. Keep the original logs. For changed source/settings or a failed cached call, use a new -RunDir.'
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $RunDir 'manifest.json') -PathType Leaf)) {
        throw "No saved run manifest found in $RunDir. Replay cannot invent results."
    }
    & $pythonExe -m flowrefine.cli analyze $RunDir --output $AnalysisDir
    if ($LASTEXITCODE -ne 0) { throw 'Saved-run analysis failed; inspect the console error.' }
    & $pythonExe -m flowrefine.cli gallery $RunDir --output $GalleryPath
    if ($LASTEXITCODE -ne 0) { throw 'Offline gallery generation failed.' }
    Write-Host "Analysis: $AnalysisDir/SUMMARY.md"
    Write-Host "Offline gallery: $GalleryPath"
    Write-Host 'Inspect coverage in the summary; successful analysis does not imply all model arms executed.'
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    Pop-Location
}
