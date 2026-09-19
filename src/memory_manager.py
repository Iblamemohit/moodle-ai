#!/usr/bin/env python3
"""
src/memory_manager.py — Programmatic Memory Engine for moodle-ai.

Manages student profile, upcoming exam schedules, course diagnostics,
and learning preferences via a persistent Markdown state engine (`memory.md`).
"""

import os
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import get_config

DEFAULT_MEMORY_TEMPLATE = """# Student Memory & Academic State

## Academic Profile
- Name: Mohit
- Institution: IIT Delhi
- Entry Number: 2022CE10423
- CGPA: 8.5
- Target Goals: 9.0+ Semester GPA, Master Structural Analysis & Design
- Enrolled Courses: CVL245, CVL341, CVL282, ESL370

## Exam & Quiz Schedule
| Date | Course | Exam/Quiz | Syllabus / Topics | Status |
| :--- | :--- | :--- | :--- | :--- |
| 2026-09-20 | CVL245 | Minor 1 | Limit State Design, Flexure, Shear & Bond (IS 456) | [PENDING] |
| 2026-09-22 | CVL341 | Minor 1 | Slope Deflection Method, Moment Distribution | [PENDING] |
| 2026-09-25 | ESL370 | Quiz 1 | Renewable Energy Systems, Solar Photovoltaics | [PENDING] |

## Course Diagnostics
### CVL245
- Strengths: Singly reinforced beams, stress block fundamentals, IS 456 assumptions.
- Weaknesses: Doubly reinforced sections ($x_u > x_{u,max}$), calculating steel stress $f_{sc}$ for Fe500, shear design with inclined stirrups.
- Active Focus: Numerical calculations for doubly reinforced beams and shear reinforcement spacing.

### CVL341
- Strengths: Cantilever and simply supported beam deflections, static indeterminacy.
- Weaknesses: Non-sway portal frame joint equilibrium equations, stiffness coefficients with settlement.
- Active Focus: Portal frame joint balance and moment distribution tables.

### ESL370
- Strengths: Qualitative energy policy, solar radiation geometry.
- Weaknesses: Cell fill factor calculation, PV diode equivalent circuit models.
- Active Focus: Numerical PV diode equation solving.

## Learning Preferences
- Learning Style: Step-by-step mathematical derivations grounded in course slides, explicit formulas with SI units, no skipping intermediate arithmetic.
- Study Rules: Strictly no ASCII art diagrams; always use publication-grade 300 DPI PNG diagrams or direct PyMuPDF slide crops. Dual citations for course materials: [Course / File.pdf (Page X)](file:///path) ([Markdown](file:///path)).
- Sleep Schedule: 11:30 PM - 7:00 AM (prioritize high-yield triage before 11:00 PM).
"""

