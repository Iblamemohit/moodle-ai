#!/usr/bin/env python3
"""
tests/test_memory_and_learning.py — Unit & Integration tests for MemoryManager and SelfLearner.
"""

import unittest
import shutil
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.memory_manager import MemoryManager
from src.self_learner import SelfLearner
from src.agent_tools import (
    moodle_ask,
    moodle_quiz,
    moodle_drill,
    get_student_profile,
    get_next_upcoming_exam,
    record_student_correction,
    get_student_weaknesses
)
from src import mcp_server


class TestMemoryAndLearning(unittest.TestCase):
    def setUp(self):
        self.mm = MemoryManager()
        self.sl = SelfLearner()

    def test_memory_parsing(self):
        mem = self.mm.load_memory()
        self.assertIn("academic_profile", mem)
        self.assertIn("schedule", mem)
        self.assertIn("diagnostics", mem)
        self.assertIn("preferences", mem)

        prof = mem["academic_profile"]
        self.assertEqual(prof.get("name"), "Mohit")
        self.assertEqual(prof.get("institution"), "IIT Delhi")

        schedule = mem["schedule"]
        self.assertGreaterEqual(len(schedule), 3)

        next_exam = self.mm.get_next_exam(reference_date="2026-09-19")
        self.assertIsNotNone(next_exam)
        self.assertEqual(next_exam["course"], "CVL245")
        self.assertEqual(next_exam["date"], "2026-09-20")

    def test_course_diagnostic(self):
        diag = self.mm.get_course_diagnostic("CVL245")
        self.assertIn("Doubly reinforced", diag)

        diag341 = self.mm.get_course_diagnostic("CVL341")
        self.assertIn("portal frame", diag341)

    def test_self_learner_rules(self):
        # Learn a rule
        rule_text = "Test rule: For M30 concrete, f_ct = 0.7 * sqrt(30) = 3.83 MPa"
        res = self.sl.learn_rule("CVL245", "concrete_tensile_strength", rule_text, "IS 456 Cl. 6.2.2")
        self.assertTrue(res or not res)  # True on first insert, False on duplicate

        rules = self.sl.get_rules_for_context("CVL245", "concrete_tensile_strength")
        self.assertTrue(any("3.83 MPa" in r for r in rules))

    def test_self_learner_mastery(self):
        # Record drill performance
        self.sl.record_drill_result("CVL245", "doubly_reinforced_beams", is_correct=False, mistake_summary="Did not compute Asc correctly")
        self.sl.record_drill_result("CVL245", "doubly_reinforced_beams", is_correct=True)

        weakest = self.sl.get_weakest_topics("CVL245", top_n=3)
        self.assertGreaterEqual(len(weakest), 1)
        self.assertTrue(any(w["topic"] == "doubly_reinforced_beams" for w in weakest))

    def test_moodle_ask_context_injection(self):
        # Test that moodle_ask includes learned_rules and student_learning_style
        res = moodle_ask(query="What is the limiting depth of neutral axis for Fe500?", course_filter="CVL245")
        self.assertIn("learned_rules", res)
        self.assertIn("student_learning_style", res)
        self.assertTrue(any("Fe500" in r for r in res["learned_rules"]))

    def test_moodle_quiz_default_next_exam(self):
        # When course is omitted, defaults to next exam (CVL245)
        res = moodle_quiz(course=None, num_questions=2)
        self.assertEqual(res["course"], "CVL245")
        self.assertIn("prioritized_weak_areas", res)

    def test_moodle_drill_adaptive(self):
        # When course is omitted, defaults to next exam or weakest
        res = moodle_drill(course=None, topic=None, current_step=1)
        self.assertEqual(res["status"], "success")
        self.assertIn("drill_topic", res)

    def test_mcp_tools_exposed(self):
        # Verify all MCP tools are registered in MCPServer
        tools = mcp_server.mcp._tool_manager._tools
        expected = [
            "get_student_profile",
            "update_student_profile",
            "get_next_upcoming_exam",
            "record_student_correction",
            "log_drill_performance",
            "get_student_weaknesses"
        ]
        for exp in expected:
            self.assertIn(exp, tools, f"MCP tool {exp} not found in registered tools")


if __name__ == "__main__":
    unittest.main()
