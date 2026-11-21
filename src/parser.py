import os
import re
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup
import pymupdf4llm

def compute_file_hash(filepath):
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def parse_pptx_to_markdown(filepath):
    chunks = []
    full_md_list = []

    try:
        import pptx
        prs = pptx.Presentation(str(filepath))

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_lines = []
            slide_title = None

            if slide.shapes.title and slide.shapes.title.has_text_frame:
                title_text = slide.shapes.title.text.strip()
                if title_text:
                    slide_title = title_text
                    slide_lines.append(f'# Slide {slide_idx}: {title_text}')
                    slide_lines.append('')

            if not slide_title:
                slide_lines.append(f'# Slide {slide_idx}')
                slide_lines.append('')

            for shape in slide.shapes:
                if shape == slide.shapes.title:
                    continue

                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        p_text = paragraph.text.strip()
                        if not p_text:
                            continue
                        indent = '  ' * paragraph.level
                        if paragraph.level > 0:
                            slide_lines.append(f'{indent}- {p_text}')
                        elif p_text.startswith(('#', '-', '*', '>')):
                            slide_lines.append(p_text)
                        else:
                            slide_lines.append(f'- {p_text}')

                elif shape.has_table:
                    table = shape.table
                    table_lines = []
                    if len(table.rows) > 0:
                        headers = [cell.text.strip().replace(chr(10), ' ') or '-' for cell in table.rows[0].cells]
                        table_lines.append('| ' + ' | '.join(headers) + ' |')
                        table_lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')

                        for row in table.rows[1:]:
                            row_cells = [cell.text.strip().replace(chr(10), ' ') or '-' for cell in row.cells]
                            table_lines.append('| ' + ' | '.join(row_cells) + ' |')

                        slide_lines.append('')
                        slide_lines.extend(table_lines)
                        slide_lines.append('')

            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_lines.append('')
                    slide_lines.append(f'> **Speaker Notes:** {notes}')

            slide_text = chr(10).join(slide_lines).strip()
            if slide_text:
                chunks.append({
                    'page': slide_idx,
                    'text': slide_text
                })
                full_md_list.append(f'<!-- Page {slide_idx} -->' + chr(10) + slide_text)

    except Exception as pptx_err:
        print(f'[Parser Error] Failed to parse PPTX {Path(filepath).name}: {pptx_err}')

    combined_md = (chr(10) + chr(10) + '---' + chr(10) + chr(10)).join(full_md_list)
    return chunks, combined_md


def parse_docx_to_markdown(filepath):
    chunks = []
    lines = []
    try:
        import zipfile
        with zipfile.ZipFile(filepath, 'r') as zf:
            if 'word/document.xml' in zf.namelist():
                xml_data = zf.read('word/document.xml')
                tree = ET.fromstring(xml_data)
                for elem in tree.iter():
                    if elem.tag.endswith('p'):
                        p_texts = [node.text for node in elem.iter() if node.text and node.tag.endswith('t')]
                        p_str = ''.join(p_texts).strip()
                        if p_str:
                            lines.append(p_str)
        text = (chr(10) + chr(10)).join(lines).strip()
        if text:
            chunks.append({'page': 1, 'text': text})
        return chunks, text
    except Exception as e:
        print(f'[Parser Error] Failed to parse DOCX {Path(filepath).name}: {e}')
        return [], ''


