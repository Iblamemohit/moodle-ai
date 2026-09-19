# moodle-ai

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Protocol-MCP%202.x-8A2BE2" alt="Model Context Protocol" />
  <img src="https://img.shields.io/badge/Retrieval-Hybrid%20RAG%20(Dense%20%2B%20BM25)-success" alt="Hybrid RAG" />
  <img src="https://img.shields.io/badge/Embeddings-Local%20ONNX%20(all--MiniLM--L6--v2)-orange" alt="Local ONNX" />
  <img src="https://img.shields.io/badge/Privacy-100%25%20Local%20%26%20Zero--Telemetry-brightgreen" alt="Privacy First" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

An intelligent, privacy-first academic study assistant, streaming Moodle scraper, and hybrid knowledge retrieval engine engineered for university courses.

**moodle-ai** automatically streams course slides, lecture decks, external course websites, and your personal notes, parses them into slide-structured Markdown, and indexes every page into a local **Hybrid Retrieval Engine (Dense ONNX Vectors + BM25 Lexical + Reciprocal Rank Fusion)** with Parent-Child windowing. It features a **native memory engine (`memory.md`)**, a **continuous self-learning feedback loop**, publication-grade **300 DPI engineering diagrams**, and exposes standard MCP tools natively into **Antigravity**, **Claude (Desktop & Code)**, **Cursor**, **Codex / VS Code**, **Windsurf**, or directly via an interactive CLI.

---

## Why moodle-ai vs. Dragging PDFs into Web LLMs?

When you drop 50 slide decks into ChatGPT, Claude, or Gemini Web, you run straight into the **"Lost-in-the-Middle"** context problem and hallucinated standards. Here is how `moodle-ai` is engineered differently:

