import os
import re
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.diagram_generator import (
    generate_sfd_bmd,
    generate_is456_stress_block,
    generate_cpm_network
)
from src.indexer import is_derivation_query, KnowledgeIndexer
from src.agent_tools import (
    moodle_diagram,
    moodle_drill,
    moodle_cheatsheet,
    moodle_triage,
    moodle_pyq
)
from src import mcp_server


class TestExamAssistantFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.diagrams_dir = PROJECT_ROOT / "output" / "diagrams"
        cls.cheatsheets_dir = PROJECT_ROOT / "output" / "cheatsheets"
        cls.user_files_dir = PROJECT_ROOT / "user_files"
        cls.diagrams_dir.mkdir(parents=True, exist_ok=True)
        cls.cheatsheets_dir.mkdir(parents=True, exist_ok=True)
        cls.user_files_dir.mkdir(parents=True, exist_ok=True)

    def test_01_sfd_bmd_generation(self):
        """Test publication-grade SFD/BMD diagram generation."""
        res = generate_sfd_bmd(
            beam_type="simply_supported",
            length=6.0,
            loads=[
                {"type": "point", "position": 3.0, "magnitude": 50.0},
                {"type": "udl", "start": 0.0, "end": 6.0, "magnitude": 20.0}
            ],
            filename="test_sfd_bmd.png"
        )
        self.assertEqual(res["status"], "success")
        img_path = Path(res["image_path"])
        self.assertTrue(img_path.exists())
        self.assertGreater(img_path.stat().st_size, 15000, "Image size should be > 15KB for 300 DPI")
        self.assertEqual(res["reactions"]["R_A"], 85.0)
        self.assertEqual(res["reactions"]["R_B"], 85.0)
        self.assertEqual(res["max_bending_moment"], 165.0)

    def test_02_is456_stress_block_generation(self):
        """Test IS 456 RC beam stress block diagram generation."""
        res = generate_is456_stress_block(
            b=250.0,
            d=450.0,
            fck=25.0,
            fy=415.0,
            Ast=942.0,
            filename="test_is456_stress_block.png"
        )
        self.assertEqual(res["status"], "success")
        img_path = Path(res["image_path"])
        self.assertTrue(img_path.exists())
        self.assertGreater(img_path.stat().st_size, 15000)
        self.assertEqual(res["parameters"]["fy_MPa"], 415.0)
        self.assertEqual(res["results"]["xu_max_mm"], 216.0)
        self.assertAlmostEqual(res["results"]["xu_mm"], 151.2, delta=0.5)
        self.assertAlmostEqual(res["results"]["Mu_kNm"], 131.6, delta=1.0)
        self.assertEqual(res["results"]["section_type"], "Under-Reinforced")

    def test_03_cpm_network_generation(self):
        """Test CPM Activity-on-Node network diagram generation."""
        res = generate_cpm_network(filename="test_cpm_network.png")
        self.assertEqual(res["status"], "success")
        img_path = Path(res["image_path"])
        self.assertTrue(img_path.exists())
        self.assertGreater(img_path.stat().st_size, 15000)
        self.assertEqual(res["critical_path"], ["A", "B", "C", "E", "F"])
        self.assertEqual(res["project_duration"], 22)

    def test_04_strict_no_ascii_art(self):
        """Verify strict ban on ASCII art diagrams across all tool responses."""
        ascii_art_patterns = [
            r"\|---.*---\|",       # Monospace beam diagrams |----|
            r"/\\_/\s*\\_/",       # Truss ASCII diagonals
            r"\|\s*\[.*\]\s*\|",   # Monospace stress block
            r"\[\s*A\s*\]\s*--->", # ASCII flowcharts with arrows
            r"\|====.*====\|",     # Monospace beam double lines
            r"\+---.*---\+",       # Monospace ASCII box tables
        ]

        # Test diagram tool response
        d_res = moodle_diagram("sfd_bmd")
        # Must be an image URL markdown link, not an ASCII drawing
        self.assertIn("![", d_res["markdown_link"])
        for pat in ascii_art_patterns:
            self.assertIsNone(re.search(pat, d_res["markdown_link"]))

        # Test drill prompt
        drill_res = moodle_drill("CVL341", "slope_deflection", current_step=1)
        for pat in ascii_art_patterns:
            self.assertIsNone(re.search(pat, drill_res["prompt"]))
            self.assertIsNone(re.search(pat, drill_res["problem_statement"]))

        # Test cheatsheet content
        cs_res = moodle_cheatsheet("CVL243")
        for pat in ascii_art_patterns:
            self.assertIsNone(re.search(pat, cs_res["markdown_content"]))

    def test_05_derivation_windowing_intent_detection(self):
        """Test derivation query detection and parent-child windowing flag."""
        self.assertTrue(is_derivation_query("Derivation of IS 456 stress block parameters"))
        self.assertTrue(is_derivation_query("Derive slope deflection equations"))
        self.assertTrue(is_derivation_query("Prove Castigliano second theorem"))
        self.assertTrue(is_derivation_query("Proof of Hardy-Weinberg equilibrium"))
        self.assertFalse(is_derivation_query("What is the slump of M25 concrete?"))
        self.assertFalse(is_derivation_query("When was the Sydney Opera House built?"))

    def test_06_socratic_drill_progression(self):
        """Test Socratic problem solver step progression and checkpoint validation."""
        # Initial prompt
        step1 = moodle_drill("CVL341", "slope_deflection", current_step=1)
        self.assertEqual(step1["current_step"], 1)
        self.assertFalse(step1["is_correct"])

        # Incorrect answer
        wrong_ans = moodle_drill("CVL341", "slope_deflection", current_step=1, user_answer="Dk is 3")
        self.assertFalse(wrong_ans["is_correct"])
        self.assertIn("Not quite", wrong_ans["feedback"])
        self.assertEqual(wrong_ans["next_step"], 1)

        # Correct answer
        correct_ans = moodle_drill("CVL341", "slope_deflection", current_step=1, user_answer="1, rotation at support B")
        self.assertTrue(correct_ans["is_correct"])
        self.assertIn("Correct", correct_ans["feedback"])
        self.assertEqual(correct_ans["next_step"], 2)

    def test_07_cheatsheet_extractor(self):
        """Test Formula & Code Provision Cheat Sheet extraction."""
        cs = moodle_cheatsheet("CVL243")
        self.assertEqual(cs["status"], "success")
        self.assertIn("IS 456", cs["title"])
        self.assertGreaterEqual(cs["num_equations"], 5)
        self.assertTrue(Path(cs["file_path"]).exists())
        # Check LaTeX formatting
        self.assertIn(r"x_{u,max}", cs["markdown_content"])
        self.assertIn(r"M_{u,lim}", cs["markdown_content"])
        self.assertIn("Standard Parameters & SI Units", cs["markdown_content"])

    def test_08_course_triage(self):
        """Test High-Yield Course Triage mode."""
        triage = moodle_triage("CVL341")
        self.assertEqual(triage["status"], "success")
        self.assertGreater(len(triage["tier1_high_weightage"]), 0)
        self.assertGreater(len(triage["tier2_high_yield"]), 0)
        self.assertGreater(len(triage["tier3_low_priority"]), 0)
        self.assertGreater(len(triage["two_hour_study_checklist"]), 0)
        # Check total time budget in 2-hour checklist
        total_time = sum(item["time_min"] for item in triage["two_hour_study_checklist"])
        self.assertEqual(total_time, 120, "Total triage checklist must equal exactly 120 minutes (2 hours)")

    def test_09_pyq_deconstruction(self):
        """Test Past-Year Paper deconstruction."""
        sample_pdf = self.user_files_dir / "sample_minor_paper.pdf"
        self.assertTrue(sample_pdf.exists(), "Sample exam paper PDF should exist")
        res = moodle_pyq(str(sample_pdf), "2601-CVL243A", question_num=1)
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["deconstructed_questions"]), 1)
        q1 = res["deconstructed_questions"][0]
        self.assertEqual(q1["question_number"], 1)
        self.assertGreater(len(q1["matched_citations"]), 0)
        self.assertGreater(len(q1["marking_scheme_structure"]), 0)
        self.assertGreater(len(q1["exam_variation_forecast"]), 0)

    def test_10_mcp_server_registration(self):
        """Test that all new exam tools are exposed in the MCP server."""
        tools = mcp_server.mcp._tool_manager._tools
        self.assertIn("generate_engineering_diagram", tools)
        self.assertIn("deconstruct_past_exam_paper", tools)
        self.assertIn("socratic_problem_drill", tools)
        self.assertIn("generate_course_cheatsheet", tools)
        self.assertIn("triage_course_exam_prep", tools)


if __name__ == "__main__":
    unittest.main()
