# moodle-ai

A privacy-first, offline-capable AI Study Agent, Streaming Moodle Scraper, Custom URL Scraper, and Knowledge Retrieval Engine for university course materials.

It downloads course slides, external course webpages, and PDFs, converts them into structured Markdown, indexes them into a local **Hybrid Vector + Keyword Search engine (ChromaDB + BM25)**, and works out-of-the-box in **Antigravity**, **Claude (Desktop & Code)**, **Cursor**, **Codex / VS Code**, **Windsurf**, and the command line.

---

## 1-Command Universal Installation

Run one single command from inside the repository folder, and everything (virtual environment, dependencies, `.env` template, and MCP server registrations across all your IDEs) will be automatically installed and configured:

```bash
# Option A: Python Installer
python3 install.py

# Option B: Shell Script
./install.sh

# Option C: CLI Tool
python3 agent_tools.py /install
```

---

## Supported IDEs & Zero-Config Setup

| Environment | Setup Method | What Works |
| :--- | :--- | :--- |
| **Antigravity IDE** | Open folder or run `/moodle-ai` | Auto-detects `.agents/skills/` & MCP tools |
| **Claude Desktop** | Pre-configured by `install.py` | Full MCP tools (`moodle-ai`) |
| **Cursor** | Open project folder (`.cursor/mcp.json`) | Native MCP server ready on project open |
| **VS Code / Codex** | Open project folder (`.vscode/mcp.json`) | Native MCP server ready on project open |
| **Windsurf** | Pre-configured by `install.py` | Global MCP server registration |
| **Terminal / CLI** | Run `python agent_tools.py <command>` | Direct interactive CLI dispatcher |

---

## Workflows & Commands

### 1. Master Command
```bash
python agent_tools.py /moodle-ai
```

### 2. Initial Setup
Enter your IIT Delhi Kerberos ID and password securely into the generated `.env` file (passwords are never typed in LLM chat prompts):
```bash
python agent_tools.py /setup
```

### 3. Syncing Course Materials, Custom URLs & Personal PDFs
```bash
# Sync active semester + custom URLs + local user_files/
python agent_tools.py /sync

# Sync only local user_files/ (fast, offline)
python agent_tools.py /sync user

# Sync a specific semester
python agent_tools.py /sync 2601

# Sync only custom external URLs
python agent_tools.py /sync custom
```

### 4. Adding Your Own PDFs & Notes (`user_files/`)
Drop your own lecture slides, notes, assignments, problem sets, or textbooks (`.pdf`, `.pptx`, `.docx`, `.txt`, `.md`) directly into `user_files/`:
- Put files directly in `user_files/` (categorized under `General`)
- Or organize by course/topic subfolders (e.g. `user_files/COL106/Data_Structures.pdf`)

Run `python agent_tools.py /sync user` (or `/sync user` in chat) to instantly parse and index them!

### 5. Adding External Custom Webpages & PDFs
Add arbitrary external URLs (course homepages, professor notes, syllabus links, public PDFs):
```bash
python agent_tools.py /add-custom-url "https://example.com/notes.pdf" "Extra_Notes"
```

### 5. Asking Questions with Direct PDF Citations
```bash
python agent_tools.py /ask "What is total float in CPM?"
```
Every citation is formatted with dual clickable links for instant access to the source file and parsed markdown notes.

### 6. Managing Custom URLs
```bash
# List all registered external sources
python agent_tools.py /list-custom-urls

# Remove a custom URL and optionally delete its files
python agent_tools.py /remove-custom-url "Extra_Notes" --delete-files
```

### 7. Practice Exams & Quizzes
```bash
python agent_tools.py /quiz "2601-CVL245A"
```

### 8. 1-Click Updates
Pull the latest improvements and refresh virtual environment dependencies without touching your local `.env` or downloaded slides:
```bash
python agent_tools.py /update-version
```

---

## Project Architecture

```text
moodle-ai/
├── install.py                 # Universal 1-click installer & auto-configurator
├── install.sh                 # Executable setup shell script
├── AGENTS.md                  # Universal agent directives & architecture
├── CLAUDE.md                  # Claude Code & Desktop instructions
├── .cursor/mcp.json           # Native Cursor MCP config
├── .vscode/mcp.json           # Native VS Code & Codex MCP config
├── .agents/skills/            # 10 modular Antigravity custom skills
│   ├── moodle-ai/             # Master AI tutor skill
│   ├── moodle-sync/           # Streaming sync skill
│   ├── moodle-add-custom-url/ # Custom URL scraper skill
│   ├── moodle-remove-custom-url/
│   ├── moodle-ask/            # Hybrid RAG search skill
│   ├── moodle-quiz/           # Practice quiz skill
│   ├── moodle-list/           # Document catalog skill
│   ├── moodle-change-sync/    # Semester switch skill
│   ├── moodle-setup/          # Secure credential setup skill
│   └── moodle-update-version/ # 1-click auto-updater skill
├── .claude/skills/            # Claude Code native skills
├── agent_tools.py             # CLI dispatcher & high-level RAG tools
├── mcp_server.py              # Official MCP standard server (moodle-ai)
├── user_files/                # Dedicated folder for user's personal PDFs and notes
└── src/
    ├── config.py              # Environment configuration loader
    ├── custom_scraper.py      # Custom URL scraper & source manager
    ├── parser.py              # PyMuPDF4LLM Markdown parser with SHA-256 caching
    ├── embeddings.py          # Standalone ONNX runtime all-MiniLM-L6-v2 embeddings
    ├── indexer.py             # SQLite + BM25 Hybrid Retriever with RRF
    ├── visual_fallback.py     # Multimodal PDF slide diagram renderer
    ├── scraper_sync.py        # Moodle & Custom URL live indexing coordinator
    ├── list_manager.py        # Document hierarchy link indexer
    └── web_search.py          # Wikipedia REST fallback retrieval
```

