import os
import sys
import json
import urllib.parse
import subprocess
import plistlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.config import get_config, save_env_config, init_env_template
from src.scraper_sync import sync_moodle_courses, discover_available_semesters
from src.indexer import KnowledgeIndexer
from src.list_manager import ListManager
from src.web_search import search_wikipedia
from src.custom_scraper import CustomUrlManager

def ensure_preview_app_installed() -> bool:
    """
    Ensures that the native macOS OpenInPreview.app URL handler is installed
    in ~/Applications/OpenInPreview.app and registered with LaunchServices to handle
    'open-preview://' and 'preview-pdf://' schemes.
    """
    try:
        app_path = os.path.expanduser("~/Applications/OpenInPreview.app")
        plist_path = os.path.join(app_path, "Contents/Info.plist")
        
        if os.path.exists(plist_path):
            return True
            
        os.makedirs(os.path.expanduser("~/Applications"), exist_ok=True)
        shutil.rmtree(app_path, ignore_errors=True)
        
        tools_script = os.path.abspath(__file__)
        python_bin = sys.executable
        
        applescript_src = f"""
on open location this_URL
    do shell script "{python_bin} {tools_script} /open-url " & quoted form of this_URL
end open location
"""
        temp_applescript = "/tmp/open_preview.applescript"
        with open(temp_applescript, "w", encoding="utf-8") as f:
            f.write(applescript_src)

        subprocess.run(["osacompile", "-o", app_path, temp_applescript], check=True, capture_output=True)

        with open(plist_path, "rb") as f:
            plist_data = plistlib.load(f)

        plist_data["CFBundleURLTypes"] = [
            {
                "CFBundleURLName": "Open In Preview URL Handler",
                "CFBundleURLSchemes": ["open-preview", "preview-pdf"]
            }
        ]
        plist_data["LSBackgroundOnly"] = True

        with open(plist_path, "wb") as f:
            plistlib.dump(plist_data, f)

        subprocess.run(["/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister", "-f", app_path], check=True, capture_output=True)
        return True
    except Exception:
        return False

def moodle_open_pdf(path_or_url_or_query: str, page: int = 1) -> Dict[str, Any]:
    """
    [Tool: /open] Resolves a PDF file path or search query and launches it directly in macOS Preview.
    """
    config = get_config()
    output_dir = Path(config["output_dir"])
    
    raw = path_or_url_or_query.strip()
    # Strip URL schemes if present
    for scheme in ("open-preview://", "preview-pdf://", "file://"):
        if raw.startswith(scheme):
            raw = raw[len(scheme):]
            break

    raw = urllib.parse.unquote(raw)

    if "#page=" in raw:
        parts = raw.split("#page=")
        raw = parts[0]
        try:
            page = int(parts[1])
        except Exception:
            pass
    elif "?page=" in raw:
        parts = raw.split("?page=")
        raw = parts[0]
        try:
            page = int(parts[1])
        except Exception:
            pass

    if raw.startswith("localhost/"):
        raw = "/" + raw[len("localhost/"):]
    if not raw.startswith("/") and os.path.exists("/" + raw):
        raw = "/" + raw

    target_path = Path(raw)
    if not target_path.exists():
        query_term = target_path.name.lower()
        q_clean = query_term.replace(".pdf", "")
        # Search recursively in output_dir
        for root, _, files in os.walk(output_dir):
            for f in files:
                if f.lower().endswith(".pdf") and (q_clean in f.lower() or all(part in f.lower() for part in q_clean.split())):
                    target_path = Path(root) / f
                    break
            if target_path.exists():
                break

    if target_path.exists() and target_path.is_file():
        # Open in macOS Preview
        subprocess.run(["open", "-a", "Preview", str(target_path.resolve())])
        return {
            "status": "success",
            "message": f"Opened '{target_path.name}' in macOS Preview.",
            "file": str(target_path.resolve()),
            "page": page
        }
    else:
        return {
            "status": "error",
            "message": f"Could not find PDF matching '{path_or_url_or_query}' in {output_dir}"
        }

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

    list_mgr = ListManager(updated_cfg["workspace_dir"], updated_cfg["output_dir"], updated_cfg["parsed_dir"])
    list_mgr.update_list_file()

    return {
        "status": "success",
        "tracked_semester": updated_cfg["tracked_semester"],
        "output_dir": updated_cfg["output_dir"],
        "list_file": str(list_mgr.list_file_path),
        "message": f"Successfully updated tracked sync semester to '{updated_cfg['tracked_semester']}' in .env."
    }

