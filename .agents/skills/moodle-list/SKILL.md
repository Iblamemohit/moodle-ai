---
name: moodle-list
description: Reads list.md and presents all courses, semesters, and available documents.
---

# Moodle List Skill

## When to use this skill
Use this skill when the user asks what courses, documents, or slides they have downloaded (e.g., "what courses do I have?", "list my moodle files", "show my syllabus list").

## Workflow Instructions
1. Run the list command using `run_command`:
   ```bash
   .venv/bin/python agent_tools.py /list
   ```
2. The command reads directly from [`list.md`](file:///Users/mohit/Documents/MoodleScraper/list.md) and outputs the complete file hierarchy across semesters and courses. Clicking any document link opens the PDF directly in macOS Preview.
3. Present the markdown document structure to the student, and offer to answer questions (`/moodle-ask`), generate a quiz (`/moodle-quiz`), or open any document in Preview (`/open <filename>`)!
