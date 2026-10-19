@echo off
rem Locus CLI dispatcher and Pi pass-through launcher (R5, R7)
if "%1"=="doctor" (
    shift
    py -3 -m locus_cli.doctor %1 %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if "%1"=="install" (
    shift
    py -3 -m locus_cli.install %1 %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if "%1"=="pair" (
    shift
    py -3 -m locus_cli.setup_telegram %1 %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if "%1"=="setup" (
    if "%2"=="pi" (
        shift
        shift
        node packages\coding-agent\dist\cli.js %1 %2 %3 %4 %5 %6 %7 %8 %9
        exit /b %ERRORLEVEL%
    )
    shift
    py -3 -m locus_cli.install %1 %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
rem Default pass-through to Pi TUI (R5) if available, otherwise doctor
if exist packages\coding-agent\dist\cli.js (
    node packages\coding-agent\dist\cli.js %*
    exit /b %ERRORLEVEL%
) else (
    py -3 -m locus_cli.doctor %*
    exit /b %ERRORLEVEL%
)