def sync_moodle(semester: Optional[str] = None, course_index: Optional[str] = None) -> Dict[str, Any]:
    """
    [Tool: /sync] Asynchronously scrapes Moodle and registered custom URLs, converts PDFs to Markdown immediately as they download, and updates ChromaDB & BM25 indexes.
    """
    cfg = get_config()
    target_sem = semester if semester else cfg.get("tracked_semester", "2601")
    return sync_moodle_courses(semester_filter=target_sem, course_index=course_index)

def moodle_add_custom_url(url: str, label: Optional[str] = None, auto_sync: bool = True) -> Dict[str, Any]:
    """
    [Tool: /moodle-add-custom-url] Registers a custom URL to scrape PDFs from and optionally triggers immediate sync & indexing.
    """
    cfg = get_config()
    url_mgr = CustomUrlManager(cfg["workspace_dir"])
    add_res = url_mgr.add_source(url, label)
    
    if add_res.get("status") in ("added", "already_exists") and auto_sync:
        print(f"\n[Custom URL] ⚡ Auto-syncing custom source: {url}...")
        sync_res = sync_moodle_courses(semester_filter="custom")
        add_res["sync_results"] = sync_res

    return add_res

def moodle_remove_custom_url(url_or_label: str, delete_files: bool = False) -> Dict[str, Any]:
    """
    [Tool: /moodle-remove-custom-url] Removes a registered custom URL. Optionally cleans up downloaded files.
    """
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
        list_mgr = ListManager(cfg["workspace_dir"], cfg["output_dir"], cfg["parsed_dir"])
        list_mgr.update_list_file()
        rem_res["list_file"] = str(list_mgr.list_file_path)

    return rem_res

def moodle_list_custom_urls() -> Dict[str, Any]:
    """
    [Tool: /moodle-list-custom-urls] Lists all registered custom URLs and their sync statuses.
    """
    cfg = get_config()
    url_mgr = CustomUrlManager(cfg["workspace_dir"])
    sources = url_mgr.get_sources()
    return {
        "status": "success",
        "total_sources": len(sources),
        "sources": sources
    }

def moodle_list(regenerate: bool = False) -> Dict[str, Any]:
    """
    [Tool: /list] Reads list.md and returns the structured document hierarchy of all courses and materials.
    """
    config = get_config()
    list_mgr = ListManager(config["workspace_dir"], config["output_dir"], config["parsed_dir"])
    
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

