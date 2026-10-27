[CmdletBinding()]
param(
    [string]$RunDir = 'runs/test_v1',
    [string]$GalleryPath = 'demo/index.html',
    [switch]$Rebuild
)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($Rebuild -or -not (Test-Path -LiteralPath $GalleryPath -PathType Leaf)) {
        $pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
        if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
            throw 'No saved gallery and no project Python environment. See README.md.'
        }
        if (-not (Test-Path -LiteralPath (Join-Path $RunDir 'tasks_public.json') -PathType Leaf)) {
            throw "No saved public tasks in $RunDir. Run or copy a real experiment first."
        }
        $previousPythonPath = $env:PYTHONPATH
        try {
            $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
            & $pythonExe -m flowrefine.cli gallery $RunDir --output $GalleryPath
            if ($LASTEXITCODE -ne 0) { throw 'Could not build the saved-results gallery.' }
        }
        finally { $env:PYTHONPATH = $previousPythonPath }
    }
    $galleryFile = (Resolve-Path -LiteralPath $GalleryPath).Path
    Write-Host "Opening saved results: $galleryFile"
    # Explicitly invoked by the user to view the demo; no inference/server starts.
    Start-Process -FilePath $galleryFile
}
finally { Pop-Location }
