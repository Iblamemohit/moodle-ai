---
name: moodle-remove-custom-url
description: Removes a registered custom URL from the active scrape registry and updates list.md.
---

# Remove Custom URL Skill

## When to use this skill
Use this skill when the user wants to remove an external URL or custom source label from their study knowledge base.

## Workflow Instructions
1. **Identify Target URL or Label**:
   - Extract the target URL or source label from the user's prompt (e.g. `CVL243_Extra` or `https://...`).
   - If unsure which URLs are registered, run:
     ```bash
     python agent_tools.py /list-custom-urls
     ```

2. **Execute Removal**:
   - Run:
     ```bash
     python agent_tools.py /remove-custom-url "<TARGET_URL_OR_LABEL>"
     ```
   - If the user explicitly asks to delete the downloaded files as well, append `--delete-files`:
     ```bash
     python agent_tools.py /remove-custom-url "<TARGET_URL_OR_LABEL>" --delete-files
     ```

3. **Report Status**:
   - Confirm the removal of the custom source and state whether files were retained or purged.