class MemoryManager:
    """Manages reading, parsing, updating, and querying memory.md."""

    def __init__(self, workspace_dir: Optional[str] = None):
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            cfg = get_config()
            self.workspace_dir = Path(cfg.get("workspace_dir", Path.cwd()))
        
        self.memory_path = self.workspace_dir / "memory.md"
        if not self.memory_path.exists():
            self._initialize_default_memory()

    def _initialize_default_memory(self):
        """Creates default memory.md if it doesn't already exist."""
        with open(self.memory_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_MEMORY_TEMPLATE.strip() + "\n")

    def load_memory(self) -> Dict[str, Any]:
        """
        Parses memory.md into structured sections:
        - academic_profile: Dict of student attributes
        - schedule: List of exam dictionaries
        - diagnostics: Dict of course-specific strengths, weaknesses, focus
        - preferences: Dict of learning style, study rules, sleep schedule
        - raw_sections: Raw text per ## section
        """
        if not self.memory_path.exists():
            self._initialize_default_memory()

        with open(self.memory_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = self._split_sections(content)

        academic_profile = self._parse_profile(sections.get("Academic Profile", ""))
        schedule = self._parse_schedule(sections.get("Exam & Quiz Schedule", ""))
        diagnostics = self._parse_diagnostics(sections.get("Course Diagnostics", ""))
        preferences = self._parse_preferences(sections.get("Learning Preferences", ""))

        return {
            "academic_profile": academic_profile,
            "schedule": schedule,
            "diagnostics": diagnostics,
            "preferences": preferences,
            "raw_sections": sections
        }

    def _split_sections(self, content: str) -> Dict[str, str]:
        """Splits markdown by level 2 headings (## Heading)."""
        sections: Dict[str, str] = {}
        current_title = "Header"
        current_lines: List[str] = []

        for line in content.splitlines():
            if line.startswith("## "):
                if current_lines:
                    sections[current_title] = "\n".join(current_lines).strip()
                current_title = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_title] = "\n".join(current_lines).strip()

        return sections

    def _parse_profile(self, text: str) -> Dict[str, str]:
        """Parses bullet points into key-value pairs."""
        profile: Dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("- ") and ":" in line:
                key, val = line[2:].split(":", 1)
                profile[key.strip().lower().replace(" ", "_")] = val.strip()
        return profile

    def _parse_schedule(self, text: str) -> List[Dict[str, str]]:
        """Parses markdown table into list of exam dicts."""
        exams: List[Dict[str, str]] = []
        lines = [l.strip() for l in text.splitlines() if l.strip().startswith("|")]
        if len(lines) < 2:
            return exams

        # First line is header, second is separator
        header_cols = [c.strip().lower().replace(" ", "_").replace("/", "_") for c in lines[0].strip("|").split("|")]
        for row in lines[2:]:
            cols = [c.strip() for c in row.strip("|").split("|")]
            if len(cols) >= len(header_cols):
                item = {}
                for h, val in zip(header_cols, cols):
                    item[h] = val
                exams.append(item)
        return exams

    def _parse_diagnostics(self, text: str) -> Dict[str, Dict[str, str]]:
        """Parses ### Course blocks into strengths/weaknesses/focus."""
        diagnostics: Dict[str, Dict[str, str]] = {}
        current_course = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("### "):
                current_course = line[4:].strip().upper()
                diagnostics[current_course] = {"strengths": "", "weaknesses": "", "active_focus": "", "raw": ""}
            elif current_course and line.startswith("- "):
                if ":" in line:
                    k, v = line[2:].split(":", 1)
                    k_norm = k.strip().lower().replace(" ", "_")
                    diagnostics[current_course][k_norm] = v.strip()
                diagnostics[current_course]["raw"] += line + "\n"
        return diagnostics

    def _parse_preferences(self, text: str) -> Dict[str, str]:
        """Parses bullet points in preferences section."""
        prefs: Dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("- ") and ":" in line:
                key, val = line[2:].split(":", 1)
                prefs[key.strip().lower().replace(" ", "_")] = val.strip()
        return prefs

    def get_next_exam(self, reference_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Calculates the immediate next incomplete upcoming exam.
        Matches date >= reference_date (default today) and status != '[COMPLETED]'.
        """
        mem = self.load_memory()
        schedule = mem.get("schedule", [])
        if not schedule:
            return None

        today_str = reference_date or datetime.date.today().isoformat()
        try:
            today_date = datetime.date.fromisoformat(today_str)
        except Exception:
            today_date = datetime.date.today()

        valid_exams = []
        for ex in schedule:
            status = ex.get("status", "").upper()
            if "COMPLETED" in status or "DONE" in status:
                continue

            ex_date_str = ex.get("date", "")
            try:
                ex_date = datetime.date.fromisoformat(ex_date_str)
                days_rem = (ex_date - today_date).days
                valid_exams.append({
                    **ex,
                    "parsed_date": ex_date,
                    "days_remaining": days_rem
                })
            except Exception:
                # If date is not standard ISO, still include with arbitrary high order
                valid_exams.append({
                    **ex,
                    "parsed_date": datetime.date.max,
                    "days_remaining": 999
                })

        if not valid_exams:
            return None

        # Sort by date ascending (closest future date first)
        valid_exams.sort(key=lambda x: (x["days_remaining"] < 0, x["parsed_date"]))
        res = valid_exams[0].copy()
        res.pop("parsed_date", None)
        return res

    def get_course_diagnostic(self, course_code: str) -> str:
        """Fetches documented weak areas and focus topics for a specific course."""
        mem = self.load_memory()
        diag = mem.get("diagnostics", {})
        
        # Normalize course code (e.g. '2601-CVL245A' -> 'CVL245')
        m = re.search(r'([A-Za-z]{2,4}\s*\d{3,4}[A-Za-z]?)', course_code)
        c_key = m.group(1).replace(" ", "").upper() if m else course_code.upper()

        if c_key in diag:
            cd = diag[c_key]
            weakness = cd.get("weaknesses", "")
            focus = cd.get("active_focus", "")
            strengths = cd.get("strengths", "")
            out = []
            if weakness:
                out.append(f"Weaknesses: {weakness}")
            if focus:
                out.append(f"Active Focus: {focus}")
            if strengths:
                out.append(f"Strengths: {strengths}")
            return "\n".join(out)

        # Fallback: check if course is substring of any key
        for k, cd in diag.items():
            if k in c_key or c_key in k:
                weakness = cd.get("weaknesses", "")
                focus = cd.get("active_focus", "")
                out = []
                if weakness:
                    out.append(f"Weaknesses: {weakness}")
                if focus:
                    out.append(f"Active Focus: {focus}")
                return "\n".join(out)

        return f"No specific diagnostics documented for course {course_code}."

    def update_section(self, section_name: str, new_entry: str, mode: str = "append") -> bool:
        """
        Safely updates or appends to a section without corrupting markdown formatting or table structures.
        mode: 'append' or 'replace'
        """
        if not self.memory_path.exists():
            self._initialize_default_memory()

        with open(self.memory_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = rf"(## {re.escape(section_name)}[^\n]*\n)(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            header_line = match.group(1)
            existing_body = match.group(2).strip()

            if mode == "append":
                updated_body = f"{existing_body}\n{new_entry}".strip()
            else:
                updated_body = new_entry.strip()

            new_section = f"{header_line}{updated_body}\n\n"
            updated_content = content[:match.start()] + new_section + content[match.end():]
        else:
            # Section doesn't exist, append new section to the end
            new_section = f"\n\n## {section_name}\n{new_entry.strip()}\n"
            updated_content = content.rstrip() + new_section

        with open(self.memory_path, "w", encoding="utf-8") as f:
            f.write(updated_content.strip() + "\n")

        return True

    def mark_exam_completed(self, course_code: str) -> bool:
        """Marks an exam for the given course as [COMPLETED] in the schedule table."""
        if not self.memory_path.exists():
            return False

        with open(self.memory_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Normalize course code
        m = re.search(r'([A-Za-z]{2,4}\s*\d{3,4}[A-Za-z]?)', course_code)
        target = m.group(1).replace(" ", "").upper() if m else course_code.upper()

        lines = content.splitlines()
        modified = False
        new_lines = []

        in_schedule = False
        for line in lines:
            if line.startswith("## Exam & Quiz Schedule"):
                in_schedule = True
                new_lines.append(line)
                continue
            elif in_schedule and line.startswith("## "):
                in_schedule = False

            if in_schedule and "|" in line and target in line.upper():
                # Replace [PENDING] or other pending status with [COMPLETED]
                if "[PENDING]" in line:
                    line = line.replace("[PENDING]", "[COMPLETED]")
                    modified = True
                elif "[UPCOMING]" in line:
                    line = line.replace("[UPCOMING]", "[COMPLETED]")
                    modified = True

            new_lines.append(line)

        if modified:
            with open(self.memory_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")

        return modified
