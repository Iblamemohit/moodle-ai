import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf

from src.config import WORKSPACE_DIR

# Visual trigger keywords and patterns
VISUAL_KEYWORDS = {
    "diagram", "diagrams", "chart", "charts", "graph", "graphs",
    "figure", "figures", "fig", "slide", "slides", "image", "images",
    "picture", "pictures", "photo", "photos", "flowchart", "flowcharts",
    "architecture", "architectural", "schematic", "schematics",
    "circuit", "circuits", "drawing", "drawings", "illustration", "illustrations",
    "plot", "plots", "curve", "curves", "table", "tables", "layout",
    "visual", "visually", "wireframe", "blueprint"
}

VISUAL_PHRASES = [
    r"look like",
    r"how does .* look",
    r"show me the",
    r"see the slide",
    r"in the diagram",
    r"on the slide",
    r"in the figure",
    r"on the graph",
    r"on page \d+",
    r"slide \d+"
]


def detect_visual_intent(query: str) -> bool:
    """
    Detects if the query expresses visual intent (requesting diagrams, charts, slides, figures, etc.).
    """
    if not query:
        return False
    
    cleaned = query.lower()
    tokens = set(re.findall(r"\b[a-z]+\b", cleaned))
    if tokens & VISUAL_KEYWORDS:
        return True
    
    for phrase in VISUAL_PHRASES:
        if re.search(phrase, cleaned):
            return True
            
    return False


def page_has_visuals(pdf_path: str, page_num: int) -> bool:
    """
    Inspects whether a specific page of a PDF contains images or vector graphics.
    page_num is 1-indexed.
    """
    try:
        path = Path(pdf_path)
        if not path.exists() or path.suffix.lower() != ".pdf":
            return False
        
        doc = pymupdf.open(str(path))
        page_idx = page_num - 1
        if 0 <= page_idx < len(doc):
            page = doc[page_idx]
            images = page.get_images()
            if len(images) > 0:
                doc.close()
                return True
            drawings = page.get_drawings()
            if len(drawings) > 5:
                doc.close()
                return True
        doc.close()
    except Exception:
        pass
    return False


def render_page_to_image(
    pdf_path: str, 
    page_num: int, 
    cache_dir: Optional[Path] = None, 
    dpi: int = 150
) -> Optional[Path]:
    """
    Renders a single page of a PDF into a high-resolution PNG using PyMuPDF.
    Caches the image under data/visual_cache/.
    page_num is 1-indexed.
    """
    try:
        path = Path(pdf_path)
        if not path.exists() or path.suffix.lower() != ".pdf":
            return None

        if cache_dir is None:
            cache_dir = Path(WORKSPACE_DIR) / "data" / "visual_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^\w\-.]", "_", path.stem)
        image_filename = f"{safe_name}_p{page_num}.png"
        image_path = cache_dir / image_filename

        # Return cached image if it already exists and is not empty
        if image_path.exists() and image_path.stat().st_size > 0:
            return image_path

        doc = pymupdf.open(str(path))
        page_idx = page_num - 1
        if not (0 <= page_idx < len(doc)):
            doc.close()
            return None

        page = doc[page_idx]
        pix = page.get_pixmap(dpi=dpi)
        pix.save(str(image_path))
        doc.close()

        return image_path
    except Exception as ex:
        print(f"[Visual Fallback] Warning: Could not render page {page_num} of {pdf_path}: {ex}")
        return None


def process_visual_fallback(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    cache_dir: Optional[Path] = None,
    max_pages: int = 2
) -> Dict[str, Any]:
    """
    Processes visual intent and slide visual content for retrieved chunks.
    If visual intent is detected or candidate slides contain images/drawings,
    renders the candidate page(s) and returns visual context for the multimodal agent.
    """
    visual_intent = detect_visual_intent(query)
    rendered_pages = []
    seen_pages = set()

    for chunk in retrieved_chunks:
        pdf_path = chunk.get("pdf_path")
        page_num = chunk.get("page")
        if not pdf_path or not page_num:
            continue

        page_key = (pdf_path, page_num)
        if page_key in seen_pages:
            continue

        has_img = page_has_visuals(pdf_path, page_num)

        # Trigger if query is visual OR if this slide explicitly contains embedded graphics
        if visual_intent or has_img:
            img_path = render_page_to_image(pdf_path, page_num, cache_dir=cache_dir)
            if img_path:
                seen_pages.add(page_key)
                rendered_pages.append({
                    "course": chunk.get("course", "Unknown"),
                    "filename": chunk.get("filename", "Unknown"),
                    "page": page_num,
                    "pdf_path": pdf_path,
                    "image_path": str(img_path.resolve()),
                    "image_url": f"file://{img_path.resolve()}",
                    "has_embedded_images": has_img,
                    "citation": chunk.get("citation", "")
                })

        if len(rendered_pages) >= max_pages:
            break

    is_triggered = len(rendered_pages) > 0
    reason = "none"
    if is_triggered:
        if visual_intent:
            reason = "visual_intent_detected"
        else:
            reason = "candidate_slide_contains_visuals"

    return {
        "triggered": is_triggered,
        "visual_intent_detected": visual_intent,
        "reason": reason,
        "rendered_pages": rendered_pages
    }
