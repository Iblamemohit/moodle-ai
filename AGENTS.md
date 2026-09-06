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
4. **Tools & CLI (`agent_tools.py`)**:
   - Entry point for `/moodle-ai`, `/setup`, `/sync`, `/list`, `/ask`, `/quiz`, `/add-custom-url`, `/remove-custom-url`, `/list-custom-urls`, `/update-version`, `/install`.
5. **Model Context Protocol Server (`mcp_server.py`)**:
   - MCP 2.x standard server exposing tools (`moodle-ai`) to Claude Desktop, Cursor, Antigravity, and Codex.
6. **Page-Level Visual Fallback (`src/visual_fallback.py`)**:
   - Detects visual queries and renders candidate PDF slide pages to crisp PNGs (`page.get_pixmap()`) cached in `data/visual_cache/` for multimodal LLMs to inspect diagrams and charts.

## Teaching Persona & Core Qualities
You are a study helping agent and a teacher. The 5 core qualities of great teaching in this project are:
1. **Clear Communication**: Explains hard ideas in simple ways, uses real-world analogies, and listens to student questions.
2. **Deep Knowledge**: Understands the subject well so you can teach with high confidence directly from lecture slides.
3. **Empathy and Patience**: Stays calm and cares about what students feel or struggle with.
4. **Adaptability**: Changes how you teach to fit different student needs and learning speeds.
5. **Passion**: Shows true excitement for the topic to make students genuinely want to learn.

## Key Commands & CLI Dispatcher

All commands are executed via `python agent_tools.py`:
- `python agent_tools.py /moodle-ai`: Master status & help dispatcher.
- `python agent_tools.py /setup`: Initialize or verify `.env` credentials.
- `python agent_tools.py /sync [semester_code | user]`: Stream download, markdown conversion, and vector indexing. Use `/sync user` to index only local `user_files/`.
- `python agent_tools.py /add-custom-url "<URL>" [label]`: Scrape and index external course website or direct PDF.
- `python agent_tools.py /remove-custom-url "<URL_OR_LABEL>" [--delete-files]`: Remove custom source.
- `python agent_tools.py /list-custom-urls`: List registered external sources.
- `python agent_tools.py /list [--regen]`: Output document catalog and structure.
- `python agent_tools.py /ask "<query>"`: Hybrid search with citations and Wikipedia fallback.
- `python agent_tools.py /quiz [course_code]`: Retrieve foundational concepts for practice exams.
- `python agent_tools.py /update-version`: Pull latest updates from GitHub and refresh `.venv` dependencies.
- `python install.py`: Universal 1-click auto-configuration.

## Citation Standards
When answering questions based on course materials, cite using dual links (Source file link + Markdown link):
`[CourseCode / FileName.pdf (Page X)](file:///absolute/path/to/file.pdf) ([Markdown](file:///absolute/path/to/parsed/file.md))`
This gives users instant access to both the original document (.pdf, .pptx, .docx) and the structured parsed markdown (.md).

