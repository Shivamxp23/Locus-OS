# install.ps1 - Locus OS thin launcher for Windows (R1, R9, R10)
$ErrorActionPreference = "Stop"

Write-Host "==> Checking Python prerequisites..." -ForegroundColor Cyan
$pythonExe = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    $ver = & py -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -eq 0 -and [version]$ver -ge [version]"3.11") {
        $pythonExe = "py -3"
    }
}

if (-not $pythonExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -eq 0 -and [version]$ver -ge [version]"3.11") {
        $pythonExe = "python"
    }
}

if (-not $pythonExe) {
    Write-Error "Python 3.11+ is required to install Locus OS. Please install Python 3.11 or newer."
    exit 1
}

Write-Host "==> Found Python ($pythonExe), launching Locus installer..." -ForegroundColor Green
$repoRoot = $PSScriptRoot
$env:PYTHONPATH = "$repoRoot;$env:PYTHONPATH"

if ($pythonExe -eq "py -3") {
    & py -3 -m locus_cli.main @args
} else {
    & python -m locus_cli.main @args
}
exit $LASTEXITCODE
