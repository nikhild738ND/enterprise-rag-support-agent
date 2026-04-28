from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json

import pandas as pd

from app.config import settings
from app.db import query_all


if __name__ == "__main__":
    run = query_all("SELECT run_id, created_at FROM eval_runs ORDER BY created_at DESC LIMIT 1")
    if not run:
        print("No eval runs found.")
        raise SystemExit(0)
    run_id = run[0]["run_id"]
    rows = query_all("SELECT * FROM eval_results WHERE run_id = ? ORDER BY id", (run_id,))
    df = pd.DataFrame(rows)
    failures = df[df["failure_category"] != "pass"].copy()
    out_csv = settings.artifacts_dir / f"failure_analysis_{run_id}.csv"
    out_txt = settings.artifacts_dir / f"failure_summary_{run_id}.txt"
    failures.to_csv(out_csv, index=False)

    lines = [f"run_id: {run_id}", f"total_rows: {len(df)}", f"failed_rows: {len(failures)}", ""]
    if not failures.empty:
        counts = failures["failure_category"].value_counts().to_dict()
        lines.append("failure_counts:")
        for key, value in counts.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append("sample_failures:")
        for _, row in failures.head(10).iterrows():
            lines.append(
                f"- mode={row['mode']} qid={row['qid']} category={row['failure_category']} question={row['question']}"
            )
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"run_id": run_id, "failure_csv": str(out_csv), "summary_txt": str(out_txt)}, indent=2))
