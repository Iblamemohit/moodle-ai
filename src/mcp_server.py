import json
import sys
from pathlib import Path
from typing import Optional
from mcp.server.mcpserver import MCPServer

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
    moodle_pyq,
    moodle_drill,
    moodle_cheatsheet,
    moodle_triage,
    get_student_profile as get_student_profile_impl,
    update_student_profile as update_student_profile_impl,
    get_next_upcoming_exam as get_next_upcoming_exam_impl,
    record_student_correction as record_student_correction_impl,
    log_drill_performance as log_drill_performance_impl,
    get_student_weaknesses as get_student_weaknesses_impl
)
from src.scraper_sync import discover_available_semesters

# Initialize MCP Server (MCP 2.x standard)
mcp = MCPServer("moodle-ai")

@mcp.tool()
def moodle_search_and_ask(query: str, doc_filter: Optional[str] = None, course_filter: Optional[str] = None) -> str:
    """Hybrid RAG search across course slides, notes, handouts, and custom URLs with dual file & markdown citations."""
    res = moodle_ask(query=query, doc_filter=doc_filter, course_filter=course_filter)
    
    output = []
    cache_tag = " [cached]" if res.get("from_cache") else ""
    output.append(f"### Results for: '{query}'{cache_tag}")

    if res.get("learned_rules"):
        output.append("\n⚠️ **Active Learned Rules & Constraints**:")
        for r in res["learned_rules"]:
            output.append(f"- {r}")

    if res.get("student_learning_style"):
        output.append(f"\n💡 *Student Learning Style*: {res['student_learning_style']}")
    
    if res.get("moodle_context"):
        for chunk in res["moodle_context"]:
            output.append(f"\n> **Source**: {chunk['citation']}")
            output.append(chunk["text"])

    if res.get("visual_fallback", {}).get("triggered") and res["visual_fallback"].get("rendered_pages"):
        output.append("\n**Visual Slides**:")
        for vp in res["visual_fallback"]["rendered_pages"]:
            output.append(f"- [{vp['filename']} (p.{vp['page']})]({vp['image_url']}) | `{vp['image_path']}`")

    if res.get("used_fallback") and res.get("fallback_context"):
        output.append("\n**Wikipedia Fallback**:")
        for w in res["fallback_context"]:
            output.append(f"\n> **Source**: {w['citation']}")
            # Dense summary excerpt
            summary = w['summary'].strip()
            if len(summary) > 400:
                summary = summary[:400].rsplit(' ', 1)[0] + "..."
            output.append(summary)

    return "\n".join(output)


@mcp.tool()
def list_available_courses_and_documents(regenerate: bool = False) -> str:
    """Returns the structured document catalog of all downloaded courses and custom sources from list.md."""
    res = moodle_list(regenerate=regenerate)
    return res.get("markdown_content", "No course documents found.")

@mcp.tool()
def discover_moodle_semesters_list() -> str:
    """Discovers available Moodle semesters, years, and enrolled courses without downloading."""
    res = discover_available_semesters()
    return json.dumps(res, indent=2)

@mcp.tool()
def trigger_moodle_sync(semester: Optional[str] = None) -> str:
    """Scrapes Moodle, custom URLs, or user_files/ and updates vector & BM25 indexes. Pass semester='user' for local files."""
    res = sync_moodle(semester=semester)
    return json.dumps(res, indent=2)

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
def generate_engineering_diagram(diagram_type: str, params: Optional[str] = None) -> str:
    """Generates 300 DPI engineering diagrams (sfd_bmd, is456_stress_block, cpm_network); returns embed link."""
    params_dict = None
    if params:
        try:
            params_dict = json.loads(params)
        except Exception:
            params_dict = None
    res = moodle_diagram(diagram_type=diagram_type, params=params_dict)
    if res.get("status") == "success":
        lines = [
            f"### {res.get('title', 'Engineering Diagram')}",
            f"![{res.get('title')}]({res.get('image_url')})",
            f"- **Image Path**: `{res.get('image_path')}`",
            f"- **Markdown Embed**: `![{res.get('title')}]({res.get('image_url')})`"
        ]
        if "critical_path" in res:
            lines.append(f"- **Critical Path**: {' -> '.join(res['critical_path'])} (Duration: {res.get('project_duration')})")
        if "max_bending_moment" in res:
            lines.append(f"- **Max Bending Moment**: {res.get('max_bending_moment')} kN·m at x = {res.get('peak_location_m')} m")
        return "\n".join(lines)
    return json.dumps(res, indent=2)


