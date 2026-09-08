# moodle-ai

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Protocol-MCP%202.x-8A2BE2" alt="Model Context Protocol" />
  <img src="https://img.shields.io/badge/Retrieval-Hybrid%20RAG%20(Dense%20%2B%20BM25)-success" alt="Hybrid RAG" />
  <img src="https://img.shields.io/badge/Embeddings-Local%20ONNX%20(all--MiniLM--L6--v2)-orange" alt="Local ONNX" />
  <img src="https://img.shields.io/badge/Privacy-100%25%20Local%20%26%20Zero--Telemetry-brightgreen" alt="Privacy First" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

An intelligent, privacy-first study assistant and knowledge retrieval engine engineered for university courses. 

**moodle-ai** automatically streams course slides, lecture decks, external course websites, and your personal notes, parses them into slide-structured Markdown, and indexes every page into a local **Hybrid Retrieval Engine (Dense ONNX Vectors + BM25 Lexical + Reciprocal Rank Fusion)**. It exposes standard MCP tools natively into **Antigravity**, **Claude (Desktop & Code)**, **Cursor**, **Codex / VS Code**, **Windsurf**, or directly via an interactive CLI.

---

## Why moodle-ai vs. Dragging PDFs into Web LLMs?

When you drop 50 slide decks into ChatGPT, Claude, or Gemini Web, you run straight into the **"Lost-in-the-Middle"** context problem. Here is how `moodle-ai` is engineered differently:

| Challenge | Drag-and-Drop Web LLMs | `moodle-ai` Architecture |
| :--- | :--- | :--- |
| **Semester-Scale Memory** | Dumps 1,000+ pages into one prompt. Suffers from attention dilution, mixing up courses and missing obscure formulas. | **Hybrid RAG (RRF)**: Pre-indexes every page locally. Pinpoints the exact 3–5 slides across your entire semester with surgical accuracy. |
| **Parsing Fidelity** | Strips PDFs into raw text streams. Headers, slide boundaries, math equations, and tables get scrambled. | **Slide-Preserving Parsers**: Uses `PyMuPDF4LLM` to maintain exact slide boundaries (`<!-- Page X -->`), tables, and LaTeX formulas. |
| **Course Grounding** | Answers from broad internet data (e.g. citing US ACI or Eurocodes instead of Indian Standards *IS 456*). | Grounded 100% in your actual department slides, grading distribution, and professor notations. |
| **Citations & Proof** | Vaguely says *"According to the document..."*, forcing you to manually scroll 150 slides to verify. | **Clickable Dual Links**: Instant one-click jump to the exact PDF page in Preview and the structured Markdown notes. |
| **Engineering Diagrams** | Text extractors see nothing on diagram-heavy slides (Mohr's circles, shear force curves, charts). | **Visual Fallback Pipeline**: Automatically renders low-text candidate slides into high-res PNGs for multimodal vision inspection. |
| **Session Persistence** | Re-uploading files every new chat tab or window. | Permanent local indexing of Moodle, external lab sites, and offline notes in `user_files/`. |

---

## ⚡ Installation Guidelines

Getting started takes less than a minute with zero manual friction:

### 🚀 The Simplest Way (Any AI Agent / Harness)
1. **Download the folder**: Download or clone the `moodle-ai` repository to your computer.
2. **Open any harness**: Open your preferred AI coding harness or editor (such as **Antigravity**, **Cursor**, **Claude Code**, **VS Code**, or **Windsurf**).
3. **Open project**: Create a new project and select the downloaded `moodle-ai` folder.
4. **Just write `setup`**: In the chat or agent prompt, simply type:
   ```text
   setup
   ```
   (or `/setup`). The agent will automatically handle environment configuration, install dependencies, guide your credentials setup, and register all tools.

---

### 💻 Alternative: 1-Command Terminal Setup
If you prefer running installation from the terminal inside the repository:

```bash
# Option A: Python Universal Installer (Recommended)
python3 install.py

# Option B: Shell Script
./install.sh

# Option C: CLI Tool
python3 agent_tools.py /install
```

---

## Supported Environments & Zero-Config IDE Setup

`install.py` auto-detects and configures all your installed developer tools:

| Environment | Configuration Path | What Works |
| :--- | :--- | :--- |
| **Antigravity IDE** | `.agents/skills/` | Full modular skills suite (`/moodle-ai`, `/ask`, `/quiz`, `/sync`) + MCP |
| **Claude Desktop** | `claude_desktop_config.json` | Registered MCP tools (`moodle_search_and_ask`, `generate_quiz`) |
| **Claude Code** | `.claude/skills/` | Native slash skills and CLI commands |
| **Cursor** | `.cursor/mcp.json` | Instant workspace MCP tool discovery on open |
| **VS Code / Codex** | `.vscode/mcp.json` | Project-level MCP server integration |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | Global Cascade assistant MCP registration |
| **Terminal / CLI** | `python agent_tools.py <command>` | Interactive standalone terminal dispatcher |

---

## Core Features & Workflow

```text
       Moodle LMS (Kerberos SSO)
                   +
      Custom Web URLs (HTML / Reveal.js)    ──►  Streaming Sync Pipeline (Async)
                   +
     Personal Notes (user_files/*.pdf)
                   │
                   ▼
       PyMuPDF4LLM Markdown Parser  ──►  Preserves <!-- Page X -->, Tables & Math
                   │
                   ▼
     ┌──────────────────────────────────────────────────────────┐
     │              Hybrid Retrieval Engine (RRF)               │
     │  Dense: ONNX all-MiniLM-L6-v2  +  Lexical: BM25 (SQLite) │
     └──────────────────────────┬───────────────────────────────┘
                                │
             ┌──────────────────┴──────────────────┐
             ▼                                     ▼
   Text Query Matches                    Visual / Diagram Query
(Dual Clickable Citations)            (High-Res PNG Visual Fallback)
```

### 1. Setup Your Credentials
Store your Moodle credentials locally in `.env`. Your password is encrypted locally and never exposed in chat prompts:
```bash
python agent_tools.py /setup
```

### 2. Stream Sync Semester Courses
Stream-download course materials, convert them to Markdown, and index vectors in one pass:
```bash
# Sync active semester + external URLs + personal notes
python agent_tools.py /sync

# Sync only local notes and textbooks in user_files/ (instant, offline)
python agent_tools.py /sync user

# Sync a specific semester code
python agent_tools.py /sync 2601
```

### 3. Add Personal Notes & Textbooks (`user_files/`)
Drop any PDF, PPTX, DOCX, or Markdown file directly into `user_files/`:
```text
user_files/
├── CVL245A/
│   ├── Additional_Solved_Problems.pdf
│   └── IS_456_2000_Plain_and_Reinforced_Concrete.pdf
└── HUL281A/
    └── Constitution_and_Key_Court_Judgments.pdf
```
Run `python agent_tools.py /sync user` to index them immediately.

### 4. Index External Course Sites & Slides
Scrape and index external course homepages, lecture websites, or public PDFs (including Reveal.js slides):
```bash
python agent_tools.py /add-custom-url "https://hpmlab.iitd.ac.in/courses/cvl282/" "CVL282_Lab"
```

### 5. Ask Questions with Dual Clickable Citations
```bash
python agent_tools.py /ask "Explain the Limit State of collapse in flexure according to IS 456"
```

Every response references verifiable, clickable links:
> According to **IS 456 Clause 38.1**, the maximum strain in concrete at the outermost compression fiber is taken as 0.0035 in bending...
> 
> **Sources:**
> * `[CVL245A / IS_456_2000.pdf (Page 67)](file:///Users/.../IS_456_2000.pdf)` ([Markdown View](file:///Users/.../IS_456_2000.md))

### 6. Interactive Practice Quizzes for Exams
Generate practice exams with multiple-choice, numerical, and conceptual questions grounded directly in your syllabus:
```bash
python agent_tools.py /quiz "2601-CVL245A"
```

### 7. Automated Multimodal Visual Fallback
When a slide contains diagrams, shear force charts, structural drawings, or low-density text:
- The visual pipeline (`src/visual_fallback.py`) renders the slide into a 300-DPI PNG in `data/visual_cache/`.
- Multimodal models inspect the exact figure, graph, or reinforcement schematic directly.

---

## 🛠️ Project Structure

```text
moodle-study-tool/
├── install.py                 # Universal 1-click auto-configurator
├── install.sh                 # Fast setup bash script
├── agent_tools.py             # CLI dispatcher for all study tools
├── mcp_server.py              # Official MCP standard server
├── list.md                    # Auto-generated catalog of indexed course materials
├── user_files/                # Directory for your personal offline PDFs & notes
├── .agents/skills/            # 10 modular Antigravity AI skills
│   ├── moodle-ai/             # Master study agent & tutor
│   ├── moodle-sync/           # Streaming course scraper & indexer
│   ├── moodle-ask/            # Hybrid RAG search engine
│   ├── moodle-quiz/           # Syllabus-grounded practice exam generator
│   ├── moodle-add-custom-url/ # Custom external webpage / PDF scraper
│   ├── moodle-remove-custom-url/
│   ├── moodle-list/           # Interactive course document explorer
│   ├── moodle-change-sync/    # Semester selector
│   ├── moodle-setup/          # Secure credential manager
│   └── moodle-update-version/ # 1-click git pull & dependency updater
└── src/
    ├── config.py              # Environment settings & directory paths
    ├── custom_scraper.py      # Web scraper for external course sites & HTML slides
    ├── parser.py              # PyMuPDF4LLM Markdown parser with SHA-256 caching
    ├── embeddings.py          # Standalone ONNX runtime (all-MiniLM-L6-v2)
    ├── indexer.py             # SQLite + BM25 Hybrid Retriever with RRF ranking
    ├── visual_fallback.py     # Multimodal PDF slide diagram renderer
    ├── scraper_sync.py        # Live multi-source indexing coordinator
    ├── list_manager.py        # Course catalog & Markdown link generator
    └── web_search.py          # Wikipedia REST fallback retrieval
```

---

## 🔒 Privacy & Local Processing

- **Zero Cloud Leakage**: Document parsing, ONNX embeddings, BM25 indexing, and search ranking run 100% locally on your machine.
- **No Stored Passwords in AI Chat**: Passwords stay inside your local, git-ignored `.env` file.
- **Offline Capable**: Once course slides are synced, you can query notes, read markdown summaries, and generate study reviews completely offline without an active internet connection.

---

## 📄 License

MIT License. Engineered for academic research and personal study productivity.

