import os
import re
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
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


def render_slide(
    pdf_path: str,
    page_num: int,
    cache_dir: Optional[Path] = None,
    max_dimension: int = 1400,
    dpi: int = 150,
    high_res: bool = False,
    **kwargs
) -> Optional[Path]:
    """Renders a PDF page to a PNG image cached in data/visual_cache/."""
    try:
        path = Path(pdf_path)
        if not path.exists() or path.suffix.lower() != ".pdf":
            return None

        cache_dir = cache_dir or (Path(WORKSPACE_DIR) / "data" / "visual_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^\w\-.]", "_", path.stem)
        suffix = "_300dpi" if high_res else "_full"
        image_path = cache_dir / f"{safe_name}_p{page_num}{suffix}.png"
        if image_path.exists() and image_path.stat().st_size > 0:
            return image_path

        doc = pymupdf.open(str(path))
        page_idx = page_num - 1
        if not (0 <= page_idx < len(doc)):
            doc.close()
            return None

        page = doc[page_idx]
        if high_res:
            pix = page.get_pixmap(dpi=300)
        else:
            orig_max = max(page.rect.width, page.rect.height)
            scale = min(max_dimension / orig_max, dpi / 72.0) if orig_max > 0 else 1.0
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))

        pix.save(str(image_path))
        doc.close()
        prune_visual_cache(cache_dir=cache_dir)
        return image_path
    except Exception as ex:
        print(f"[Visual Fallback] Warning: Could not render page {page_num} of {pdf_path}: {ex}")
        return None


# Backward-compatible unified aliases
render_page_to_image = render_slide
render_full_slide_image = render_slide


def process_visual_fallback(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    cache_dir: Optional[Path] = None,
    max_pages: int = 2
) -> Dict[str, Any]:
    """
    Processes visual intent for retrieved chunks.
    STRICT GATING: Slide rendering is ONLY triggered when the user explicitly expresses
    visual intent (asking for diagrams, charts, graphs, figures, layouts, or visual appearance).
    This eliminates visual token waste on standard textual/conceptual queries.
    """
    visual_intent = detect_visual_intent(query)
    
    # Strict Gating: If user did NOT ask for visual content, skip rendering completely!
    if not visual_intent:
        return {
            "triggered": False,
            "visual_intent_detected": False,
            "reason": "no_visual_intent",
            "rendered_pages": []
        }

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

        # Trigger rendering for the top visual candidate slides
        img_path = render_slide(pdf_path, page_num, cache_dir=cache_dir, max_dimension=1024)
        if img_path:
            seen_pages.add(page_key)
            b64_data = get_image_base64(img_path)
            rendered_pages.append({
                "course": chunk.get("course", "Unknown"),
                "filename": chunk.get("filename", "Unknown"),
                "page": page_num,
                "pdf_path": pdf_path,
                "image_path": str(img_path.resolve()),
                "image_url": f"file://{img_path.resolve()}",
                "image_base64": b64_data,
                "has_embedded_images": has_img,
                "citation": chunk.get("citation", "")
            })

        if len(rendered_pages) >= max_pages:
            break

    is_triggered = len(rendered_pages) > 0
    return {
        "triggered": is_triggered,
        "visual_intent_detected": True,
        "reason": "visual_intent_detected" if is_triggered else "no_renderable_slides",
        "rendered_pages": rendered_pages
    }


def get_image_base64(image_path: Union[str, Path]) -> Optional[str]:
    """Reads a local image file and returns its base64-encoded string."""
    try:
        p = Path(image_path)
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        pass
    return None





def prune_visual_cache(max_files: int = 150, cache_dir: Optional[Path] = None) -> int:
    """
    Prunes visual cache directory when file count exceeds max_files.
    Deletes oldest PNGs first to keep disk footprint bounded.
    """
    try:
        if cache_dir is None:
            cache_dir = Path(WORKSPACE_DIR) / "data" / "visual_cache"
        if not cache_dir.exists():
            return 0
        png_files = sorted(cache_dir.glob("*.png"), key=lambda p: p.stat().st_mtime)
        if len(png_files) <= max_files:
            return 0
        to_delete = png_files[:len(png_files) - max_files]
        deleted_count = 0
        for f in to_delete:
            try:
                f.unlink(missing_ok=True)
                deleted_count += 1
            except Exception:
                pass
        return deleted_count
    except Exception as ex:
        print(f"[Visual Cache Prune Warning]: {ex}")
        return 0


