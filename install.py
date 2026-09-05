#!/usr/bin/env python3
"""
moodle-study-agent / moodle-ai Universal Auto-Installer & Configurator
Configures virtual environment, dependencies, macOS preview handler,
and registers MCP tools across Claude Desktop, Cursor, Antigravity, VS Code / Codex, and Windsurf.
"""

import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path

# Reconfigure console streams on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKSPACE_DIR = Path(__file__).resolve().parent
PYTHON_BIN = sys.executable

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}=== {title} ==={Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*60}{Colors.ENDC}\n")

def print_step(step_num: int, message: str):
    print(f"{Colors.BOLD}{Colors.OKBLUE}[Step {step_num}]{Colors.ENDC} {message}")

def print_success(message: str):
    print(f"  {Colors.OKGREEN}[OK] {message}{Colors.ENDC}")

def print_warn(message: str):
    print(f"  {Colors.WARNING}[WARN] {message}{Colors.ENDC}")

def print_fail(message: str):
    print(f"  {Colors.FAIL}[FAIL] {message}{Colors.ENDC}")

def get_venv_python() -> Path:
    if platform.system() == "Windows":
        return WORKSPACE_DIR / ".venv" / "Scripts" / "python.exe"
    return WORKSPACE_DIR / ".venv" / "bin" / "python"

