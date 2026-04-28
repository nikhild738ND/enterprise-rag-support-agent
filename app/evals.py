from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings
from app.dashboard import build_dashboard
from app.db import save_eval_rows, save_eval_run
from app.metrics import (
    answer_correct,
    base_source_id,
    citation_correct,
    failure_category,
    hallucination_flag,
    p95,
    parse_source_list,
)
from app.rag import ask_question


def _summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    output = {}
    for mode, sub in df.groupby("mode"):
        output[mode] = {
            "sample_size": int(len(sub)),
            "retrieval_hit_rate": round(float(sub["retrieval_hit"].mean()), 4),
            "answer_correctness": round(float(sub["answer_correct"].mean()), 4),
            "citation_correctness": round(float(sub["citation_correct"].mean()), 4),
            "hallucination_rate": round(float(sub["hallucination_flag"].mean()), 4),
            "avg_grounding_score": round(float(sub["grounding_score"].mean()), 4),
            "p95_latency_ms": p95(sub["latency_ms"].tolist()),
            "avg_cost_usd": round(float(sub["cost_usd"].mean()), 6),
        }
    return output


def run_eval(eval_path: str, modes: list[str], limit: int | None = None) -> dict[str, Any]:
    path = Path(eval_path)
    if not path.is_absolute():
        path = settings.base_dir / eval_path
    df = pd.read_csv(path)
    if limit:
        df = df.head(limit)

    run_id = str(uuid.uuid4())
    rows_to_save: list[dict[str, Any]] = []

    for mode in modes:
        for row in df.to_dict(orient="records"):
            result = ask_question(
                question=row["question"],
                mode=mode,
                top_k=settings.top_k,
                session_id=f"eval-{run_id}",
            )
            gold_sources = parse_source_list(str(row.get("gold_sources", "")))
            pred_sources = result["citation_ids"]
            gold_base = {base_source_id(item) for item in gold_sources}
            retrieved_base = {base_source_id(item) for item in result["retrieved_sources"]}
            retrieval_hit = int(True if not gold_base else bool(gold_base & retrieved_base))
            answer_ok, answer_f1 = answer_correct(result["answer"], row["gold_answer"])
            cite_ok = citation_correct(pred_sources, gold_sources)
            hallucinated = hallucination_flag(result["answer"], result["grounding_score"], cite_ok)
            category = failure_category(
                route=row["route"],
                retrieval_hit=bool(retrieval_hit),
                answer_ok=answer_ok,
                citation_ok=cite_ok,
                hallucinated=bool(hallucinated),
            )
            rows_to_save.append(
                {
                    "run_id": run_id,
                    "qid": row["qid"],
                    "mode": mode,
                    "route": row["route"],
                    "question": row["question"],
                    "gold_answer": row["gold_answer"],
                    "pred_answer": result["answer"],
                    "gold_sources": gold_sources,
                    "pred_sources": pred_sources,
                    "retrieval_hit": retrieval_hit,
                    "answer_f1": answer_f1,
                    "answer_correct": int(answer_ok),
                    "citation_correct": int(cite_ok),
                    "grounding_score": result["grounding_score"],
                    "hallucination_flag": hallucinated,
                    "latency_ms": result["latency_ms"],
                    "cost_usd": result["estimated_cost_usd"],
                    "failure_category": category,
                    "trace_id": result["trace_id"],
                }
            )

    save_eval_rows(rows_to_save)
    summary = _summary_from_rows(rows_to_save)
    dashboard_path = settings.artifacts_dir / f"eval_dashboard_{run_id}.png"
    dashboard = build_dashboard(run_id, str(dashboard_path))
    save_eval_run(
        run_id=run_id,
        modes=modes,
        eval_path=str(path),
        sample_size=int(len(df)),
        summary=summary,
        dashboard_path=dashboard,
    )
    return {
        "run_id": run_id,
        "sample_size": int(len(df)),
        "modes": modes,
        "summary": summary,
        "dashboard_path": dashboard,
    }
