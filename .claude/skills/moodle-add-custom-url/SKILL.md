---
name: moodle-add-custom-url
description: Registers a custom external web URL or direct PDF link to scrape PDFs from, convert them to Markdown, embed into ChromaDB and BM25 RAG index, and track in list.md.
---

# Add Custom URL Skill

## When to use this skill
Use this skill when the user wants to add an external website, professor homepage, course syllabus URL, or direct PDF link to their study knowledge base.

## Workflow Instructions
1. **Extract URL & Optional Label**:
   - Extract the target URL from the user's prompt.
   - If the user gave a course or resource label (e.g. `CVL243_Extra`, `NPTEL_Notes`), use it. Otherwise, a clean label will be inferred automatically from the URL domain/path.

2. **Execute Registration & Auto-Sync**:
   - Run:
     ```bash
     python agent_tools.py /add-custom-url "<TARGET_URL>" "<OPTIONAL_LABEL>"
     ```
   - The tool will register the URL in `data/custom_urls.json`, download all PDF links found on that page, convert them to Markdown, embed them in the ChromaDB & BM25 index, and update `list.md`.

3. **Report Status**:
   - Report the label, number of discovered and downloaded PDFs, and confirm that all materials are indexed and ready for `/ask` and `/quiz`.
   - Provide a clickable link to [`list.md`](list.md).
