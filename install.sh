#!/usr/bin/env bash
# Universal setup launcher delegating to setup.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/setup.sh" "$@"
