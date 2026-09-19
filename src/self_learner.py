#!/usr/bin/env python3
"""
src/self_learner.py — Continuous Self-Learning Engine for moodle-ai.

Persists student corrections and professor-specific rules,
tracks concept mastery across problem-solving drills,
and auto-tunes retrieval without retraining model weights.
"""

import os
import json
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import get_config


class SelfLearner:
    """Manages persistent learned rules, student concept mastery, and retrieval feedback."""

    def __init__(self, workspace_dir: Optional[str] = None):
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
        else:
            cfg = get_config()
            self.workspace_dir = Path(cfg.get("workspace_dir", Path.cwd()))

        self.data_dir = self.workspace_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.rules_path = self.data_dir / "learned_rules.json"
        self.mastery_path = self.data_dir / "mastery_tracker.json"
        self.feedback_path = self.data_dir / "retrieval_feedback.json"

        self._ensure_storage_files()

    def _ensure_storage_files(self):
        """Initializes empty JSON stores if they do not already exist."""
        if not self.rules_path.exists():
            default_rules = {
                "rules": [
                    {
                        "id": "rule_init_1",
                        "course": "CVL245",
                        "topic": "flexure",
                        "rule": "For Fe500, limiting depth of neutral axis xu_max / d = 0.46 (Fe415 is 0.48, Fe250 is 0.53).",
                        "reason": "IS 456:2000 Cl. 38.1 Note",
                        "created_at": datetime.datetime.now().isoformat()
                    },
                    {
                        "id": "rule_init_2",
                        "course": "CVL245",
                        "topic": "doubly_reinforced",
                        "rule": "When calculating steel compression force C_s, always subtract 0.446*f_ck from f_sc: C_s = A_sc * (f_sc - 0.446 * f_ck).",
                        "reason": "Concrete area displaced by compression steel",
                        "created_at": datetime.datetime.now().isoformat()
                    },
                    {
                        "id": "rule_init_3",
                        "course": "CVL341",
                        "topic": "slope_deflection",
                        "rule": "For far end hinged/pinned without settlement, modified stiffness is 3EI/L instead of 4EI/L.",
                        "reason": "Modified slope-deflection formulation",
                        "created_at": datetime.datetime.now().isoformat()
                    }
                ]
            }
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(default_rules, f, indent=2)

        if not self.mastery_path.exists():
            default_mastery = {
                "courses": {
                    "CVL245": {
                        "topics": {
                            "singly_reinforced_flexure": {
                                "attempts": 6,
                                "correct": 5,
                                "mastery_score": 0.83,
                                "recent_mistakes": ["Minor arithmetic slip on lever arm"]
                            },
                            "doubly_reinforced_beams": {
                                "attempts": 4,
                                "correct": 1,
                                "mastery_score": 0.25,
                                "recent_mistakes": [
                                    "Did not verify if compression steel yields",
                                    "Used f_sc = 0.87*fy directly instead of strain table"
                                ]
                            },
                            "shear_reinforcement_spacing": {
                                "attempts": 3,
                                "correct": 1,
                                "mastery_score": 0.33,
                                "recent_mistakes": [
                                    "Forgot maximum spacing limit 0.75*d or 300 mm",
                                    "Did not check tau_c_max vs tau_v"
                                ]
                            }
                        },
                        "overall_score": 0.47
                    },
                    "CVL341": {
                        "topics": {
                            "determinate_trusses": {
                                "attempts": 5,
                                "correct": 5,
                                "mastery_score": 1.0,
                                "recent_mistakes": []
                            },
                            "slope_deflection_frames": {
                                "attempts": 4,
                                "correct": 1,
                                "mastery_score": 0.25,
                                "recent_mistakes": [
                                    "Missed sway equilibrium equation (sum of shear forces = 0)",
                                    "Sign convention error for clockwise fixed-end moments"
                                ]
                            }
                        },
                        "overall_score": 0.62
                    }
                }
            }
            with open(self.mastery_path, "w", encoding="utf-8") as f:
                json.dump(default_mastery, f, indent=2)

        if not self.feedback_path.exists():
            default_feedback = {
                "feedbacks": []
            }
            with open(self.feedback_path, "w", encoding="utf-8") as f:
                json.dump(default_feedback, f, indent=2)

    # -------------------------------------------------------------
    # 1. Learned Rules & Corrections
    # -------------------------------------------------------------

    def learn_rule(self, course: str, topic: str, rule: str, reason: str = "") -> bool:
        """
        Stores a professor-specific or student correction rule permanently.
        Prevents duplicate entries.
        """
        self._ensure_storage_files()
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"rules": []}

        # Normalize course
        m = re.search(r'([A-Za-z]{2,4}\s*\d{3,4}[A-Za-z]?)', course)
        c_norm = m.group(1).replace(" ", "").upper() if m else course.upper()
        t_norm = topic.strip().lower().replace(" ", "_")

        # Check for duplicates
        for r in data.get("rules", []):
            if r.get("course") == c_norm and r.get("rule", "").strip().lower() == rule.strip().lower():
                return False  # Already exists

        new_id = f"rule_{len(data.get('rules', [])) + 1}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        new_rule = {
            "id": new_id,
            "course": c_norm,
            "topic": t_norm,
            "rule": rule.strip(),
            "reason": reason.strip(),
            "created_at": datetime.datetime.now().isoformat()
        }

        data.setdefault("rules", []).append(new_rule)

        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return True

    def get_rules_for_context(self, course: Optional[str] = None, topic: Optional[str] = None, query: Optional[str] = None) -> List[str]:
        """
        Returns relevant learned rules formatted for LLM context injection.
        If query is provided, performs lexical relevance filtering to prevent irrelevant
        rule injection and reduce prompt token overhead.
        """
        self._ensure_storage_files()
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        c_norm = None
        if course:
            m = re.search(r'([A-Za-z]{2,4}\s*\d{3,4}[A-Za-z]?)', course)
            c_norm = m.group(1).replace(" ", "").upper() if m else course.upper()

        t_norm = topic.strip().lower().replace(" ", "_") if topic else None

        # Precompute query terms if query is provided
        query_words = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', query.lower())) if query else None

        matching_rules = []
        for r in data.get("rules", []):
            r_course = r.get("course", "").upper()
            r_topic = r.get("topic", "").lower()

            course_match = (c_norm is None) or (c_norm in r_course) or (r_course in c_norm)
            topic_match = (t_norm is None) or (t_norm in r_topic) or (r_topic in t_norm)

            if not (course_match and topic_match):
                continue

            # If query is provided, verify query relevance to avoid token bloating
            if query_words:
                rule_text = f"{r.get('rule', '')} {r.get('topic', '')} {r.get('reason', '')}".lower()
                rule_words = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', rule_text))
                # If there is no overlap between query and the rule keywords, skip injecting it
                if not (query_words & rule_words):
                    continue

            formatted = f"⚠️ [Rule for {r['course']} / {r['topic']}]: {r['rule']}"
            if r.get("reason"):
                formatted += f" (Basis: {r['reason']})"
            matching_rules.append(formatted)

        return matching_rules

    # -------------------------------------------------------------
    # 2. Concept Mastery Tracker
    # -------------------------------------------------------------

    def record_drill_result(self, course: str, topic: str, is_correct: bool, mistake_summary: Optional[str] = None):
        """
        Records the outcome of a drill or quiz problem, updating attempt count,
        correct count, mastery score, and recent mistake logs.
        """
        self._ensure_storage_files()
        try:
            with open(self.mastery_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"courses": {}}

        m = re.search(r'([A-Za-z]{2,4}\s*\d{3,4}[A-Za-z]?)', course)
        c_norm = m.group(1).replace(" ", "").upper() if m else course.upper()
        t_norm = topic.strip().lower().replace(" ", "_")

        course_data = data.setdefault("courses", {}).setdefault(c_norm, {"topics": {}, "overall_score": 0.0})
        topic_data = course_data["topics"].setdefault(t_norm, {
            "attempts": 0,
            "correct": 0,
            "mastery_score": 0.0,
            "recent_mistakes": []
        })

        topic_data["attempts"] += 1
        if is_correct:
            topic_data["correct"] += 1
        elif mistake_summary:
            topic_data.setdefault("recent_mistakes", []).append(mistake_summary.strip())
            # Keep only the last 5 mistakes
            if len(topic_data["recent_mistakes"]) > 5:
                topic_data["recent_mistakes"] = topic_data["recent_mistakes"][-5:]

        topic_data["mastery_score"] = round(topic_data["correct"] / topic_data["attempts"], 2)

        # Recalculate course overall score
        all_scores = [t["mastery_score"] for t in course_data["topics"].values()]
        if all_scores:
            course_data["overall_score"] = round(sum(all_scores) / len(all_scores), 2)

        with open(self.mastery_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_weakest_topics(self, course: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Returns the top N weakest topics for a course sorted by mastery score (ascending).
        """
        self._ensure_storage_files()
        try:
            with open(self.mastery_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        m = re.search(r'([A-Za-z]{2,4}\s*\d{3,4}[A-Za-z]?)', course)
        c_norm = m.group(1).replace(" ", "").upper() if m else course.upper()

        course_data = data.get("courses", {}).get(c_norm, {})
        topics = course_data.get("topics", {})

        topic_list = []
        for t_name, t_info in topics.items():
            topic_list.append({
                "topic": t_name,
                "mastery_score": t_info.get("mastery_score", 0.0),
                "attempts": t_info.get("attempts", 0),
                "correct": t_info.get("correct", 0),
                "recent_mistakes": t_info.get("recent_mistakes", [])
            })

        # Sort ascending by mastery_score (weakest first)
        topic_list.sort(key=lambda x: (x["mastery_score"], -x["attempts"]))
        return topic_list[:top_n]

    def get_overall_mastery(self, course: str) -> Dict[str, Any]:
        """Returns the full mastery summary for a course."""
        self._ensure_storage_files()
        try:
            with open(self.mastery_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"courses": {}}

        m = re.search(r'([A-Za-z]{2,4}\s*\d{3,4}[A-Za-z]?)', course)
        c_norm = m.group(1).replace(" ", "").upper() if m else course.upper()

        course_data = data.get("courses", {}).get(c_norm, {
            "topics": {},
            "overall_score": 0.0
        })

        return {
            "course": c_norm,
            "overall_score": course_data.get("overall_score", 0.0),
            "total_topics_tracked": len(course_data.get("topics", {})),
            "topics": course_data.get("topics", {})
        }

    # -------------------------------------------------------------
    # 3. Retrieval Feedback Loop
    # -------------------------------------------------------------

    def record_retrieval_feedback(self, query: str, correct_doc: str, was_helpful: bool):
        """
        Stores document feedback to boost or penalize candidate results in future searches.
        """
        self._ensure_storage_files()
        try:
            with open(self.feedback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"feedbacks": []}

        # Normalize query tokens
        q_clean = query.strip().lower()
        doc_clean = Path(correct_doc).name.lower()

        # Update existing feedback or create new
        found = False
        for fb in data.get("feedbacks", []):
            if fb.get("query") == q_clean and fb.get("doc") == doc_clean:
                fb["was_helpful"] = was_helpful
                fb["weight_boost"] = 1.5 if was_helpful else 0.5
                fb["updated_at"] = datetime.datetime.now().isoformat()
                found = True
                break

        if not found:
            data.setdefault("feedbacks", []).append({
                "query": q_clean,
                "doc": doc_clean,
                "was_helpful": was_helpful,
                "weight_boost": 1.5 if was_helpful else 0.5,
                "created_at": datetime.datetime.now().isoformat()
            })

        with open(self.feedback_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def apply_retrieval_boost(self, query: str, candidate_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Adjusts candidate search result scores based on historical feedback.
        """
        self._ensure_storage_files()
        try:
            with open(self.feedback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return candidate_results

        feedbacks = data.get("feedbacks", [])
        if not feedbacks or not candidate_results:
            return candidate_results

        q_lower = query.lower()
        query_words = set(re.findall(r'\w+', q_lower))

        # Build document boost map for relevant feedbacks
        doc_boosts: Dict[str, float] = {}
        for fb in feedbacks:
            fb_q_words = set(re.findall(r'\w+', fb.get("query", "")))
            # Check overlap of significant words
            overlap = query_words.intersection(fb_q_words)
            if len(overlap) >= 2 or (len(query_words) <= 2 and len(overlap) >= 1):
                doc_name = fb.get("doc", "").lower()
                doc_boosts[doc_name] = fb.get("weight_boost", 1.0)

        if not doc_boosts:
            return candidate_results

        boosted_results = []
        for item in candidate_results:
            item_copy = item.copy()
            filename = Path(item.get("filename", "") or item.get("file", "")).name.lower()
            
            boost = 1.0
            for doc_pattern, b_val in doc_boosts.items():
                if doc_pattern in filename or filename in doc_pattern:
                    boost = max(boost, b_val)

            # Apply boost to score
            orig_score = item_copy.get("score", 1.0)
            item_copy["score"] = orig_score * boost
            if boost != 1.0:
                item_copy["boosted_by_learner"] = boost

            boosted_results.append(item_copy)

        # Re-sort by boosted score descending
        boosted_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return boosted_results