@mcp.tool()
def deconstruct_past_exam_paper(paper_pdf_path: str, course_code: str, question_num: Optional[int] = None) -> str:
    """Deconstructs past-year exam PDF into questions, slide citations, marking scheme, and variation forecasts."""
    res = moodle_pyq(paper_pdf_path=paper_pdf_path, course_code=course_code, question_num=question_num)
    if res.get("status") == "success":
        lines = [
            f"### Past-Year Paper Deconstruction: {res['course']}",
            f"- **Source Paper**: `{res['paper_file']}` ({res['paper_path']})",
            f"- **Total Questions Parsed**: {res['total_questions_parsed']}\n"
        ]
        for q in res.get("deconstructed_questions", []):
            lines.append(f"#### Question {q['question_number']}:")
            lines.append(f"> {q['question_text']}\n")
            lines.append("**Matched Course Slides & Materials**:")
            for c in q.get("matched_citations", []):
                lines.append(f"- {c}")
            lines.append("\n**IIT-Style Marking Scheme Solution Outline**:")
            for s in q.get("marking_scheme_structure", []):
                lines.append(f"{s}")
            lines.append("\n**Exam Variation Forecast (Twists & Edge Cases)**:")
            for t in q.get("exam_variation_forecast", []):
                lines.append(f"- {t}")
            lines.append("\n---\n")
        return "\n".join(lines)
    return json.dumps(res, indent=2)


@mcp.tool()
def socratic_problem_drill(course: str, topic: str, current_step: int = 1, user_answer: Optional[str] = None) -> str:
    """Guides student through interactive calculation drills step-by-step with checkpoint validation."""
    res = moodle_drill(course=course, topic=topic, current_step=current_step, user_answer=user_answer)
    lines = [
        f"### Socratic Problem Drill: {res['drill_topic']} ({res['course']})",
        f"**Problem Statement**:\n{res['problem_statement']}\n"
    ]
    if res.get("feedback"):
        lines.append(f"**Evaluation Feedback**:\n{res['feedback']}\n")
    lines.append(res["prompt"])
    lines.append(f"\n*Next step index to submit: `{res['next_step']}`*")
    return "\n".join(lines)


@mcp.tool()
def generate_course_cheatsheet(course_code: str) -> str:
    """Compiles formula, parameter, and IS code cheat sheet saved to output/cheatsheets/<course>_cheatsheet.md."""
    res = moodle_cheatsheet(course_code=course_code)
    if res.get("status") == "success":
        return f"Saved cheat sheet to: [{res['title']}]({res['file_url']}) (`{res['file_path']}`)\n\n" + res["markdown_content"]
    return json.dumps(res, indent=2)


@mcp.tool()
def triage_course_exam_prep(course_code: str) -> str:
    """Prioritizes course topics into Tier 1/2/3 with a 2-hour night-before study checklist."""
    res = moodle_triage(course_code=course_code)
    if res.get("status") == "success":
        lines = [
            f"### High-Yield Exam Triage: {res['course']}",
            "\n🔥 **Tier 1: Guaranteed 60% Weightage (Must-Master Calculations & Theorems)**:"
        ]
        for t in res.get("tier1_high_weightage", []):
            lines.append(f"- [x] {t}")
        lines.append("\n⚡ **Tier 2: High Yield per Hour (Definitions, Mechanisms & Standard Rules)**:")
        for t in res.get("tier2_high_yield", []):
            lines.append(f"- [ ] {t}")
        lines.append("\n⛔ **Tier 3: Low Priority / Skip Unless Aiming for 10/10**:")
        for t in res.get("tier3_low_priority", []):
            lines.append(f"- {t}")
        lines.append("\n⏱️ **2-Hour Night-Before Study Checklist**:")
        for item in res.get("two_hour_study_checklist", []):
            lines.append(f"- ⏱️ **{item['time_min']} mins**: {item['action']}")
        return "\n".join(lines)
    return json.dumps(res, indent=2)


@mcp.tool()
def get_student_profile() -> str:
    """Returns active semester, upcoming exam countdowns, and study focus areas from memory.md."""
    res = get_student_profile_impl()
    return json.dumps(res, indent=2)


@mcp.tool()
def update_student_profile(section: str, update_text: str) -> str:
    """Updates schedule changes, test scores, or study preferences in memory.md."""
    res = update_student_profile_impl(section=section, update_text=update_text)
    return json.dumps(res, indent=2)


@mcp.tool()
def get_next_upcoming_exam() -> str:
    """Returns course code, date, syllabus, and countdown for the immediate next exam."""
    res = get_next_upcoming_exam_impl()
    return json.dumps(res, indent=2)


@mcp.tool()
def record_student_correction(course: str, topic: str, correction: str, reason: str = "") -> str:
    """Logs professor-specific rules or corrections into learned_rules.json to prevent repeated mistakes."""
    res = record_student_correction_impl(course=course, topic=topic, correction=correction, reason=reason)
    return json.dumps(res, indent=2)


@mcp.tool()
def log_drill_performance(course: str, topic: str, is_correct: bool, mistake_notes: Optional[str] = None) -> str:
    """Updates concept mastery scores and logs mistake summaries in mastery_tracker.json."""
    res = log_drill_performance_impl(course=course, topic=topic, is_correct=is_correct, mistake_notes=mistake_notes)
    return json.dumps(res, indent=2)


@mcp.tool()
def get_student_weaknesses(course: str) -> str:
    """Returns top weakest topics and recent mistake history for a course to guide targeted revision."""
    res = get_student_weaknesses_impl(course=course)
    return json.dumps(res, indent=2)


if __name__ == "__main__":
    mcp.run()
