import os
import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from src.embeddings import MiniLMEmbeddings


class MarkdownTextSplitter:
    """
    Lightweight, dependency-free Markdown recursive text splitter.
    Splits along headers, paragraphs, and lines with configurable overlap.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text or len(text) <= self.chunk_size:
            return [text.strip()] if text and text.strip() else []

        separators = ["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " "]
        return self._split(text, separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size or not separators:
            return [text.strip()] if text.strip() else []

        sep = separators[0]
        remaining_seps = separators[1:]
        parts = text.split(sep)

        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for idx, part in enumerate(parts):
            token = (sep + part) if idx > 0 and not sep.startswith("\n#") else part
            token_len = len(token)

            if token_len > self.chunk_size:
                if current:
                    chunks.append("".join(current).strip())
                    current = []
                    current_len = 0
                sub_chunks = self._split(token, remaining_seps)
                chunks.extend(sub_chunks)
            elif current_len + token_len <= self.chunk_size:
                current.append(token)
                current_len += token_len
            else:
                chunks.append("".join(current).strip())
                overlap_tokens: List[str] = []
                overlap_len = 0
                for prev in reversed(current):
                    if overlap_len + len(prev) <= self.chunk_overlap:
                        overlap_tokens.insert(0, prev)
                        overlap_len += len(prev)
                    else:
                        break
                current = overlap_tokens + [token]
                current_len = overlap_len + token_len

        if current:
            cleaned = "".join(current).strip()
            if cleaned:
                chunks.append(cleaned)

        return [c for c in chunks if c]

def prune_chunk_text(text: str, query: str = "", max_chars: int = 450) -> str:
    """
    Returns clean, intact chunk text without mid-equation butchering.
    Collapses excessive newlines while preserving formatting and formulas.
    """
    if not text:
        return ""
    return re.sub(r"\n{3,}", "\n\n", text.strip())


DERIVATION_KEYWORDS = (
    "derivation", "derive", "prove", "proof", "theorem", "show that", "deduce",
    "stiffness matrix", "transformation matrix", "matrix assembly", "assembly",
    "shape function", "shape functions", "equilibrium equation", "equilibrium equations",
    "governing equation", "governing equations", "formulation", "constitutive",
    "differential equation", "virtual work", "stress block", "moment distribution",
    "compatibility", "boundary condition", "solution derivation"
)


def is_derivation_query(query: str) -> bool:
    """
    Detects whether a user query requires complete mathematical derivation context
    to trigger parent-child window expansion (3 contiguous slide pages).
    """
    if not query:
        return False
    q_lower = query.lower()
    return any(k in q_lower for k in DERIVATION_KEYWORDS)


MATH_PATTERNS = [
    r"\$\$[\s\S]+?\$\$",                                                # display math blocks
    r"\\begin\{(?:bmatrix|pmatrix|matrix|align|equation|gather)\*?\}", # matrix and equation environments
    r"\\(?:frac|int|iint|sum|prod|partial|sqrt|nabla)\b",              # calculus and math operators
    r"\[(?:[Kk]|[Tt]|[Mm]|[Cc])\]",                                     # structural matrix notations [K], [k], [T], [M], [C]
    r"\{(?:[dD]|[Ff]|[Uu]|[Qq]|[rR])\}",                                # displacement and force vectors {d}, {F}, {u}, {q}
    r"\b[A-Za-z]+_[A-Za-z0-9]+\s*=\s*",                                 # indexed equations like k_11 =, M_BA =
    r"\\(?:mathbf|boldsymbol|mathbb)\b",                                # vector/tensor notation
]


def has_math_or_derivation_content(text: str) -> bool:
    """
    Detects whether a chunk of text contains complex mathematics, structural matrices,
    or derivation formulations that warrant contiguous tri-page window expansion.
    """
    if not text:
        return False
    for pattern in MATH_PATTERNS:
        if re.search(pattern, text):
            return True
    
    # Dense inline math occurrences (3+ inline $...$ expressions)
    inline_math = re.findall(r"\$[^$\n]+\$", text)
    if len(inline_math) >= 3:
        return True

    return False



class KnowledgeIndexer:
    """
    Lightweight Hybrid Vector + Lexical Search Indexer using SQLite, NumPy, and BM25.
    Zero dependency on ChromaDB or client-server databases.
    """

    def __init__(self, db_path_or_dir: Optional[str] = None):
        if db_path_or_dir:
            p = Path(db_path_or_dir)
            if p.suffix == ".db":
                self.db_path = p
            elif p.name == "chroma_db":
                self.db_path = p.parent / "moodle_knowledge.db"
            else:
                self.db_path = p / "moodle_knowledge.db" if p.is_dir() else p
        else:
            self.db_path = Path("data/moodle_knowledge.db")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

        # Standalone ONNX MiniLM embedding generator
        self.embedding_fn = MiniLMEmbeddings()

        # Markdown-Aware Text Splitter (Native, stdlib)
        self.text_splitter = MarkdownTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        # In-memory BM25 index cache
        self.bm25_corpus: List[Dict[str, Any]] = []
        self.bm25_index: Optional[BM25Okapi] = None
        self._load_bm25_corpus()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    course TEXT NOT NULL,
                    semester TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    embedding BLOB NOT NULL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_course ON chunks(course)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_filename ON chunks(filename)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")

    def count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        row = cursor.fetchone()
        return row[0] if row else 0

    def _load_bm25_corpus(self):
        """Loads all existing documents from SQLite into BM25 memory."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, text, source, filename, course, semester, page, chunk_index FROM chunks")
            rows = cursor.fetchall()
            if not rows:
                self.bm25_corpus = []
                self.bm25_index = None
                return

            self.bm25_corpus = []
            tokenized_corpus = []

            for row in rows:
                doc_id, text, source, filename, course, semester, page, chunk_index = row
                item = {
                    "id": doc_id,
                    "text": text,
                    "metadata": {
                        "source": source,
                        "filename": filename,
                        "course": course,
                        "semester": semester,
                        "page": page,
                        "chunk_index": chunk_index
                    }
                }
                self.bm25_corpus.append(item)
                tokens = self._tokenize(text)
                tokenized_corpus.append(tokens)

            if tokenized_corpus:
                self.bm25_index = BM25Okapi(tokenized_corpus)
        except Exception as e:
            print(f"[Indexer Warning] Could not load BM25 corpus: {e}")
            self.bm25_corpus = []
            self.bm25_index = None

    def _tokenize(self, text: str) -> List[str]:
        """Lowercase word tokenizer filtering common stop words for BM25."""
        stop_words = {'what', 'is', 'the', 'of', 'in', 'and', 'to', 'a', 'for', 'on', 'how', 'it', 'are', 'as', 'by', 'an', 'be', 'at', 'with', 'or', 'from', 'this', 'that', 'which', 'do', 'does', 'can', 'we', 'i', 'you'}
        return [w.lower() for w in re.findall(r'\w+', text) if len(w) > 1 and w.lower() not in stop_words]

    def index_parsed_chunks(self, page_chunks: List[Dict[str, Any]]) -> int:
        """
        Splits page chunks and indexes them into SQLite and BM25.
        Purges old chunks for the same source file first to avoid stale duplicates.
        """
        if not page_chunks:
            return 0

        # Group by source file to purge old chunks
        source_paths = {c["metadata"]["source"] for c in page_chunks if "source" in c.get("metadata", {})}
        for src in source_paths:
            self.delete_by_source(src)

        chunk_records = []
        texts_to_embed = []
        count = 0

        from src.quality_filter import SlideQualityClassifier

        for chunk in page_chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue

            is_gib, _, _ = SlideQualityClassifier.is_gibberish_text(text)
            if is_gib:
                continue

            meta = chunk.get("metadata", {})
            sub_chunks = self.text_splitter.split_text(text)

            for i, sub_text in enumerate(sub_chunks):
                clean_sub = SlideQualityClassifier.sanitize_markdown_text(sub_text)
                if not clean_sub:
                    continue
                is_sub_gib, _, _ = SlideQualityClassifier.is_gibberish_text(clean_sub)
                if is_sub_gib:
                    continue

                chunk_id = f"{meta.get('filename', 'doc')}_p{meta.get('page', 1)}_c{i}_{hash(clean_sub) & 0xfffffff}"
                chunk_records.append({
                    "id": chunk_id,
                    "text": clean_sub,
                    "source": str(meta.get("source", "")),
                    "filename": str(meta.get("filename", "")),
                    "course": str(meta.get("course", "")),
                    "semester": str(meta.get("semester", "")),
                    "page": int(meta.get("page", 1)),
                    "chunk_index": i
                })
                texts_to_embed.append(clean_sub)
                count += 1

        if chunk_records:
            # Batch generate embeddings via standalone ONNX model
            embs = self.embedding_fn.embed_documents(texts_to_embed, batch_size=32)
            
            records_to_insert = []
            for item, emb_vec in zip(chunk_records, embs):
                records_to_insert.append((
                    item["id"],
                    item["text"],
                    item["source"],
                    item["filename"],
                    item["course"],
                    item["semester"],
                    item["page"],
                    item["chunk_index"],
                    emb_vec.tobytes()
                ))

            with self.conn:
                self.conn.executemany("""
                    INSERT OR REPLACE INTO chunks
                    (id, text, source, filename, course, semester, page, chunk_index, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, records_to_insert)

            # Refresh BM25
            self._load_bm25_corpus()

        return count

    def delete_by_source(self, source_path: str):
        """Removes all chunks belonging to a specific source file."""
        try:
            with self.conn:
                self.conn.execute("DELETE FROM chunks WHERE source = ?", (str(source_path),))
        except Exception:
            pass
    def _get_ranker(self):
        """Lazily initializes the flashrank Ranker."""
        if not hasattr(self, "_ranker"):
            self._ranker = None
            try:
                from flashrank import Ranker
                self._ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")
            except Exception as e:
                print(f"[Indexer Warning] Flashrank reranker not available, falling back: {e}")
        return self._ranker

    def hybrid_search(self, query: str, course_filter: Optional[str] = None, filename_filter: Optional[str] = None, top_k: int = 2, prune_text: bool = True) -> List[Dict[str, Any]]:
        """
        Executes an Ensemble Hybrid Search (Dense Cosine Similarity + BM25 Lexical)
        with FlashRank Cross-Encoder Re-ranking and high-density paragraph pruning.
        """
        total_count = self.count()
        if total_count == 0:
            return []

        # Candidate pool size: gather enough candidates for cross-encoder reranking
        candidate_k = max(top_k * 3, 6)

        # 1. Dense Cosine Search via NumPy
        dense_results = []
        try:
            q_vec = self.embedding_fn.embed_query(query)
            
            sql = "SELECT id, text, source, filename, course, semester, page, chunk_index, embedding FROM chunks"
            params = []
            conditions = []
            if course_filter:
                conditions.append("course = ?")
                params.append(course_filter)
            if filename_filter:
                conditions.append("filename = ?")
                params.append(filename_filter)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            cursor = self.conn.cursor()
            rows = cursor.execute(sql, params).fetchall()

            if rows:
                # Reconstruct candidate embeddings matrix
                embs_raw = b"".join(r[8] for r in rows)
                matrix = np.frombuffer(embs_raw, dtype=np.float32).reshape(len(rows), 384)
                
                # Dot product calculates exact cosine similarity (both are L2-normalized)
                sims = matrix @ q_vec
                
                # Top dense candidates
                limit = min(candidate_k, len(rows))
                top_dense_idx = np.argsort(sims)[::-1][:limit]

                for rank_idx, r_idx in enumerate(top_dense_idx):
                    row = rows[r_idx]
                    dense_results.append({
                        "id": row[0],
                        "text": row[1],
                        "metadata": {
                            "source": row[2],
                            "filename": row[3],
                            "course": row[4],
                            "semester": row[5],
                            "page": row[6],
                            "chunk_index": row[7]
                        },
                        "rank": rank_idx + 1,
                        "cosine_similarity": float(sims[r_idx])
                    })
        except Exception as e:
            print(f"[Indexer Warning] Dense search failed: {e}")
            dense_results = []

        # 2. BM25 Lexical Search
        bm25_scores = {}
        if self.bm25_index and self.bm25_corpus:
            query_tokens = self._tokenize(query)
            if query_tokens:
                doc_scores = self.bm25_index.get_scores(query_tokens)
                for idx, score in enumerate(doc_scores):
                    if score > 0:
                        doc = self.bm25_corpus[idx]
                        doc_meta = doc["metadata"]
                        
                        # Apply filters to BM25
                        if course_filter and doc_meta.get("course") != course_filter:
                            continue
                        if filename_filter and doc_meta.get("filename") != filename_filter:
                            continue
                            
                        bm25_scores[doc["id"]] = {
                            "score": float(score),
                            "doc": doc
                        }

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        doc_store = {}
        RRF_K = 60

        # Rank Dense Results
        for item in dense_results:
            d_id = item["id"]
            rank = item["rank"]
            rrf_scores[d_id] = rrf_scores.get(d_id, 0.0) + (1.0 / (RRF_K + rank))
            doc_store[d_id] = {
                "id": d_id,
                "text": item["text"],
                "metadata": item["metadata"],
                "dense_rank": rank,
                "cosine_similarity": round(item["cosine_similarity"], 4),
                "bm25_score": 0.0,
                "rerank_score": 0.0
            }

        # Rank BM25 Results
        sorted_bm25 = sorted(bm25_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        for rank, (b_id, data) in enumerate(sorted_bm25[:candidate_k]):
            rrf_scores[b_id] = rrf_scores.get(b_id, 0.0) + (1.0 / (RRF_K + rank + 1))
            if b_id in doc_store:
                doc_store[b_id]["bm25_rank"] = rank + 1
                doc_store[b_id]["bm25_score"] = round(data["score"], 4)
            else:
                doc_store[b_id] = {
                    "id": b_id,
                    "text": data["doc"]["text"],
                    "metadata": data["doc"]["metadata"],
                    "dense_rank": None,
                    "cosine_similarity": 0.0,
                    "bm25_rank": rank + 1,
                    "bm25_score": round(data["score"], 4),
                    "rerank_score": 0.0
                }

        # Sort candidates by RRF score
        sorted_by_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:candidate_k]

        # 4. Cross-Encoder Re-ranking via FlashRank
        ranker = self._get_ranker()
        if ranker and sorted_by_rrf:
            try:
                from flashrank import RerankRequest
                passages = [{"id": d_id, "text": doc_store[d_id]["text"]} for d_id, _ in sorted_by_rrf]
                rerank_req = RerankRequest(query=query, passages=passages)
                rerank_results = ranker.rerank(rerank_req)
                
                # Update rerank scores
                for res_item in rerank_results:
                    r_id = res_item["id"]
                    if r_id in doc_store:
                        doc_store[r_id]["rerank_score"] = round(float(res_item["score"]), 4)
                
                # Order by rerank score
                candidate_ids = [res_item["id"] for res_item in rerank_results]
            except Exception as ex:
                print(f"[Indexer Warning] Flashrank rerank failed, using RRF: {ex}")
                candidate_ids = [d_id for d_id, _ in sorted_by_rrf]
        else:
            candidate_ids = [d_id for d_id, _ in sorted_by_rrf]

        query_tokens = set(self._tokenize(query))
        
        # 5. Intent Detection: Derivation Windowing & Math Preservation
        is_query_derivation = is_derivation_query(query)
        covered_window_pages = set()

        final_results = []
        for d_id in candidate_ids:
            if len(final_results) >= top_k:
                break

            item = doc_store[d_id]
            meta = item["metadata"]
            source = meta.get("source")
            page = meta.get("page", 1)

            # Avoid adding duplicate chunks already fully included in an earlier window of the same document
            if source and (source, page) in covered_window_pages and len(final_results) > 0:
                continue

            item["rrf_score"] = round(rrf_scores.get(d_id, 0.0), 5)

            # Text pruning vs Derivation Window Expansion
            raw_text = item["text"]
            item["raw_text"] = raw_text

            is_chunk_math = has_math_or_derivation_content(raw_text)
            should_window = (is_query_derivation or is_chunk_math) and source

            if should_window:
                # Parent-Child Windowing: Fetch contiguous 3-page window (page - 1, page, page + 1)
                try:
                    cursor = self.conn.cursor()
                    p_start = max(1, page - 1)
                    p_end = page + 1
                    contiguous_rows = cursor.execute(
                        "SELECT page, chunk_index, text FROM chunks WHERE source = ? AND page BETWEEN ? AND ? ORDER BY page ASC, chunk_index ASC",
                        (source, p_start, p_end)
                    ).fetchall()

                    if contiguous_rows and len(contiguous_rows) > 1:
                        windowed_parts = []
                        current_p = None
                        for cp, _, ctext in contiguous_rows:
                            if cp != current_p:
                                windowed_parts.append(f"\n<!-- Derivation Context: Page {cp} -->\n")
                                current_p = cp
                            windowed_parts.append(ctext.strip())
                            covered_window_pages.add((source, cp))
                        item["text"] = "\n".join(windowed_parts).strip()
                        item["is_derivation_window"] = True
                        item["window_pages"] = [p_start, page, p_end]
                    else:
                        item["text"] = raw_text
                except Exception as w_err:
                    print(f"[Indexer Warning] Windowing failed: {w_err}")
                    item["text"] = raw_text
            elif prune_text:
                item["text"] = prune_chunk_text(raw_text, query, max_chars=450)
            else:
                item["text"] = raw_text

            # Check distinct query keywords in doc
            doc_tokens = set(self._tokenize(raw_text))
            overlap = len(query_tokens.intersection(doc_tokens)) if query_tokens else 0
            overlap_ratio = overlap / len(query_tokens) if query_tokens else 0.0

            # Confidence determination:
            # 1. FlashRank cross-encoder rerank_score >= 0.20, OR
            # 2. Cosine similarity >= 0.50, OR
            # 3. Keyword overlap >= 50% and BM25 >= 3.0
            is_conf = (item["rerank_score"] >= 0.20) or (item["cosine_similarity"] >= 0.50) or (overlap_ratio >= 0.5 and item["bm25_score"] >= 3.0)
            item["is_confident"] = is_conf
            item["keyword_overlap_ratio"] = round(overlap_ratio, 2)
            final_results.append(item)

        return final_results


