import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi

COLLECTION_NAME = "moodle_course_materials"

class KnowledgeIndexer:
    def __init__(self, chroma_dir: str):
        self.chroma_dir = Path(chroma_dir)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.chroma_dir))
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Text Splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "]
        )

        # In-memory BM25 index cache
        self.bm25_corpus: List[Dict[str, Any]] = []
        self.bm25_index: Optional[BM25Okapi] = None
        self._load_bm25_corpus()

    def _load_bm25_corpus(self):
        """Loads all existing documents from ChromaDB into BM25 memory."""
        try:
            total = self.collection.count()
            if total == 0:
                self.bm25_corpus = []
                self.bm25_index = None
                return

            # Fetch all documents in batches
            all_docs = self.collection.get(include=["documents", "metadatas"])
            self.bm25_corpus = []
            tokenized_corpus = []

            for doc_id, text, meta in zip(all_docs["ids"], all_docs["documents"], all_docs["metadatas"]):
                item = {
                    "id": doc_id,
                    "text": text,
                    "metadata": meta
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
        Splits page chunks and indexes them into ChromaDB and BM25.
        Purges old chunks for the same source file first to avoid stale duplicates.
        """
        if not page_chunks:
            return 0

        # Group by source file to purge old chunks
        source_paths = {c["metadata"]["source"] for c in page_chunks if "source" in c.get("metadata", {})}
        for src in source_paths:
            self.delete_by_source(src)

        documents = []
        metadatas = []
        ids = []
        count = 0

        for chunk in page_chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue

            meta = chunk.get("metadata", {})
            sub_chunks = self.text_splitter.split_text(text)

            for i, sub_text in enumerate(sub_chunks):
                chunk_id = f"{meta.get('filename', 'doc')}_p{meta.get('page', 1)}_c{i}_{hash(sub_text) & 0xfffffff}"
                
                # Ensure all metadata values are primitive types supported by ChromaDB
                clean_meta = {
                    "source": str(meta.get("source", "")),
                    "filename": str(meta.get("filename", "")),
                    "course": str(meta.get("course", "")),
                    "semester": str(meta.get("semester", "")),
                    "page": int(meta.get("page", 1)),
                    "chunk_index": i
                }

                documents.append(sub_text)
                metadatas.append(clean_meta)
                ids.append(chunk_id)
                count += 1

        if documents:
            # Batch add into ChromaDB (max batch 500)
            batch_size = 500
            for i in range(0, len(documents), batch_size):
                end = min(i + batch_size, len(documents))
                self.collection.add(
                    documents=documents[i:end],
                    metadatas=metadatas[i:end],
                    ids=ids[i:end]
                )
            # Refresh BM25
            self._load_bm25_corpus()

        return count

    def delete_by_source(self, source_path: str):
        """Removes all chunks belonging to a specific source file."""
        try:
            self.collection.delete(where={"source": str(source_path)})
        except Exception:
            pass

    def hybrid_search(self, query: str, course_filter: Optional[str] = None, filename_filter: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Executes an Ensemble Hybrid Search (ChromaDB Dense + BM25 Lexical)
        combining results with Reciprocal Rank Fusion (RRF).
        """
        if self.collection.count() == 0:
            return []

        # 1. ChromaDB Dense Search
        where_clause = None
        if course_filter and filename_filter:
            where_clause = {"$and": [{"course": course_filter}, {"filename": filename_filter}]}
        elif course_filter:
            where_clause = {"course": course_filter}
        elif filename_filter:
            where_clause = {"filename": filename_filter}

        try:
            dense_res = self.collection.query(
                query_texts=[query],
                n_results=min(top_k * 3, self.collection.count()),
                where=where_clause
            )
        except Exception as e:
            dense_res = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

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
        if dense_res.get("ids") and dense_res["ids"][0]:
            for rank, (d_id, text, meta, dist) in enumerate(zip(dense_res["ids"][0], dense_res["documents"][0], dense_res["metadatas"][0], dense_res["distances"][0])):
                # Cosine distance: 0 is identical, 1 is orthogonal, 2 is opposite
                sim = 1.0 - dist if dist is not None else 0.0
                rrf_scores[d_id] = rrf_scores.get(d_id, 0.0) + (1.0 / (RRF_K + rank + 1))
                doc_store[d_id] = {
                    "id": d_id,
                    "text": text,
                    "metadata": meta,
                    "dense_rank": rank + 1,
                    "cosine_similarity": round(sim, 4),
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

    def list_all_indexed_documents(self) -> List[Dict[str, Any]]:
        """Returns a summary of all indexed courses and files."""
        try:
            all_meta = self.collection.get(include=["metadatas"])["metadatas"]
            courses = {}
            for m in all_meta:
                c = m.get("course", "Unknown")
                fn = m.get("filename", "Unknown")
                sem = m.get("semester", "Unknown")
                if c not in courses:
                    courses[c] = {"semester": sem, "files": set()}
                courses[c]["files"].add(fn)

            formatted = []
            for c, data in courses.items():
                formatted.append({
                    "course": c,
                    "semester": data["semester"],
                    "files": sorted(list(data["files"]))
                })
            return sorted(formatted, key=lambda x: x["course"])
        except Exception:
            return []
