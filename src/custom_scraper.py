import os
import re
import json
import urllib.parse
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
}

class CustomUrlManager:
    """
    Manages custom URLs stored in data/custom_urls.json.
    """
    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.data_dir = self.workspace_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.data_dir / "custom_urls.json"
        self._ensure_file()

    def _ensure_file(self):
        if not self.config_path.exists():
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"sources": []}, f, indent=2)

    def get_sources(self) -> List[Dict[str, Any]]:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("sources", [])
        except Exception:
            return []

    def save_sources(self, sources: List[Dict[str, Any]]) -> bool:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"sources": sources}, f, indent=2)
            return True
        except Exception:
            return False

    def sanitize_label(self, label: str) -> str:
        # Replace non-alphanumeric chars with underscore
        clean = re.sub(r'[^a-zA-Z0-9_\-.]', '_', label.strip())
        return clean.strip("_") or "Custom_Resource"

    def infer_label_from_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.rstrip("/")
        if path:
            last_segment = path.split("/")[-1]
            if last_segment.lower().endswith(".pdf"):
                last_segment = last_segment[:-4]
            clean = self.sanitize_label(last_segment)
            if clean:
                return clean
        clean_netloc = self.sanitize_label(parsed.netloc)
        return clean_netloc or "Custom_Resource"

    def add_source(self, url: str, label: Optional[str] = None) -> Dict[str, Any]:
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        sources = self.get_sources()
        for s in sources:
            if s["url"].lower() == url.lower():
                return {
                    "status": "already_exists",
                    "source": s,
                    "message": f"URL '{url}' is already registered as '{s['label']}'."
                }

        final_label = self.sanitize_label(label) if label else self.infer_label_from_url(url)
        # Ensure unique label
        existing_labels = {s["label"] for s in sources}
        base_label = final_label
        counter = 1
        while final_label in existing_labels:
            final_label = f"{base_label}_{counter}"
            counter += 1

        new_source = {
            "url": url,
            "label": final_label,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_synced": None,
            "files_count": 0
        }
        sources.append(new_source)
        self.save_sources(sources)

        return {
            "status": "added",
            "source": new_source,
            "message": f"Successfully registered custom URL under label '{final_label}'."
        }

    def remove_source(self, url_or_label: str) -> Dict[str, Any]:
        target = url_or_label.strip().lower()
        sources = self.get_sources()
        found = None
        remaining = []

        for s in sources:
            if s["url"].lower() == target or s["label"].lower() == target:
                found = s
            else:
                remaining.append(s)

        if not found:
            return {
                "status": "not_found",
                "message": f"No custom source found matching '{url_or_label}'."
            }

        self.save_sources(remaining)
        return {
            "status": "removed",
            "source": found,
            "message": f"Removed custom URL source '{found['label']}' ({found['url']})."
        }

    def update_sync_stats(self, url: str, files_count: int):
        sources = self.get_sources()
        for s in sources:
            if s["url"].lower() == url.lower():
                s["last_synced"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                s["files_count"] = files_count
                break
        self.save_sources(sources)


def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "_", name)
    return clean.strip()


