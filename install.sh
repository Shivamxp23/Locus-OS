#!/usr/bin/env bash
# install.sh - Locus OS thin launcher for Linux/macOS (R1, R9, R10)
set -euo pipefail

echo "==> Checking Python prerequisites..."
PYTHON_BIN=""

for cmd in python3 python py; do
    if command -v "$cmd" >/dev/null 2>&1; then
        VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        if [ -n "$VER" ]; then
            MAJOR=$(echo "$VER" | cut -d. -f1)
            MINOR=$(echo "$VER" | cut -d. -f2)
            if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
                PYTHON_BIN="$cmd"
                break
            fi
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: Python 3.11+ is required to install Locus OS. Please install Python 3.11 or newer." >&2
    exit 1
fi

echo "==> Found Python ($PYTHON_BIN), launching Locus installer..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

exec "$PYTHON_BIN" -m locus_cli.main install "$@"
