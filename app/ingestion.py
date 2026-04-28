from __future__ import annotations

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.db import init_db, upsert_document
from app.parsing import parse_document
from app.vector_store import get_vector_index


def _split_text(doc_id: str, text: str) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    pieces = splitter.split_text(text)
    return [
        {
            "chunk_id": f"{doc_id}::chunk_{idx:03d}",
            "doc_id": doc_id,
            "chunk_index": idx,
            "text": piece.strip(),
            "token_estimate": max(1, len(piece.split())),
        }
        for idx, piece in enumerate(pieces)
        if piece.strip()
    ]


def ingest_paths(paths: list[str]) -> dict:
    init_db()
    ingested = []
    errors = []

    for raw_path in paths:
        try:
            path = Path(raw_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {raw_path}")
            parsed = parse_document(str(path))
            chunks = _split_text(parsed["doc_id"], parsed["text"])
            upsert_document(
                doc_id=parsed["doc_id"],
                title=parsed["title"],
                source_path=parsed["source_path"],
                source_type=parsed["source_type"],
                content_hash=parsed["content_hash"],
                chunks=chunks,
            )
            ingested.append(
                {
                    "doc_id": parsed["doc_id"],
                    "title": parsed["title"],
                    "chunks": len(chunks),
                    "source_path": parsed["source_path"],
                }
            )
        except Exception as exc:
            errors.append({"path": raw_path, "error": str(exc)})

    index_stats = get_vector_index().rebuild()
    return {
        "ingested_count": len(ingested),
        "index_stats": index_stats,
        "documents": ingested,
        "errors": errors,
    }
