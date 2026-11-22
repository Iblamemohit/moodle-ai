import os
import sys
import functools
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
from dotenv import load_dotenv

# Reconfigure console streams on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_ACTIVE_WORKSPACE_OVERRIDE: Optional[Path] = None


def set_active_workspace(path: Union[str, Path]) -> Path:
    """
    Manually switches the active workspace directory at runtime.
    Clears configuration caches so subsequent calls dynamically resolve to the new root.
    """
    global _ACTIVE_WORKSPACE_OVERRIDE
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Workspace directory does not exist: {p}")
    _ACTIVE_WORKSPACE_OVERRIDE = p
    get_config.cache_clear()
    return p


def reset_active_workspace() -> None:
    """Resets any manual workspace override back to automatic dynamic discovery."""
    global _ACTIVE_WORKSPACE_OVERRIDE
    _ACTIVE_WORKSPACE_OVERRIDE = None
    get_config.cache_clear()


def get_workspace_dir() -> Path:
    """
    Dynamically discovers and resolves the active moodle workspace directory.
    Prevents silent divergence between development ('moodle-study-tool') and
    production ('moodle-ai').

    Resolution priority:
    1. Programmatic runtime override (via set_active_workspace)
    2. Environment variables: MOODLE_AI_ROOT, MOODLE_STUDY_TOOL_ROOT, WORKSPACE_DIR
    3. Active working directory (cwd) or its parents if containing moodle.py / src
    4. Codebase root containing this config.py file
    5. Standard production / dev directory discovery:
       - ~/Desktop/moodle-ai or ~/moodle-ai (production)
       - ~/Documents/moodle-study-tool (development)
    """
    global _ACTIVE_WORKSPACE_OVERRIDE
    if _ACTIVE_WORKSPACE_OVERRIDE is not None and _ACTIVE_WORKSPACE_OVERRIDE.exists():
        return _ACTIVE_WORKSPACE_OVERRIDE

    # 1. Environment variable override
    for env_var in ("MOODLE_AI_ROOT", "MOODLE_STUDY_TOOL_ROOT", "WORKSPACE_DIR"):
        val = os.getenv(env_var)
        if val:
            try:
                p = Path(val).expanduser().resolve()
                if p.exists() and p.is_dir():
                    return p
            except (PermissionError, OSError):
                continue

    # 2. Check current working directory and its parents
    try:
        cwd = Path.cwd().resolve()
        for candidate in [cwd, *cwd.parents]:
            if (candidate / "moodle.py").exists() and (candidate / "src").exists():
                return candidate
    except Exception:
        pass

    # 3. Default to the codebase containing this config file
    codebase_root = Path(__file__).resolve().parent.parent
    if (codebase_root / "moodle.py").exists():
        return codebase_root

    # 4. Standard production / dev directory fallback
    home = Path.home()
    candidates = [
        home / "Desktop" / "moodle-ai",
        home / "moodle-ai",
        home / "Documents" / "moodle-study-tool"
    ]
    for c in candidates:
        if c.exists() and (c / "moodle.py").exists():
            return c.resolve()

    return codebase_root


def discover_available_workspaces() -> List[Dict[str, Any]]:
    """
    Discovers all known moodle-ai / moodle-study-tool workspaces on this machine.
    Helpful for MCP clients to inspect available environments and data stores.
    """
    discovered = []
    current_active = get_workspace_dir()
    candidates = [
        ("Current Active", current_active),
        ("Local Codebase", Path(__file__).resolve().parent.parent),
        ("Production (Desktop)", Path.home() / "Desktop" / "moodle-ai"),
        ("Production (Symlink)", Path.home() / "moodle-ai"),
        ("Development (Documents)", Path.home() / "Documents" / "moodle-study-tool")
    ]
    seen_paths = set()
    for label, candidate in candidates:
        try:
            p = candidate.expanduser().resolve()
            if p.exists() and (p / "moodle.py").exists() and str(p) not in seen_paths:
                seen_paths.add(str(p))
                db_file = p / "data" / "moodle_knowledge.db"
                has_db = db_file.exists()
                has_env = (p / ".env").exists()
                is_prod = "moodle-ai" in p.name.lower()
                discovered.append({
                    "label": label,
                    "path": str(p),
                    "name": p.name,
                    "type": "production" if is_prod else "development",
                    "is_active": str(p) == str(current_active),
                    "has_database": has_db,
                    "has_env": has_env,
                    "database_size_bytes": db_file.stat().st_size if has_db else 0
                })
        except Exception:
            continue
    return discovered


