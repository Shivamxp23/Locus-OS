@echo off
rem Locus Unified Installer (Windows CMD thin launcher)
py -3 -m locus_cli.install %*
if %ERRORLEVEL% NEQ 0 (
    python -m locus_cli.install %*
)
