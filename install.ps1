# Locus Unified Installer (PowerShell thin launcher)
# Checks Python 3.10+ and launches locus_cli.install
$ErrorActionPreference = "Stop"

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3 -m locus_cli.install @args
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & python -m locus_cli.install @args
    exit $LASTEXITCODE
}

Write-Error "Python 3 is required but was not found in PATH."
exit 1
