import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.indexer import is_derivation_query
from src import mcp_server


class TestExamAssistantFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user_files_dir = PROJECT_ROOT / "user_files"
        cls.user_files_dir.mkdir(parents=True, exist_ok=True)

    def test_01_derivation_windowing_intent_detection(self):
        """Test derivation query detection and parent-child windowing flag."""
        self.assertTrue(is_derivation_query("Derivation of IS 456 stress block parameters"))
        self.assertTrue(is_derivation_query("Derive slope deflection equations"))
        self.assertTrue(is_derivation_query("Prove Castigliano second theorem"))
        self.assertTrue(is_derivation_query("Proof of Hardy-Weinberg equilibrium"))
        self.assertFalse(is_derivation_query("What is the slump of M25 concrete?"))
        self.assertFalse(is_derivation_query("When was the Sydney Opera House built?"))

    def test_02_mcp_server_registration(self):
        """Test that core tools are exposed in the MCP server and diagram tool is removed."""
        tools = mcp_server.mcp._tool_manager._tools
        self.assertNotIn("generate_engineering_diagram", tools)
        self.assertIn("moodle_search_and_ask", tools)
        self.assertIn("get_course_slide", tools)
        self.assertIn("trigger_moodle_sync", tools)
        self.assertIn("list_available_courses_and_documents", tools)
        self.assertIn("generate_practice_quiz_context", tools)
        self.assertIn("get_workspace_info", tools)
        self.assertIn("switch_active_workspace", tools)


if __name__ == "__main__":
    unittest.main()
