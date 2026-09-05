import os
import sys
import tarfile
import urllib.request
import hashlib
from pathlib import Path
from typing import List, Union
import numpy as np

MODEL_DOWNLOAD_URL = "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz"
MODEL_SHA256 = "9108346672de42656fc9af81d4a03e1e55ec7492c6c1981d77a28e3b5e4ff580"

class MiniLMEmbeddings:
    """
    Lightweight, standalone embedding generator for all-MiniLM-L6-v2.
    Produces 384-dimensional L2-normalized embeddings for exact cosine similarity.
    Requires only onnxruntime, tokenizers, and numpy.
    """

    def __init__(self, cache_dir: Union[str, Path, None] = None):
        if cache_dir:
            self.model_dir = Path(cache_dir)
        else:
            # Check if Chroma already downloaded it previously
            chroma_cache = Path.home() / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2" / "onnx"
            if (chroma_cache / "model.onnx").exists() and (chroma_cache / "tokenizer.json").exists():
                self.model_dir = chroma_cache
            else:
                self.model_dir = Path.home() / ".cache" / "moodle-ai" / "models" / "all-MiniLM-L6-v2" / "onnx"

        self._session = None
        self._tokenizer = None

    def _ensure_model_downloaded(self):
        if (self.model_dir / "model.onnx").exists() and (self.model_dir / "tokenizer.json").exists():
            return

        self.model_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self.model_dir.parent / "onnx.tar.gz"

        print("[Embeddings] [INFO] Downloading lightweight all-MiniLM-L6-v2 model (~80MB)...")
        urllib.request.urlretrieve(MODEL_DOWNLOAD_URL, archive_path)

        # Verify hash
        sha = hashlib.sha256()
        with open(archive_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        if sha.hexdigest() != MODEL_SHA256:
            archive_path.unlink(missing_ok=True)
            raise ValueError("Downloaded model archive failed SHA256 checksum verification.")

        # Extract
        with tarfile.open(archive_path, "r:gz") as tar:
            if sys.version_info >= (3, 12):
                tar.extractall(path=self.model_dir.parent, filter="data")
            else:
                tar.extractall(path=self.model_dir.parent)

        archive_path.unlink(missing_ok=True)
        print("[Embeddings] [OK] Model ready.")

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._ensure_model_downloaded()
            from tokenizers import Tokenizer
            tok_path = self.model_dir / "tokenizer.json"
            self._tokenizer = Tokenizer.from_file(str(tok_path))
            self._tokenizer.enable_truncation(max_length=256)
            self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", length=256)
        return self._tokenizer

    @property
    def session(self):
        if self._session is None:
            self._ensure_model_downloaded()
            import onnxruntime as ort
            model_path = self.model_dir / "model.onnx"
            
            # Suppress verbose ONNX logs
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            providers = ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(str(model_path), sess_options=opts, providers=providers)
        return self._session

    def embed_documents(self, documents: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed a list of text documents.
        Returns a float32 numpy array of shape (N, 384).
        """
        if not documents:
            return np.empty((0, 384), dtype=np.float32)

        all_embs = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            encoded = [self.tokenizer.encode(d) for d in batch]

            input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
            token_type_ids = np.array([e.type_ids for e in encoded], dtype=np.int64)

            outputs = self.session.run(None, {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            })
            last_hidden_state = outputs[0]

            # Mean pooling with attention mask
            input_mask_expanded = np.broadcast_to(
                np.expand_dims(attention_mask, -1), last_hidden_state.shape
            )
            sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
            sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            embs = sum_embeddings / sum_mask

            # L2 normalization for cosine similarity via dot product
            norms = np.linalg.norm(embs, axis=1, keepdims=True)
            embs = embs / np.clip(norms, a_min=1e-9, a_max=None)
            all_embs.append(embs.astype(np.float32))

        return np.concatenate(all_embs, axis=0)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query string.
        Returns a 1D float32 numpy array of shape (384,).
        """
        embs = self.embed_documents([query], batch_size=1)
        return embs[0]
