import os
import hashlib
import json
from pathlib import Path
from bs4 import BeautifulSoup
import pymupdf4llm

def compute_file_hash(filepath):
    """Computes SHA-256 hash of a file for change tracking."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

class DocumentParser:
    def __init__(self, output_dir, parsed_dir):
        self.output_dir = Path(output_dir)
        self.parsed_dir = Path(parsed_dir)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.hash_cache_file = self.parsed_dir / ".file_hashes.json"
        self.hashes = self._load_hashes()

    def _load_hashes(self):
        if self.hash_cache_file.exists():
            try:
                with open(self.hash_cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_hashes(self):
        with open(self.hash_cache_file, "w", encoding="utf-8") as f:
            json.dump(self.hashes, f, indent=2)

    def parse_file(self, filepath, force=False):
        """
        Parses a single document into structured markdown chunks.
        Returns a list of dicts:
        [{'text': str, 'metadata': {'source': str, 'filename': str, 'course': str, 'semester': str, 'page': int}}]
        """
        filepath = Path(filepath).resolve()
        if not filepath.exists() or filepath.name.startswith("."):
            return []

        rel_path = filepath.relative_to(self.output_dir)
        parts = rel_path.parts
        sem_label = parts[0] if len(parts) > 0 else "Unknown_Semester"
        course_name = parts[1] if len(parts) > 1 else "Unknown_Course"

        curr_hash = compute_file_hash(filepath)
        cached_hash = self.hashes.get(str(rel_path))

        # Check if already up-to-date
        md_dest = self.parsed_dir / rel_path.with_suffix(".md")
        if not force and cached_hash == curr_hash and md_dest.exists():
            # Return cached parsed chunks with exact page numbers
            try:
                with open(md_dest, "r", encoding="utf-8") as f:
                    full_md = f.read()
                
                page_sections = re.split(r'<!-- Page (\d+) -->\n', full_md)
                if len(page_sections) > 1:
                    cached_chunks = []
                    for i in range(1, len(page_sections), 2):
                        p_num = int(page_sections[i])
                        p_txt = page_sections[i+1].strip().rstrip("-").strip()
                        if p_txt:
                            cached_chunks.append({
                                "text": p_txt,
                                "metadata": {
                                    "source": str(filepath),
                                    "filename": filepath.name,
                                    "course": course_name,
                                    "semester": sem_label,
                                    "page": p_num
                                }
                            })
                    if cached_chunks:
                        return cached_chunks

                return [{
                    "text": full_md,
                    "metadata": {
                        "source": str(filepath),
                        "filename": filepath.name,
                        "course": course_name,
                        "semester": sem_label,
                        "page": 1
                    }
                }]
            except Exception:
                pass

        ext = filepath.suffix.lower()
        chunks = []

        if ext == ".pdf":
            try:
                pages_data = pymupdf4llm.to_markdown(str(filepath), page_chunks=True)
                full_md_list = []
                for p in pages_data:
                    p_text = p.get("text", "").strip()
                    p_meta = p.get("metadata", {})
                    page_num = p_meta.get("page_number", 1)
                    if p_text:
                        chunks.append({
                            "text": p_text,
                            "metadata": {
                                "source": str(filepath),
                                "filename": filepath.name,
                                "course": course_name,
                                "semester": sem_label,
                                "page": page_num
                            }
                        })
                        full_md_list.append(f"<!-- Page {page_num} -->\n{p_text}")
                
                # Save complete combined Markdown
                md_dest.parent.mkdir(parents=True, exist_ok=True)
                with open(md_dest, "w", encoding="utf-8") as f:
                    f.write("\n\n---\n\n".join(full_md_list))
                
            except Exception as e:
                print(f"[Parser Error] Failed to parse PDF {filepath.name}: {e}")
                return []

        elif ext in (".txt", ".md"):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().strip()
                if text:
                    chunks.append({
                        "text": text,
                        "metadata": {
                            "source": str(filepath),
                            "filename": filepath.name,
                            "course": course_name,
                            "semester": sem_label,
                            "page": 1
                        }
                    })
                    md_dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(md_dest, "w", encoding="utf-8") as f:
                        f.write(text)
            except Exception as e:
                print(f"[Parser Error] Failed to parse text file {filepath.name}: {e}")
                return []

        elif ext in (".html", ".htm"):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                # Remove scripts and styles
                for s in soup(["script", "style", "meta", "noscript"]):
                    s.extract()
                text = soup.get_text(separator="\n").strip()
                if text:
                    chunks.append({
                        "text": text,
                        "metadata": {
                            "source": str(filepath),
                            "filename": filepath.name,
                            "course": course_name,
                            "semester": sem_label,
                            "page": 1
                        }
                    })
                    md_dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(md_dest, "w", encoding="utf-8") as f:
                        f.write(text)
            except Exception as e:
                print(f"[Parser Error] Failed to parse HTML {filepath.name}: {e}")
                return []

        # Update cache
        self.hashes[str(rel_path)] = curr_hash
        self._save_hashes()

        return chunks

    def parse_all(self, force=False):
        """Parses all supported files across the entire output directory."""
        all_chunks = []
        supported_exts = {".pdf", ".txt", ".md", ".html", ".htm"}
        
        for root_d, _, files in os.walk(self.output_dir):
            if ".dump" in root_d:
                continue
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in supported_exts and not f.startswith("."):
                    file_path = os.path.join(root_d, f)
                    chunks = self.parse_file(file_path, force=force)
                    all_chunks.extend(chunks)
        return all_chunks
