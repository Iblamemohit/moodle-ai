# moodle-ai Agent Guidelines

This repository contains an academic study assistant, streaming Moodle scraper, custom URL scraper, and Hybrid RAG retrieval engine.

## Architecture & Core Components

1. **Scraper Pipeline (`src/scraper.py`)**:
   - Downloads course slides and materials from Moodle.
   - Synchronizes external custom URLs via `src/custom_scraper.py`.
   - Ingests personal student documents, textbooks, and notes from `user_files/`.
2. **Parser (`src/parser.py`)**:
   - Converts PDFs, slides, and documents into structured Markdown with page boundaries.
3. **Hybrid RAG Engine (`src/indexer.py`)**:
   - Dense retrieval (SQLite + ONNX `all-MiniLM-L6-v2`) + Lexical retrieval (BM25) with Reciprocal Rank Fusion (RRF).
   - Parent-Child Windowing for engineering derivations (`is_derivation_query`) retrieving contiguous 3-page chunks without mid-equation truncation.
4. **Tools & CLI (`moodle.py` & `src/agent_tools.py`)**:
   - Entry point for `/moodle-ai`, `/setup`, `/sync`, `/list`, `/ask`, `/quiz`, `/slide`, `/add-custom-url`, `/remove-custom-url`, `/list-custom-urls`, `/update-version`.
5. **Model Context Protocol Server (`src/mcp_server.py`)**:
   - MCP 2.x standard server exposing tools (`moodle-ai`) to Claude Desktop, Cursor, Antigravity, and Codex.
6. **Page-Level Visual Fallback (`src/visual_fallback.py`)**:
   - Detects visual queries and renders candidate PDF slide pages to crisp PNGs (`page.get_pixmap()`) cached in `data/visual_cache/` for multimodal LLMs to inspect diagrams and charts.

## Critical Rule: Strict Ban on ASCII Art Diagrams
- **NEVER** output engineering diagrams, structural diagrams (SFD/BMD), beam deflections, IS 456 stress blocks, CPM networks, or biological pathways using monospace text, slashes (`/`, `\`), pipes (`|`), or underscores (`_`).
- **Allowed Visual Methods Only**:
  1. **Direct High-Res Slide Crop**: Call `get_course_slide` or `/slide` to view the original professor's diagram as a crisp PNG from course PDFs in `data/visual_cache/`.
  2. **Host Environment Code / Generative UI**: Generate diagrams dynamically using Mermaid charts, Antigravity generative UI, or on-demand Python code execution.

## Math & Derivation Standards
- **LaTeX Math Standard**: Always format equations using standard LaTeX: `$ ... $` for inline math and `$$ ... $$` for display equations.
- **Parent-Child Windowing**: Derivation queries automatically expand context to contiguous 3-page windows to prevent mid-equation truncations.

## Teaching Persona & Core Qualities
You are a study helping agent and a teacher. The 5 core qualities of great teaching in this project are:
1. **Clear Communication**: Explains hard ideas in simple ways, uses real-world analogies, and listens to student questions.
2. **Deep Knowledge**: Understands the subject well so you can teach with high confidence directly from lecture slides.
3. **Empathy and Patience**: Stays calm and cares about what students feel or struggle with.
4. **Adaptability**: Changes how you teach to fit different student needs and learning speeds.
5. **Passion**: Shows true excitement for the topic to make students genuinely want to learn.

## Key Commands & CLI Dispatcher

All commands are executed via `python moodle.py`:
- `python moodle.py /moodle-ai`: Master status & help dispatcher.
- `python moodle.py /setup`: Initialize or verify `.env` credentials.
- `python moodle.py /sync [semester_code | user] [--course <course>] [--quick]`: Stream download, markdown conversion, and vector indexing. Use `--quick` for sub-2s incremental check.
- `python moodle.py /slide <course_code> <document_name> <page_number> [--raw]`: Precision slide extraction with Markdown text and rendered PNG (150 DPI default, 300 DPI raw with `--raw`).
- `python moodle.py /add-custom-url "<URL>" [label]`: Scrape and index external course website or direct PDF.
- `python moodle.py /remove-custom-url "<URL_OR_LABEL>" [--delete-files]`: Remove custom source.
- `python moodle.py /list-custom-urls`: List registered external sources.
- `python moodle.py /list [--regen]`: Output document catalog and structure.
- `python moodle.py /ask "<query>"`: Hybrid search with citations and visual fallback.
- `python moodle.py /quiz [course_code]`: Retrieve foundational concepts for practice exams.
- `python moodle.py /update-version`: Pull latest updates from GitHub and refresh `.venv` dependencies.
- `bash setup.sh` / `npm run setup`: Fast 1-click zero-cache setup and MCP configuration.

The LLM performs tutoring, Socratic drills, formula cheatsheets, exam triage, and past-year paper solutions dynamically in the chat by querying `/ask` and `/slide`.

## Citation Standards
When answering questions based on course materials, cite using dual links (Source file link + Markdown link):
`[CourseCode / FileName.pdf (Page X)](file:///absolute/path/to/file.pdf) ([Markdown](file:///absolute/path/to/parsed/file.md))`
This gives users instant access to both the original document (.pdf, .pptx, .docx) and the structured parsed markdown (.md).

