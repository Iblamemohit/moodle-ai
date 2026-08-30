import os
import datetime
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf

class ListManager:
    def __init__(self, workspace_dir: str, output_dir: str, parsed_dir: str, list_file: str = "list.md"):
        self.workspace_dir = Path(workspace_dir)
        self.output_dir = Path(output_dir)
        self.parsed_dir = Path(parsed_dir)
        self.list_file_path = self.workspace_dir / list_file

    def get_file_stats(self, file_path: Path) -> Dict[str, Any]:
        size_bytes = file_path.stat().st_size if file_path.exists() else 0
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

        ext = file_path.suffix.lower()
        pages = 1
        if ext == ".pdf":
            try:
                doc = pymupdf.open(str(file_path))
                pages = len(doc)
                doc.close()
            except Exception:
                pages = 1

        rel_from_output = file_path.relative_to(self.output_dir)
        parsed_md = self.parsed_dir / rel_from_output.with_suffix(".md")
        is_parsed = parsed_md.exists()

        return {
            "name": file_path.name,
            "rel_path": str(rel_from_output),
            "size": size_str,
            "bytes": size_bytes,
            "pages": pages,
            "ext": ext.replace(".", "").upper(),
            "is_parsed": is_parsed,
            "modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        }

    def scan_all_documents(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Scans output_dir and groups files by Semester -> Course.
        """
        structure: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

        if not self.output_dir.exists():
            return structure

        for sem_dir in sorted(self.output_dir.iterdir()):
            if not sem_dir.is_dir() or sem_dir.name.startswith("."):
                continue
            sem_name = sem_dir.name
            structure[sem_name] = {}

            for course_dir in sorted(sem_dir.iterdir()):
                if not course_dir.is_dir() or course_dir.name.startswith("."):
                    continue
                course_name = course_dir.name
                structure[sem_name][course_name] = []

                for root, _, files in os.walk(course_dir):
                    if ".dump" in root:
                        continue
                    for f in sorted(files):
                        if f.startswith("."):
                            continue
                        f_path = Path(root) / f
                        stats = self.get_file_stats(f_path)
                        structure[sem_name][course_name].append(stats)

        return structure

    def generate_list_markdown(self) -> str:
        structure = self.scan_all_documents()
        total_sems = len(structure)
        total_courses = sum(len(courses) for courses in structure.values())
        total_files = sum(
            len(files) for courses in structure.values() for files in courses.values()
        )
        total_pages = sum(
            f["pages"] for courses in structure.values() for files in courses.values() for f in files
        )

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "# 📚 Moodle Knowledge Base Document Index",
            "",
            f"*Last Updated: {now_str}*",
            f"**Total Semesters:** {total_sems} | **Total Courses:** {total_courses} | **Total Files:** {total_files} | **Total Slides/Pages:** {total_pages}",
            "",
            "---",
            ""
        ]

        if not structure:
            lines.append("*No course documents downloaded yet. Run `/sync` to download course materials.*")
            return "\n".join(lines)

        for sem_name, courses in structure.items():
            lines.append(f"## 🏛️ {sem_name.replace('_', ' ')}")
            lines.append("")

            for course_name, files in courses.items():
                lines.append(f"### 📖 {course_name}")
                if not files:
                    lines.append("*No files downloaded for this course.*")
                    lines.append("")
                    continue

                lines.append("| Document Name | Type | Size | Pages | Status |")
                lines.append("| :--- | :---: | :---: | :---: | :---: |")

                for f in files:
                    status = "✅ Parsed & Indexed" if f["is_parsed"] else "⏳ Pending Parse"
                    full_src_path = (self.output_dir / f["rel_path"]).resolve()
                    if full_src_path.exists():
                        quoted_path = urllib.parse.quote(str(full_src_path), safe="/:")
                        doc_display = f"[{f['name']}](open-preview://{quoted_path}#page=1)"
                    else:
                        doc_display = f"`{f['name']}`"
                    lines.append(f"| {doc_display} | {f['ext']} | {f['size']} | {f['pages']} | {status} |")

                lines.append("")

        return "\n".join(lines)

    def update_list_file(self) -> str:
        content = self.generate_list_markdown()
        with open(self.list_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return content

    def read_list_file(self) -> str:
        if not self.list_file_path.exists():
            return self.update_list_file()
        with open(self.list_file_path, "r", encoding="utf-8") as f:
            return f.read()
