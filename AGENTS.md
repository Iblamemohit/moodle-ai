# moodle-ai Agent Guidelines

This repository contains an academic study assistant, streaming Moodle scraper, custom URL scraper, and Hybrid RAG retrieval engine.

## Architecture & Core Components

1. **Scraper Pipeline (`scraper.py` & `src/scraper_sync.py`)**:
   - Downloads course slides and materials from Moodle.
   - Synchronizes external custom URLs via `src/custom_scraper.py`.
   - Ingests personal student documents, textbooks, and notes from `user_files/`.
2. **Parser (`src/parser.py`)**:
   - Converts PDFs, slides, and documents into structured Markdown with page boundaries.
3. **Hybrid RAG Engine (`src/indexer.py`)**:
   - Dense retrieval (SQLite + ONNX `all-MiniLM-L6-v2`) + Lexical retrieval (BM25) with Reciprocal Rank Fusion (RRF).
   - Parent-Child Windowing for engineering derivations (`is_derivation_query`) retrieving contiguous 3-page chunks without mid-equation truncation.
4. **Diagram Generator (`src/diagram_generator.py`)**:
   - Generates publication-grade 300 DPI engineering diagrams for SFD/BMD, IS 456 stress blocks, and CPM AON networks.
5. **Tools & CLI (`moodle.py` & `src/agent_tools.py`)**:
   - Entry point for `/moodle-ai`, `/setup`, `/sync`, `/list`, `/ask`, `/quiz`, `/diagram`, `/pyq`, `/drill`, `/cheatsheet`, `/triage`, `/add-custom-url`, `/remove-custom-url`, `/list-custom-urls`, `/update-version`, `/install`.
6. **Model Context Protocol Server (`src/mcp_server.py`)**:
   - MCP 2.x standard server exposing tools (`moodle-ai`) to Claude Desktop, Cursor, Antigravity, and Codex.
7. **Page-Level Visual Fallback (`src/visual_fallback.py`)**:
   - Detects visual queries and renders candidate PDF slide pages to crisp PNGs (`page.get_pixmap()`) cached in `data/visual_cache/` for multimodal LLMs to inspect diagrams and charts.
8. **Native Memory Engine (`src/memory_manager.py`)**:
   - Programmatically tracks academic profile, upcoming exam schedules, course diagnostics, and learning preferences in `memory.md`.
9. **Self-Learning Engine (`src/self_learner.py`)**:
   - Continuous feedback system tracking concept mastery, logging student corrections (`data/learned_rules.json`), and boosting retrieval.

## Critical Rule: Strict Ban on ASCII Art Diagrams
- **NEVER** output engineering diagrams, structural diagrams (SFD/BMD), beam deflections, IS 456 stress blocks, CPM networks, or biological pathways using monospace text, slashes (`/`, `\`), pipes (`|`), or underscores (`_`).
- **Allowed Visual Methods Only**:
  1. **Direct High-Res Slide Crop**: Use PyMuPDF to extract and crop diagram regions or pages directly from course PDFs as crisp PNGs into `data/visual_cache/`.
  2. **Programmatic Diagram Generator (`src/diagram_generator.py` / `/diagram`)**: Render publication-grade 300 DPI PNGs saved to `output/diagrams/` and embed them as `![Title](file:///path/to/img.png)`.
  3. **Native Mermaid**: For flowcharts and simple logic diagrams.

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
- `python moodle.py /sync [semester_code | user]`: Stream download, markdown conversion, and vector indexing. Use `/sync user` to index only local `user_files/`.
- `python moodle.py /add-custom-url "<URL>" [label]`: Scrape and index external course website or direct PDF.
- `python moodle.py /remove-custom-url "<URL_OR_LABEL>" [--delete-files]`: Remove custom source.
- `python moodle.py /list-custom-urls`: List registered external sources.
- `python moodle.py /list [--regen]`: Output document catalog and structure.
- `python moodle.py /ask "<query>"`: Hybrid search with citations and Wikipedia fallback.
- `python moodle.py /quiz [course_code]`: Retrieve foundational concepts for practice exams.
- `python moodle.py /diagram <type> [params_json]`: Generate publication-grade 300 DPI diagram (`sfd_bmd`, `is456_stress_block`, `cpm_network`).
- `python moodle.py /pyq <paper_pdf_path> <course_code> [question_num]`: Past-year exam paper deconstruction with slide citations, IIT-style marking scheme, and exam variation forecasts.
- `python moodle.py /drill <course> <topic> [--step N] [--answer "<ans>"]`: Interactive Socratic problem solver with checkpoint calculation validation.
- `python moodle.py /cheatsheet <course_code>`: Compile formula, SI units, and IS code provision cheat sheet to `output/cheatsheets/<course>_cheatsheet.md`.
- `python moodle.py /triage <course_code>`: High-yield course triage (Tier 1/2/3) with a 2-hour night-before study checklist.
- `python moodle.py /update-version`: Pull latest updates from GitHub and refresh `.venv` dependencies.
- `python install.py`: Universal 1-click auto-configuration.

## Citation Standards
When answering questions based on course materials, cite using dual links (Source file link + Markdown link):
`[CourseCode / FileName.pdf (Page X)](file:///absolute/path/to/file.pdf) ([Markdown](file:///absolute/path/to/parsed/file.md))`
This gives users instant access to both the original document (.pdf, .pptx, .docx) and the structured parsed markdown (.md).

