from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import asyncio
import time
from statistics import mean

import httpx
import pandas as pd

from app.config import settings


async def one_request(client: httpx.AsyncClient, question: str, mode: str) -> float:
    start = time.perf_counter()
    response = await client.post(
        "http://127.0.0.1:8000/ask",
        json={"question": question, "mode": mode, "top_k": 4},
        timeout=120.0,
    )
    response.raise_for_status()
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    eval_df = pd.read_csv(settings.eval_dir / "eval_set.csv").head(30)
    questions = eval_df["question"].tolist()
    for mode in ["simple", "agentic"]:
        async with httpx.AsyncClient() as client:
            latencies = await asyncio.gather(*[one_request(client, q, mode) for q in questions])
        p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1]
        print({
            "mode": mode,
            "requests": len(latencies),
            "avg_latency_ms": round(mean(latencies), 2),
            "p95_latency_ms": round(p95, 2),
        })


if __name__ == "__main__":
    asyncio.run(main())
