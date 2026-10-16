# uninstall.ps1 - Locus OS thin uninstaller launcher for Windows
$ErrorActionPreference = "Stop"

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
    Write-Error "Python 3.11+ is required to uninstall Locus OS."
    exit 1
}

$repoRoot = $PSScriptRoot
$env:PYTHONPATH = "$repoRoot;$env:PYTHONPATH"

if ($pythonExe -eq "py -3") {
    & py -3 -m locus_cli.main uninstall @args
} else {
    & python -m locus_cli.main uninstall @args
}
exit $LASTEXITCODE
