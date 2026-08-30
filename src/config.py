import os
import configparser
from pathlib import Path
from dotenv import load_dotenv

# Base workspace directory
WORKSPACE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
ENV_PATH = WORKSPACE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

def get_config():
    """Loads configuration directly from .env."""
    user = os.getenv("KERBEROS_USER", "")
    password = os.getenv("KERBEROS_PASSWORD", "")
    baseurls = os.getenv("MOODLE_BASEURLS", "https://moodle.iitd.ac.in/, https://moodlenew.iitd.ac.in/")
    output_dir = os.getenv("OUTPUT_DIR", "output")
    parsed_dir = os.getenv("PARSED_DIR", "data/parsed")
    chroma_dir = os.getenv("CHROMA_DIR", "data/chroma_db")
    tracked_semester = os.getenv("TRACKED_SEMESTER", "2601")

    urls_list = [u.strip() for u in baseurls.split(",") if u.strip()]

    return {
        "user": user,
        "password": password,
        "baseurls": urls_list,
        "output_dir": str((WORKSPACE_DIR / output_dir).resolve()),
        "parsed_dir": str((WORKSPACE_DIR / parsed_dir).resolve()),
        "chroma_dir": str((WORKSPACE_DIR / chroma_dir).resolve()),
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
            "TRACKED_SEMESTER=2601\n"
            "OUTPUT_DIR=output\n"
            "PARSED_DIR=data/parsed\n"
            "CHROMA_DIR=data/chroma_db\n"
        )
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write(template_content)
    return str(ENV_PATH)

def save_env_config(user, password, baseurls=None, output_dir=None, tracked_semester=None):
    """Saves user credentials, tracked semester, and paths to .env."""
    lines = [
        f"KERBEROS_USER={user}",
        f"KERBEROS_PASSWORD={password}",
    ]
    if baseurls:
        if isinstance(baseurls, list):
            baseurls = ", ".join(baseurls)
        lines.append(f"MOODLE_BASEURLS={baseurls}")
    else:
        lines.append("MOODLE_BASEURLS=https://moodle.iitd.ac.in/, https://moodlenew.iitd.ac.in/")

    if tracked_semester:
        lines.append(f"TRACKED_SEMESTER={tracked_semester}")
    else:
        curr_sem = os.getenv("TRACKED_SEMESTER", "2601")
        lines.append(f"TRACKED_SEMESTER={curr_sem}")

    if output_dir:
        lines.append(f"OUTPUT_DIR={output_dir}")
    else:
        curr_out = os.getenv("OUTPUT_DIR", "output")
        lines.append(f"OUTPUT_DIR={curr_out}")

    lines.append("PARSED_DIR=data/parsed")
    lines.append("CHROMA_DIR=data/chroma_db")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    
    # Reload environment
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    return True

