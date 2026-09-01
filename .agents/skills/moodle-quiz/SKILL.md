---
name: moodle-quiz
description: Generates interactive practice quizzes for exam preparation using course lecture slides and summaries from the local Moodle Knowledge Base.
---

# Moodle Quiz Skill

## When to use this skill
Use this skill when the user wants to test their knowledge, practice for an exam, or take a quiz on a specific course (e.g., "quiz me on CVL245A", "generate practice questions for Construction Management").

## Workflow Instructions
1. Run the quiz command for the requested course using `run_command`:
   ```bash
   .venv/bin/python agent_tools.py /quiz "<COURSE_NAME>"
   ```
2. Read the sampled foundational course concepts and summary slides.
3. Generate 3 to 5 multiple-choice questions (or present them one by one interactively):
   - Provide 4 options (A, B, C, D) per question.
   - Ground the correct answers in the retrieved slides.
4. After the student answers, explain whether they were correct, provide the full explanation, and cite the exact slide using dual citations: `[CourseCode / FileName.pdf (Page X)](file:///Users/mohit/Documents/moodle-study-tool/output/.../FileName.pdf) ([Markdown](file:///Users/mohit/Documents/moodle-study-tool/data/parsed/.../FileName.md))`.

