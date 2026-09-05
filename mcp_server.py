import json
from typing import Optional
from mcp.server.mcpserver import MCPServer
from agent_tools import (
    setup_moodle,
    sync_moodle,
    moodle_list,
    moodle_ask,
    moodle_quiz,
    moodle_change_sync,
    moodle_add_custom_url,
    moodle_remove_custom_url,
    moodle_list_custom_urls,
    update_moodle_ai
)
from src.scraper_sync import discover_available_semesters

# Initialize MCP Server (MCP 2.x standard)
mcp = MCPServer("moodle-ai")

@mcp.tool()
def moodle_search_and_ask(query: str, doc_filter: Optional[str] = None, course_filter: Optional[str] = None) -> str:
    """
    Search downloaded Moodle course lecture slides, notes, handouts, and custom URL sources using Hybrid RAG (ChromaDB + BM25).
    Falls back to Wikipedia if the topic is general or out-of-scope.
    Returns the most relevant chunks with slide/page citations.
    """
    res = moodle_ask(query=query, doc_filter=doc_filter, course_filter=course_filter)
    
    output = []
    output.append(f"### Results for query: '{query}'")
    
    if res.get("has_confident_moodle_hit") and res.get("moodle_context"):
        output.append("\n#### Course Materials & Custom Sources:")
        for chunk in res["moodle_context"]:
            output.append(f"\n> **Citation**: {chunk['citation']}")
            output.append(f"```markdown\n{chunk['text']}\n```")
    elif res.get("moodle_context"):
        output.append("\n#### Partial Hits (Low Confidence):")
        for chunk in res["moodle_context"]:
            output.append(f"\n> **Citation**: {chunk['citation']}")
            output.append(f"```markdown\n{chunk['text']}\n```")

    if res.get("visual_fallback", {}).get("triggered") and res["visual_fallback"].get("rendered_pages"):
        output.append("\n#### Visual Slide Fallback (Rendered Page Images):")
        output.append("> **Note for Multimodal AI Agent**: Visual intent was detected or candidate slides contain diagrams/drawings. Inspect the rendered image(s) using your vision capabilities (e.g. `view_file`) to interpret charts, diagrams, and visual layouts for the user.")
        for vp in res["visual_fallback"]["rendered_pages"]:
            output.append(f"\n- **Slide p.{vp['page']}** ({vp['filename']}):")
            output.append(f"  - **Image File**: `{vp['image_path']}`")
            output.append(f"  - **Preview Link**: [{vp['filename']} (p.{vp['page']})]({vp['image_url']})")
            output.append(f"  - **Citation**: {vp['citation']}")

    if res.get("used_fallback") and res.get("fallback_context"):
        output.append("\n#### Wikipedia Fallback:")
        for w in res["fallback_context"]:
            output.append(f"\n> **Citation**: {w['citation']}")
            output.append(f"{w['summary']}")

    return "\n".join(output)

@mcp.tool()
def list_available_courses_and_documents(regenerate: bool = False) -> str:
    """
    Reads list.md and returns the structured document hierarchy of all downloaded courses, semesters, and custom URL sources.
    """
    res = moodle_list(regenerate=regenerate)
    return res.get("markdown_content", "No course documents found.")

@mcp.tool()
def discover_moodle_semesters_list() -> str:
    """
    Connects to Moodle and discovers all available semesters/years and courses without downloading.
    """
    res = discover_available_semesters()
    return json.dumps(res, indent=2)

@mcp.tool()
def trigger_moodle_sync(semester: Optional[str] = None) -> str:
    """
    Asynchronously scrapes Moodle and registered custom URLs, converting each file to Markdown and embedding into ChromaDB & BM25 on the fly!
    """
    res = sync_moodle(semester=semester)
    return json.dumps(res, indent=2)

@mcp.tool()
def add_custom_scrape_url(url: str, label: Optional[str] = None, auto_sync: bool = True) -> str:
    """
    Registers a custom web URL or direct PDF link to scrape PDFs from and optionally triggers immediate sync & indexing.
    """
    res = moodle_add_custom_url(url=url, label=label, auto_sync=auto_sync)
    return json.dumps(res, indent=2)

@mcp.tool()
def remove_custom_scrape_url(url_or_label: str, delete_files: bool = False) -> str:
    """
    Removes a registered custom URL. Optionally deletes downloaded files.
    """
    res = moodle_remove_custom_url(url_or_label=url_or_label, delete_files=delete_files)
    return json.dumps(res, indent=2)

@mcp.tool()
def list_custom_scrape_urls() -> str:
    """
    Lists all registered custom URLs and their sync statuses.
    """
    res = moodle_list_custom_urls()
    return json.dumps(res, indent=2)

@mcp.tool()
def change_moodle_tracked_semester(target_semester: Optional[str] = None) -> str:
    """
    Changes the default tracked semester (e.g. 2601, 2502, 2501, all) in .env and updates list.md.
    """
    res = moodle_change_sync(target_semester=target_semester)
    return json.dumps(res, indent=2)

@mcp.tool()
def generate_practice_quiz_context(course: Optional[str] = None, num_questions: int = 5) -> str:
    """
    Samples foundational concepts and summary slides from course materials to help the LLM generate a practice quiz.
    """
    res = moodle_quiz(course=course, num_questions=num_questions)
    output = [f"### Foundational Materials for Course: {res['course']}"]
    for m in res["materials"]:
        output.append(f"\n> **Source**: {m['citation']}")
        output.append(f"```markdown\n{m['text']}\n```")
    return "\n".join(output)

@mcp.tool()
def configure_moodle_credentials(user: Optional[str] = None, password: Optional[str] = None) -> str:
    """
    Configures or verifies Kerberos credentials in .env.
    """
    res = setup_moodle(user, password)
    return json.dumps(res, indent=2)

@mcp.tool()
def update_moodle_ai_repository() -> str:
    """
    Pulls the latest code updates from the GitHub repository and refreshes Python dependencies in the virtual environment.
    """
    res = update_moodle_ai()
    return json.dumps(res, indent=2)



if __name__ == "__main__":
    mcp.run()
