#!/usr/bin/env bash
# Universal 1-Click Installer for moodle-study-agent / moodle-ai
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎓 Launching moodle-study-agent Universal Setup..."

# Detect available python3 binary
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo "❌ Error: Python 3 was not found on your system. Please install Python 3.10+ and re-run."
    exit 1
fi

"$PY_BIN" "$SCRIPT_DIR/install.py"