def moodle_ask(query: str, doc_filter: Optional[str] = None, course_filter: Optional[str] = None, top_k: int = 4, fallback_to_web: bool = True) -> Dict[str, Any]:
    """
    [Tool: /ask] Hybrid search across Moodle course materials with Wikipedia fallback.
    Returns the most relevant chunks with exact file & page citations.
    """
    config = get_config()
    indexer = KnowledgeIndexer(config["chroma_dir"])
    
    # 1. Perform Hybrid Search
    results = indexer.hybrid_search(
        query=query,
        course_filter=course_filter,
        filename_filter=doc_filter,
        top_k=top_k
    )

    parsed_dir = Path(config["parsed_dir"])
    output_dir = Path(config["output_dir"])

    # Ensure Preview URL handler app is registered
    ensure_preview_app_installed()

    # Format retrieved Moodle context
    retrieved_chunks = []
    has_confident_match = False
    for r in results:
        meta = r["metadata"]
        score = r.get("rrf_score", 0.0)
        is_conf = r.get("is_confident", False)
        if is_conf:
            has_confident_match = True

        src_path = Path(meta.get("source", ""))
        pdf_url = None
        preview_url = None
        page_num = meta.get("page", 1)
        if src_path.exists():
            quoted_path = urllib.parse.quote(str(src_path.resolve()), safe="/:")
            pdf_url = f"file://{src_path.resolve()}"
            preview_url = f"open-preview://{quoted_path}#page={page_num}"

        citation_label = f"{meta.get('course')} / {meta.get('filename')} (Page {page_num})"
        if pdf_url and preview_url:
            citation = f"[{citation_label}]({pdf_url}) ([Open in Preview]({preview_url}))"
        elif pdf_url:
            citation = f"[{citation_label}]({pdf_url}#page={page_num})"
        else:
            citation = f"[{citation_label}]"

        retrieved_chunks.append({
            "source_type": "moodle_course_material",
            "course": meta.get("course", "Unknown"),
            "filename": meta.get("filename", "Unknown"),
            "page": page_num,
            "score": score,
            "is_confident": is_conf,
            "cosine_similarity": r.get("cosine_similarity", 0.0),
            "bm25_score": r.get("bm25_score", 0.0),
            "text": r["text"],
            "pdf_path": str(src_path.resolve()) if src_path.exists() else None,
            "pdf_url": pdf_url,
            "preview_url": preview_url,
            "citation": citation
        })

    # 2. Check if Fallback is needed
    # If no confident matches were found in course materials, query Wikipedia
    fallback_results = []
    if (not has_confident_match) and fallback_to_web:
        wiki_hits = search_wikipedia(query, max_results=2)
        for w in wiki_hits:
            fallback_results.append({
                "source_type": "wikipedia_fallback",
                "title": w["title"],
                "url": w["url"],
                "summary": w["summary"],
                "citation": f"[Wikipedia: {w['title']}]({w['url']})"
            })

    return {
        "status": "success",
        "query": query,
        "total_moodle_hits": len(retrieved_chunks),
        "has_confident_moodle_hit": has_confident_match,
        "moodle_context": retrieved_chunks if has_confident_match else retrieved_chunks[:2],
        "fallback_context": fallback_results,
        "used_fallback": len(fallback_results) > 0
    }

def moodle_quiz(course: Optional[str] = None, num_questions: int = 5) -> Dict[str, Any]:
    """
    [Tool: /quiz] Retrieves representative course material chunks to generate practice quizzes.
    """
    config = get_config()
    indexer = KnowledgeIndexer(config["chroma_dir"])
    parsed_dir = Path(config["parsed_dir"])
    output_dir = Path(config["output_dir"])
    
    # Ensure Preview URL handler app is registered
    ensure_preview_app_installed()

    # Query broad foundational concepts for the course
    query = "introduction definitions key principles formulas summary concepts"
    results = indexer.hybrid_search(query=query, course_filter=course, top_k=num_questions * 2)
    
    sampled_materials = []
    for r in results[:num_questions]:
        meta = r["metadata"]
        src_path = Path(meta.get("source", ""))
        pdf_url = None
        preview_url = None
        page_num = meta.get("page", 1)
        if src_path.exists():
            quoted_path = urllib.parse.quote(str(src_path.resolve()), safe="/:")
            pdf_url = f"file://{src_path.resolve()}"
            preview_url = f"open-preview://{quoted_path}#page={page_num}"

        citation_label = f"{meta.get('course')} / {meta.get('filename')} (Page {page_num})"
        if pdf_url and preview_url:
            citation = f"[{citation_label}]({pdf_url}) ([Open in Preview]({preview_url}))"
        elif pdf_url:
            citation = f"[{citation_label}]({pdf_url}#page={page_num})"
        else:
            citation = f"[{citation_label}]"

        sampled_materials.append({
            "course": meta.get("course"),
            "filename": meta.get("filename"),
            "page": page_num,
            "text": r["text"],
            "pdf_path": str(src_path.resolve()) if src_path.exists() else None,
            "pdf_url": pdf_url,
            "preview_url": preview_url,
            "citation": citation
        })


    return {
        "status": "success",
        "course": course or "All Enrolled Courses",
        "num_topics": len(sampled_materials),
        "materials": sampled_materials
    }

