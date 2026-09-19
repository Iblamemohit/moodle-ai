import sqlite3
import json
import time
import re
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

from src.config import WORKSPACE_DIR


def normalize_query_text(query: str) -> str:
    """Normalizes query text: lowercase, strip punctuation, collapse whitespace."""
    q = query.lower()
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def compute_query_hash(query: str, course_filter: Optional[str] = None, doc_filter: Optional[str] = None) -> str:
    """Computes a deterministic MD5 hash for exact query caching."""
    norm_q = normalize_query_text(query)
    c_filter = (course_filter or "").strip().lower()
    d_filter = (doc_filter or "").strip().lower()
    raw = f"{norm_q}::{c_filter}::{d_filter}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class QueryCache:
    """
    Two-Tier Local Query Cache:
    1. In-memory fast LRU cache for current process.
    2. SQLite persistent cache across CLI and MCP process invocations.
    Supports both Exact Match (hash) and Semantic Similarity Match (cosine threshold >= 0.95).
    """

    def __init__(self, db_path: Optional[str] = None, max_memory_entries: int = 128, semantic_threshold: float = 0.95):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(WORKSPACE_DIR) / "data" / "query_cache.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.max_memory_entries = max_memory_entries
        self.semantic_threshold = semantic_threshold

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    normalized_query TEXT NOT NULL,
                    course_filter TEXT,
                    doc_filter TEXT,
                    embedding BLOB,
                    response_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_norm_query ON query_cache(normalized_query)")

    def get(
        self,
        query: str,
        course_filter: Optional[str] = None,
        doc_filter: Optional[str] = None,
        query_embedding: Optional[np.ndarray] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response using exact match first, then semantic match if query_embedding is provided.
        """
        q_hash = compute_query_hash(query, course_filter, doc_filter)

        # 1. Check in-memory cache
        if q_hash in self.memory_cache:
            entry = self.memory_cache[q_hash]
            entry["hit_count"] += 1
            self._increment_db_hits(q_hash)
            cached_data = dict(entry["response"])
            cached_data["from_cache"] = True
            cached_data["cache_match_type"] = "memory_exact"
            return cached_data

        # 2. Check SQLite exact match
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT response_json, hit_count FROM query_cache WHERE query_hash = ?",
            (q_hash,)
        )
        row = cursor.fetchone()
        if row:
            resp_json, hits = row
            try:
                resp_data = json.loads(resp_json)
                self._increment_db_hits(q_hash)
                self._store_memory(q_hash, resp_data)
                resp_data["from_cache"] = True
                resp_data["cache_match_type"] = "sqlite_exact"
                return resp_data
            except Exception:
                pass

        # 3. Semantic Similarity Match (optional, if query_embedding is provided)
        if query_embedding is not None and self.semantic_threshold > 0:
            sem_result = self._semantic_match(query_embedding, course_filter, doc_filter)
            if sem_result:
                sem_result["from_cache"] = True
                sem_result["cache_match_type"] = "semantic_match"
                return sem_result

        return None

    def set(
        self,
        query: str,
        response_dict: Dict[str, Any],
        course_filter: Optional[str] = None,
        doc_filter: Optional[str] = None,
        query_embedding: Optional[np.ndarray] = None
    ):
        """Saves response into memory and SQLite persistent cache."""
        q_hash = compute_query_hash(query, course_filter, doc_filter)
        norm_q = normalize_query_text(query)
        emb_bytes = query_embedding.tobytes() if query_embedding is not None else None

        # Clean response dict to prevent recursive cache metadata
        clean_resp = {k: v for k, v in response_dict.items() if k not in ("from_cache", "cache_match_type")}
        resp_json = json.dumps(clean_resp, ensure_ascii=False)

        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO query_cache
                (query_hash, query_text, normalized_query, course_filter, doc_filter, embedding, response_json, created_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q_hash,
                query,
                norm_q,
                course_filter or "",
                doc_filter or "",
                emb_bytes,
                resp_json,
                time.time(),
                0
            ))

        self._store_memory(q_hash, clean_resp)

    def _store_memory(self, q_hash: str, resp: Dict[str, Any]):
        if len(self.memory_cache) >= self.max_memory_entries:
            # Drop oldest entry
            oldest_k = next(iter(self.memory_cache))
            del self.memory_cache[oldest_k]
        self.memory_cache[q_hash] = {
            "response": resp,
            "hit_count": 0,
            "time": time.time()
        }

    def _increment_db_hits(self, q_hash: str):
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE query_cache SET hit_count = hit_count + 1 WHERE query_hash = ?",
                    (q_hash,)
                )
        except Exception:
            pass

    def _semantic_match(
        self,
        q_vec: np.ndarray,
        course_filter: Optional[str],
        doc_filter: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Scans cached embeddings to find a close match above semantic_threshold."""
        cursor = self.conn.cursor()
        c_filter = course_filter or ""
        d_filter = doc_filter or ""
        cursor.execute(
            "SELECT query_hash, embedding, response_json FROM query_cache WHERE course_filter = ? AND doc_filter = ? AND embedding IS NOT NULL",
            (c_filter, d_filter)
        )
        rows = cursor.fetchall()
        if not rows:
            return None

        best_sim = -1.0
        best_resp_json = None
        best_hash = None

        q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-9)

        for q_hash, emb_blob, resp_json in rows:
            cached_emb = np.frombuffer(emb_blob, dtype=np.float32)
            c_norm = cached_emb / (np.linalg.norm(cached_emb) + 1e-9)
            sim = float(np.dot(q_norm, c_norm))
            if sim > best_sim:
                best_sim = sim
                best_resp_json = resp_json
                best_hash = q_hash

        if best_sim >= self.semantic_threshold and best_resp_json:
            try:
                self._increment_db_hits(best_hash)
                resp = json.loads(best_resp_json)
                resp["semantic_similarity"] = round(best_sim, 4)
                return resp
            except Exception:
                pass

        return None

    def clear(self):
        """Clears both in-memory and SQLite cache."""
        self.memory_cache.clear()
        with self.conn:
            self.conn.execute("DELETE FROM query_cache")


_GLOBAL_QUERY_CACHE = None

def get_query_cache() -> QueryCache:
    """Singleton getter for QueryCache."""
    global _GLOBAL_QUERY_CACHE
    if _GLOBAL_QUERY_CACHE is None:
        _GLOBAL_QUERY_CACHE = QueryCache()
    return _GLOBAL_QUERY_CACHE
