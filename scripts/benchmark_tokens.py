#!/usr/bin/env python3
"""
scripts/benchmark_tokens.py - Comprehensive Token Profiling & Benchmarking Suite for moodle-ai.

Measures prompt/context token consumption across cl100k_base (GPT-4) and o200k_base (GPT-4o),
evaluates latency, visual fallback overhead (including vision token calculations),
and simulates a realistic 5-turn student study session.
"""

import os
import sys
import json
import time
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
import tiktoken
import pymupdf

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent_tools import moodle_ask, moodle_quiz
from src.mcp_server import moodle_search_and_ask, generate_practice_quiz_context

# Initialize tokenizers
enc_cl100k = tiktoken.get_encoding("cl100k_base")
enc_o200k = tiktoken.get_encoding("o200k_base")


def count_tokens(text: str) -> Dict[str, int]:
    """Counts tokens using cl100k_base and o200k_base encodings."""
    if not text:
        return {"cl100k": 0, "o200k": 0}
    return {
        "cl100k": len(enc_cl100k.encode(text)),
        "o200k": len(enc_o200k.encode(text))
    }


def estimate_vision_tokens(image_path: str) -> int:
    """
    Estimates multimodal vision tokens based on image dimensions
    using the standard 512x512 tile formula (85 base + 170 per tile).
    """
    try:
        p = Path(image_path)
        if not p.exists():
            return 0
        doc = pymupdf.open(str(p))
        if len(doc) == 0:
            return 0
        page = doc[0]
        rect = page.rect
        w, h = rect.width, rect.height
        doc.close()

        # Step 1: Scale within 2048 x 2048
        max_side = max(w, h)
        if max_side > 2048:
            scale = 2048.0 / max_side
            w = w * scale
            h = h * scale

        # Step 2: Scale shortest side to 768
        min_side = min(w, h)
        if min_side > 768:
            scale = 768.0 / min_side
            w = w * scale
            h = h * scale

        # Step 3: Count 512x512 tiles
        tiles_w = math.ceil(w / 512.0)
        tiles_h = math.ceil(h / 512.0)
        total_tiles = tiles_w * tiles_h

        return 85 + (total_tiles * 170)
    except Exception:
        # Default fallback estimate for typical slide
        return 765