def step_setup_virtualenv():
    print_step(1, "Checking Python Virtual Environment (.venv)...")
    venv_dir = WORKSPACE_DIR / ".venv"
    venv_py = get_venv_python()

    if not venv_py.exists():
        print("  Creating virtual environment in .venv...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print_success("Created .venv virtual environment.")
    else:
        print_success("Virtual environment already exists.")

    print("  Installing / updating dependencies from requirements.txt...")
    req_file = WORKSPACE_DIR / "requirements.txt"
    if req_file.exists():
        subprocess.run([str(venv_py), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
        subprocess.run([str(venv_py), "-m", "pip", "install", "-q", "-r", str(req_file)], check=True)
        print_success("Installed all dependencies successfully.")
    else:
        print_warn("requirements.txt not found, skipping pip install.")

def step_setup_env():
    print_step(2, "Checking Configuration (.env)...")
    env_file = WORKSPACE_DIR / ".env"
    sample_file = WORKSPACE_DIR / ".env.sample" if (WORKSPACE_DIR / ".env.sample").exists() else WORKSPACE_DIR / "env.sample"

    if not env_file.exists():
        if sample_file.exists():
            shutil.copy(sample_file, env_file)
            print_success(f"Created .env from {sample_file.name} template.")
        else:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(
                    "# Enter your IIT Delhi Kerberos credentials below:\n"
                    "KERBEROS_USER=your_kerberos_id_here\n"
                    "KERBEROS_PASSWORD=your_kerberos_password_here\n\n"
                    "# Moodle Configuration\n"
                    "MOODLE_BASEURLS=https://moodle.iitd.ac.in/, https://moodlenew.iitd.ac.in/\n"
                    "TRACKED_SEMESTER=2601\n"
                    "OUTPUT_DIR=output\n"
                    "PARSED_DIR=data/parsed\n"
                    "CHROMA_DIR=data/chroma_db\n"
                )
            print_success("Created new .env configuration file.")
    else:
        print_success(".env file is present.")

def update_json_mcp_config(config_file: Path, server_name: str, python_path: Path, script_path: Path):
    config_file.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}

    data["mcpServers"][server_name] = {
        "command": str(python_path.resolve()),
        "args": [str(script_path.resolve())]
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def step_setup_mcp_configs():
    print_step(4, "Auto-Configuring MCP Servers for Claude, Cursor, Antigravity, VS Code, Windsurf...")
    
    venv_py = get_venv_python()
    mcp_script = WORKSPACE_DIR / "mcp_server.py"

    # 1. Claude Desktop
    claude_paths = []
    if platform.system() == "Darwin":
        claude_paths.append(Path.home() / "Library/Application Support/Claude/claude_desktop_config.json")
    elif platform.system() == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            claude_paths.append(Path(appdata) / "Claude/claude_desktop_config.json")
    else:
        claude_paths.append(Path.home() / ".config/Claude/claude_desktop_config.json")

    for c_path in claude_paths:
        try:
            update_json_mcp_config(c_path, "moodle-ai", venv_py, mcp_script)
            print_success(f"Configured Claude Desktop: {c_path}")
        except Exception as e:
            print_warn(f"Could not update Claude Desktop config at {c_path}: {e}")

    # 2. Workspace configs (.cursor/mcp.json and .vscode/mcp.json)
    cursor_workspace = WORKSPACE_DIR / ".cursor" / "mcp.json"
    vscode_workspace = WORKSPACE_DIR / ".vscode" / "mcp.json"

    try:
        update_json_mcp_config(cursor_workspace, "moodle-ai", venv_py, mcp_script)
        print_success(f"Configured Cursor Workspace: {cursor_workspace.relative_to(WORKSPACE_DIR)}")
    except Exception as e:
        print_warn(f"Cursor workspace config error: {e}")

    try:
        update_json_mcp_config(vscode_workspace, "moodle-ai", venv_py, mcp_script)
        print_success(f"Configured VS Code / Codex Workspace: {vscode_workspace.relative_to(WORKSPACE_DIR)}")
    except Exception as e:
        print_warn(f"VS Code workspace config error: {e}")

    # 3. Global Cursor
    cursor_global = Path.home() / ".cursor" / "mcp.json"
    try:
        update_json_mcp_config(cursor_global, "moodle-ai", venv_py, mcp_script)
        print_success(f"Configured Cursor Global: {cursor_global}")
    except Exception as e:
        pass

    # 4. Antigravity Global (~/.gemini/config/mcp_config.json)
    gemini_mcp = Path.home() / ".gemini" / "config" / "mcp_config.json"
    if gemini_mcp.parent.exists():
        try:
            update_json_mcp_config(gemini_mcp, "moodle-ai", venv_py, mcp_script)
            print_success(f"Configured Antigravity Global: {gemini_mcp}")
        except Exception as e:
            pass

    # 5. Windsurf (~/.codeium/windsurf/mcp_config.json)
    windsurf_mcp = Path.home() / ".codeium" / "windsurf" / "mcp_config.json"
    if windsurf_mcp.parent.exists():
        try:
            update_json_mcp_config(windsurf_mcp, "moodle-ai", venv_py, mcp_script)
            print_success(f"Configured Windsurf Global: {windsurf_mcp}")
        except Exception as e:
            pass

def step_sync_skills():
    print_step(5, "Syncing Skills for Antigravity, Claude Code & Agentic IDEs...")
    agents_skills = WORKSPACE_DIR / ".agents" / "skills"
    claude_skills = WORKSPACE_DIR / ".claude" / "skills"
    global_skills = Path.home() / ".gemini" / "config" / "skills"

    # Ensure .claude/skills mirrors .agents/skills
    if agents_skills.exists():
        claude_skills.mkdir(parents=True, exist_ok=True)
        for skill_dir in agents_skills.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                dest = claude_skills / skill_dir.name
                shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
        print_success("Synchronized local skills in .agents/skills/ and .claude/skills/.")

    if agents_skills.exists() and global_skills.exists():
        for skill_dir in agents_skills.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                dest = global_skills / skill_dir.name
                shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
        print_success("Synchronized skills into Antigravity global skills directory.")

def main():
    print_header("moodle-ai Universal Setup & Installer")
    print(f"  Workspace: {WORKSPACE_DIR}")
    print(f"  System:    {platform.system()} ({platform.machine()})\n")

    step_setup_virtualenv()
    step_setup_env()
    step_setup_mcp_configs()
    step_sync_skills()

    print_header("Installation & Configuration Complete!")
    print("You are ready to use moodle-ai in any environment:\n")
    print(f"  * {Colors.BOLD}Antigravity IDE / Gemini{Colors.ENDC}: Type `/moodle-ai` in chat.")
    print(f"  * {Colors.BOLD}Claude Desktop{Colors.ENDC}: Open Claude (MCP server 'moodle-ai' is pre-configured).")
    print(f"  * {Colors.BOLD}Cursor / Windsurf / Codex{Colors.ENDC}: Open this folder (MCP is auto-configured).")
    print(f"  * {Colors.BOLD}Terminal / CLI{Colors.ENDC}: Run `python agent_tools.py /sync`")
    print("\nNext step: Open `.env` to verify your Kerberos ID & password, then run `/sync`!\n")

if __name__ == "__main__":
    main()

