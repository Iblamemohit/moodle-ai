# 🎓 moodle-study-agent

A privacy-first, offline-capable AI Study Agent, Scraper, and Knowledge Engine for Moodle course materials and external custom PDF resources.

It downloads course slides and custom URLs, converts them to Markdown, indexes them into a local **Hybrid Vector + Keyword Search engine (ChromaDB + BM25)**, opens lecture PDFs directly in **macOS Preview** at cited pages, and provides native tool integration for **Antigravity IDE**, **Claude Desktop**, and the command line.

---

## 🚀 Features

- **Automated Moodle Scraper**: Multi-instance concurrent downloads with captcha solving and clean, organized folder hierarchies.
- **Custom URL Scraper & Sync**: Add arbitrary external course websites, professor pages, or direct PDF links to scrape, parse, and synchronize into your RAG knowledge base.
- **Deep Markdown Parsing**: Uses `PyMuPDF4LLM` to convert lecture slides into structured Markdown preserving equations, page numbers, and slide titles.
- **Hybrid RAG Retrieval**: Combines **ChromaDB** (`all-MiniLM-L6-v2`) with **BM25 Lexical Keyword Search** using **Reciprocal Rank Fusion (RRF)** for pinpoint accuracy.
- **Native Preview Citations**: Cites slides with `open-preview://` links that open the exact PDF page directly in macOS Preview.
- **Wikipedia Fallback**: Automatically queries Wikipedia if a question is out-of-scope of course materials.
- **Universal Deployment**: Runs natively as an **Antigravity Custom Skill** and as a standard **Model Context Protocol (MCP) Server** for Claude Desktop, Cursor, and Cline.

---

## 🛠️ Quick Installation

```bash
# 1. Clone & create virtual environment
git clone https://github.com/<your-username>/moodle-study-agent.git
cd moodle-study-agent
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

---

## ⚡ Deployment & Workflows

### Option 1: Antigravity IDE (Native Skills)
The custom skills are globally registered in `~/.gemini/config/skills/`:
- `/moodle-study-agent`: Master academic AI tutor.
- `/moodle-sync`: Streaming scraper and indexer.
- `/moodle-add-custom-url`: Scrapes external URLs or direct PDFs into RAG.
- `/moodle-remove-custom-url`: Removes custom URL sources.
- `/moodle-list`: Document index and catalog.
- `/moodle-ask`: Academic hybrid Q&A with deep citations.
- `/moodle-quiz`: Interactive practice quiz generator.

---

### Option 2: Claude Desktop (MCP Server)
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "moodle-study-agent": {
      "command": "/absolute/path/to/moodle-study-tool/.venv/bin/python",
      "args": [
        "/absolute/path/to/moodle-study-tool/mcp_server.py"
      ]
    }
  }
}
```
Restart Claude Desktop, and Claude will automatically gain access to:
- `moodle_search_and_ask`: Queries course slides and custom URLs with page citations.
- `list_available_courses_and_documents`: Lists all indexed files.
- `trigger_moodle_sync`: Downloads new files from Moodle and custom URLs.
- `add_custom_scrape_url` & `remove_custom_scrape_url`: Manages custom PDF web sources.
- `generate_practice_quiz_context`: Generates custom quizzes.
- `open_course_pdf_in_preview`: Launches PDF slides in Preview.

---

### Option 3: Terminal / CLI Mode
You can interact with the assistant directly in your terminal:

```bash
# 1. Setup credentials
python agent_tools.py /setup

# 2. Add external custom URLs or direct PDFs
python agent_tools.py /add-custom-url "https://example.com/notes.pdf" "Extra_Notes"

# 3. Sync and index course materials + custom URLs
python agent_tools.py /sync

# 4. List all downloaded courses & files
python agent_tools.py /list

# 5. Ask a question (with Preview slide citations)
python agent_tools.py /ask "What is total float in CPM?"

# 6. Remove a custom URL
python agent_tools.py /remove-custom-url "Extra_Notes" --delete-files

# 7. Generate a practice quiz
python agent_tools.py /quiz "2601-CVL245A"
```

---

## 📂 Project Architecture

```text
moodle-study-agent/
├── .env                       # Stored Kerberos credentials & storage paths (git ignored)
├── requirements.txt           # chromadb, pymupdf4llm, rank_bm25, mcp, bs4, requests
├── agent_tools.py             # CLI dispatcher & high-level RAG / Preview tools
├── mcp_server.py              # Official MCP standard server (for Claude/Cursor)
├── mcp_config_snippet.json    # Ready-to-copy MCP config snippet
└── src/
    ├── config.py              # Environment configuration loader
    ├── custom_scraper.py      # Custom URL scraper & source manager
    ├── parser.py              # PyMuPDF4LLM Markdown parser with SHA-256 caching
    ├── indexer.py             # ChromaDB + BM25 Hybrid Retriever with RRF
    ├── scraper_sync.py        # Moodle & Custom URL live indexing coordinator
    ├── list_manager.py        # Document hierarchy & Preview link indexer
    └── web_search.py          # Wikipedia REST fallback retrieval
```