| Challenge | Drag-and-Drop Web LLMs | `moodle-ai` Architecture |
| :--- | :--- | :--- |
| **Semester-Scale Memory** | Dumps 1,000+ pages into one prompt. Suffers from attention dilution, mixing up courses and missing obscure formulas. | **Hybrid RAG (RRF)**: Pre-indexes every page locally with BM25 + ONNX dense vectors. Pinpoints the exact slides across your entire semester with surgical accuracy. |
| **Active Student State** | Forgets student context, exam dates, strengths, and weaknesses between conversations. | **Native Memory Engine (`memory.md`)**: Programmatically tracks academic profile, upcoming exam countdowns, course diagnostics, and learning preferences. |
| **Continuous Self-Learning** | Repeats previous mistakes across chats; cannot learn professor-specific grading rules or notation. | **Self-Learning Engine (`src/self_learner.py`)**: Persists student/professor corrections, tracks concept mastery across drills, and auto-tunes retrieval. |
| **Math & Derivations** | Scrambles LaTeX and truncates multi-page proofs mid-equation. | **Parent-Child Windowing**: Expands derivation queries to contiguous 3-page chunks without mid-equation truncation. |
| **Engineering Diagrams** | Produces unreadable ASCII art diagrams with monospace slashes and pipes. | **Publication-Grade 300 DPI PNGs**: Strict ban on ASCII art. Generates crisp SFD/BMD, IS 456 stress blocks, and CPM networks or crops direct slide regions. |
| **Course Grounding** | Answers from broad internet data (e.g. citing US ACI or Eurocodes instead of Indian Standards *IS 456*). | Grounded 100% in your actual department slides, grading distribution, and professor notations. |
| **Citations & Proof** | Vaguely says *"According to the document..."*, forcing you to manually scroll 150 slides to verify. | **Clickable Dual Links**: Instant one-click jump to the exact PDF page in Preview and the structured Markdown notes. |
| **Visual Inspection** | Text extractors see nothing on diagram-heavy slides (Mohr's circles, shear force curves, charts). | **Visual Fallback Pipeline**: Automatically renders candidate slides into high-res PNGs for multimodal vision inspection. |

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
python3 moodle.py /install
```

---

## Supported Environments & Zero-Config IDE Setup

`install.py` auto-detects and configures all your installed developer tools:

| Environment | Configuration Path | What Works |
| :--- | :--- | :--- |
| **Antigravity IDE** | `.agents/skills/` | Full modular skills suite (`/moodle-ai`, `/ask`, `/quiz`, `/sync`, etc.) + MCP |
| **Claude Desktop** | `claude_desktop_config.json` | Registered MCP tools (`moodle_search_and_ask`, `get_student_profile`, etc.) |
| **Claude Code** | `.claude/skills/` | Native slash skills and CLI commands |
| **Cursor** | `.cursor/mcp.json` | Instant workspace MCP tool discovery on open |
| **VS Code / Codex** | `.vscode/mcp.json` | Project-level MCP server integration |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | Global Cascade assistant MCP registration |
| **Terminal / CLI** | `python moodle.py <command>` | Interactive standalone terminal dispatcher |

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
     │  Parent-Child Windowing  +  Learner Retrieval Boosting   │
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
python moodle.py /setup
```

### 2. Stream Sync Semester Courses
Stream-download course materials, convert them to Markdown, and index vectors in one pass:
```bash
# Sync active semester + external URLs + personal notes
python moodle.py /sync

# Sync only local notes and textbooks in user_files/ (instant, offline)
python moodle.py /sync user

# Sync a specific semester code
python moodle.py /sync 2601
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
Run `python moodle.py /sync user` to index them immediately.

### 4. Index External Course Sites & Slides
Scrape and index external course homepages, lecture websites, or public PDFs (including Reveal.js slides):
```bash
python moodle.py /add-custom-url "https://hpmlab.iitd.ac.in/courses/cvl282/" "CVL282_Lab"
```

### 5. Ask Questions with Dual Clickable Citations
```bash
python moodle.py /ask "Explain the Limit State of collapse in flexure according to IS 456"
```

Every response references verifiable, clickable links:
> According to **IS 456 Clause 38.1**, the maximum strain in concrete at the outermost compression fiber is taken as 0.0035 in bending...
> 
> **Sources:**
> * `[CVL245A / IS_456_2000.pdf (Page 67)](file:///Users/.../IS_456_2000.pdf)` ([Markdown View](file:///Users/.../IS_456_2000.md))

### 6. Native Student Memory & Exam Countdown
View your academic profile, upcoming exam countdowns, and documented weak areas:
```bash
# View complete academic profile & exam countdowns
python moodle.py /profile

# View immediate next upcoming exam
python moodle.py /exam

# View diagnostic weaknesses for a course
python moodle.py /weakness CVL245
```

### 7. Continuous Self-Learning & Corrections
Log professor-specific rules or corrections so `moodle-ai` never repeats a mistake:
```bash
python moodle.py /correct CVL245 flexure "For Fe500, limiting xu_max/d = 0.46" "IS 456 Cl. 38.1 Note"
```

### 8. Socratic Step-by-Step Problem Solver (`/drill`)
Interactive engineering tutor that guides you through calculation checkpoints:
```bash
# Start or continue an interactive calculation drill
python moodle.py /drill CVL341 slope_deflection --step 1 --answer "1"
```

### 9. Publication-Grade 300 DPI Engineering Diagrams (`/diagram`)
Generate crisp, publication-grade engineering diagrams (strictly no ASCII art):
```bash
python moodle.py /diagram sfd_bmd
python moodle.py /diagram is456_stress_block
python moodle.py /diagram cpm_network
```

### 10. Past-Year Exam Paper Deconstruction (`/pyq`)
Deconstruct past exam papers with slide citations, IIT-style marking schemes, and exam variation forecasts:
```bash
python moodle.py /pyq user_files/sample_minor_paper.pdf CVL243 1
```

### 11. Formula Cheat Sheet Generator (`/cheatsheet`)
Extract governing equations in LaTeX, parameter units, and IS code clauses into `output/cheatsheets/<course>_cheatsheet.md`:
```bash
python moodle.py /cheatsheet CVL243
```

### 12. High-Yield Course Triage (`/triage`)
Emergency night-before exam preparation mode with Tier 1/2/3 breakdown and a 2-hour study checklist:
```bash
python moodle.py /triage CVL341
```

---

## 🛠️ Project Structure

```text
moodle-study-tool/
├── moodle.py                  # Minimal 5-line CLI entrypoint
├── memory.md                  # Native student state & exam schedule engine
├── install.py                 # Universal 1-click auto-configurator
├── install.sh                 # Fast setup bash script
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Dev & profiling dependencies (tiktoken)
├── list.md                    # Auto-generated catalog of indexed course materials
├── AGENTS.md / CLAUDE.md      # Assistant guidelines & instructions
├── src/                       # Core application packages
│   ├── agent_tools.py         # Study tools implementation & CLI dispatcher
│   ├── mcp_server.py          # MCP 2.x standard server exposing tools
│   ├── memory_manager.py      # Programmatic memory manager for memory.md
│   ├── self_learner.py        # Persistent learning, mastery & retrieval boosting
│   ├── diagram_generator.py   # Publication-grade 300 DPI diagram generator
│   ├── parser.py              # PyMuPDF4LLM Markdown parser with SHA-256 caching
│   ├── indexer.py             # SQLite + BM25 Hybrid Retriever with RRF ranking
│   ├── embeddings.py          # Standalone ONNX runtime (all-MiniLM-L6-v2)
│   ├── visual_fallback.py     # Multimodal PDF slide diagram renderer
│   ├── query_cache.py         # High-speed SQLite query & embedding cache
│   ├── scraper_sync.py        # Live multi-source indexing coordinator
│   ├── scraper.py             # Moodle async scraper internals
│   ├── custom_scraper.py      # Web scraper for external course sites & HTML slides
│   ├── list_manager.py        # Course catalog & Markdown link generator
│   └── web_search.py          # Wikipedia REST fallback retrieval
├── notes/                     # Curated study notes, guides & solution PDFs
├── output/                    # Downloaded course slides & generated assets
│   ├── diagrams/              # Generated 300 DPI diagrams & high-res slide crops
│   └── cheatsheets/           # Auto-compiled course cheat sheets
├── data/                      # Local vector databases & learning stores
│   ├── learned_rules.json     # Persistent professor rules & student corrections
│   ├── mastery_tracker.json   # Concept mastery scores & mistake logs
│   ├── retrieval_feedback.json# Search feedback & document boost weights
│   ├── moodle_knowledge.db    # SQLite BM25 full-text search database
│   └── query_cache.db         # Fast query cache database
├── scratch/                   # One-off scratch & calculation scripts
├── scripts/                   # Benchmarking & profiling utilities
├── tests/                     # Automated unit and integration test suites
└── user_files/                # Directory for your personal offline PDFs & notes
```

---

## 📋 Complete CLI Command Reference

All commands are executed through the root entrypoint:
```bash
python moodle.py <command> [arguments]
```

| Command | Description |
| :--- | :--- |
| `/moodle-ai` | Master status and interactive help dispatcher |
| `/setup` | Initialize or verify `.env` credentials securely |
| `/sync [sem \| user]` | Stream download, convert to Markdown, and index vectors |
| `/list [--regen]` | Display all courses and indexed documents from `list.md` |
| `/ask "<query>"` | Hybrid RAG search with dual citations and Wikipedia fallback |
| `/quiz [course]` | Generate practice exam questions from syllabus |
| `/profile` | Display student profile, upcoming exam countdowns, and focus areas |
| `/exam` | Show immediate next upcoming exam and syllabus |
| `/weakness [course]` | Display weakest topics and recent mistake history |
| `/correct <c> <t> <r>` | Permanently log a correction rule in `learned_rules.json` |
| `/drill [c] [t] [--step N]` | Socratic step-by-step problem solver with calculation validation |
| `/diagram <type>` | Generate 300 DPI diagram (`sfd_bmd`, `is456_stress_block`, `cpm_network`) |
| `/pyq <pdf> <course> [q]` | Past-year exam paper deconstruction with marking scheme |
| `/cheatsheet <course>` | Compile formula & IS code provision cheat sheet |
| `/triage <course>` | High-yield exam triage with 2-hour night-before study checklist |
| `/add-custom-url <url>` | Register and index external course website or direct PDF |
| `/remove-custom-url <url>`| Remove registered custom URL |
| `/list-custom-urls` | List all registered external URLs |
| `/change-sync [sem]` | Change active tracked semester in `.env` |
| `/update-version` | Pull latest updates from GitHub and refresh `.venv` dependencies |
| `/install` | Universal 1-click auto-configuration wizard |

---

## 🔒 Privacy & Local Processing

- **Zero Cloud Leakage**: Document parsing, ONNX embeddings, BM25 indexing, memory tracking, and search ranking run 100% locally on your machine.
- **No Stored Passwords in AI Chat**: Passwords stay inside your local, git-ignored `.env` file.
- **Offline Capable**: Once course slides are synced, you can query notes, read markdown summaries, solve drills, and review formulas completely offline without an active internet connection.

---

## 📄 License

MIT License. Engineered for academic research and personal study productivity.
