# User Files & Custom Study Materials

Place your personal study documents, textbooks, lecture slides, notes, assignments, and research papers here!

## Supported File Formats
- **PDF Documents** (`.pdf`) - Slides, lecture notes, textbook chapters, problem sets
- **PowerPoint Presentations** (`.pptx`) - Lecture slide decks
- **Word Documents** (`.docx`) - Course notes, study guides
- **Markdown & Plain Text** (`.md`, `.txt`) - Summaries, cheat sheets, formulae

## Organization Options

You can organize your files in either of two ways:

1. **Directly in this folder**:
   ```
   user_files/
     ├── Probability_and_Statistics.pdf
     └── Linear_Algebra_CheatSheet.md
   ```
   *These will be categorized under `User Files / General`.*

2. **Organized into course or topic subfolders**:
   ```
   user_files/
     ├── COL106/
     │     ├── Lecture_01_Trees.pdf
     │     └── Assignment_02.pdf
     └── ELL205/
           └── Signals_and_Systems_Slides.pptx
   ```
   *These will be categorized under `User Files / COL106` and `User Files / ELL205`.*

## How to Ingest & Index Your Files

Whenever you add or update files in this folder, simply run:

- In chat: `/sync user` (or full `/sync`)
- In terminal: `python agent_tools.py /sync user`

Your documents will immediately be:
1. Converted to structured Markdown with page boundaries in `data/parsed/User_Files/`
2. Embedded into the local Hybrid RAG engine (ChromaDB vector store + BM25 keyword search)
3. Cataloged in `list.md` with file stats and clickable links
4. Ready to be queried with `/ask` and quizzed with `/quiz`!
