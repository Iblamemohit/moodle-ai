import os
import json
import sys
from pathlib import Path
from typing import Optional, List, Union

# Enforce MCP Execution Mode: strips ANSI escape sequences, carriage returns, and terminal spinners
os.environ["MCP_MODE"] = "1"

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent, ImageContent

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.agent_tools import (
    setup_moodle,
    sync_moodle,
    moodle_list,
    moodle_ask,
    moodle_quiz,
    moodle_change_sync,
    moodle_add_custom_url,
    moodle_remove_custom_url,
    moodle_list_custom_urls,
    update_moodle_ai,
    moodle_diagram,
    clean_output_text,
    get_course_slide as get_course_slide_impl
)
from src.scraper import discover_available_semesters
from src.visual_fallback import get_image_base64

# Initialize MCP Server (MCP 2.x standard)
mcp = MCPServer("moodle-ai")


def _tool_result(text: str, res: dict, images: Optional[List[Any]] = None) -> CallToolResult:
    """Constructs CallToolResult with text and optional images."""
    blocks: List[Union[TextContent, ImageContent]] = [TextContent(type="text", text=clean_output_text(text))]
    for img in (images if images is not None else ([res.get("image_base64") or res.get("image_path")] if res.get("image_path") or res.get("image_base64") else [])):
        b64 = img if isinstance(img, str) and len(img) > 500 else (get_image_base64(img) if img else None)
        if b64:
            blocks.append(ImageContent(type="image", data=b64, mime_type="image/png"))
    return CallToolResult(content=blocks, structured_content=res)


@mcp.tool()
def moodle_search_and_ask(query: str, doc_filter: Optional[str] = None, course_filter: Optional[str] = None) -> CallToolResult:
    """Hybrid RAG search across course slides, notes, handouts, and custom URLs with dual file citations & multimodal images."""
    res = moodle_ask(query=query, doc_filter=doc_filter, course_filter=course_filter)
    
    output = []
    cache_tag = " [cached]" if res.get("from_cache") else ""
    output.append(f"### Results for: '{query}'{cache_tag}")

    if res.get("moodle_context"):
        for chunk in res["moodle_context"]:
            output.append(f"\n> **Source**: {chunk['citation']}")
            output.append(chunk["text"])

    rendered_pages = res.get("visual_fallback", {}).get("rendered_pages", [])
    if res.get("visual_fallback", {}).get("triggered") and rendered_pages:
        output.append("\n**Visual Slides**:")
        for vp in rendered_pages:
            output.append(f"- [{vp['filename']} (p.{vp['page']})]({vp['image_url']}) | `{vp['image_path']}`")

    imgs = [vp.get("image_base64") or vp.get("image_path") for vp in rendered_pages] if res.get("visual_fallback", {}).get("triggered") else []
    return _tool_result("\n".join(output), res, imgs)



@mcp.tool()
def list_available_courses_and_documents(regenerate: bool = False) -> str:
    """Returns the structured document catalog of all downloaded courses and custom sources from list.md."""
    res = moodle_list(regenerate=regenerate)
    return clean_output_text(res.get("markdown_content", "No course documents found."))

@mcp.tool()
def discover_moodle_semesters_list() -> str:
    """Discovers available Moodle semesters, years, and enrolled courses without downloading."""
    res = discover_available_semesters()
    return clean_output_text(json.dumps(res, indent=2))

@mcp.tool()
def trigger_moodle_sync(
    semester: Optional[str] = None,
    course_filter: Optional[str] = None,
    quick_check: bool = False
) -> str:
    """Scrapes Moodle, custom URLs, or user_files/ and updates vector & BM25 indexes. Pass quick_check=True for fast single-course sync."""
    res = sync_moodle(semester=semester, course_filter=course_filter, quick_check=quick_check)
    return clean_output_text(json.dumps(res, indent=2))


@mcp.tool()
def get_course_slide(
    course_code: str,
    document_name: str,
    page_number: int,
    render_image: bool = True,
    high_res: bool = False
) -> CallToolResult:
    """Retrieves exact markdown text and high-res rendered slide PNG for a specific page (high_res=True for 300 DPI raw)."""
    res = get_course_slide_impl(
        course_code=course_code,
        document_name=document_name,
        page_number=page_number,
        render_image=render_image,
        high_res=high_res
    )
    return _tool_result(res.get("summary_markdown", res.get("text", "")), res)



@mcp.tool()
def add_custom_scrape_url(url: str, label: Optional[str] = None, auto_sync: bool = True) -> str:
    """Registers a custom web URL or PDF to scrape and indexes its contents into the knowledge base."""
    res = moodle_add_custom_url(url=url, label=label, auto_sync=auto_sync)
    return json.dumps(res, indent=2)

@mcp.tool()
def remove_custom_scrape_url(url_or_label: str, delete_files: bool = False) -> str:
    """Removes a registered custom URL and optionally deletes downloaded files."""
    res = moodle_remove_custom_url(url_or_label=url_or_label, delete_files=delete_files)
    return json.dumps(res, indent=2)

@mcp.tool()
def list_custom_scrape_urls() -> str:
    """Lists registered custom URLs and their sync statuses."""
    res = moodle_list_custom_urls()
    return json.dumps(res, indent=2)

@mcp.tool()
def change_moodle_tracked_semester(target_semester: Optional[str] = None) -> str:
    """Updates the default tracked semester (e.g. 2601, 2502, all) in .env and list.md."""
    res = moodle_change_sync(target_semester=target_semester)
    return json.dumps(res, indent=2)

@mcp.tool()
def generate_practice_quiz_context(course: Optional[str] = None, num_questions: int = 3) -> str:
    """Samples foundational course concepts and summary slides to generate practice quiz questions."""
    res = moodle_quiz(course=course, num_questions=num_questions)
    output = [f"### Practice Quiz Topics: {res['course']}"]
    for m in res["materials"]:
        output.append(f"\n> **Source**: {m['citation']}")
        output.append(m["text"])
    return "\n".join(output)


@mcp.tool()
def configure_moodle_credentials(user: Optional[str] = None, password: Optional[str] = None) -> str:
    """Configures or verifies Kerberos credentials in .env."""
    res = setup_moodle(user, password)
    return json.dumps(res, indent=2)

@mcp.tool()
def update_moodle_ai_version() -> str:
    """Pulls latest code updates from GitHub and refreshes virtual environment dependencies."""
    res = update_moodle_ai()
    return json.dumps(res, indent=2)


@mcp.tool()
def generate_engineering_diagram(diagram_type: str, params: Optional[str] = None) -> CallToolResult:
    """Generates 300 DPI engineering diagrams (sfd_bmd, is456_stress_block, cpm_network); returns multimodal diagram & embed link."""
    params_dict = None
    if params:
        try:
            params_dict = json.loads(params)
        except Exception:
            params_dict = None
    res = moodle_diagram(diagram_type=diagram_type, params=params_dict)
    summary = res.get("summary_markdown") or (f"### {res.get('title', 'Engineering Diagram')}\n![{res.get('title')}]({res.get('image_url')})\n- **Image Path**: `{res.get('image_path')}`" if res.get("status") == "success" else json.dumps(res, indent=2))
    return _tool_result(summary, res)


if __name__ == "__main__":
    mcp.run()
