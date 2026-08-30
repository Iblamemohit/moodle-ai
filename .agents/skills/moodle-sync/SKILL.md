---
name: moodle-sync
description: Triggers the streaming async scraper to download Moodle course materials and registered custom URLs, convert them into Markdown, and update local ChromaDB and BM25 search indexes on the fly.
---

# Moodle Sync Skill (Async Streaming)

## When to use this skill
Use this skill when the user wants to sync, download, or update their course materials from Moodle and any registered custom URLs.

## Workflow Instructions
1. **Semester/Year Selection**:
   - If the user did NOT specify a semester/year in their request (e.g., they just said "sync moodle"):
     - Run:
       ```bash
       .venv/bin/python agent_tools.py /sync --json
       ```
     - If the tool returns available semesters (e.g., `[2601]: Semester 1 2026-2027`, `[all]: All Semesters`), ask the user which semester they would like to sync!
2. **Execute Streaming Sync**:
   - Once the user specifies a semester (e.g., `2601`, `all`, or `custom`), run:
     ```bash
     .venv/bin/python agent_tools.py /sync "<SEMESTER_CODE>" --json
     ```
   - **Streaming Processing**: As each file downloads from Moodle courses and registered custom URLs, it is immediately converted to Markdown, embedded in ChromaDB & BM25, and registered in `list.md` in real-time.
3. **Report Results**:
   - Report the number of courses and custom URLs synced, documents converted to Markdown, chunks indexed, and provide the link to [`list.md`](file:///Users/mohit/Documents/moodle-study-tool/list.md).