class DocumentParser:
    def __init__(self, output_dir, parsed_dir, user_files_dir=None):
        self.output_dir = Path(output_dir).resolve()
        self.parsed_dir = Path(parsed_dir).resolve()
        self.user_files_dir = Path(user_files_dir).resolve() if user_files_dir else None
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.hash_cache_file = self.parsed_dir / '.file_hashes.json'
        self.hashes = self._load_hashes()

    def _load_hashes(self):
        if self.hash_cache_file.exists():
            try:
                with open(self.hash_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_hashes(self):
        with open(self.hash_cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.hashes, f, indent=2)

    def _make_chunk(self, text, filepath, course_name, sem_label, page=1):
        return {
            'text': text,
            'metadata': {
                'source': str(filepath),
                'filename': Path(filepath).name,
                'course': course_name,
                'semester': sem_label,
                'page': page
            }
        }

    def _save_markdown(self, md_dest, content):
        if content:
            md_dest.parent.mkdir(parents=True, exist_ok=True)
            with open(md_dest, 'w', encoding='utf-8') as f:
                f.write(content)

    def parse_file(self, filepath, force=False):
        filepath = Path(filepath).resolve()
        if not filepath.exists() or filepath.name.startswith('.'):
            return []

        # Check if file is inside user_files_dir
        if self.user_files_dir and (filepath == self.user_files_dir or self.user_files_dir in filepath.parents):
            sub_rel = filepath.relative_to(self.user_files_dir)
            rel_path = Path("User_Files") / sub_rel
            sem_label = "User_Files"
            course_name = sub_rel.parts[0] if len(sub_rel.parts) > 1 else "General"
        else:
            try:
                rel_path = filepath.relative_to(self.output_dir)
            except ValueError:
                rel_path = Path(filepath.name)

            parts = rel_path.parts
            sem_label = parts[0] if len(parts) > 0 else 'Unknown_Semester'
            course_name = parts[1] if len(parts) > 1 else 'Unknown_Course'

        curr_hash = compute_file_hash(filepath)
        cached_hash = self.hashes.get(str(rel_path))

        # Check if already up-to-date (Anti-cache penalty eliminated: return immediately without re-checking gibberish)
        md_dest = self.parsed_dir / rel_path.with_suffix('.md')
        if not force and cached_hash == curr_hash and md_dest.exists():
            try:
                with open(md_dest, 'r', encoding='utf-8') as f:
                    full_md = f.read()

                page_sections = re.split(r'<!-- Page \d+(?::\s*\[[^\]]+\])?\s*-->', full_md)
                if len(page_sections) > 1:
                    cached_chunks = []
                    page_matches = re.findall(r'<!-- Page (\d+)(?::\s*\[[^\]]+\])?\s*-->', full_md)
                    for i, p_num_str in enumerate(page_matches):
                        if i + 1 < len(page_sections):
                            p_txt = page_sections[i+1].strip().rstrip('-').strip()
                            if p_txt:
                                cached_chunks.append(self._make_chunk(p_txt, filepath, course_name, sem_label, int(p_num_str)))
                    if cached_chunks:
                        return cached_chunks

                if full_md.strip():
                    return [self._make_chunk(full_md.strip(), filepath, course_name, sem_label, 1)]
                return []
            except Exception:
                pass

        ext = filepath.suffix.lower()
        chunks = []

        # 1. PDF Documents
        if ext == '.pdf':
            try:
                import pymupdf
                from src.quality_filter import SlideQualityClassifier, QualityAssessment
                from src.visual_fallback import render_page_to_image

                doc = pymupdf.open(str(filepath))
                pages_data = pymupdf4llm.to_markdown(str(filepath), page_chunks=True)
                full_md_list = []

                # First pass: identify repetitive headers/footers across slides
                line_freq = {}
                for p in pages_data:
                    p_txt = p.get('text', '')
                    for line in p_txt.splitlines():
                        s_line = line.strip()
                        if len(s_line) > 10 and not s_line.startswith('|') and not s_line.startswith('#'):
                            line_freq[s_line] = line_freq.get(s_line, 0) + 1

                boilerplate_lines = {
                    l for l, count in line_freq.items()
                    if count >= 5 or (len(pages_data) >= 6 and count >= len(pages_data) * 0.5)
                }

                for idx, p in enumerate(pages_data):
                    p_text = p.get('text', '').strip()
                    p_meta = p.get('metadata', {})
                    page_num = p_meta.get('page_number', idx + 1)

                    # Sanitize formatting noise
                    p_text = SlideQualityClassifier.sanitize_markdown_text(p_text)

                    # Strip repetitive headers/footers
                    if boilerplate_lines and p_text:
                        clean_lines = [l for l in p_text.splitlines() if l.strip() not in boilerplate_lines]
                        p_text = "\n".join(clean_lines).strip()

                    # Assess quality with PyMuPDF page object
                    page_obj = doc[idx] if idx < len(doc) else None
                    if page_obj is not None:
                        quality = SlideQualityClassifier.assess_page_quality(page_obj, p_text)
                    else:
                        is_gib, reason, _ = SlideQualityClassifier.is_gibberish_text(p_text)
                        quality = QualityAssessment(
                            is_acceptable=not is_gib,
                            is_visual_only=is_gib,
                            reason=reason,
                            alphanumeric_ratio=0.5,
                            drawing_count=0,
                            word_count=len(p_text.split())
                        )

                    if quality.is_acceptable:
                        chunks.append(self._make_chunk(p_text, filepath, course_name, sem_label, page_num))
                        full_md_list.append(f'<!-- Page {page_num} -->\n' + p_text)
                    elif quality.is_visual_only:
                        try:
                            render_page_to_image(str(filepath), page_num)
                        except Exception:
                            pass
                        visual_note = f"*Contains visual diagram / schematic / CAD drawing ({quality.reason}). Available via visual inspection.*"
                        full_md_list.append(f'<!-- Page {page_num}: [Visual Diagram/Drawing] -->\n' + visual_note)
                    else:
                        full_md_list.append(f'<!-- Page {page_num}: [Omitted: {quality.reason}] -->')

                doc.close()
                combined_md = (chr(10) + chr(10) + '---' + chr(10) + chr(10)).join(full_md_list)
                self._save_markdown(md_dest, combined_md)

            except Exception as e:
                print(f'[Parser Error] Failed to parse PDF {filepath.name}: {e}')
                return []

        # 2. PowerPoint Presentations (.pptx, .ppt)
        elif ext in ('.pptx', '.ppt'):
            try:
                raw_chunks, combined_md = parse_pptx_to_markdown(filepath)
                for ch in raw_chunks:
                    chunks.append(self._make_chunk(ch['text'], filepath, course_name, sem_label, ch['page']))
                self._save_markdown(md_dest, combined_md)
            except Exception as e:
                print(f'[Parser Error] Failed to parse presentation {filepath.name}: {e}')
                return []

        # 3. Word Documents (.docx)
        elif ext == '.docx':
            try:
                raw_chunks, combined_md = parse_docx_to_markdown(filepath)
                for ch in raw_chunks:
                    chunks.append(self._make_chunk(ch['text'], filepath, course_name, sem_label, ch['page']))
                self._save_markdown(md_dest, combined_md)
            except Exception as e:
                print(f'[Parser Error] Failed to parse DOCX {filepath.name}: {e}')
                return []

        # 4. ZIP Archives (.zip)
        elif ext == '.zip':
            try:
                extract_dir = filepath.parent / filepath.stem
                if not extract_dir.exists():
                    shutil.unpack_archive(str(filepath), str(extract_dir))

                zip_md_sections = [f'# Archive: {filepath.name}\n']
                for sub_root, _, sub_files in os.walk(extract_dir):
                    for sub_f in sorted(sub_files):
                        if sub_f.startswith('.'):
                            continue
                        sub_path = Path(sub_root) / sub_f
                        sub_chunks = self.parse_file(sub_path, force=force)
                        for sc in sub_chunks:
                            chunks.append(sc)
                            zip_md_sections.append(f'## File: {sub_f}\n\n' + sc['text'])

                if zip_md_sections:
                    combined_md = '\n\n---\n\n'.join(zip_md_sections)
                    self._save_markdown(md_dest, combined_md)
            except Exception as e:
                print(f'[Parser Error] Failed to parse ZIP archive {filepath.name}: {e}')
                return []

        # 5. Plain text and Markdown
        elif ext in ('.txt', '.md'):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read().strip()
                if text:
                    chunks.append(self._make_chunk(text, filepath, course_name, sem_label, 1))
                    self._save_markdown(md_dest, text)
            except Exception as e:
                print(f'[Parser Error] Failed to parse text file {filepath.name}: {e}')
                return []

        # 6. HTML files
        elif ext in ('.html', '.htm'):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                for s in soup(['script', 'style', 'meta', 'noscript']):
                    s.extract()
                text = soup.get_text(separator=chr(10)).strip()
                if text:
                    chunks.append(self._make_chunk(text, filepath, course_name, sem_label, 1))
                    self._save_markdown(md_dest, text)
            except Exception as e:
                print(f'[Parser Error] Failed to parse HTML {filepath.name}: {e}')
                return []

        # Update cache
        self.hashes[str(rel_path)] = curr_hash
        self._save_hashes()

        return chunks

    def parse_all(self, force=False):
        all_chunks = []
        supported_exts = {'.pdf', '.pptx', '.ppt', '.docx', '.zip', '.txt', '.md', '.html', '.htm'}

        target_dirs = [self.output_dir]
        if self.user_files_dir and self.user_files_dir.exists():
            target_dirs.append(self.user_files_dir)

        for base_dir in target_dirs:
            for root_d, _, files in os.walk(base_dir):
                if '.dump' in root_d:
                    continue
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in supported_exts and not f.startswith('.'):
                        file_path = os.path.join(root_d, f)
                        chunks = self.parse_file(file_path, force=force)
                        all_chunks.extend(chunks)
        return all_chunks
