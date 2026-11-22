import os
import sys
import re
import json
import urllib.parse
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

# Reconfigure console streams on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import get_config, save_env_config, init_env_template

def setup_moodle(user: Optional[str] = None, password: Optional[str] = None, baseurls: Optional[str] = None, output_dir: str = "output") -> Dict[str, Any]:
    """
    [Tool: /setup] Generates or verifies the local .env configuration file securely.
    """
    env_path = init_env_template()
    
    if user and password and user != "your_kerberos_id_here":
        urls = [u.strip() for u in baseurls.split(",") if u.strip()] if baseurls else None
        success = save_env_config(user, password, urls, output_dir)
        return {
            "status": "success",
            "is_ready": True,
            "env_path": env_path,
            "message": f"Successfully updated .env with user '{user}' and output dir '{output_dir}'."
        }

    # Check if existing .env has valid credentials
    cfg = get_config()
    curr_user = cfg.get("user", "")
    curr_pwd = cfg.get("password", "")
    is_valid = bool(curr_user and curr_pwd and curr_user != "your_kerberos_id_here")

    if is_valid:
        return {
            "status": "configured",
            "is_ready": True,
            "env_path": env_path,
            "user": curr_user,
            "output_dir": cfg.get("output_dir"),
            "message": f"Credentials already configured in .env for user '{curr_user}'."
        }
    else:
        return {
            "status": "template_ready",
            "is_ready": False,
            "env_path": env_path,
            "message": "Created .env template file. Please enter your Kerberos ID and password directly into the .env file."
        }

