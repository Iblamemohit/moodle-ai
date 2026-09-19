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

from src.quality_filter import SlideQualityClassifier
from src.self_learner import SelfLearner


class TestQualityFilter(unittest.TestCase):

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

    def test_query_aware_rule_filtering(self):
        sl = SelfLearner()
        # Learn a test rule for CVL245
        sl.learn_rule(
            course="CVL245",
            topic="shear_design",
            rule="Always use 0.75*d or 300 mm as maximum spacing for vertical stirrups",
            reason="IS 456 Clause 26.5.1.5"
        )

        # Relevant query should match
        rules_relevant = sl.get_rules_for_context(course="CVL245", query="shear stirrups spacing")
        self.assertTrue(any("shear_design" in r or "stirrups" in r for r in rules_relevant))

        # Completely unrelated query should be filtered out to save prompt tokens
        rules_unrelated = sl.get_rules_for_context(course="CVL245", query="chlorophyll photosynthesis in plants")
        self.assertEqual(len(rules_unrelated), 0)

        # Without query, all course rules should be returned
        rules_all = sl.get_rules_for_context(course="CVL245")
        self.assertGreater(len(rules_all), 0)


if __name__ == "__main__":
    unittest.main()
