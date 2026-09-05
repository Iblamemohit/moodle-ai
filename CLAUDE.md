# CLAUDE.md — Moodle AI Instructions

## Quick Start
- Run universal setup: `python install.py` (or `./install.sh`)
- Master command: `python agent_tools.py /moodle-ai`
- Run MCP server: `python mcp_server.py`

## Commands
- `/moodle-ai`: Master status and interactive command router.
- `/setup`: Setup `.env` Kerberos credentials safely without asking passwords in chat.
- `/sync [semester]`: Sync Moodle courses and custom URLs into local ChromaDB + BM25 index.
- `/add-custom-url <url> [label]`: Register and auto-index external web URLs or direct PDFs.
- `/remove-custom-url <url_or_label>`: Remove registered custom URL.
- `/list-custom-urls`: List registered custom URLs.
- `/list`: Display all courses and indexed documents from `list.md`.
- `/ask <question>`: Hybrid search course knowledge base with slide citations.
- `/quiz [course]`: Generate practice quiz context.

- `/install`: Universal 1-click installer.

## Citations
Format citations using dual links: `[Course / File.pdf (Page X)](file:///absolute/path/to/file.pdf) ([Markdown](file:///absolute/path/to/parsed/file.md))`.

