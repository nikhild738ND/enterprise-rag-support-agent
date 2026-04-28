from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    paths: list[str] = Field(description="Local file paths to ingest")


class AskRequest(BaseModel):
    question: str
    mode: Literal["simple", "agentic"] = "simple"
    top_k: int = 4
    session_id: str | None = None


class FeedbackRequest(BaseModel):
    trace_id: str
    thumb: Literal["up", "down"]
    issue_tags: list[str] = []
    comment: str = ""


class EvalRequest(BaseModel):
    eval_path: str = "data/eval/eval_set.csv"
    modes: list[Literal["simple", "agentic"]] = ["simple", "agentic"]
    limit: int | None = None