def run_benchmark(save_path: Optional[str] = None) -> Dict[str, Any]:
    """Runs full token benchmark suite and returns detailed metrics."""
    results = {
        "timestamp": time.time(),
        "workflows": {},
        "summary": {}
    }

    print("=" * 70)
    print("moodle-ai Token & Context Benchmark")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Factual Lookup
    # -------------------------------------------------------------
    q_factual = "What year did Gregor Mendel publish his work on inheritance of traits?"
    print(f"\n[1/7] Running Factual Lookup: '{q_factual}'...")
    t0 = time.perf_counter()
    res_factual = moodle_ask(q_factual)
    mcp_factual = moodle_search_and_ask(q_factual)
    lat_factual = (time.perf_counter() - t0) * 1000

    factual_tokens = count_tokens(mcp_factual)
    factual_chunks = len(res_factual.get("moodle_context", []))
    print(f"      -> Chunks retrieved: {factual_chunks}")
    print(f"      -> Tokens (o200k): {factual_tokens['o200k']} | (cl100k): {factual_tokens['cl100k']} | Latency: {lat_factual:.1f}ms")

    results["workflows"]["factual_lookup"] = {
        "query": q_factual,
        "tokens": factual_tokens,
        "latency_ms": round(lat_factual, 2),
        "chunks_retrieved": factual_chunks,
        "payload_chars": len(mcp_factual)
    }

    # -------------------------------------------------------------
    # 2. Conceptual Explanation
    # -------------------------------------------------------------
    q_conceptual = "Explain the core concepts and principles of Mendelian inheritance and allele separation."
    print(f"\n[2/7] Running Conceptual Explanation: '{q_conceptual}'...")
    t0 = time.perf_counter()
    res_conceptual = moodle_ask(q_conceptual)
    mcp_conceptual = moodle_search_and_ask(q_conceptual)
    lat_conceptual = (time.perf_counter() - t0) * 1000

    conceptual_tokens = count_tokens(mcp_conceptual)
    conceptual_chunks = len(res_conceptual.get("moodle_context", []))
    print(f"      -> Chunks retrieved: {conceptual_chunks}")
    print(f"      -> Tokens (o200k): {conceptual_tokens['o200k']} | (cl100k): {conceptual_tokens['cl100k']} | Latency: {lat_conceptual:.1f}ms")

    results["workflows"]["conceptual_explanation"] = {
        "query": q_conceptual,
        "tokens": conceptual_tokens,
        "latency_ms": round(lat_conceptual, 2),
        "chunks_retrieved": conceptual_chunks,
        "payload_chars": len(mcp_conceptual)
    }

    # -------------------------------------------------------------
    # 3. Out-of-Scope Fallback
    # -------------------------------------------------------------
    q_oos = "What is quantum entanglement in supersymmetric quantum electrodynamics?"
    print(f"\n[3/7] Running Out-of-Scope Query (Web Fallback): '{q_oos}'...")
    t0 = time.perf_counter()
    res_oos = moodle_ask(q_oos)
    mcp_oos = moodle_search_and_ask(q_oos)
    lat_oos = (time.perf_counter() - t0) * 1000

    oos_tokens = count_tokens(mcp_oos)
    used_fallback = res_oos.get("used_fallback", False)
    print(f"      -> Used Fallback: {used_fallback}")
    print(f"      -> Tokens (o200k): {oos_tokens['o200k']} | (cl100k): {oos_tokens['cl100k']} | Latency: {lat_oos:.1f}ms")

    results["workflows"]["out_of_scope"] = {
        "query": q_oos,
        "tokens": oos_tokens,
        "latency_ms": round(lat_oos, 2),
        "used_fallback": used_fallback,
        "payload_chars": len(mcp_oos)
    }

    # -------------------------------------------------------------
    # 4. Practice Quiz Generation
    # -------------------------------------------------------------
    course_quiz = "2601-SBL100A"
    print(f"\n[4/7] Running Quiz Context Generation: course '{course_quiz}'...")
    t0 = time.perf_counter()
    res_quiz = moodle_quiz(course=course_quiz, num_questions=3)
    mcp_quiz = generate_practice_quiz_context(course=course_quiz, num_questions=3)
    lat_quiz = (time.perf_counter() - t0) * 1000

    quiz_tokens = count_tokens(mcp_quiz)
    quiz_materials = len(res_quiz.get("materials", []))
    print(f"      -> Materials sampled: {quiz_materials}")
    print(f"      -> Tokens (o200k): {quiz_tokens['o200k']} | (cl100k): {quiz_tokens['cl100k']} | Latency: {lat_quiz:.1f}ms")

    results["workflows"]["quiz_generation"] = {
        "course": course_quiz,
        "tokens": quiz_tokens,
        "latency_ms": round(lat_quiz, 2),
        "materials_count": quiz_materials,
        "payload_chars": len(mcp_quiz)
    }

    # -------------------------------------------------------------
    # 5. Visual Fallback: Non-Visual Query vs. Visual Query
    # -------------------------------------------------------------
    q_non_visual = "What is the phenotypic ratio in a monohybrid cross?"
    print(f"\n[5/7] Testing Visual Fallback Behavior...")
    print(f"      a) Non-visual query: '{q_non_visual}'")
    t0 = time.perf_counter()
    res_non_vis = moodle_ask(q_non_visual)
    vf_non_vis = res_non_vis.get("visual_fallback", {})
    lat_non_vis = (time.perf_counter() - t0) * 1000

    non_vis_triggered = vf_non_vis.get("triggered", False)
    non_vis_images = len(vf_non_vis.get("rendered_pages", []))
    non_vis_vision_tokens = sum(estimate_vision_tokens(p["image_path"]) for p in vf_non_vis.get("rendered_pages", []))
    print(f"         Triggered: {non_vis_triggered} | Rendered images: {non_vis_images} | Vision tokens: {non_vis_vision_tokens}")

    q_visual = "Show me the diagram of the Mendelian inheritance cross"
    print(f"      b) Explicit visual query: '{q_visual}'")
    t0 = time.perf_counter()
    res_vis = moodle_ask(q_visual)
    mcp_vis = moodle_search_and_ask(q_visual)
    vf_vis = res_vis.get("visual_fallback", {})
    lat_vis = (time.perf_counter() - t0) * 1000

    vis_triggered = vf_vis.get("triggered", False)
    vis_images = len(vf_vis.get("rendered_pages", []))
    vis_vision_tokens = sum(estimate_vision_tokens(p["image_path"]) for p in vf_vis.get("rendered_pages", []))
    vis_text_tokens = count_tokens(mcp_vis)
    total_vis_tokens = {
        "cl100k": vis_text_tokens["cl100k"] + vis_vision_tokens,
        "o200k": vis_text_tokens["o200k"] + vis_vision_tokens
    }
    print(f"         Triggered: {vis_triggered} | Rendered images: {vis_images} | Vision tokens: {vis_vision_tokens} | Total o200k: {total_vis_tokens['o200k']}")

    results["workflows"]["visual_fallback"] = {
        "non_visual_query": {
            "query": q_non_visual,
            "triggered": non_vis_triggered,
            "images_rendered": non_vis_images,
            "vision_tokens": non_vis_vision_tokens,
            "latency_ms": round(lat_non_vis, 2)
        },
        "visual_query": {
            "query": q_visual,
            "triggered": vis_triggered,
            "images_rendered": vis_images,
            "vision_tokens": vis_vision_tokens,
            "text_tokens": vis_text_tokens,
            "total_tokens": total_vis_tokens,
            "latency_ms": round(lat_vis, 2)
        }
    }

    # -------------------------------------------------------------
    # 6. Repeat Query (Cache Test)
    # -------------------------------------------------------------
    print(f"\n[6/7] Testing Repeat Query (Caching): '{q_factual}'...")
    t0 = time.perf_counter()
    res_repeat = moodle_ask(q_factual)
    mcp_repeat = moodle_search_and_ask(q_factual)
    lat_repeat = (time.perf_counter() - t0) * 1000

    repeat_tokens = count_tokens(mcp_repeat)
    from_cache = res_repeat.get("from_cache", False)
    print(f"      -> From Cache: {from_cache} | Tokens (o200k): {repeat_tokens['o200k']} | Latency: {lat_repeat:.1f}ms")

    results["workflows"]["repeat_query"] = {
        "query": q_factual,
        "from_cache": from_cache,
        "tokens": repeat_tokens,
        "latency_ms": round(lat_repeat, 2)
    }

    # -------------------------------------------------------------
    # 7. Multi-Turn Session Simulation (5 Turns)
    # -------------------------------------------------------------
    print(f"\n[7/7] Simulating 5-Turn Study Session...")
    session_turns = [
        ("Turn 1: Factual", lambda: moodle_search_and_ask(q_factual)),
        ("Turn 2: Conceptual", lambda: moodle_search_and_ask(q_conceptual)),
        ("Turn 3: Repeat Factual", lambda: moodle_search_and_ask(q_factual)),
        ("Turn 4: Visual Query", lambda: moodle_search_and_ask(q_visual)),
        ("Turn 5: Quiz Context", lambda: generate_practice_quiz_context(course=course_quiz, num_questions=3)),
    ]

    session_text_o200k = 0
    session_text_cl100k = 0
    t0 = time.perf_counter()

    for name, fn in session_turns:
        payload = fn()
        toks = count_tokens(payload)
        session_text_o200k += toks["o200k"]
        session_text_cl100k += toks["cl100k"]

    # Calculate vision tokens for turns that triggered visual fallback
    # In baseline, almost every turn triggers visual fallback if slide has graphics!
    # We accurately sum the vision tokens actually produced during the 5 turns:
    session_vision_tokens = 0
    # Check turns for visual fallback
    for q in [q_factual, q_conceptual, q_factual, q_visual]:
        r = moodle_ask(q)
        vf = r.get("visual_fallback", {})
        if vf.get("triggered"):
            for p in vf.get("rendered_pages", []):
                session_vision_tokens += estimate_vision_tokens(p["image_path"])

    session_total_o200k = session_text_o200k + session_vision_tokens
    session_total_cl100k = session_text_cl100k + session_vision_tokens
    session_lat = (time.perf_counter() - t0) * 1000

    print(f"      -> Cumulative Text Tokens (o200k): {session_text_o200k}")
    print(f"      -> Cumulative Vision Tokens: {session_vision_tokens}")
    print(f"      -> Total Session Tokens (o200k): {session_total_o200k} | Latency: {session_lat:.1f}ms")

    results["workflows"]["session_5_turns"] = {
        "text_tokens": {"cl100k": session_text_cl100k, "o200k": session_text_o200k},
        "vision_tokens": session_vision_tokens,
        "total_tokens": {"cl100k": session_total_cl100k, "o200k": session_total_o200k},
        "latency_ms": round(session_lat, 2)
    }

    # Summary table output
    print("\n" + "=" * 75)
    print("CURRENT RUN SUMMARY (o200k encoding)")
    print("=" * 75)
    print(f"{'Workflow / Component':<35} | {'Tokens (o200k)':<15} | {'Latency':<10}")
    print("-" * 75)
    print(f"{'Factual Lookup (/ask)':<35} | {factual_tokens['o200k']:<15} | {lat_factual:.1f}ms")
    print(f"{'Conceptual (/ask)':<35} | {conceptual_tokens['o200k']:<15} | {lat_conceptual:.1f}ms")
    print(f"{'Out-of-Scope Fallback':<35} | {oos_tokens['o200k']:<15} | {lat_oos:.1f}ms")
    print(f"{'Quiz Generation (/quiz)':<35} | {quiz_tokens['o200k']:<15} | {lat_quiz:.1f}ms")
    print(f"{'Visual Fallback Query (incl vision)':<35} | {total_vis_tokens['o200k']:<15} | {lat_vis:.1f}ms")
    print(f"{'Non-visual Query (vision leak)':<35} | {non_vis_vision_tokens:<15} | {lat_non_vis:.1f}ms")
    print(f"{'Repeat Query':<35} | {repeat_tokens['o200k']:<15} | {lat_repeat:.1f}ms")
    print("-" * 75)
    print(f"{'Overall 5-Turn Session Total':<35} | {session_total_o200k:<15} | {session_lat:.1f}ms")
    print("=" * 75)

    # If baseline benchmark exists and this is an optimized run, print Before vs. After comparison table
    baseline_path = Path("data/baseline_benchmark.json")
    if baseline_path.exists() and save_path and "baseline" not in Path(save_path).name:
        try:
            with open(baseline_path, "r", encoding="utf-8") as bf:
                base_data = json.load(bf)
            base_wf = base_data.get("workflows", {})

            print("\n" + "=" * 80)
            print("TOKEN OPTIMIZATION AUDIT REPORT: BEFORE vs. AFTER COMPARISON")
            print("=" * 80)
            header = f"{'Workflow / Component':<35} | {'Baseline':<10} | {'Optimized':<10} | {'Saved (%)':<10} | {'Latency Impact':<12}"
            print(header)
            print("-" * 80)

            rows = [
                ("Factual Lookup (/ask)",
                 base_wf.get("factual_lookup", {}).get("tokens", {}).get("o200k", 0),
                 factual_tokens['o200k'],
                 base_wf.get("factual_lookup", {}).get("latency_ms", 0),
                 lat_factual),
                ("Conceptual Explanation (/ask)",
                 base_wf.get("conceptual_explanation", {}).get("tokens", {}).get("o200k", 0),
                 conceptual_tokens['o200k'],
                 base_wf.get("conceptual_explanation", {}).get("latency_ms", 0),
                 lat_conceptual),
                ("Out-of-Scope Fallback",
                 base_wf.get("out_of_scope", {}).get("tokens", {}).get("o200k", 0),
                 oos_tokens['o200k'],
                 base_wf.get("out_of_scope", {}).get("latency_ms", 0),
                 lat_oos),
                ("Quiz Generation (/quiz)",
                 base_wf.get("quiz_generation", {}).get("tokens", {}).get("o200k", 0),
                 quiz_tokens['o200k'],
                 base_wf.get("quiz_generation", {}).get("latency_ms", 0),
                 lat_quiz),
                ("Visual Fallback (Visual Intent)",
                 base_wf.get("visual_fallback", {}).get("visual_query", {}).get("total_tokens", {}).get("o200k", 0),
                 total_vis_tokens['o200k'],
                 base_wf.get("visual_fallback", {}).get("visual_query", {}).get("latency_ms", 0),
                 lat_vis),
                ("Non-Visual Slide Query (Leak)",
                 base_wf.get("visual_fallback", {}).get("non_visual_query", {}).get("vision_tokens", 0),
                 non_vis_vision_tokens,
                 base_wf.get("visual_fallback", {}).get("non_visual_query", {}).get("latency_ms", 0),
                 lat_non_vis),
                ("Repeat Query (Cache Hit)",
                 base_wf.get("repeat_query", {}).get("tokens", {}).get("o200k", 0),
                 repeat_tokens['o200k'],
                 base_wf.get("repeat_query", {}).get("latency_ms", 0),
                 lat_repeat),
                ("5-Turn Session Total",
                 base_wf.get("session_5_turns", {}).get("total_tokens", {}).get("o200k", 0),
                 session_total_o200k,
                 base_wf.get("session_5_turns", {}).get("latency_ms", 0),
                 session_lat),
            ]

            for label, b_tok, o_tok, b_lat, o_lat in rows:
                if b_tok > 0:
                    pct_saved = ((b_tok - o_tok) / b_tok) * 100
                    saved_str = f"-{pct_saved:.1f}%" if pct_saved >= 0 else f"+{abs(pct_saved):.1f}%"
                else:
                    saved_str = "0.0%"
                lat_diff = o_lat - b_lat
                lat_str = f"{lat_diff:+.1f}ms ({o_lat:.0f}ms)"
                print(f"{label:<35} | {b_tok:<10} | {o_tok:<10} | {saved_str:<10} | {lat_str:<12}")

            print("=" * 80)
        except Exception as comp_err:
            print(f"[Comparison Warning]: Could not load baseline comparison: {comp_err}")

    if save_path:
        out_path = Path(save_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n[Saved benchmark data to: {out_path}]")

    return results


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "data/optimized_benchmark.json"
    run_benchmark(save_path=out_file)
    import os
    os._exit(0)