def moodle_change_sync(target_semester: Optional[str] = None, new_output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    [Tool: /change-sync] Changes the default tracked semester (e.g. 2601, 2502, all) or storage directory in .env.
    """
    cfg = get_config()
    user = cfg.get("user", "")
    pwd = cfg.get("password", "")
    baseurls = cfg.get("baseurls", [])
    curr_sem = cfg.get("tracked_semester", "2601")
    curr_out = cfg.get("output_dir", "output")

    if not target_semester and not new_output_dir:
        # Discover available semesters to let user choose
        from src.scraper import discover_available_semesters
        sems_res = discover_available_semesters()
        return {
            "status": "needs_selection",
            "current_tracked_semester": curr_sem,
            "current_output_dir": curr_out,
            "available_semesters": sems_res.get("semesters", {}),
            "instruction": "Specify the semester to track: `/change-sync <SEMESTER_CODE>` (e.g. `/change-sync 2601` or `/change-sync all`)"
        }

    sem_to_save = target_semester if target_semester else curr_sem
    out_to_save = new_output_dir if new_output_dir else curr_out

    save_env_config(user, pwd, baseurls, output_dir=out_to_save, tracked_semester=sem_to_save)
    updated_cfg = get_config()

    from src.list_manager import ListManager
    list_mgr = ListManager(updated_cfg["workspace_dir"], updated_cfg["output_dir"], updated_cfg["parsed_dir"])
    list_mgr.update_list_file()

    return {
        "status": "success",
        "tracked_semester": updated_cfg["tracked_semester"],
        "output_dir": updated_cfg["output_dir"],
        "list_file": str(list_mgr.list_file_path),
        "message": f"Successfully updated tracked sync semester to '{updated_cfg['tracked_semester']}' in .env."
    }

def sync_moodle(
    semester: Optional[str] = None,
    course_filter: Optional[str] = None,
    quick_check: bool = False,
    course_index: Optional[str] = None
) -> Dict[str, Any]:
    """
    [Tool: /sync] Asynchronously scrapes Moodle and registered custom URLs, converts PDFs to Markdown immediately as they download, and updates ChromaDB & BM25 indexes.
    Supports course_filter and quick_check (<2s check) for single course incremental sync.
    """
    from src.scraper import sync_moodle_courses
    cfg = get_config()
    target_sem = semester if semester else cfg.get("tracked_semester", "2601")
    return sync_moodle_courses(
        semester_filter=target_sem,
        course_filter=course_filter,
        quick_check=quick_check,
        course_index=course_index
    )

def moodle_add_custom_url(url: str, label: Optional[str] = None, auto_sync: bool = True) -> Dict[str, Any]:
    """
    [Tool: /moodle-add-custom-url] Registers a custom URL to scrape PDFs from and optionally triggers immediate sync & indexing.
    """
    from src.custom_scraper import CustomUrlManager
    cfg = get_config()
    url_mgr = CustomUrlManager(cfg["workspace_dir"])
    add_res = url_mgr.add_source(url, label)
    
    if add_res.get("status") in ("added", "already_exists") and auto_sync:
        print(f"\n[Custom URL] Auto-syncing custom source: {url}...")
        from src.scraper import sync_moodle_courses
        sync_res = sync_moodle_courses(semester_filter="custom")
        add_res["sync_results"] = sync_res

    return add_res

def moodle_remove_custom_url(url_or_label: str, delete_files: bool = False) -> Dict[str, Any]:
    """
    [Tool: /moodle-remove-custom-url] Removes a registered custom URL. Optionally cleans up downloaded files.
    """
    from src.custom_scraper import CustomUrlManager
    cfg = get_config()
    url_mgr = CustomUrlManager(cfg["workspace_dir"])
    rem_res = url_mgr.remove_source(url_or_label)

    if rem_res.get("status") == "removed":
        label = rem_res["source"]["label"]
        output_dir = Path(cfg["output_dir"])
        target_folder = output_dir / "Custom_Sources" / label
        if delete_files and target_folder.exists():
            shutil.rmtree(target_folder, ignore_errors=True)
            rem_res["deleted_folder"] = str(target_folder)

        # Refresh list.md
        from src.list_manager import ListManager
        list_mgr = ListManager(cfg["workspace_dir"], cfg["output_dir"], cfg["parsed_dir"])
        list_mgr.update_list_file()
        rem_res["list_file"] = str(list_mgr.list_file_path)

    return rem_res

def moodle_list_custom_urls() -> Dict[str, Any]:
    """
    [Tool: /moodle-list-custom-urls] Lists all registered custom URLs and their sync statuses.
    """
    from src.custom_scraper import CustomUrlManager
    cfg = get_config()
    url_mgr = CustomUrlManager(cfg["workspace_dir"])
    sources = url_mgr.get_sources()
    return {
        "status": "success",
        "total_sources": len(sources),
        "sources": sources
    }

def update_moodle_ai() -> Dict[str, Any]:
    """
    [Tool: /update] Pulls latest code from GitHub and refreshes Python dependencies in .venv.
    """
    import subprocess
    config = get_config()
    ws = Path(config["workspace_dir"])

    try:
        git_res = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(ws),
            capture_output=True,
            text=True,
            check=True
        )
        git_output = git_res.stdout.strip() or "Already up to date."
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Git pull failed: {e.stderr.strip() or e.stdout.strip()}",
            "hint": "Check if you have uncommitted changes or network connectivity issues."
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Git binary not found on system."
        }

    req_file = ws / "requirements.txt"
    pip_updated = False
    if req_file.exists():
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-q", "-r", str(req_file)],
                cwd=str(ws),
                capture_output=True,
                check=True
            )
            pip_updated = True
        except Exception as e:
            return {
                "status": "partial_success",
                "git_output": git_output,
                "warning": f"Code updated, but dependencies failed to install: {e}"
            }

    return {
        "status": "success",
        "message": "moodle-ai updated successfully.",
        "git_output": git_output,
        "dependencies_updated": pip_updated
    }


def moodle_list(regenerate: bool = False) -> Dict[str, Any]:
    """
    [Tool: /list] Reads list.md and returns the structured document hierarchy of all courses and materials.
    """
    from src.list_manager import ListManager
    config = get_config()
    list_mgr = ListManager(config["workspace_dir"], config["output_dir"], config["parsed_dir"], user_files_dir=config["user_files_dir"])
    
    if regenerate or not list_mgr.list_file_path.exists():
        markdown_content = list_mgr.update_list_file()
    else:
        markdown_content = list_mgr.read_list_file()

    docs_structure = list_mgr.scan_all_documents()
    total_files = sum(len(f) for c in docs_structure.values() for f in c.values())
    total_courses = sum(len(c) for c in docs_structure.values())

    return {
        "status": "success",
        "total_semesters": len(docs_structure),
        "total_courses": total_courses,
        "total_files": total_files,
        "list_file": str(list_mgr.list_file_path),
        "markdown_content": markdown_content,
        "structure": docs_structure
    }

_GLOBAL_INDEXER = None

def _get_indexer():
    """Lazily loads and caches the KnowledgeIndexer instance for reuse across MCP queries."""
    global _GLOBAL_INDEXER
    if _GLOBAL_INDEXER is None:
        from src.indexer import KnowledgeIndexer
        config = get_config()
        _GLOBAL_INDEXER = KnowledgeIndexer(config["chroma_dir"])
    return _GLOBAL_INDEXER

def moodle_ask(
    query: str, 
    doc_filter: Optional[str] = None, 
    course_filter: Optional[str] = None, 
    top_k: int = 2, 
    fallback_to_web: bool = False,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    [Tool: /ask] High-Efficiency Hybrid search across Moodle course materials with FlashRank reranking,
    paragraph-level pruning, and multimodal visual fallback.
    Returns the most relevant chunks with exact dual file & page citations.
    """
    indexer = _get_indexer()
    config = get_config()
    
    # 1. Perform Hybrid Search with FlashRank Cross-Encoder & Paragraph Pruning
    results = indexer.hybrid_search(
        query=query,
        course_filter=course_filter,
        filename_filter=doc_filter,
        top_k=top_k,
        prune_text=True
    )

    parsed_dir = Path(config["parsed_dir"])
    output_dir = Path(config["output_dir"])
    user_files_dir = Path(config["user_files_dir"])

    # Format retrieved Moodle context
    retrieved_chunks = []
    has_confident_match = False
    for r in results:
        meta = r["metadata"]
        score = r.get("rrf_score", 0.0)
        rerank_score = r.get("rerank_score", 0.0)
        is_conf = r.get("is_confident", False)
        if is_conf:
            has_confident_match = True

        src_path = Path(meta.get("source", ""))
        file_url = None
        md_url = None
        page_num = meta.get("page", 1)
        if src_path.exists():
            file_url = src_path.resolve().as_uri()
            try:
                rel_path = src_path.relative_to(output_dir)
            except ValueError:
                try:
                    rel_path = Path("User_Files") / src_path.relative_to(user_files_dir)
                except ValueError:
                    rel_path = Path(src_path.name)
            md_path = (parsed_dir / rel_path).with_suffix(".md")
            if md_path.exists():
                md_url = md_path.resolve().as_uri()

        citation_label = f"{meta.get('course')} / {meta.get('filename')} (Page {page_num})"
        if file_url and md_url:
            citation = f"[{citation_label}]({file_url}) ([Markdown]({md_url}))"
        elif file_url:
            citation = f"[{citation_label}]({file_url})"
        elif md_url:
            citation = f"[{citation_label}]({md_url})"
        else:
            citation = f"[{citation_label}]"

        retrieved_chunks.append({
            "source_type": "moodle_course_material",
            "course": meta.get("course", "Unknown"),
            "filename": meta.get("filename", "Unknown"),
            "page": page_num,
            "score": score,
            "rerank_score": rerank_score,
            "is_confident": is_conf,
            "cosine_similarity": r.get("cosine_similarity", 0.0),
            "bm25_score": r.get("bm25_score", 0.0),
            "text": r["text"],
            "pdf_path": str(src_path.resolve()) if src_path.exists() else None,
            "pdf_url": file_url,
            "md_url": md_url,
            "citation": citation
        })

    # Dynamic Top-K Optimization:
    # If the top match is exceptionally confident (FlashRank rerank_score >= 0.75, or high cosine + confident),
    # prune lower-ranked chunks to save prompt tokens without sacrificing answer accuracy.
    if retrieved_chunks:
        top_c = retrieved_chunks[0]
        top_rerank = top_c.get("rerank_score", 0.0)
        top_cosine = top_c.get("cosine_similarity", 0.0)
        top_is_conf = top_c.get("is_confident", False)

        if top_rerank >= 0.75 or (top_cosine >= 0.65 and top_is_conf):
            retrieved_chunks = retrieved_chunks[:1]
        elif len(retrieved_chunks) > 2 and (top_rerank >= 0.50 or top_cosine >= 0.55):
            retrieved_chunks = retrieved_chunks[:2]

    # 2. Check for Page-Level Visual Fallback (Strict Gated)
    visual_fallback = {
        "triggered": False,
        "visual_intent_detected": False,
        "reason": "none",
        "rendered_pages": []
    }
    try:
        from src.visual_fallback import process_visual_fallback
        visual_fallback = process_visual_fallback(query, retrieved_chunks)
    except Exception as v_ex:
        print(f"[Visual Fallback Error]: {v_ex}")

    return {
        "query": query,
        "has_confident_moodle_hit": has_confident_match,
        "used_fallback": False,
        "visual_fallback": visual_fallback,
        "moodle_context": retrieved_chunks,
        "from_cache": False
    }


def moodle_quiz(course: Optional[str] = None, num_questions: int = 3) -> Dict[str, Any]:
    """
    Generates practice questions grounded in course materials with high-density concept summaries.
    """
    target_course = course
    weak_areas = []

    config = get_config()
    parsed_dir = Path(config["parsed_dir"])
    output_dir = Path(config["output_dir"])

    indexer = _get_indexer()
    
    # Query foundational concepts, prioritizing weak areas if identified
    if weak_areas:
        query = f"{' '.join(weak_areas[:2])} key principles formulas definitions summary concepts"
    else:
        query = "key principles formulas definitions summary concepts"
    results = indexer.hybrid_search(query=query, course_filter=target_course, top_k=num_questions, prune_text=True)
    
    sampled_materials = []
    for r in results[:num_questions]:
        meta = r["metadata"]
        src_path = Path(meta.get("source", ""))
        file_url = None
        md_url = None
        page_num = meta.get("page", 1)
        if src_path.exists():
            file_url = src_path.resolve().as_uri()
            try:
                rel_path = src_path.relative_to(output_dir)
            except ValueError:
                rel_path = Path(src_path.name)
            md_path = (parsed_dir / rel_path).with_suffix(".md")
            if md_path.exists():
                md_url = md_path.resolve().as_uri()

        citation_label = f"{meta.get('course')} / {meta.get('filename')} (Page {page_num})"
        if file_url and md_url:
            citation = f"[{citation_label}]({file_url}) ([Markdown]({md_url}))"
        elif file_url:
            citation = f"[{citation_label}]({file_url})"
        elif md_url:
            citation = f"[{citation_label}]({md_url})"
        else:
            citation = f"[{citation_label}]"

        q_text = r["text"].strip()

        sampled_materials.append({
            "course": meta.get("course"),
            "filename": meta.get("filename"),
            "page": page_num,
            "text": q_text,
            "pdf_path": str(src_path.resolve()) if src_path.exists() else None,
            "pdf_url": file_url,
            "md_url": md_url,
            "citation": citation
        })

    return {
        "status": "success",
        "course": target_course or "All Enrolled Courses",
        "prioritized_weak_areas": weak_areas,
        "num_topics": len(sampled_materials),
        "materials": sampled_materials
    }


def get_course_slide(
    course_code: str,
    document_name: str,
    page_number: int,
    render_image: bool = True,
    high_res: bool = False
) -> Dict[str, Any]:
    """
    [Tool: /slide] Precision slide and page extractor.
    Locates the requested course document, extracts exact page text from parsed Markdown
    or PyMuPDF, and renders a high-res slide PNG (150 DPI default, 300 DPI raw when high_res=True).
    Returns structured metadata, markdown text, file paths, base64 image data, and human summary.
    """
    import pymupdf
    from src.visual_fallback import render_slide, get_image_base64
    config = get_config()
    output_dir = Path(config["output_dir"])
    parsed_dir = Path(config["parsed_dir"])
    user_files_dir = Path(config["user_files_dir"])

    course_clean = course_code.strip() if course_code else ""
    doc_clean = document_name.strip() if document_name else ""

    if not doc_clean:
        return {
            "status": "error",
            "message": "Document name is required to locate the slide."
        }

    # Find matching document
    search_dirs = [output_dir, user_files_dir]
    matched_file = None
    all_candidates = []

    doc_norm = re.sub(r"[^\w]", "", doc_clean.lower())
    course_norm = re.sub(r"[^\w]", "", course_clean.lower())

    for base in search_dirs:
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in (".pdf", ".pptx", ".ppt", ".docx", ".md", ".txt"):
                f_course_match = True
                if course_norm:
                    f_course_match = course_norm in re.sub(r"[^\w]", "", str(f).lower())
                
                f_name_norm = re.sub(r"[^\w]", "", f.name.lower())
                f_stem_norm = re.sub(r"[^\w]", "", f.stem.lower())

                if doc_norm == f_name_norm or doc_norm == f_stem_norm:
                    if f_course_match:
                        matched_file = f
                        break
                    else:
                        all_candidates.append(f)
                elif doc_norm in f_name_norm or doc_norm in f_stem_norm:
                    if f_course_match:
                        all_candidates.append(f)
        if matched_file:
            break

    if not matched_file and all_candidates:
        matched_file = all_candidates[0]

    if not matched_file or not matched_file.exists():
        return {
            "status": "not_found",
            "course": course_code,
            "document": document_name,
            "message": f"Could not find document '{document_name}' in course '{course_code}'. Available files: {[c.name for c in all_candidates[:5]]}"
        }

    # Determine total pages
    total_pages = 1
    doc_obj = None
    ext = matched_file.suffix.lower()

    if ext == ".pdf":
        try:
            doc_obj = pymupdf.open(str(matched_file))
            total_pages = len(doc_obj)
        except Exception as e:
            print(f"[Slide Tool Warning] Could not open PDF {matched_file.name}: {e}")

    if page_number < 1 or page_number > total_pages:
        if doc_obj:
            doc_obj.close()
        return {
            "status": "page_out_of_bounds",
            "course": course_code,
            "document": matched_file.name,
            "requested_page": page_number,
            "total_pages": total_pages,
            "message": f"Page {page_number} is out of bounds for '{matched_file.name}' (Valid page range: 1 to {total_pages})."
        }

    # Extract Markdown Text of that page
    page_text = ""
    try:
        try:
            rel_p = matched_file.relative_to(output_dir)
        except ValueError:
            try:
                rel_p = Path("User_Files") / matched_file.relative_to(user_files_dir)
            except ValueError:
                rel_p = Path(matched_file.name)
        
        md_file = parsed_dir / rel_p.with_suffix(".md")
        if md_file.exists():
            with open(md_file, "r", encoding="utf-8") as f:
                full_md = f.read()
            page_sections = re.split(r'<!-- Page \d+(?::\s*\[[^\]]+\])?\s*-->', full_md)
            page_matches = re.findall(r'<!-- Page (\d+)(?::\s*\[[^\]]+\])?\s*-->', full_md)
            for i, p_str in enumerate(page_matches):
                if int(p_str) == page_number and i + 1 < len(page_sections):
                    page_text = page_sections[i + 1].strip().rstrip("-").strip()
                    break
    except Exception as ex:
        print(f"[Slide Tool Warning] Parsed markdown extraction failed: {ex}")

    if not page_text and doc_obj and 0 <= page_number - 1 < len(doc_obj):
        page_text = doc_obj[page_number - 1].get_text("text").strip()

    if not page_text:
        page_text = f"*Slide {page_number} contains visual diagrams or graphic illustrations without extractable body text.*"

    image_path = None
    image_url = None
    image_b64 = None

    if render_image and ext == ".pdf":
        img_p = render_slide(
            str(matched_file),
            page_number,
            max_dimension=1400,
            dpi=150,
            high_res=high_res
        )
        if img_p:
            image_path = str(img_p.resolve())
            image_url = f"file://{img_p.resolve()}"
            image_b64 = get_image_base64(img_p)

    if doc_obj:
        doc_obj.close()

    summary_lines = [
        f"### Slide {page_number}: {matched_file.name} ({course_code or 'Course'})",
        f"- **Document**: `{matched_file.name}` (Page {page_number} of {total_pages})",
        f"- **Source File**: `{matched_file.resolve()}`"
    ]
    if image_url:
        mode_tag = " [300 DPI Raw]" if high_res else " [150 DPI]"
        summary_lines.append(f"- **Slide Visual{mode_tag}**: [{matched_file.stem}_p{page_number}]({image_url}) (`{image_path}`)")
        summary_lines.append(f"\n![Slide {page_number}]({image_url})\n")
    summary_lines.append("\n**Slide Content**:\n")
    summary_lines.append(page_text)

    summary_markdown = "\n".join(summary_lines)

    return {
        "status": "success",
        "course": course_code,
        "document_name": matched_file.name,
        "document_path": str(matched_file.resolve()),
        "page_number": page_number,
        "total_pages": total_pages,
        "text": page_text,
        "image_path": image_path,
        "image_url": image_url,
        "image_base64": image_b64,
        "high_res": high_res,
        "summary_markdown": summary_markdown
    }



import threading
import itertools
import time

ANSI_REGEX = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\r')

def clean_output_text(text: str) -> str:
    """Strips ANSI escape codes, carriage returns, and terminal redraw sequences."""
    if not text:
        return ""
    return ANSI_REGEX.sub("", text)


class CLISpinner:
    def __init__(self, message="Working..."):
        self.message = message
        self.spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        self.stop_event = threading.Event()
        self.is_json = "--json" in sys.argv
        # Dual-Mode Output Gating:
        # Spinners and cursor redraws are ONLY enabled for interactive human terminals (TTY).
        # Completely disabled when:
        # - Running in MCP mode (MCP_MODE=1)
        # - Output is non-TTY / piped / captured
        # - JSON output requested (--json)
        # - Quiet mode / no-spinner flags passed (--no-spinner, --quiet, -q)
        # - NO_COLOR environment variable is set
        self.disabled = (
            self.is_json
            or not sys.stdout.isatty()
            or os.environ.get("MCP_MODE") == "1"
            or os.environ.get("NO_COLOR") == "1"
            or "--no-spinner" in sys.argv
            or "--quiet" in sys.argv
            or "-q" in sys.argv
        )
        self.thread = threading.Thread(target=self.spin, daemon=True) if not self.disabled else None

    def spin(self):
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r\033[96m{next(self.spinner)}\033[0m {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
        # Clear line on exit
        sys.stdout.write('\r' + ' ' * (len(self.message) + 4) + '\r')
        sys.stdout.flush()

    def __enter__(self):
        if not self.disabled and self.thread:
            self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.disabled and self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=1.0)


def check_dependencies() -> bool:
    """Verifies that all critical runtime dependencies are installed."""
    critical_modules = [
        ("pymupdf", "PyMuPDF"),
        ("onnxruntime", "onnxruntime"),
        ("rank_bm25", "rank_bm25"),
        ("flashrank", "flashrank"),
        ("tokenizers", "tokenizers")
    ]
    missing = []
    for mod_name, pkg_name in critical_modules:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)
    if missing:
        print(f"[Dependency Warning] Missing required packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt (or bash setup.sh)")
        return False
    return True


# CLI Handler for direct terminal invocation
def main():
    check_dependencies()
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Missing command. Usage: python moodle.py </setup | /sync | /list | /ask | /quiz | /slide | ...> [args...]"
        }, indent=2))
        sys.exit(0)

    # Normalize command: strip leading slashes and common prefixes
    raw_cmd = sys.argv[1].lower().lstrip("/")
    cmd = re.sub(r"^(moodle-ai-|moodle-)", "", raw_cmd)
    args = sys.argv[2:]
    flags = {a for a in args if a.startswith("-")}
    pos_args = [a for a in args if not a.startswith("-")]

    if cmd in ("ai", "moodle-ai", "help", ""):
        if pos_args:
            sys.argv = [sys.argv[0]] + args
            return main()
        print(json.dumps({
            "status": "success",
            "name": "moodle-ai",
            "version": "1.1.0",
            "description": "Academic Study Assistant & Moodle Streaming RAG Engine",
            "user_files_folder": "user_files/ (drop custom PDFs, slides, and notes here)",
            "available_commands": [
                "/setup", "/sync [sem] [--course C] [--quick]", "/slide <course> <doc> <page> [--raw]",
                "/list", "/ask <query>", "/quiz [course]", "/change-sync [sem]",
                "/add-custom-url <URL> [label]", "/remove-custom-url <URL>", "/list-custom-urls",
                "/update-version", "/install"
            ]
        }, indent=2))
        return

    if cmd == "setup":
        user = pos_args[0] if len(pos_args) > 0 else None
        pwd = pos_args[1] if len(pos_args) > 1 else None
        baseurls = pos_args[2] if len(pos_args) > 2 else None
        out_dir = pos_args[3] if len(pos_args) > 3 else "output"
        with CLISpinner("Setting up Moodle..."):
            res = setup_moodle(user, pwd, baseurls=baseurls, output_dir=out_dir)
        print(json.dumps(res, indent=2))

    elif cmd in ("change-sync", "tracked-semester"):
        sem = pos_args[0] if pos_args else None
        print(json.dumps(moodle_change_sync(target_semester=sem), indent=2))

    elif cmd == "sync":
        sem = None
        course_flt = None
        for i, a in enumerate(args):
            if a in ("--course", "-c") and i + 1 < len(args):
                course_flt = args[i + 1]
            elif not a.startswith("-") and sem is None and (i == 0 or args[i - 1] not in ("--course", "-c")):
                sem = a
        with CLISpinner("Syncing course materials..."):
            res = sync_moodle(semester=sem, course_filter=course_flt, quick_check=("--quick" in flags or "-q" in flags))
        print(json.dumps(res, indent=2))

    elif cmd in ("add-custom-url", "add-url"):
        if not pos_args:
            print(json.dumps({"status": "error", "message": "Usage: /add-custom-url <URL> [label]"}, indent=2))
            return
        res = moodle_add_custom_url(pos_args[0], label=pos_args[1] if len(pos_args) > 1 else None, auto_sync="--no-sync" not in flags)
        print(json.dumps(res, indent=2))

    elif cmd in ("remove-custom-url", "remove-url"):
        if not pos_args:
            print(json.dumps({"status": "error", "message": "Usage: /remove-custom-url <URL or label>"}, indent=2))
            return
        res = moodle_remove_custom_url(pos_args[0], delete_files=("--delete-files" in flags or "-d" in flags))
        print(json.dumps(res, indent=2))

    elif cmd in ("list-custom-urls", "custom-urls"):
        print(json.dumps(moodle_list_custom_urls(), indent=2))

    elif cmd == "list":
        with CLISpinner("Scanning document hierarchy..."):
            res = moodle_list(regenerate=("--regen" in flags or "--force" in flags))
        print(json.dumps(res, indent=2) if "--json" in flags else res["markdown_content"])

    elif cmd == "ask":
        if not pos_args:
            print(json.dumps({"status": "error", "message": "Usage: /ask \"<query>\" [--no-cache]"}, indent=2))
            return
        q = " ".join(pos_args)
        no_cache = "--no-cache" in flags
        with CLISpinner("Searching knowledge base..."):
            res = moodle_ask(q, use_cache=not no_cache)
        if "--json" in flags:
            print(json.dumps(res, indent=2))
        else:
            print(f"\n--- Results for: '{res['query']}' ---")
            m_ctx = res.get("moodle_context", [])
            v_slides = res.get("visual_fallback", {}).get("rendered_pages", [])
            f_ctx = res.get("fallback_context", [])
            if not m_ctx and not v_slides and not f_ctx:
                print("No matching course materials found for this query.")
            for item in m_ctx:
                print(f"\n{item['citation']}:\n{item['text'][:350]}...")
            for vp in v_slides:
                print(f"\n📸 Slide p.{vp['page']} from {vp['filename']}: {vp['image_path']}")
            for item in f_ctx:
                print(f"\n{item['citation']}:\n{item['summary'][:350]}...")

    elif cmd == "quiz":
        course = pos_args[0] if pos_args else None
        with CLISpinner("Generating practice quiz..."):
            res = moodle_quiz(course)
        print(json.dumps(res, indent=2))

    elif cmd in ("slide", "get-slide"):
        if len(pos_args) < 3:
            print(json.dumps({"status": "error", "message": "Usage: /slide <course_code> <document_name> <page_number> [--raw] [--no-image]"}, indent=2))
            return
        try:
            p_num = int(pos_args[2])
        except ValueError:
            print(json.dumps({"status": "error", "message": f"Invalid page number '{pos_args[2]}'."}, indent=2))
            return
        is_raw = any(f in flags for f in ("--raw", "--300dpi", "--high-res"))
        with CLISpinner(f"Extracting slide {p_num} from {pos_args[1]}..."):
            res = get_course_slide(course_code=pos_args[0], document_name=pos_args[1], page_number=p_num, render_image="--no-image" not in flags, high_res=is_raw)
        print(json.dumps(res, indent=2) if "--json" in flags else res.get("summary_markdown", res.get("text", "")))

    elif cmd in ("update-version", "update"):
        with CLISpinner("Updating moodle-ai version..."):
            res = update_moodle_ai()
        print(json.dumps(res, indent=2))

    elif cmd in ("install", "configure", "setup-all"):
        setup_script = Path(__file__).resolve().parent.parent / "setup.sh"
        if setup_script.exists():
            subprocess.run(["bash", str(setup_script)], check=False)
        else:
            print(json.dumps({"status": "info", "message": "Run 'bash setup.sh' or 'npm run setup' to configure moodle-ai."}, indent=2))

    else:
        print(json.dumps({
            "status": "error",
            "message": f"Unknown command '{raw_cmd}'. Usage: python moodle.py </setup | /sync | /list | /ask | /quiz | /slide | /change-sync | /add-custom-url | /remove-custom-url | /list-custom-urls | /update-version>"
        }, indent=2))


if __name__ == "__main__":
    main()
