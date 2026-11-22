#!/usr/bin/env bash
# ==============================================================================
# moodle-ai Universal Setup & MCP Configurator (Zero Global Cache Footprint)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Enforce zero cache accumulation for uv and pip
export UV_NO_CACHE=1
export PIP_NO_CACHE_DIR=1

echo "============================================================"
echo "=== moodle-ai Fast Zero-Bloat Setup ==="
echo "============================================================"
echo "Directory: $SCRIPT_DIR"

# 1. Select Python / UV Runtime
VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
fi

echo "[1/5] Checking Virtual Environment & Dependencies..."
if command -v uv &>/dev/null; then
    echo "  -> Detected uv: $(uv --version)"
    if [ ! -f "$VENV_PY" ]; then
        echo "  -> Creating local .venv using uv (zero-cache mode)..."
        uv venv .venv --no-cache
    fi
    echo "  -> Installing dependencies via uv pip (zero-cache mode)..."
    uv pip install --no-cache -r requirements.txt
else
    echo "  -> uv not detected; falling back to standard python3 venv..."
    if command -v python3 &>/dev/null; then
        PY_SYS="python3"
    elif command -v python &>/dev/null; then
        PY_SYS="python"
    else
        echo "[ERROR] Python 3 was not found. Please install Python 3.10+."
        exit 1
    fi
    if [ ! -f "$VENV_PY" ]; then
        echo "  -> Creating local .venv..."
        "$PY_SYS" -m venv .venv
    fi
    echo "  -> Installing dependencies via pip (--no-cache-dir)..."
    "$VENV_PY" -m pip install --no-cache-dir -q -r requirements.txt
fi
echo "  [OK] Python dependencies verified in $VENV_DIR"

# 2. Configuration (.env) Setup
echo "[2/5] Checking Configuration (.env)..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env.sample" ]; then
        cp "$SCRIPT_DIR/.env.sample" "$SCRIPT_DIR/.env"
        echo "  [OK] Created .env from .env.sample"
    elif [ -f "$SCRIPT_DIR/env.sample" ]; then
        cp "$SCRIPT_DIR/env.sample" "$SCRIPT_DIR/.env"
        echo "  [OK] Created .env from env.sample"
    fi
else
    echo "  [OK] .env already exists."
fi

# Ensure user_files folder exists
mkdir -p "$SCRIPT_DIR/user_files"
touch "$SCRIPT_DIR/user_files/.gitkeep"

# 3. Configure MCP Servers Across Host Harnesses
echo "[3/5] Configuring MCP Tools for Antigravity, Claude, Cursor, and VS Code..."
"$VENV_PY" - << 'EOF'
import json
import os
import platform
from pathlib import Path

root_dir = Path(".").resolve()
is_win = platform.system() == "Windows"
venv_py = root_dir / (".venv/Scripts/python.exe" if is_win else ".venv/bin/python")
mcp_script = root_dir / "src/mcp_server.py"

server_entry = {
    "command": str(venv_py),
    "args": [str(mcp_script)]
}

targets = [
    root_dir / ".cursor/mcp.json",
    root_dir / ".vscode/mcp.json",
    Path.home() / ".cursor/mcp.json",
    Path.home() / ".gemini/config/mcp_config.json"
]

if platform.system() == "Darwin":
    targets.append(Path.home() / "Library/Application Support/Claude/claude_desktop_config.json")
elif platform.system() == "Windows":
    appdata = os.getenv("APPDATA")
    if appdata:
        targets.append(Path(appdata) / "Claude/claude_desktop_config.json")
else:
    targets.append(Path.home() / ".config/Claude/claude_desktop_config.json")

for target in targets:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        if not isinstance(data, dict):
            data = {}
        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}
        data["mcpServers"]["moodle-ai"] = server_entry
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"  [OK] Registered MCP server in: {target}")
    except Exception as e:
        print(f"  [WARN] Skipped {target}: {e}")
EOF

# 4. Synchronize Skills
echo "[4/5] Synchronizing Agent Skills..."
mkdir -p "$SCRIPT_DIR/.claude/skills/moodle-ai"
if [ -d "$SCRIPT_DIR/.agents/skills/moodle-ai" ]; then
    cp -r "$SCRIPT_DIR/.agents/skills/moodle-ai/"* "$SCRIPT_DIR/.claude/skills/moodle-ai/"
fi
GEMINI_SKILLS="$HOME/.gemini/config/skills"
if [ -d "$GEMINI_SKILLS" ]; then
    mkdir -p "$GEMINI_SKILLS/moodle-ai"
    cp -r "$SCRIPT_DIR/.agents/skills/moodle-ai/"* "$GEMINI_SKILLS/moodle-ai/"
    echo "  [OK] Synchronized skills into Antigravity global skills directory."
fi

# 5. CLI Link & Completion
echo "[5/5] Setup Complete!"
echo "============================================================"
echo "You can now run moodle-ai via:"
echo "  - Terminal:   python moodle.py /moodle-ai"
echo "  - Node / NPX: npm run sync | npm test | npx moodle-ai /ask \"...\""
echo "  - MCP Host:   Antigravity, Claude Desktop, Cursor, and VS Code"
echo "============================================================"
