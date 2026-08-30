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
from src.parser import DocumentParser
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
    on_file_saved_callback=None,
    max_workers: int = 4
) -> Dict[str, Any]:
    """
    Syncs all registered custom URLs from data/custom_urls.json.
    """
    config = get_config()
    output_dir = Path(config["output_dir"])
    parsed_dir = config["parsed_dir"]
    chroma_dir = config["chroma_dir"]
    workspace_dir = config["workspace_dir"]

    url_mgr = CustomUrlManager(workspace_dir)
    sources = url_mgr.get_sources()

    if not sources:
        return {
            "status": "empty",
            "message": "No custom URLs registered. Add one using `/moodle-add-custom-url <URL> [label]`.",
            "sources_count": 0,
            "files_downloaded": 0
        }

    print(f"\n[Custom URL Sync] 🌐 Syncing {len(sources)} registered custom URL source(s)...")

    results = []
    total_downloaded = 0
    for s in sources:
        print(f"  [Scraping] {s['label']} -> {s['url']}")
        res = scrape_custom_source(s, output_dir, on_file_saved=on_file_saved_callback)
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

def sync_moodle_courses(semester_filter: Optional[str] = None, course_index: Optional[str] = None, max_workers: int = 4, sync_custom: bool = True) -> Dict[str, Any]:
    """
    Truly asynchronous streaming sync pipeline:
    1. Discovers courses. If semester_filter is missing, asks or returns available semesters.
    2. Downloads files.
    3. Scrapes registered custom URLs.
    4. IMMEDIATELY as each file finishes downloading, it is converted to Markdown, embedded in ChromaDB+BM25, and added to list.md on the fly!
    """
    config = get_config()
    output_dir = Path(config["output_dir"])
    parsed_dir = config["parsed_dir"]
    chroma_dir = config["chroma_dir"]
    workspace_dir = config["workspace_dir"]

    # Shared thread-safe instances
    parser = DocumentParser(str(output_dir), parsed_dir)
    indexer = KnowledgeIndexer(chroma_dir)
    list_mgr = ListManager(workspace_dir, str(output_dir), parsed_dir)

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

        ext = p.suffix.lower()
        if ext in (".pdf", ".txt", ".md", ".html", ".htm"):
            try:
                # 1. Immediately Parse to Markdown
                chunks = parser.parse_file(p, force=is_new)
                if chunks:
                    # 2. Immediately Embed into ChromaDB & BM25
                    with lock:
                        count = indexer.index_parsed_chunks(chunks)
                        indexed_chunks_total += count
                    print(f"  [Async RAG] ⚡ Converted & Indexed: {p.name} ({len(chunks)} pages, {count} chunks)")
            except Exception as ex:
                print(f"  [Async RAG Error] {p.name}: {ex}")

    def on_file_saved_callback(saved_path: str, is_new: bool = True):
        # Dispatch immediately to background worker
        future = executor.submit(async_process_file, saved_path, is_new)
        futures.append(future)

    # Check if only custom sync was requested
    if semester_filter and semester_filter.lower() == "custom":
        custom_res = sync_custom_sources(on_file_saved_callback=on_file_saved_callback, max_workers=max_workers)
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

            print(f"\n[Sync] 🚀 Starting streaming sync for {len(target_courses)} course(s) (Semester: {semester_filter})...")
            for course_item in target_courses:
                sem_label = f"Semester_{course_item['sem']}" if course_item.get("sem") else "General"
                downloadCourse(course_item, sem_label, on_file_saved=on_file_saved_callback)
            moodle_courses_synced = len(target_courses)
    else:
        print(f"[Sync Notice] Moodle credentials not configured or failed ({err}). Proceeding with custom sources if any.")

    # Also sync registered custom URLs
    custom_sources_count = 0
    if sync_custom:
        custom_res = sync_custom_sources(on_file_saved_callback=on_file_saved_callback, max_workers=max_workers)
        custom_sources_count = custom_res.get("sources_synced", 0)

    # Wait for all background parsing & embedding tasks to complete
    print("\n[Sync] Waiting for streaming indexing pipeline to finish remaining files...")
    concurrent.futures.wait(futures)
    executor.shutdown(wait=True)

    # Update list.md with final file structure
    print("[Sync] 📝 Updating list.md file structure...")
    list_mgr.update_list_file()

    return {
        "status": "success",
        "semester": semester_filter,
        "courses_synced": moodle_courses_synced,
        "custom_sources_synced": custom_sources_count,
        "files_processed": len(processed_files),
        "total_chunks_indexed": indexed_chunks_total,
        "list_file": str(list_mgr.list_file_path),
        "message": f"Successfully synced {moodle_courses_synced} Moodle course(s) and {custom_sources_count} custom source(s). Converted and indexed {len(processed_files)} documents in real-time."
    }
