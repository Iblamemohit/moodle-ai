import os
import sys
import functools
from pathlib import Path
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

# Base workspace directory
WORKSPACE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
ENV_PATH = WORKSPACE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

@functools.lru_cache(maxsize=1)
def get_config():
    """Loads configuration directly from .env, cached for fast repeated access."""
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
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
    user_files_resolved = (WORKSPACE_DIR / user_files_dir).resolve()

    return {
        "user": user,
        "password": password,
        "baseurls": urls_list,
        "output_dir": str((WORKSPACE_DIR / output_dir).resolve()),
        "user_files_dir": str(user_files_resolved),
        "parsed_dir": str((WORKSPACE_DIR / parsed_dir).resolve()),
        "chroma_dir": str((WORKSPACE_DIR / chroma_dir).resolve()),
        "db_path": str((WORKSPACE_DIR / db_path).resolve()),
        "tracked_semester": tracked_semester,
        "workspace_dir": str(WORKSPACE_DIR),
        "env_path": str(ENV_PATH),
    }

def init_env_template():
    """Creates a default .env file from template if it doesn't exist."""
    if not ENV_PATH.exists():
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
        ENV_PATH.write_text(template_content, encoding="utf-8")
    return str(ENV_PATH)

def save_env_config(user, password, baseurls=None, output_dir=None, tracked_semester=None, user_files_dir=None):
    """Saves user credentials, tracked semester, and paths to .env."""
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

    ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in cfg.items()) + "\n", encoding="utf-8")
    get_config.cache_clear()
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    return True
