---
name: moodle-update
description: Pulls the latest code updates from GitHub and refreshes Python dependencies in the virtual environment.
---

# Moodle Update Skill

## When to use this skill
Use this skill whenever the user asks to update `moodle-ai`, pull the latest features/bug fixes from GitHub, or sync repository code updates.

## Workflow Instructions
1. Run the update tool via `run_command`:
   ```bash
   python agent_tools.py /update --json
   ```
2. Read the JSON output:
   - `status`: `"success"`, `"partial_success"`, or `"error"`.
   - `git_output`: Output from Git pull (e.g., `"Already up to date."` or list of updated files).
   - `dependencies_updated`: Whether `.venv` pip dependencies were checked and updated.
3. Summarize the update status for the user. If uncommitted merge conflicts exist, explain that local modified files should be stashed or committed first.
