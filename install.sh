#!/usr/bin/env bash
# Locus Unified Installer (POSIX thin launcher)
# Checks Python 3.10+ and launches locus_cli.install
set -e

if command -v python3 &>/dev/null; then
    exec python3 -m locus_cli.install "$@"
elif command -v python &>/dev/null; then
    exec python -m locus_cli.install "$@"
else
    echo "Python 3 is required but was not found in PATH." >&2
    exit 1
fi
