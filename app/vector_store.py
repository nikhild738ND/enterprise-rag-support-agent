from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.db import query_all, query_one


class LocalFaissIndex:
    def __init__(self) -> None:
        self.model = SentenceTransformer(settings.embedding_model)
        self.index = None
        self.id_map: list[str] = []
        self._load()

    def _load(self) -> None:
        if settings.faiss_index_path.exists() and settings.faiss_id_map_path.exists():
            self.index = faiss.read_index(str(settings.faiss_index_path))
            self.id_map = json.loads(settings.faiss_id_map_path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        if self.index is None:
            return
        faiss.write_index(self.index, str(settings.faiss_index_path))
        settings.faiss_id_map_path.write_text(
            json.dumps(self.id_map, indent=2), encoding="utf-8"
        )

    def rebuild(self) -> dict[str, int]:
        rows = query_all("SELECT chunk_id, doc_id, text FROM chunks ORDER BY id")
        if not rows:
            self.index = None
            self.id_map = []
            return {"chunks_indexed": 0}

        texts = [row["text"] for row in rows]
        vectors = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        matrix = np.array(vectors, dtype="float32")
        self.index = faiss.IndexFlatIP(matrix.shape[1])
        self.index.add(matrix)
        self.id_map = [row["chunk_id"] for row in rows]
        self._save()
        return {"chunks_indexed": len(rows)}

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        if self.index is None or not self.id_map:
            return []
        qvec = self.model.encode([query], normalize_embeddings=True)
        scores, positions = self.index.search(np.array(qvec, dtype="float32"), top_k)
        results: list[dict] = []
        for score, pos in zip(scores[0], positions[0]):
            if pos < 0 or pos >= len(self.id_map):
                continue
            chunk_id = self.id_map[pos]
            row = query_one(
                """
                SELECT c.chunk_id, c.doc_id, c.chunk_index, c.text, d.title
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE c.chunk_id = ?
                """,
                (chunk_id,),
            )
            if row:
                row["score"] = round(float(score), 4)
                row["source_id"] = row["chunk_id"]
                results.append(row)
        return results


_INDEX: LocalFaissIndex | None = None


def get_vector_index() -> LocalFaissIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = LocalFaissIndex()
    return _INDEX
