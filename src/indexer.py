import os
import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from src.embeddings import MiniLMEmbeddings

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
            else:
                self.db_path = p.parent / "moodle_knowledge.db"
        else:
            self.db_path = Path("data/moodle_knowledge.db")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

        # Standalone ONNX MiniLM embedding generator
        self.embedding_fn = MiniLMEmbeddings()

        # Markdown-Aware Text Splitter (LangChain)
        self.text_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN,
            chunk_size=1000,
            chunk_overlap=200
        )

        # In-memory BM25 index cache
        self.bm25_corpus: List[Dict[str, Any]] = []
        self.bm25_index: Optional[BM25Okapi] = None
        self._load_bm25_corpus()

        # If database is empty, check if we can migrate from existing ChromaDB
        if self.count() == 0:
            self._try_chroma_migration()

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

    def _try_chroma_migration(self):
        chroma_dir = self.db_path.parent / "chroma_db"
        if chroma_dir.exists():
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(chroma_dir))
                coll = client.get_collection("moodle_course_materials")
                if coll.count() > 0:
                    print(f"[Indexer] [INFO] Migrating {coll.count()} existing chunks from ChromaDB to SQLite...")
                    res = coll.get(include=["documents", "metadatas", "embeddings"])
                    if res and res["ids"]:
                        records = []
                        for cid, text, meta, emb in zip(res["ids"], res["documents"], res["metadatas"], res["embeddings"]):
                            emb_bytes = np.array(emb, dtype=np.float32).tobytes()
                            records.append((
                                cid,
                                text,
                                str(meta.get("source", "")),
                                str(meta.get("filename", "")),
                                str(meta.get("course", "")),
                                str(meta.get("semester", "")),
                                int(meta.get("page", 1)),
                                int(meta.get("chunk_index", 0)),
                                emb_bytes
                            ))
                        with self.conn:
                            self.conn.executemany("""
                                INSERT OR REPLACE INTO chunks
                                (id, text, source, filename, course, semester, page, chunk_index, embedding)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, records)
                        print(f"[Indexer] [OK] Successfully migrated {len(records)} chunks to SQLite.")
                        self._load_bm25_corpus()
            except Exception as e:
                print(f"[Indexer] [INFO] Chroma migration skipped: {e}")

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

        for chunk in page_chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue

            meta = chunk.get("metadata", {})
            sub_chunks = self.text_splitter.split_text(text)

            for i, sub_text in enumerate(sub_chunks):
                chunk_id = f"{meta.get('filename', 'doc')}_p{meta.get('page', 1)}_c{i}_{hash(sub_text) & 0xfffffff}"
                chunk_records.append({
                    "id": chunk_id,
                    "text": sub_text,
                    "source": str(meta.get("source", "")),
                    "filename": str(meta.get("filename", "")),
                    "course": str(meta.get("course", "")),
                    "semester": str(meta.get("semester", "")),
                    "page": int(meta.get("page", 1)),
                    "chunk_index": i
                })
                texts_to_embed.append(sub_text)
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

    def hybrid_search(self, query: str, course_filter: Optional[str] = None, filename_filter: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Executes an Ensemble Hybrid Search (Dense Cosine Similarity + BM25 Lexical)
        combining results with Reciprocal Rank Fusion (RRF).
        """
        total_count = self.count()
        if total_count == 0:
            return []

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
                limit = min(top_k * 3, len(rows))
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
                "bm25_score": 0.0
            }

        # Rank BM25 Results
        sorted_bm25 = sorted(bm25_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        for rank, (b_id, data) in enumerate(sorted_bm25[:top_k * 3]):
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
                    "bm25_score": round(data["score"], 4)
                }

        # Sort combined results by RRF score
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        query_tokens = set(self._tokenize(query))
        
        final_results = []
        for d_id, score in sorted_results[:top_k]:
            item = doc_store[d_id]
            item["rrf_score"] = round(score, 5)
            
            # Check how many distinct significant query keywords appear in this document
            doc_tokens = set(self._tokenize(item["text"]))
            overlap = len(query_tokens.intersection(doc_tokens)) if query_tokens else 0
            overlap_ratio = overlap / len(query_tokens) if query_tokens else 0.0

            # Confident if:
            # 1. Cosine similarity >= 0.50 (semantic match), OR
            # 2. At least 50% of the query keywords are found in the doc and BM25 score >= 3.0
            is_conf = (item["cosine_similarity"] >= 0.50) or (overlap_ratio >= 0.5 and item["bm25_score"] >= 3.0)
            item["is_confident"] = is_conf
            item["keyword_overlap_ratio"] = round(overlap_ratio, 2)
            final_results.append(item)

        return final_results
