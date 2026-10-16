#!/usr/bin/env bash
# uninstall.sh - Locus OS uninstaller launcher for Linux/macOS
set -euo pipefail

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
    echo "ERROR: Python 3.11+ is required to uninstall Locus OS." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

exec "$PYTHON_BIN" -m locus_cli.main uninstall "$@"