def render_pdf_to_images(pdf_query: str, target_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    [Tool: /view] Renders pages of a PDF into high-res PNG images for native Antigravity slide viewing.
    """
    import pymupdf
    config = get_config()
    output_dir = Path(config["output_dir"])
    
    # Locate the PDF file
    matched_pdf = None
    if os.path.exists(pdf_query) and pdf_query.endswith(".pdf"):
        matched_pdf = Path(pdf_query)
    else:
        q_lower = pdf_query.lower()
        for root, _, files in os.walk(output_dir):
            for f in files:
                if f.lower().endswith(".pdf") and (q_lower in f.lower() or all(part in f.lower() for part in q_lower.split())):
                    matched_pdf = Path(root) / f
                    break
            if matched_pdf:
                break

    if not matched_pdf or not matched_pdf.exists():
        return {
            "status": "error",
            "message": f"Could not find PDF matching '{pdf_query}' in {output_dir}"
        }

    dest_folder = Path(target_dir) if target_dir else output_dir.parent / "data" / "slides" / matched_pdf.stem
    dest_folder.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(str(matched_pdf))
    rendered_images = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_dest = dest_folder / f"page_{i+1}.png"
        pix.save(str(img_dest))
        rendered_images.append(str(img_dest.resolve()))

    return {
        "status": "success",
        "pdf_name": matched_pdf.name,
        "pdf_path": str(matched_pdf.resolve()),
        "total_pages": len(rendered_images),
        "images": rendered_images
    }

# CLI Handler for direct terminal invocation
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Missing command. Usage: python agent_tools.py </setup | /sync | /list | /ask | /quiz | /open | /change-sync | /add-custom-url | /remove-custom-url | /list-custom-urls> [args...]"
        }, indent=2))
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd in ("/moodle-ai", "moodle-ai"):
        if len(sys.argv) > 2:
            sub = sys.argv[2].lower()
            # Rewrite argv and recurse / dispatch
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            cmd = sys.argv[1].lower()
        else:
            print(json.dumps({
                "status": "success",
                "name": "moodle-ai",
                "version": "1.0.0-alpha",
                "description": "Academic Study Assistant & Moodle Streaming RAG Engine",
                "available_commands": [
                    "/setup",
                    "/sync [semester]",
                    "/add-custom-url <URL> [label]",
                    "/remove-custom-url <URL_OR_LABEL>",
                    "/list-custom-urls",
                    "/list",
                    "/ask <query>",
                    "/quiz [course]",
                    "/open <path_or_query> [page]",
                    "/install"
                ]
            }, indent=2))
            sys.exit(0)

    if cmd in ("/setup", "setup", "/moodle-ai-setup", "moodle-ai-setup", "/moodle-setup", "moodle-setup"):
        user = sys.argv[2] if len(sys.argv) >= 4 else None
        pwd = sys.argv[3] if len(sys.argv) >= 4 else None
        baseurls = sys.argv[4] if len(sys.argv) > 4 else None
        out_dir = sys.argv[5] if len(sys.argv) > 5 else "output"
        res = setup_moodle(user, pwd, baseurls=baseurls, output_dir=out_dir)
        print(json.dumps(res, indent=2))

    elif cmd in ("/change-sync", "change-sync", "/moodle-ai-change-sync", "moodle-ai-change-sync", "/tracked-semester", "tracked-semester"):
        sem_arg = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        res = moodle_change_sync(target_semester=sem_arg)
        print(json.dumps(res, indent=2))

    elif cmd in ("/sync", "sync", "/moodle-ai-sync", "moodle-ai-sync", "/moodle-sync", "moodle-sync"):
        sem = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        res = sync_moodle(semester=sem)
        print(json.dumps(res, indent=2))

    elif cmd in ("/add-custom-url", "add-custom-url", "/moodle-ai-add-custom-url", "moodle-ai-add-custom-url", "/moodle-add-custom-url", "moodle-add-custom-url", "/add-url", "add-url"):
        if len(sys.argv) < 3:
            print(json.dumps({
                "status": "error",
                "message": "Missing URL. Usage: python agent_tools.py /add-custom-url <URL> [label]"
            }, indent=2))
            sys.exit(0)
        url_arg = sys.argv[2]
        label_arg = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
        no_sync = "--no-sync" in sys.argv
        res = moodle_add_custom_url(url_arg, label=label_arg, auto_sync=not no_sync)
        print(json.dumps(res, indent=2))

    elif cmd in ("/remove-custom-url", "remove-custom-url", "/moodle-ai-remove-custom-url", "moodle-ai-remove-custom-url", "/moodle-remove-custom-url", "moodle-remove-custom-url", "/remove-url", "remove-url"):
        if len(sys.argv) < 3:
            print(json.dumps({
                "status": "error",
                "message": "Missing URL or label. Usage: python agent_tools.py /remove-custom-url <URL or label>"
            }, indent=2))
            sys.exit(0)
        target_arg = sys.argv[2]
        del_files = "--delete-files" in sys.argv or "-d" in sys.argv
        res = moodle_remove_custom_url(target_arg, delete_files=del_files)
        print(json.dumps(res, indent=2))

    elif cmd in ("/list-custom-urls", "list-custom-urls", "/moodle-ai-list-custom-urls", "moodle-ai-list-custom-urls", "/moodle-list-custom-urls", "moodle-list-custom-urls", "/custom-urls", "custom-urls"):
        res = moodle_list_custom_urls()
        print(json.dumps(res, indent=2))

    elif cmd in ("/list", "list", "/moodle-ai-list", "moodle-ai-list", "/moodle-list", "moodle-list"):
        regen = "--regen" in sys.argv or "--force" in sys.argv
        res = moodle_list(regenerate=regen)
        if "--json" in sys.argv:
            print(json.dumps(res, indent=2))
        else:
            print(res["markdown_content"])

    elif cmd in ("/ask", "ask", "/moodle-ai-ask", "moodle-ai-ask", "/moodle-ask", "moodle-ask"):
        raw_args = [a for a in sys.argv[2:] if not a.startswith("--")]
        if not raw_args:
            print(json.dumps({
                "status": "error",
                "message": "Missing query. Usage: python agent_tools.py /ask \"<your question>\""
            }, indent=2))
            sys.exit(0)

        q = " ".join(raw_args)
        res = moodle_ask(q)
        if "--json" in sys.argv:
            print(json.dumps(res, indent=2))
        else:
            print(f"\n--- Results for: '{res['query']}' ---")
            if res.get("moodle_context"):
                print("\n🎓 Course Materials & Custom Sources:")
                for item in res["moodle_context"]:
                    print(f"\n{item['citation']}:")
                    print(item['text'][:350] + "...")
            if res.get("used_fallback"):
                print("\n🌐 Wikipedia Fallback:")
                for item in res.get("fallback_context", []):
                    print(f"\n{item['citation']}:")
                    print(item['summary'][:350] + "...")

    elif cmd in ("/quiz", "quiz", "/moodle-ai-quiz", "moodle-ai-quiz", "/moodle-quiz", "moodle-quiz"):
        course_name = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        res = moodle_quiz(course_name)
        print(json.dumps(res, indent=2))

    elif cmd in ("/open", "open", "/preview", "preview"):
        target = " ".join([a for a in sys.argv[2:] if not a.startswith("--")]) if len(sys.argv) > 2 else ""
        if not target:
            print(json.dumps({
                "status": "error",
                "message": "Missing target file or search query. Usage: python agent_tools.py /open \"<filename or topic>\" [page]"
            }, indent=2))
            sys.exit(0)
        page_arg = 1
        for arg in sys.argv[2:]:
            if arg.isdigit():
                page_arg = int(arg)
                break
        res = moodle_open_pdf(target, page=page_arg)
        print(json.dumps(res, indent=2))

    elif cmd in ("/open-url", "open-url"):
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        res = moodle_open_pdf(url)
        print(json.dumps(res, indent=2))

    elif cmd in ("/install", "install", "/configure", "configure"):
        import install
        install.main()

    else:
        print(json.dumps({
            "status": "error",
            "message": f"Unknown command '{cmd}'. Available commands: /moodle-ai, /setup, /sync, /list, /ask, /quiz, /open, /change-sync, /add-custom-url, /remove-custom-url, /list-custom-urls, /install"
        }, indent=2))

