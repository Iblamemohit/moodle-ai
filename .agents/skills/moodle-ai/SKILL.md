---
name: moodle-ai
description: Master AI Study Agent & Tutor (moodle-ai) that orchestrates Moodle setup, syncing, custom URL scraping, document exploration, hybrid RAG questioning, multimodal slide inspection, formula cheatsheets, exam triage, and practice quizzes across university courses.
---

# Moodle AI (Master Tutor Skill)

## When to use this skill
Activate this skill whenever the user calls `/moodle-ai`, asks questions about university course materials or slides, wants exam preparation (cheatsheets, triage, past-year papers, drills, practice quizzes), needs Moodle synchronization, or wants to inspect slide diagrams.

## Architecture & Integration with Agent Runetimes
`moodle-ai` acts as the **grounding and visual engine** for agent harnesses (Antigravity, Claude Code, OpenAI Codex, Cursor).
- **Engine Responsibilities (Python)**: Intranet Kerberos authentication, course slide scraping, PDF-to-Markdown parsing, local Hybrid RAG (SQLite BM25 + ONNX Dense + RRF), slide PNG rendering (150/300 DPI), and publication-grade engineering diagrams.
- **Harness Responsibilities (LLM)**: Socratic dialogue, conceptual explanations, step-by-step mathematical problem solving, exam triage synthesis, and creative question generation.

## Available Tools & CLI Commands

All commands are executed non-interactively via `python moodle.py` or through the standard MCP server (`moodle-ai`):

| Action | CLI Command | MCP Tool Equivalent | Description |
| :--- | :--- | :--- | :--- |
| **Search & Ask** | `python moodle.py /ask "<query>"` | `moodle_search_and_ask` | Hybrid search with dual file citations and visual fallback. |
| **Inspect Slide** | `python moodle.py /slide <course> <doc> <page> [--raw]` | `get_course_slide` | Extracts slide text and rendered PNG (150 DPI default, 300 DPI raw with `--raw`). |
| **Course Catalog** | `python moodle.py /list [--regen]` | `list_available_courses_and_documents` | Structured catalog of downloaded courses and files from `list.md`. |
| **Sync Moodle** | `python moodle.py /sync [semester] [--quick]` | `trigger_moodle_sync` | Downloads and indexes course slides. Use `--quick` for sub-2s incremental sync. |
| **Practice Quiz** | `python moodle.py /quiz [course_code]` | `generate_practice_quiz_context` | Samples high-density concept slides for practice exam questions. |
| **Diagrams** | `python moodle.py /diagram <type> [json_params]` | `generate_engineering_diagram` | Generates 300 DPI vector diagrams (`sfd_bmd`, `is456_stress_block`, `cpm_network`). |
| **Add Custom URL** | `python moodle.py /add-custom-url "<url>" [label]` | `add_custom_scrape_url` | Scrapes and indexes external course website or direct PDF. |
| **Remove Custom URL**| `python moodle.py /remove-custom-url "<url_or_label>"` | `remove_custom_scrape_url` | Removes custom source from registry. |
| **Setup & Env** | `python moodle.py /setup` | `configure_moodle_credentials` | Configures or verifies Kerberos credentials in `.env`. |

### Dynamic LLM-Powered Study Capabilities
Rather than rigid Python scripts, the LLM generates the following on-demand using retrieved course context (`moodle_search_and_ask` + `get_course_slide`):
- **Formula & Code Provision Cheat Sheets**: Retrieve course principles and format clean LaTeX cheat sheets with SI units.
- **High-Yield Exam Triage**: Extract syllabus topics into Tier 1 (computational/theorems), Tier 2 (mechanisms), and Tier 3 (intros), along with custom night-before checklists.
- **Socratic Problem Drills**: Guide the student step-by-step through calculations, checking intermediate numbers before revealing answers.
- **Past-Year Exam Solutions (PYQs)**: Solve paper problems step-by-step, cross-referencing lecture slide theorems and providing IIT-style marking schemes.

## Critical Rules & Standards

### 1. Strict Ban on ASCII Art Diagrams
- **NEVER** output engineering diagrams, structural diagrams (SFD/BMD), beam deflections, IS 456 stress blocks, or CPM networks using monospace text, slashes (`/`, `\`), pipes (`|`), or underscores (`_`).
- **Allowed Visual Methods**:
  1. **Direct Slide Crop**: Call `get_course_slide` or `/slide` to view the original professor's diagram as a crisp PNG.
  2. **Programmatic Diagram Generator**: Call `moodle_diagram` / `generate_engineering_diagram` for publication-grade 300 DPI PNGs saved to `output/diagrams/` and embedded as `![Title](file:///path/to/img.png)`.
  3. **Native Mermaid**: For flowcharts and simple logic graphs.

### 2. Dual Citation Standards
When citing course materials, cite using dual links (Source file link + Markdown link):
`[CourseCode / FileName.pdf (Page X)](file:///absolute/path/to/file.pdf) ([Markdown](file:///absolute/path/to/parsed/file.md))`
This gives users instant access to both the original document (.pdf, .pptx, .docx) and the structured parsed markdown (.md).

### 3. LaTeX Math Standard
Always format equations using standard LaTeX:
- Inline equations: `$ ... $`
- Display / Block equations: `$$ ... $$`
