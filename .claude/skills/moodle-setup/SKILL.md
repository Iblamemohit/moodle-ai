---
name: moodle-setup
description: Configures Kerberos login credentials securely via local .env file template without asking for passwords in LLM chat.
---

# Moodle Setup Skill (Privacy-First)

## When to use this skill
Use this skill when the user wants to set up, configure, or check their Moodle login credentials.

## Privacy & Security Principle
**NEVER ask the user to type their Kerberos password in the chat window.** 
For security and privacy, credentials should only be entered locally inside the `.env` file.

## Workflow Instructions
1. Run the setup tool using `run_command` in the workspace directory:
   ```bash
   python agent_tools.py /setup
   ```
2. Check the JSON output:
   - If `is_ready` is `true`: Confirm to the user that their credentials are already configured and offer to run `/moodle-sync` or `/moodle-list`.
   - If `is_ready` is `false` (or `status` is `template_ready`):
     - Tell the user:
       > "For your privacy and security, please do not type your password in chat. I have prepared your local `.env` configuration file."
     - Provide the clickable link to their file: `[.env](.env)`.
     - Guide the user: *"Click [`.env`](.env) to open it in your editor, enter your Kerberos ID and password, save the file, and then run `/moodle-sync`!"*