@functools.lru_cache(maxsize=8)
def _load_workspace_config(ws_str: str) -> Dict[str, Any]:
    ws = Path(ws_str)
    env_path = ws / ".env"
    try:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
    except (PermissionError, OSError):
        pass

    user = os.getenv("KERBEROS_USER", "")
    password = os.getenv("KERBEROS_PASSWORD", "")
    baseurls = os.getenv("MOODLE_BASEURLS", "https://moodle.iitd.ac.in/, https://moodlenew.iitd.ac.in/")
    output_dir = os.getenv("OUTPUT_DIR", "output")
    user_files_dir = os.getenv("USER_FILES_DIR", "user_files")
    parsed_dir = os.getenv("PARSED_DIR", "data/parsed")
    chroma_dir = os.getenv("CHROMA_DIR", "data/chroma_db")
    db_path = os.getenv("KNOWLEDGE_DB_PATH", "data/moodle_knowledge.db")
    tracked_semester = os.getenv("TRACKED_SEMESTER", "")

    urls_list = [u.strip() for u in baseurls.split(",") if u.strip()]
    user_files_resolved = (ws / user_files_dir).resolve()

    return {
        "user": user,
        "password": password,
        "baseurls": urls_list,
        "output_dir": str((ws / output_dir).resolve()),
        "user_files_dir": str(user_files_resolved),
        "parsed_dir": str((ws / parsed_dir).resolve()),
        "chroma_dir": str((ws / chroma_dir).resolve()),
        "db_path": str((ws / db_path).resolve()),
        "tracked_semester": tracked_semester,
        "workspace_dir": str(ws),
        "env_path": str(env_path),
    }


def get_config(workspace_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Loads configuration directly from the active workspace's .env,
    cached for fast repeated access.
    """
    ws = Path(workspace_dir).expanduser().resolve() if workspace_dir else get_workspace_dir()
    return _load_workspace_config(str(ws))


# Maintain backward compatibility for cache_clear on get_config
get_config.cache_clear = _load_workspace_config.cache_clear  # type: ignore


def init_env_template(workspace_dir: Optional[Union[str, Path]] = None) -> str:
    """Creates a default .env file from template if it doesn't exist in the active workspace."""
    ws = Path(workspace_dir).expanduser().resolve() if workspace_dir else get_workspace_dir()
    env_path = ws / ".env"
    if not env_path.exists():
        template_content = (
            "# Enter your IIT Delhi Kerberos credentials below:\n"
            "KERBEROS_USER=your_kerberos_id_here\n"
            "KERBEROS_PASSWORD=your_kerberos_password_here\n\n"
            "# Moodle Configuration\n"
            "MOODLE_BASEURLS=https://moodle.iitd.ac.in/, https://moodlenew.iitd.ac.in/\n"
            "TRACKED_SEMESTER=\n"
            "OUTPUT_DIR=output\n"
            "USER_FILES_DIR=user_files\n"
            "PARSED_DIR=data/parsed\n"
            "CHROMA_DIR=data/chroma_db\n"
        )
        env_path.write_text(template_content, encoding="utf-8")
    return str(env_path)


def save_env_config(
    user: str,
    password: str,
    baseurls: Optional[Union[str, List[str]]] = None,
    output_dir: Optional[str] = None,
    tracked_semester: Optional[str] = None,
    user_files_dir: Optional[str] = None,
    workspace_dir: Optional[Union[str, Path]] = None
) -> bool:
    """Saves user credentials, tracked semester, and paths to .env in the active workspace."""
    ws = Path(workspace_dir).expanduser().resolve() if workspace_dir else get_workspace_dir()
    env_path = ws / ".env"
    if isinstance(baseurls, list):
        baseurls = ", ".join(baseurls)

    cfg = {
        "KERBEROS_USER": user,
        "KERBEROS_PASSWORD": password,
        "MOODLE_BASEURLS": baseurls or os.getenv("MOODLE_BASEURLS", "https://moodle.iitd.ac.in/, https://moodlenew.iitd.ac.in/"),
        "TRACKED_SEMESTER": tracked_semester or os.getenv("TRACKED_SEMESTER", ""),
        "OUTPUT_DIR": output_dir or os.getenv("OUTPUT_DIR", "output"),
        "USER_FILES_DIR": user_files_dir or os.getenv("USER_FILES_DIR", "user_files"),
        "PARSED_DIR": os.getenv("PARSED_DIR", "data/parsed"),
        "CHROMA_DIR": os.getenv("CHROMA_DIR", "data/chroma_db"),
    }

    env_path.write_text("\n".join(f"{k}={v}" for k, v in cfg.items()) + "\n", encoding="utf-8")
    get_config.cache_clear()
    load_dotenv(dotenv_path=env_path, override=True)
    return True


def __getattr__(name: str) -> Any:
    """Dynamically resolves module-level attributes like WORKSPACE_DIR and ENV_PATH."""
    if name == "WORKSPACE_DIR":
        return get_workspace_dir()
    if name == "ENV_PATH":
        return get_workspace_dir() / ".env"
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
