import os
import sys
import concurrent.futures
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import scraper internals
from scraper import (
    login,
    getAllCoursesAndSemesters,
    downloadCourse,
    colors
)
from src.config import get_config
from src.parser import DocumentParser, compute_file_hash
from src.indexer import KnowledgeIndexer
from src.list_manager import ListManager
from src.custom_scraper import CustomUrlManager, scrape_custom_source

def get_moodle_sessions():
    config = get_config()
    user = config["user"]
    password = config["password"]
    baseurls = config["baseurls"]

    if not user or not password or user == "your_kerberos_id_here":
        return None, "Missing Kerberos credentials in .env. Please run /setup first."

    sessions_by_url = {}
    for b_url in baseurls:
        ses = login(b_url, user, password)
        if ses:
            sessions_by_url[b_url] = ses

    if not sessions_by_url:
        return None, "Could not authenticate with any Moodle instance. Please check your credentials in .env."

    return sessions_by_url, None

def discover_available_semesters() -> Dict[str, Any]:
    """
    Connects to Moodle and discovers all enrolled semesters and courses without downloading.
    """
    sessions_by_url, err = get_moodle_sessions()
    if err:
        return {"status": "error", "message": err}

    all_courses, sems = getAllCoursesAndSemesters(sessions_by_url)
    if not all_courses:
        return {"status": "error", "message": "No courses found."}

    sem_info = {}
    for s_key, s_label in sems.items():
        if s_key == "all":
            course_count = len(all_courses)
        else:
            course_count = len([c for c in all_courses if c["sem"] == s_key])
        sem_info[s_key] = {
            "label": s_label,
            "course_count": course_count
        }

    return {
        "status": "success",
        "total_courses": len(all_courses),
        "semesters": sem_info
    }

def sync_custom_sources(
    known_catalog: Optional[Dict[str, Any]] = None,
    on_file_saved_callback=None,
    max_workers: int = 4
) -> Dict[str, Any]:
    """
    Syncs all registered custom URLs from data/custom_urls.json using list.md catalog upfront.
    """
    config = get_config()
    output_dir = Path(config["output_dir"])
    parsed_dir = config["parsed_dir"]
    chroma_dir = config["chroma_dir"]
    workspace_dir = config["workspace_dir"]

    from src.custom_scraper import CustomUrlManager
    
    url_mgr = CustomUrlManager(workspace_dir)
    sources = url_mgr.get_sources()

    if not sources:
        return {
            "status": "empty",
            "message": "No custom URLs registered. Add one using `/moodle-add-custom-url <URL> [label]`.",
            "sources_count": 0,
            "files_downloaded": 0
        }

    print(f"\n[Custom URL Sync] [START] Syncing {len(sources)} registered custom URL source(s)...")

    results = []
    total_downloaded = 0
    for s in sources:
        print(f"  [Scraping] {s['label']} -> {s['url']}")
        res = scrape_custom_source(s, output_dir, known_catalog=known_catalog, on_file_saved=on_file_saved_callback)
        count = res.get("downloaded_files_count", 0)
        total_downloaded += count
        url_mgr.update_sync_stats(s["url"], count)
        results.append(res)

    return {
        "status": "success",
        "sources_synced": len(sources),
        "files_downloaded": total_downloaded,
        "details": results
    }

def sync_user_files(
    known_catalog: Optional[Dict[str, Any]] = None,
    on_file_saved_callback=None
) -> Dict[str, Any]:
    """
    Scans the local user_files/ folder for personal PDFs, slides, and study notes.
    Calls on_file_saved_callback(str(f_path.resolve()), is_new) for each file found.
    """
    config = get_config()
    user_files_dir = Path(config["user_files_dir"])
    
    if not user_files_dir.exists():
        user_files_dir.mkdir(parents=True, exist_ok=True)
        return {"status": "empty", "files_found": 0, "message": "user_files/ folder is empty."}

    supported_exts = {".pdf", ".pptx", ".ppt", ".docx", ".zip", ".txt", ".md", ".html", ".htm"}
    files_to_sync = []

    for root, _, files in os.walk(user_files_dir):
        if ".dump" in root:
            continue
        for f in sorted(files):
            if f.startswith(".") or f.lower() in ("readme.md", ".gitkeep"):
                continue
            ext = Path(f).suffix.lower()
            if ext in supported_exts:
                f_path = Path(root) / f
                files_to_sync.append(f_path)

    if not files_to_sync:
        return {
            "status": "empty",
            "files_found": 0,
            "message": "No documents found in user_files/."
        }

    print(f"\n[User Files Sync] [START] Discovered {len(files_to_sync)} personal document(s) in user_files/...")

    dispatched = 0
    for f_path in files_to_sync:
        abs_str = str(f_path.resolve())
        is_new = True
        if known_catalog and abs_str in known_catalog.get("paths", set()):
            is_new = False
        if on_file_saved_callback:
            on_file_saved_callback(abs_str, is_new=is_new)
            dispatched += 1

    return {
        "status": "success",
        "files_found": len(files_to_sync),
        "files_dispatched": dispatched
    }

