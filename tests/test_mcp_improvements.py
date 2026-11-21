import unittest
import asyncio
import os
import re
from pathlib import Path

from src.visual_fallback import get_image_base64, render_full_slide_image
from src.agent_tools import (
    get_course_slide,
    sync_moodle,
    moodle_diagram
)
from src.indexer import (
    is_derivation_query,
    has_math_or_derivation_content,
    prune_chunk_text
)
from src.mcp_server import mcp
from mcp.types import CallToolResult, TextContent, ImageContent


class TestMCPImprovements(unittest.TestCase):

    def test_multimodal_image_encoding(self):
        """Validates base64 encoding of image files."""
        # Find an existing cached image or diagram
        vis_cache = Path("data/visual_cache")
        sample_img = None
        if vis_cache.exists():
            pngs = list(vis_cache.glob("*.png"))
            if pngs:
                sample_img = pngs[0]

        if sample_img:
            b64_str = get_image_base64(sample_img)
            self.assertIsNotNone(b64_str)
            self.assertIsInstance(b64_str, str)
            self.assertGreater(len(b64_str), 100)

        # Invalid path should safely return None without crashing
        self.assertIsNone(get_image_base64("non_existent_file.png"))

    def test_get_course_slide_precision(self):
        """Validates precision slide extraction with 150 DPI and 300 DPI raw modes."""
        res_150 = get_course_slide(
            course_code="CVL341",
            document_name="Lecture8",
            page_number=1,
            render_image=True,
            high_res=False
        )
        self.assertEqual(res_150["status"], "success")
        self.assertEqual(res_150["page_number"], 1)
        self.assertIn("Lecture8.pdf", res_150["document_name"])
        self.assertIsNotNone(res_150["image_path"])
        self.assertTrue(os.path.exists(res_150["image_path"]))
        self.assertIn("_full.png", res_150["image_path"])
        self.assertIsNotNone(res_150["image_base64"])
        self.assertIn("summary_markdown", res_150)

        # Test 300 DPI raw mode
        res_300 = get_course_slide(
            course_code="CVL341",
            document_name="Lecture8",
            page_number=1,
            render_image=True,
            high_res=True
        )
        self.assertEqual(res_300["status"], "success")
        self.assertIn("_300dpi.png", res_300["image_path"])
        self.assertTrue(res_300["high_res"])

        # Test out-of-bounds page handling
        res_oob = get_course_slide(
            course_code="CVL341",
            document_name="Lecture8",
            page_number=9999
        )
        self.assertEqual(res_oob["status"], "page_out_of_bounds")
        self.assertIn("out of bounds", res_oob["message"])

    def test_mcp_server_slide_tool(self):
        """Validates get_course_slide returns MCP CallToolResult with TextContent and ImageContent."""
        async def run_tool():
            return await mcp._tool_manager.call_tool(
                "get_course_slide",
                {"course_code": "CVL341", "document_name": "Lecture8", "page_number": 1},
                None,
                convert_result=True
            )

        res = asyncio.run(run_tool())
        self.assertIsInstance(res, CallToolResult)
        self.assertGreaterEqual(len(res.content), 2)
        self.assertIsInstance(res.content[0], TextContent)
        self.assertIsInstance(res.content[1], ImageContent)
        self.assertEqual(res.content[1].mime_type, "image/png")
        self.assertIsNotNone(res.structured_content)
        self.assertEqual(res.structured_content["page_number"], 1)

    def test_fast_sync_parameters(self):
        """Validates course_filter and quick_check parameters in sync_moodle."""
        # Course filter should constrain sync and bypass custom/user scans
        res = sync_moodle(course_filter="CVL341", quick_check=True)
        self.assertIn("status", res)
        # Even if moodle credentials fail/mocked, custom_sources_synced and user_files_found should be 0
        self.assertEqual(res.get("custom_sources_synced", 0), 0)
        self.assertEqual(res.get("user_files_found", 0), 0)

    def test_dual_format_returns(self):
        """Validates that analytical tools return both summary_markdown and structured parameters."""
        # Diagram Tool
        diag_res = moodle_diagram("sfd_bmd")
        self.assertEqual(diag_res["status"], "success")
        self.assertIn("summary_markdown", diag_res)
        self.assertIn("max_bending_moment", diag_res)
        self.assertIn("reactions", diag_res)

    def test_contiguous_derivation_math_classification(self):
        """Validates detection of math, matrix, and derivation keywords."""
        # Derivation query detection
        self.assertTrue(is_derivation_query("Derive the stiffness matrix for beam element"))
        self.assertTrue(is_derivation_query("Explain transformation matrix assembly"))
        self.assertTrue(is_derivation_query("Show that virtual work equals internal work"))
        self.assertFalse(is_derivation_query("Who is the course coordinator?"))

        # Math content detection in slide text
        math_text = r"The global stiffness equation is given by $[K] \{d\} = \{F\}$, where $[K] = [T]^T [k'] [T]$."
        self.assertTrue(has_math_or_derivation_content(math_text))

        latex_matrix = r"\begin{bmatrix} k_{11} & k_{12} \\ k_{21} & k_{22} \end{bmatrix}"
        self.assertTrue(has_math_or_derivation_content(latex_matrix))

        plain_text = "Course logistics: Please submit assignments on Sunday before 11:59 PM."
        self.assertFalse(has_math_or_derivation_content(plain_text))

        # Math-safe text pruning
        pruned = prune_chunk_text(math_text, query="stiffness matrix", max_chars=400)
        self.assertIn("[K]", pruned)
        self.assertFalse(pruned.count('$') % 2 != 0, "LaTeX dollar signs should never be left unclosed")

    def test_dual_mode_ansi_and_spinner_suppression(self):
        """Validates Golden Rule: Dual-Mode Output. ANSI and spinners suppressed for MCP / non-TTY."""
        from src.agent_tools import clean_output_text, CLISpinner
        from src.scraper import colors

        # 1. clean_output_text should strip ANSI escape sequences and \r
        dirty_str = "\r\033[92m[DONE]\033[0m Converted & Indexed: Lecture1.pdf\r\n"
        cleaned = clean_output_text(dirty_str)
        self.assertEqual(cleaned, "[DONE] Converted & Indexed: Lecture1.pdf\n")
        self.assertNotIn("\033", cleaned)
        self.assertNotIn("\r", cleaned)

        # 2. In MCP mode, colors class should evaluate to empty strings
        old_mcp = os.environ.get("MCP_MODE")
        try:
            os.environ["MCP_MODE"] = "1"
            self.assertEqual(colors.OKGREEN, "")
            self.assertEqual(colors.HEADER, "")
            self.assertEqual(colors.ENDC, "")

            # 3. CLISpinner should be disabled in MCP mode
            spinner = CLISpinner("Testing...")
            self.assertTrue(spinner.disabled)
            self.assertIsNone(spinner.thread)
        finally:
            if old_mcp is not None:
                os.environ["MCP_MODE"] = old_mcp
            else:
                os.environ.pop("MCP_MODE", None)


if __name__ == "__main__":
    unittest.main()
