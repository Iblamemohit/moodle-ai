# 🎓 moodle-ai Agent Guidelines

This repository contains an academic study assistant, streaming Moodle scraper, custom URL scraper, and Hybrid RAG retrieval engine.

## 🛠️ Architecture & Core Components

1. **Scraper Pipeline (`scraper.py` & `src/scraper_sync.py`)**:
   - Downloads course slides and materials from Moodle.
   - Synchronizes external custom URLs via `src/custom_scraper.py`.
2. **Parser (`src/parser.py`)**:
   - Converts PDFs, slides, and documents into structured Markdown with page boundaries.
3. **Hybrid RAG Engine (`src/indexer.py`)**:
   - Dense retrieval (ChromaDB `all-MiniLM-L6-v2`) + Lexical retrieval (BM25) with Reciprocal Rank Fusion (RRF).
4. **Tools & CLI (`agent_tools.py`)**:
   - Entry point for `/moodle-ai`, `/setup`, `/sync`, `/list`, `/ask`, `/quiz`, `/open`, `/add-custom-url`, `/remove-custom-url`, `/list-custom-urls`, `/install`.
5. **Model Context Protocol Server (`mcp_server.py`)**:
   - MCP 2.x standard server exposing tools (`moodle-ai`) to Claude Desktop, Cursor, Antigravity, and Codex.

## ⚡ Key Commands & CLI Dispatcher

All commands are executed via `.venv/bin/python agent_tools.py`:
- `python agent_tools.py /moodle-ai`: Master status & help dispatcher.
- `python agent_tools.py /setup`: Initialize or verify `.env` credentials.
- `python agent_tools.py /sync [semester_code]`: Stream download, markdown conversion, and vector indexing.
- `python agent_tools.py /add-custom-url "<URL>" [label]`: Scrape and index external course website or direct PDF.
- `python agent_tools.py /remove-custom-url "<URL_OR_LABEL>" [--delete-files]`: Remove custom source.
- `python agent_tools.py /list-custom-urls`: List registered external sources.
- `python agent_tools.py /list`: Output document catalog and structure.
- `python agent_tools.py /ask "<query>"`: Hybrid search with Preview citations and Wikipedia fallback.
- `python agent_tools.py /quiz [course_code]`: Retrieve foundational concepts for practice exams.
- `python agent_tools.py /open "<path_or_query>" [page]`: Launch PDF at page in macOS Preview.
- `python install.py`: Universal 1-click auto-configuration.

## 🎯 Citation Standards
When answering questions based on course materials, cite using dual links (Source file link + Markdown link):
`[CourseCode / FileName.pdf (Page X)](file:///absolute/path/to/file.pdf) ([Markdown](file:///absolute/path/to/parsed/file.md))`
This gives users instant access to both the original document (.pdf, .pptx, .docx) and the structured parsed markdown (.md).