def sync_moodle_courses(semester_filter: Optional[str] = None, course_index: Optional[str] = None, max_workers: int = 4, sync_custom: bool = True) -> Dict[str, Any]:
    """
    Truly asynchronous streaming sync pipeline:
    1. Inspects list.md upfront to get an in-memory catalog of all existing files.
    2. Discovers courses and downloads only genuinely new files.
    3. Scrapes registered custom URLs.
    4. Scans local user_files/ for personal study materials.
    5. IMMEDIATELY as each new file finishes downloading or is discovered, it is converted to Markdown, embedded in ChromaDB+BM25, and added to list.md on the fly!
    """
    config = get_config()
    output_dir = Path(config["output_dir"])
    user_files_dir = Path(config["user_files_dir"])
    parsed_dir = config["parsed_dir"]
    chroma_dir = config["chroma_dir"]
    workspace_dir = config["workspace_dir"]

    # Shared thread-safe instances
    parser = DocumentParser(str(output_dir), parsed_dir, user_files_dir=str(user_files_dir))
    indexer = KnowledgeIndexer(chroma_dir)
    list_mgr = ListManager(workspace_dir, str(output_dir), parsed_dir, user_files_dir=str(user_files_dir))

    # 1. Inspect list.md upfront
    known_catalog = list_mgr.get_known_files_from_list()
    if known_catalog["total_files"] > 0:
        print(f"[Sync] [INFO] Inspected list.md: Found {known_catalog['total_files']} files already indexed across courses.")

    lock = threading.Lock()
    processed_files = set()
    indexed_chunks_total = 0
    futures = []

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def async_process_file(file_path_str: str, is_new: bool):
        nonlocal indexed_chunks_total
        p = Path(file_path_str)
        if not p.exists() or p.is_dir() or p.name.startswith("."):
            return

        with lock:
            if file_path_str in processed_files:
                return
            processed_files.add(file_path_str)

        # Quick check: if not new and already cataloged in list.md, bypass parsing/indexing
        if not is_new and str(p.resolve()) in known_catalog.get("paths", set()):
            return

        ext = p.suffix.lower()
        if ext in (".pdf", ".txt", ".md", ".html", ".htm", ".pptx", ".ppt", ".docx", ".zip"):
            try:
                try:
                    rel_path = p.relative_to(output_dir)
                except ValueError:
                    try:
                        rel_path = Path("User_Files") / p.relative_to(user_files_dir)
                    except ValueError:
                        rel_path = Path(p.name)

                md_dest = Path(parsed_dir) / rel_path.with_suffix('.md')
                cached_hash = parser.hashes.get(str(rel_path))
                curr_hash = compute_file_hash(p)

                # Skip re-parsing and re-indexing if file is already up to date
                if not is_new and cached_hash == curr_hash and md_dest.exists():
                    return

                # 1. Immediately Parse to Markdown
                chunks = parser.parse_file(p, force=True)
                if chunks:
                    # 2. Immediately Embed into ChromaDB & BM25
                    with lock:
                        count = indexer.index_parsed_chunks(chunks)
                        indexed_chunks_total += count
                    print(f"  [Async RAG] [DONE] Converted & Indexed: {p.name} ({len(chunks)} pages, {count} chunks)")
            except Exception as ex:
                print(f"  [Async RAG Error] {p.name}: {ex}")

    def on_file_saved_callback(saved_path: str, is_new: bool = True):
        # Dispatch immediately to background worker
        future = executor.submit(async_process_file, saved_path, is_new)
        futures.append(future)

    # Check if only user files sync was requested
    if semester_filter and semester_filter.lower() in ("user", "user_files", "local"):
        user_res = sync_user_files(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback)
        print("\n[Sync] Waiting for streaming indexing pipeline to finish user files...")
        concurrent.futures.wait(futures)
        executor.shutdown(wait=True)
        list_mgr.update_list_file()
        return {
            "status": "success",
            "type": "user_files_only",
            "files_found": user_res.get("files_found", 0),
            "files_processed": len(processed_files),
            "total_chunks_indexed": indexed_chunks_total,
            "list_file": str(list_mgr.list_file_path),
            "message": f"Successfully synced user_files/ ({user_res.get('files_found', 0)} files found, {len(processed_files)} processed, {indexed_chunks_total} chunks indexed)."
        }

    # Check if only custom sync was requested
    if semester_filter and semester_filter.lower() == "custom":
        custom_res = sync_custom_sources(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback, max_workers=max_workers)
        print("\n[Sync] Waiting for streaming indexing pipeline to finish remaining files...")
        concurrent.futures.wait(futures)
        executor.shutdown(wait=True)
        list_mgr.update_list_file()
        return {
            "status": "success",
            "type": "custom_only",
            "sources_synced": custom_res.get("sources_synced", 0),
            "files_processed": len(processed_files),
            "total_chunks_indexed": indexed_chunks_total,
            "list_file": str(list_mgr.list_file_path),
            "message": f"Successfully synced custom URLs ({custom_res.get('sources_synced', 0)} sources, {len(processed_files)} files indexed)."
        }

    sessions_by_url, err = get_moodle_sessions()
    moodle_courses_synced = 0

    if not err:
        print("[Sync] Discovering courses and semesters across Moodle...")
        all_courses, sems = getAllCoursesAndSemesters(sessions_by_url)
        if all_courses:
            valid_sems = [k for k in sems.keys() if k != "all"]
            if not semester_filter:
                if sys.stdin.isatty():
                    print(colors.WARNING + "\nAvailable semesters:" + colors.ENDC)
                    for s_key in sorted(sems.keys()):
                        print(f"  [{s_key}]: {sems[s_key]}")
                    chosen = input(colors.WARNING + '\nSelect semester (or "all"): ' + colors.ENDC).strip()
                    semester_filter = chosen if chosen in sems else "all"
                else:
                    return {
                        "status": "needs_semester_selection",
                        "message": "Please specify which semester/year you would like to sync.",
                        "available_semesters": {k: sems[k] for k in sorted(sems.keys())},
                        "instruction": "Run `/sync <SEMESTER_CODE>` (e.g. `/sync 2601` or `/sync all`)"
                    }

            if semester_filter == "all":
                target_courses = all_courses
            elif semester_filter in sems:
                target_courses = [c for c in all_courses if c["sem"] == semester_filter]
            else:
                matched = [c for c in all_courses if semester_filter in str(c.get("sem", ""))]
                target_courses = matched if matched else all_courses

            if course_index is not None:
                try:
                    idx = int(course_index)
                    if 0 <= idx < len(target_courses):
                        target_courses = [target_courses[idx]]
                except ValueError:
                    pass

            print(f"\n[Sync] [START] Starting streaming sync for {len(target_courses)} course(s) (Semester: {semester_filter})...")
            for course_item in target_courses:
                sem_label = f"Semester_{course_item['sem']}" if course_item.get("sem") else "General"
                downloadCourse(course_item, sem_label, known_catalog=known_catalog, on_file_saved=on_file_saved_callback)
            moodle_courses_synced = len(target_courses)
    else:
        print(f"[Sync Notice] Moodle credentials not configured or failed ({err}). Proceeding with custom sources if any.")

    # Also sync registered custom URLs
    custom_sources_count = 0
    if sync_custom:
        custom_res = sync_custom_sources(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback, max_workers=max_workers)
        custom_sources_count = custom_res.get("sources_synced", 0)

    # Also sync personal user_files/
    user_res = sync_user_files(known_catalog=known_catalog, on_file_saved_callback=on_file_saved_callback)
    user_files_count = user_res.get("files_found", 0)

    # Wait for all background parsing & embedding tasks to complete
    print("\n[Sync] Waiting for streaming indexing pipeline to finish remaining files...")
    concurrent.futures.wait(futures)
    executor.shutdown(wait=True)

    # Update list.md with final file structure
    print("[Sync] [INFO] Updating list.md file structure...")
    list_mgr.update_list_file()

    return {
        "status": "success",
        "semester": semester_filter,
        "courses_synced": moodle_courses_synced,
        "custom_sources_synced": custom_sources_count,
        "user_files_found": user_files_count,
        "files_processed": len(processed_files),
        "total_chunks_indexed": indexed_chunks_total,
        "list_file": str(list_mgr.list_file_path),
        "message": f"Successfully synced {moodle_courses_synced} Moodle course(s), {custom_sources_count} custom source(s), and {user_files_count} user file(s). Converted and indexed {len(processed_files)} documents in real-time."
    }
