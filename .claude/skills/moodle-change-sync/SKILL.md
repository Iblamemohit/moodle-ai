---
name: moodle-change-sync
description: Changes the active tracked semester/year.
---

# Moodle Change Sync (Tracked Semester) Skill

## When to use this skill
Use this skill when the user wants to change, switch, or configure which semester/year is tracked by default for Moodle syncing and document retrieval (e.g., "change sync to 2601", "switch tracked semester", "change sync to all").

## Workflow Instructions
1. Check if the user specified a target semester in their prompt (e.g. `2601`, `2502`, `all`).
2. If NOT specified:
   - Run:
     ```bash
     .venv/bin/python agent_tools.py /change-sync
     ```
   - Present the list of available semesters and ask the user which semester they would like to switch to.
3. Once the user specifies a semester:
   - Run:
     ```bash
     .venv/bin/python agent_tools.py /change-sync "<SEMESTER_CODE>"
     ```
4. Confirm to the user:
   - The active tracked semester is now configured in `.env`.
   - All future `/moodle-sync` operations will automatically target this semester!
