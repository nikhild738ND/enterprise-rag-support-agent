from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    source_docs_dir: Path = BASE_DIR / "data" / "source_docs"
    eval_dir: Path = BASE_DIR / "data" / "eval"
    db_dir: Path = BASE_DIR / "data" / "db"
    artifacts_dir: Path = BASE_DIR / "data" / "artifacts"
    sqlite_path: Path = BASE_DIR / "data" / "db" / "rag_agent.db"
    faiss_index_path: Path = BASE_DIR / "data" / "artifacts" / "chunks.faiss"
    faiss_id_map_path: Path = BASE_DIR / "data" / "artifacts" / "chunk_ids.json"
    llm_model: str = os.getenv("LLM_MODEL", "")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "700"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    prompt_cost_per_1k: float = float(os.getenv("PROMPT_COST_PER_1K", "0.0"))
    completion_cost_per_1k: float = float(os.getenv("COMPLETION_COST_PER_1K", "0.0"))


settings = Settings()

for path in [
    settings.data_dir,
    settings.source_docs_dir,
    settings.eval_dir,
    settings.db_dir,
    settings.artifacts_dir,
]:
    path.mkdir(parents=True, exist_ok=True)
