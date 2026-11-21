#!/usr/bin/env python3
"""
tests/test_quality_filter.py — Unit tests for SlideQualityClassifier, gibberish filtering,
and query-aware rule filtering.
"""

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.quality_filter import SlideQualityClassifier, QualityAssessment


class TestQualityFilter(unittest.TestCase):

    def test_quality_assessment_fields(self):
        qa = QualityAssessment(is_acceptable=True, is_visual_only=False, reason="Pristine slide text")
        self.assertTrue(qa.is_acceptable)
        self.assertFalse(qa.is_visual_only)
        self.assertEqual(qa.reason, "Pristine slide text")

    def test_clean_text_passes(self):
        clean_text = (
            "Calculate the ultimate moment of resistance for a singly reinforced beam "
            "of width 250 mm and effective depth 450 mm using IS 456:2000 provisions. "
            "Assume M20 concrete and Fe 415 grade steel."
        )
        is_gibberish, reason, alpha_ratio = SlideQualityClassifier.is_gibberish_text(clean_text)
        self.assertFalse(is_gibberish, f"Clean text should not be gibberish: {reason}")
        self.assertGreater(alpha_ratio, 0.70)

    def test_corrupt_unicode_detected(self):
        corrupt_text = "Analysis of \ufffd\ufffd\ufffd\ufffd structural \ufffd\ufffd members \ufffd\ufffd"
        is_gibberish, reason, _ = SlideQualityClassifier.is_gibberish_text(corrupt_text)
        self.assertTrue(is_gibberish)
        self.assertIn("Corrupt encoding", reason)

    def test_low_alphanumeric_density_detected(self):
        noisy_table = "| --- | --- | --- | --- |\n| / / / | \\ \\ \\ | _ _ _ | | |\n| * * * | --- | + + + | == |"
        is_gibberish, reason, _ = SlideQualityClassifier.is_gibberish_text(noisy_table)
        self.assertTrue(is_gibberish)
        self.assertIn("Low alphanumeric density", reason)

    def test_decomposed_font_artifact_detected(self):
        decomposed_text = "C O N S T R U C T I O N P L A N N I N G A N D M A N A G E M E N T"
        is_gibberish, reason, _ = SlideQualityClassifier.is_gibberish_text(decomposed_text)
        self.assertTrue(is_gibberish)
        self.assertIn("Decomposed font artifact", reason)

    def test_sanitize_markdown_text(self):
        dirty_input = (
            "# Lecture Title\n"
            "---------------------\n"
            ".....................\n"
            "Valid paragraph describing moment distribution method.\n"
            "<br><br><br><br><br><br>\n"
            "$$M_u = 0.36 f_{ck} b x_u (d - 0.42 x_u)$$\n"
        )
        sanitized = SlideQualityClassifier.sanitize_markdown_text(dirty_input)
        self.assertIn("Valid paragraph describing moment distribution method.", sanitized)
        self.assertIn("$$M_u = 0.36 f_{ck} b x_u (d - 0.42 x_u)$$", sanitized)
        self.assertNotIn("---------------------", sanitized)
        self.assertNotIn(".....................", sanitized)
        self.assertNotIn("<br><br><br><br>", sanitized)


if __name__ == "__main__":
    unittest.main()
