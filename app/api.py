from __future__ import annotations

from fastapi import FastAPI

from app.db import init_db, list_documents, save_feedback
from app.evals import run_eval
from app.ingestion import ingest_paths
from app.rag import ask_question
from app.schemas import AskRequest, EvalRequest, FeedbackRequest, IngestRequest

app = FastAPI(title="Enterprise RAG Support Agent", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {"message": "Enterprise RAG Support Agent is running"}


@app.post("/ingest")
def ingest(request: IngestRequest) -> dict:
    return ingest_paths(request.paths)


@app.post("/ask")
def ask(request: AskRequest) -> dict:
    return ask_question(
        question=request.question,
        mode=request.mode,
        top_k=request.top_k,
        session_id=request.session_id,
    )


@app.post("/feedback")
def feedback(request: FeedbackRequest) -> dict:
    save_feedback(
        trace_id=request.trace_id,
        thumb=request.thumb,
        issue_tags=request.issue_tags,
        comment=request.comment,
    )
    return {"status": "saved", "trace_id": request.trace_id}


@app.post("/eval")
def evaluate(request: EvalRequest) -> dict:
    return run_eval(
        eval_path=request.eval_path,
        modes=request.modes,
        limit=request.limit,
    )


@app.get("/documents")
def documents() -> dict:
    docs = list_documents()
    return {"count": len(docs), "documents": docs}
