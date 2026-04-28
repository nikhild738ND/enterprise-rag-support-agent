from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from app.db import query_all


def build_dashboard(run_id: str, output_path: str) -> str:
    rows = query_all("SELECT * FROM eval_results WHERE run_id = ? ORDER BY id", (run_id,))
    if not rows:
        raise ValueError(f"No eval rows found for run_id={run_id}")

    df = pd.DataFrame(rows)
    summary = (
        df.groupby("mode")
        .agg(
            retrieval_hit_rate=("retrieval_hit", "mean"),
            answer_correctness=("answer_correct", "mean"),
            citation_correctness=("citation_correct", "mean"),
            hallucination_rate=("hallucination_flag", "mean"),
            p95_latency_ms=("latency_ms", lambda s: s.quantile(0.95)),
            avg_cost_usd=("cost_usd", "mean"),
            avg_grounding=("grounding_score", "mean"),
        )
        .reset_index()
    )

    failures = (
        df[df["failure_category"] != "pass"]
        .groupby(["mode", "failure_category"]) 
        .size()
        .reset_index(name="count")
    )

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    axes[0, 0].bar(summary["mode"], summary["retrieval_hit_rate"])
    axes[0, 0].set_title("Retrieval hit rate")
    axes[0, 0].set_ylim(0, 1)

    axes[0, 1].bar(summary["mode"], summary["answer_correctness"], label="answer")
    axes[0, 1].bar(summary["mode"], summary["citation_correctness"], alpha=0.6, label="citation")
    axes[0, 1].set_title("Answer vs citation correctness")
    axes[0, 1].set_ylim(0, 1)
    axes[0, 1].legend()

    axes[0, 2].bar(summary["mode"], summary["avg_grounding"])
    axes[0, 2].set_title("Grounding score")
    axes[0, 2].set_ylim(0, 1)

    axes[1, 0].bar(summary["mode"], summary["p95_latency_ms"])
    axes[1, 0].set_title("P95 latency (ms)")

    axes[1, 1].bar(summary["mode"], summary["avg_cost_usd"])
    axes[1, 1].set_title("Cost per answer (USD)")

    if failures.empty:
        axes[1, 2].text(0.5, 0.5, "No failures", ha="center", va="center")
        axes[1, 2].set_title("Failure categories")
        axes[1, 2].axis("off")
    else:
        pivot = failures.pivot(index="failure_category", columns="mode", values="count").fillna(0)
        pivot.plot(kind="bar", ax=axes[1, 2])
        axes[1, 2].set_title("Failure categories")
        axes[1, 2].set_ylabel("count")

    fig.suptitle(f"Enterprise RAG Eval Dashboard - {run_id}")
    fig.tight_layout()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return str(output)
