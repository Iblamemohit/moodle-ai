# CLAUDE.md — Moodle Study Agent Instructions

## Quick Start
- Run universal setup: `python install.py` (or `./install.sh`)
- Run CLI tools: `.venv/bin/python agent_tools.py <command>`
- Run MCP server: `.venv/bin/python mcp_server.py`

## Commands
- `/setup`: Setup `.env` Kerberos credentials safely without asking passwords in chat.
- `/sync [semester]`: Sync Moodle courses and custom URLs into local ChromaDB + BM25 index.
- `/add-custom-url <url> [label]`: Register and auto-index external web URLs or direct PDFs.
- `/remove-custom-url <url_or_label>`: Remove registered custom URL.
- `/list-custom-urls`: List registered custom URLs.
- `/list`: Display all courses and indexed documents from `list.md`.
- `/ask <question>`: Hybrid search course knowledge base with slide citations.
- `/quiz [course]`: Generate practice quiz context.
- `/open <file_or_query> [page]`: Launch PDF in macOS Preview.

## Citations
Format citations as `[Course / File.pdf (Page X)](open-preview:///absolute/path/to/output/.../File.pdf#page=X)`.
