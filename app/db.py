from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from typing import Any, Iterable

from app.config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id TEXT NOT NULL UNIQUE,
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_estimate INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL UNIQUE,
    session_id TEXT,
    mode TEXT NOT NULL,
    question TEXT NOT NULL,
    system_prompt TEXT,
    prompt_text TEXT,
    retrieved_sources_json TEXT,
    tool_calls_json TEXT,
    raw_output TEXT,
    answer TEXT,
    citations_json TEXT,
    grounding_score REAL,
    latency_ms REAL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    estimated_cost_usd REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    thumb TEXT NOT NULL,
    issue_tags_json TEXT,
    comment TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    modes_json TEXT NOT NULL,
    eval_path TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    summary_json TEXT,
    dashboard_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    qid TEXT NOT NULL,
    mode TEXT NOT NULL,
    route TEXT NOT NULL,
    question TEXT NOT NULL,
    gold_answer TEXT NOT NULL,
    pred_answer TEXT NOT NULL,
    gold_sources_json TEXT,
    pred_sources_json TEXT,
    retrieval_hit INTEGER NOT NULL,
    answer_f1 REAL NOT NULL,
    answer_correct INTEGER NOT NULL,
    citation_correct INTEGER NOT NULL,
    grounding_score REAL NOT NULL,
    hallucination_flag INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    cost_usd REAL NOT NULL,
    failure_category TEXT NOT NULL,
    trace_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    plan TEXT NOT NULL,
    seats INTEGER NOT NULL,
    renewal_date TEXT NOT NULL,
    region TEXT NOT NULL,
    account_status TEXT NOT NULL,
    owner_email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    category TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    assigned_to TEXT NOT NULL,
    resolution_summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    order_status TEXT NOT NULL,
    tracking_number TEXT NOT NULL,
    expected_delivery TEXT NOT NULL,
    total_amount REAL NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_conn()) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def execute(sql: str, params: Iterable[Any] | None = None) -> None:
    with closing(get_conn()) as conn:
        conn.execute(sql, params or [])
        conn.commit()


def executemany(sql: str, rows: Iterable[Iterable[Any]]) -> None:
    with closing(get_conn()) as conn:
        conn.executemany(sql, rows)
        conn.commit()


def query_all(sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    with closing(get_conn()) as conn:
        cur = conn.execute(sql, params or [])
        return [dict(row) for row in cur.fetchall()]


def query_one(sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
    with closing(get_conn()) as conn:
        cur = conn.execute(sql, params or [])
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_document(
    doc_id: str,
    title: str,
    source_path: str,
    source_type: str,
    content_hash: str,
    chunks: list[dict[str, Any]],
) -> None:
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.execute(
            """
            INSERT INTO documents(doc_id, title, source_path, source_type, content_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, title, source_path, source_type, content_hash),
        )
        conn.executemany(
            """
            INSERT INTO chunks(chunk_id, doc_id, chunk_index, text, token_estimate)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk["chunk_id"],
                    chunk["doc_id"],
                    chunk["chunk_index"],
                    chunk["text"],
                    chunk["token_estimate"],
                )
                for chunk in chunks
            ],
        )
        conn.commit()


def save_trace(payload: dict[str, Any]) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            """
            INSERT INTO traces(
                trace_id, session_id, mode, question, system_prompt, prompt_text,
                retrieved_sources_json, tool_calls_json, raw_output, answer,
                citations_json, grounding_score, latency_ms, prompt_tokens,
                completion_tokens, estimated_cost_usd
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["trace_id"],
                payload.get("session_id"),
                payload["mode"],
                payload["question"],
                payload.get("system_prompt", ""),
                payload.get("prompt_text", ""),
                json.dumps(payload.get("retrieved_sources", [])),
                json.dumps(payload.get("tool_calls", [])),
                payload.get("raw_output", ""),
                payload.get("answer", ""),
                json.dumps(payload.get("citations", [])),
                payload.get("grounding_score", 0.0),
                payload.get("latency_ms", 0.0),
                payload.get("prompt_tokens", 0),
                payload.get("completion_tokens", 0),
                payload.get("estimated_cost_usd", 0.0),
            ),
        )
        conn.commit()


def save_feedback(trace_id: str, thumb: str, issue_tags: list[str], comment: str) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            """
            INSERT INTO feedback(trace_id, thumb, issue_tags_json, comment)
            VALUES (?, ?, ?, ?)
            """,
            (trace_id, thumb, json.dumps(issue_tags), comment),
        )
        conn.commit()


def save_eval_run(
    run_id: str,
    modes: list[str],
    eval_path: str,
    sample_size: int,
    summary: dict[str, Any],
    dashboard_path: str,
) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            """
            INSERT INTO eval_runs(run_id, modes_json, eval_path, sample_size, summary_json, dashboard_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, json.dumps(modes), eval_path, sample_size, json.dumps(summary), dashboard_path),
        )
        conn.commit()


def save_eval_rows(rows: list[dict[str, Any]]) -> None:
    with closing(get_conn()) as conn:
        conn.executemany(
            """
            INSERT INTO eval_results(
                run_id, qid, mode, route, question, gold_answer, pred_answer,
                gold_sources_json, pred_sources_json, retrieval_hit, answer_f1,
                answer_correct, citation_correct, grounding_score,
                hallucination_flag, latency_ms, cost_usd, failure_category, trace_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["run_id"],
                    row["qid"],
                    row["mode"],
                    row["route"],
                    row["question"],
                    row["gold_answer"],
                    row["pred_answer"],
                    json.dumps(row["gold_sources"]),
                    json.dumps(row["pred_sources"]),
                    row["retrieval_hit"],
                    row["answer_f1"],
                    row["answer_correct"],
                    row["citation_correct"],
                    row["grounding_score"],
                    row["hallucination_flag"],
                    row["latency_ms"],
                    row["cost_usd"],
                    row["failure_category"],
                    row.get("trace_id"),
                )
                for row in rows
            ],
        )
        conn.commit()


def list_documents() -> list[dict[str, Any]]:
    return query_all(
        """
        SELECT d.doc_id, d.title, d.source_path, d.source_type, d.created_at,
               COUNT(c.id) AS chunk_count
        FROM documents d
        LEFT JOIN chunks c ON d.doc_id = c.doc_id
        GROUP BY d.doc_id, d.title, d.source_path, d.source_type, d.created_at
        ORDER BY d.doc_id
        """
    )
