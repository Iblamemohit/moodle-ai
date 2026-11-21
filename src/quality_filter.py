#!/usr/bin/env python3
"""
src/quality_filter.py — Pre-Ingestion Slide Quality Gate & Gibberish Sanitizer.

Prevents CAD drawings, vector coordinate dumps, corrupt CID fonts,
and OCR noise from entering the SQLite BM25 and ONNX vector databases.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Tuple, List, Optional
import pymupdf


@dataclass
class QualityAssessment:
    is_acceptable: bool
    is_visual_only: bool
    reason: str

    def __init__(self, is_acceptable: bool, is_visual_only: bool, reason: str, **kwargs):
        self.is_acceptable = is_acceptable
        self.is_visual_only = is_visual_only
        self.reason = reason


class SlideQualityClassifier:
    """Classifies slides and text chunks to detect gibberish, CAD dumps, and corrupted fonts."""

    # Thresholds
    MIN_ALPHANUMERIC_RATIO = 0.35
    MAX_CORRUPT_CHAR_RATIO = 0.05
    MAX_SINGLE_CHAR_WORD_RATIO = 0.50
    MIN_REAL_WORDS_FOR_TEXT_SLIDE = 6
    CAD_DRAWING_THRESHOLD = 80
    CAD_MAX_WORDS = 40

    @classmethod
    def assess_page_quality(cls, page: pymupdf.Page, raw_text: str) -> QualityAssessment:
        """
        Assesses a PDF page directly using layout graphics and extracted text.
        Returns QualityAssessment with decision flags.
        """
        # 1. Count drawings and images
        drawings = page.get_drawings()
        drawing_count = len(drawings)
        images = page.get_images()
        image_count = len(images)

        # 2. Analyze extracted text
        text_clean = raw_text.strip()
        words = re.findall(r'\b[A-Za-z0-9_]+\b', text_clean)
        word_count = len(words)

        # Rule 1: CAD Blueprint / Complex Vector Drawing Detector
        if drawing_count >= cls.CAD_DRAWING_THRESHOLD and word_count <= cls.CAD_MAX_WORDS:
            return QualityAssessment(
                is_acceptable=False,
                is_visual_only=True,
                reason=f"CAD/Vector Drawing ({drawing_count} vector paths, only {word_count} words)"
            )

        # Rule 2: Low-Information or Scanned Image Slide with negligible text
        if word_count < cls.MIN_REAL_WORDS_FOR_TEXT_SLIDE:
            has_visuals = drawing_count > 0 or image_count > 0
            return QualityAssessment(
                is_acceptable=False,
                is_visual_only=has_visuals,
                reason=f"Insufficient text ({word_count} words)"
            )

        # 3. Analyze text quality heuristics
        is_gibberish, reason, _ = cls.is_gibberish_text(text_clean)
        if is_gibberish:
            has_visuals = drawing_count > 5 or image_count > 0
            return QualityAssessment(
                is_acceptable=False,
                is_visual_only=has_visuals,
                reason=reason
            )

        return QualityAssessment(
            is_acceptable=True,
            is_visual_only=False,
            reason="Pristine slide text"
        )

    @classmethod
    def is_gibberish_text(cls, text: str) -> Tuple[bool, str, float]:
        """
        Heuristic test for text quality:
        - Corrupt Unicode / replacement characters
        - Alphanumeric density
        - Decomposed single-character words
        - Extreme HTML/table tag spam
        """
        if not text or not text.strip():
            return True, "Empty text", 0.0

        stripped = text.strip()
        total_len = len(stripped)

        # Check 1: Corrupt Unicode / Control Characters
        corrupt_chars = sum(1 for c in stripped if c == '\ufffd' or (ord(c) < 32 and c not in '\n\r\t'))
        corrupt_ratio = corrupt_chars / total_len
        if corrupt_ratio > cls.MAX_CORRUPT_CHAR_RATIO:
            return True, f"Corrupt encoding ({corrupt_ratio:.1%} replacement/control chars)", 0.0

        # Check 2: Alphanumeric Density Threshold
        alpha_chars = sum(1 for c in stripped if c.isalnum())
        alpha_ratio = alpha_chars / total_len

        # If text is heavily populated by pipes, slashes, br tags, or symbols
        if alpha_ratio < cls.MIN_ALPHANUMERIC_RATIO and total_len > 30:
            return True, f"Low alphanumeric density ({alpha_ratio:.1%} alphanumeric)", alpha_ratio

        # Check 3: Single-Character Word Spam (Decomposed font artifact)
        words = re.findall(r'\b[A-Za-z0-9]+\b', stripped)
        if words and len(words) >= 8:
            single_char_words = sum(1 for w in words if len(w) == 1)
            single_ratio = single_char_words / len(words)
            if single_ratio > cls.MAX_SINGLE_CHAR_WORD_RATIO:
                return True, f"Decomposed font artifact ({single_ratio:.1%} single-letter words)", alpha_ratio

        # Check 4: Coordinate / Number Dump Detector
        words_alpha = [w for w in words if any(c.isalpha() for c in w)]
        if len(words) >= 15 and len(words_alpha) / len(words) < 0.15:
            return True, "Coordinate/numeric table dump without semantic words", alpha_ratio

        return False, "Acceptable text", alpha_ratio

    @classmethod
    def sanitize_markdown_text(cls, text: str) -> str:
        """
        Cleans repetitive lines of non-alphanumeric noise, repeated underscores/pipes,
        and empty markdown tables while preserving valid LaTeX formulas and code blocks.
        """
        if not text:
            return ""

        # Collapse repetitive <br> tags
        text = re.sub(r'(?i)(?:<br\s*/?>\s*){3,}', '<br>', text)

        clean_lines = []
        for line in text.splitlines():
            s_line = line.strip()
            if not s_line:
                clean_lines.append("")
                continue

            # Strip lines that are pure repetitive punctuation
            if re.fullmatch(r'[-_=*~|#\s/\\+.,:;]+', s_line) and len(s_line) > 3:
                # Keep standard markdown hr '---' or table dividers
                if s_line in ('---', '***', '___') or re.fullmatch(r'\|(?:\s*:?---+:?\s*\|)+', s_line):
                    clean_lines.append(s_line)
                continue

            # Strip lines with excessive <br> tag dumps
            if s_line.lower().count('<br>') > 3:
                continue

            clean_lines.append(line)

        # Collapse 3+ consecutive newlines into 2
        return re.sub(r'\n{3,}', '\n\n', "\n".join(clean_lines)).strip()