def scrape_custom_source(
    source_entry: Dict[str, Any],
    output_base_dir: Path,
    known_catalog: Optional[Dict[str, Any]] = None,
    on_file_saved: Optional[Callable[[str, bool], None]] = None,
    timeout: int = 25
) -> Dict[str, Any]:
    """
    Downloads direct PDFs or scans a webpage for all PDF links and downloads them.
    Saves them in output_base_dir / "Custom_Sources" / <label> / <filename.pdf>.
    Calls on_file_saved(file_path, is_new) for each saved file.
    """
    url = source_entry["url"]
    label = source_entry["label"]

    dest_folder = output_base_dir / "Custom_Sources" / label
    dest_folder.mkdir(parents=True, exist_ok=True)

    downloaded_files = []
    errors = []

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # 1. First probe the URL (HEAD or GET)
        res = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
        res.raise_for_status()

        content_type = res.headers.get("Content-Type", "").lower()
        final_url = res.url

        # Check if direct PDF
        if "application/pdf" in content_type or url.lower().endswith(".pdf") or final_url.lower().endswith(".pdf"):
            # Direct PDF
            parsed = urllib.parse.urlparse(final_url)
            filename = urllib.parse.unquote(parsed.path.split("/")[-1])
            if not filename or not filename.lower().endswith(".pdf"):
                filename = f"{label}.pdf"
            filename = sanitize_filename(filename)

            target_file = (dest_folder / filename).resolve()
            
            # Check against list.md catalog upfront
            is_cataloged = False
            if known_catalog:
                if str(target_file) in known_catalog.get("paths", set()) or (label, filename) in known_catalog.get("course_files", set()):
                    is_cataloged = True

            if is_cataloged or (target_file.exists() and target_file.stat().st_size > 0):
                res.close()
                print(f"[Custom Scraper] Skipping cataloged file: {filename}")
                downloaded_files.append(str(target_file))
                if on_file_saved:
                    on_file_saved(str(target_file), False)
            else:
                with open(target_file, "wb") as f:
                    for chunk in res.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)

                downloaded_files.append(str(target_file))
                if on_file_saved:
                    on_file_saved(str(target_file), True)

        else:
            # HTML Webpage - Parse for PDF links
            html_content = res.content
            soup = BeautifulSoup(html_content, "html.parser")

            found_pdf_links = set()
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                abs_href = urllib.parse.urljoin(final_url, href)
                parsed_href = urllib.parse.urlparse(abs_href)
                path_lower = parsed_href.path.lower()
                
                if (
                    path_lower.endswith(".pdf") or 
                    "pdf" in parsed_href.query.lower() or 
                    ("download" in parsed_href.path.lower() and "pdf" in href.lower())
                ):
                    found_pdf_links.add((abs_href, a_tag.get_text().strip()))

            print(f"[Custom Scraper] Found {len(found_pdf_links)} PDF link(s) on page {url}")

            for pdf_link, link_text in found_pdf_links:
                try:
                    # Pre-determine filename to check against list.md before making any network request
                    parsed_p = urllib.parse.urlparse(pdf_link)
                    fname = urllib.parse.unquote(parsed_p.path.split("/")[-1])
                    if not fname.lower().endswith(".pdf"):
                        if link_text:
                            fname = sanitize_filename(link_text) + ".pdf"
                        else:
                            fname = sanitize_filename(fname) + ".pdf"
                    fname = sanitize_filename(fname)
                    if not fname or fname == ".pdf":
                        fname = f"document_{len(downloaded_files)+1}.pdf"

                    target_file = (dest_folder / fname).resolve()
                    if known_catalog and (str(target_file) in known_catalog.get("paths", set()) or (label, fname) in known_catalog.get("course_files", set())):
                        downloaded_files.append(str(target_file))
                        if on_file_saved:
                            on_file_saved(str(target_file), False)
                        continue

                    if target_file.exists() and target_file.stat().st_size > 0:
                        # Already on disk - skip network request completely!
                        downloaded_files.append(str(target_file))
                        if on_file_saved:
                            on_file_saved(str(target_file), False)
                        continue

                    pdf_res = session.get(pdf_link, timeout=timeout, allow_redirects=True, stream=True)
                    if pdf_res.status_code != 200:
                        continue
                    
                    pdf_ct = pdf_res.headers.get("Content-Type", "").lower()
                    if not ("application/pdf" in pdf_ct or pdf_link.lower().endswith(".pdf") or pdf_res.url.lower().endswith(".pdf")):
                        pdf_res.close()
                        continue

                    with open(target_file, "wb") as f:
                        for chunk in pdf_res.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)

                    downloaded_files.append(str(target_file.resolve()))
                    if on_file_saved:
                        on_file_saved(str(target_file.resolve()), True)

                except Exception as dl_err:
                    errors.append(f"Failed to download {pdf_link}: {dl_err}")

    except Exception as ex:
        errors.append(f"Failed to scrape {url}: {ex}")

    return {
        "status": "success" if downloaded_files else ("partial_or_empty" if not errors else "error"),
        "url": url,
        "label": label,
        "destination_folder": str(dest_folder.resolve()),
        "downloaded_files_count": len(downloaded_files),
        "files": downloaded_files,
        "errors": errors
    }
