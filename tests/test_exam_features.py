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
from src.agent_tools import moodle_diagram
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

    def test_05_derivation_windowing_intent_detection(self):
        """Test derivation query detection and parent-child windowing flag."""
        self.assertTrue(is_derivation_query("Derivation of IS 456 stress block parameters"))
        self.assertTrue(is_derivation_query("Derive slope deflection equations"))
        self.assertTrue(is_derivation_query("Prove Castigliano second theorem"))
        self.assertTrue(is_derivation_query("Proof of Hardy-Weinberg equilibrium"))
        self.assertFalse(is_derivation_query("What is the slump of M25 concrete?"))
        self.assertFalse(is_derivation_query("When was the Sydney Opera House built?"))

    def test_06_mcp_server_registration(self):
        """Test that core tools are exposed in the MCP server."""
        tools = mcp_server.mcp._tool_manager._tools
        self.assertIn("generate_engineering_diagram", tools)
        self.assertIn("moodle_search_and_ask", tools)
        self.assertIn("get_course_slide", tools)
        self.assertIn("trigger_moodle_sync", tools)
        self.assertIn("list_available_courses_and_documents", tools)


if __name__ == "__main__":
    unittest.main()
