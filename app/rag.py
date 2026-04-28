from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

from app.config import settings
from app.db import query_all, query_one, save_trace
from app.llm import generate_grounded_answer
from app.metrics import base_source_id, grounding_score
from app.vector_store import get_vector_index


SIMPLE_SYSTEM_PROMPT = """
You are an internal enterprise support copilot.
Use only the supplied evidence.
If the evidence is missing or incomplete, say that you do not know based on the provided evidence.
Return ONLY valid JSON with exactly these keys:
- answer: string
- citations: list of source ids from the evidence
- confidence: number from 0 to 1
Keep the answer concise and helpful.
""".strip()

AGENT_SYSTEM_PROMPT = """
You are an internal support agent.
Decide which tools are needed.
Use retrieve_support_docs for policy, runbook, FAQ, and product-document questions.
Use SQL tools for structured account or ticket questions.
Use API tools for live ticket status or order status questions.
Think with tools, but keep the final draft concise.
""".strip()

SYNTHESIS_SYSTEM_PROMPT = SIMPLE_SYSTEM_PROMPT


@dataclass
class AgentContext:
    evidence: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def add_evidence(self, item: dict[str, Any]) -> None:
        existing = {entry["source_id"] for entry in self.evidence}
        if item["source_id"] not in existing:
            self.evidence.append(item)

    def add_tool_call(self, name: str, tool_input: Any, tool_output: Any) -> None:
        self.tool_calls.append(
            {
                "tool_name": name,
                "input": tool_input,
                "output_preview": json.dumps(tool_output, ensure_ascii=False)[:700],
            }
        )


def _build_user_prompt(question: str, evidence: list[dict[str, Any]], draft: str | None = None) -> str:
    evidence_blocks = []
    for item in evidence:
        evidence_blocks.append(
            {
                "source_id": item["source_id"],
                "title": item.get("title", ""),
                "doc_id": item.get("doc_id", ""),
                "text": item.get("text", ""),
            }
        )
    payload = {
        "question": question,
        "evidence": evidence_blocks,
        "draft": draft or "",
        "rules": [
            "Use only source ids that appear in the evidence.",
            "If unsure, answer with uncertainty instead of making up facts.",
            "Citations must support the answer directly.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _canonicalize_citations(citations: list[str], evidence: list[dict[str, Any]]) -> list[str]:
    exact = {item["source_id"]: item["source_id"] for item in evidence}
    base_map: dict[str, str] = {}
    for item in evidence:
        base_map.setdefault(base_source_id(item["source_id"]), item["source_id"])
    resolved = []
    for cite in citations:
        cite = cite.strip()
        if cite in exact:
            resolved.append(exact[cite])
            continue
        base = base_source_id(cite)
        if base in base_map:
            resolved.append(base_map[base])
    seen = set()
    out = []
    for cite in resolved:
        if cite not in seen:
            seen.add(cite)
            out.append(cite)
    return out


def _citations_to_objects(citation_ids: list[str], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["source_id"]: item for item in evidence}
    output = []
    for cid in citation_ids:
        item = by_id.get(cid)
        if not item:
            continue
        output.append(
            {
                "source_id": cid,
                "doc_id": item.get("doc_id", ""),
                "title": item.get("title", ""),
                "snippet": item.get("text", "")[:240],
            }
        )
    return output


def _serialize_agent_messages(agent_result: dict[str, Any]) -> str:
    messages = agent_result.get("messages", [])
    compact = []
    for msg in messages:
        compact.append(
            {
                "type": msg.__class__.__name__,
                "content": getattr(msg, "content", str(msg)),
            }
        )
    return json.dumps(compact, ensure_ascii=False)


def _finalize_result(
    mode: str,
    question: str,
    session_id: str | None,
    system_prompt: str,
    user_prompt: str,
    evidence: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    raw_output: str,
    parsed: dict[str, Any],
    latency_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost_usd: float,
) -> dict[str, Any]:
    citation_ids = _canonicalize_citations(parsed.get("citations", []), evidence)
    answer_text = parsed.get("answer", "I do not know based on the provided evidence.").strip()
    cited_evidence = [item["text"] for item in evidence if item["source_id"] in set(citation_ids)]
    if not cited_evidence:
        cited_evidence = [item["text"] for item in evidence]
    score = grounding_score(answer_text, cited_evidence)
    trace_id = str(uuid.uuid4())
    citation_objects = _citations_to_objects(citation_ids, evidence)
    result = {
        "trace_id": trace_id,
        "session_id": session_id,
        "mode": mode,
        "question": question,
        "answer": answer_text,
        "citations": citation_objects,
        "citation_ids": citation_ids,
        "retrieved_sources": [item["source_id"] for item in evidence],
        "retrieved_base_sources": [base_source_id(item["source_id"]) for item in evidence],
        "grounding_score": score,
        "latency_ms": round(latency_ms, 2),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "tool_calls": tool_calls,
    }
    save_trace(
        {
            "trace_id": trace_id,
            "session_id": session_id,
            "mode": mode,
            "question": question,
            "system_prompt": system_prompt,
            "prompt_text": user_prompt,
            "retrieved_sources": result["retrieved_sources"],
            "tool_calls": tool_calls,
            "raw_output": raw_output,
            "answer": answer_text,
            "citations": citation_ids,
            "grounding_score": score,
            "latency_ms": round(latency_ms, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        }
    )
    return result


def ask_simple(question: str, top_k: int | None = None, session_id: str | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    top_k = top_k or settings.top_k
    evidence = get_vector_index().search(question, top_k=top_k)
    user_prompt = _build_user_prompt(question, evidence)
    generation = generate_grounded_answer(SIMPLE_SYSTEM_PROMPT, user_prompt)
    latency_ms = (time.perf_counter() - start) * 1000
    return _finalize_result(
        mode="simple",
        question=question,
        session_id=session_id,
        system_prompt=SIMPLE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        evidence=evidence,
        tool_calls=[],
        raw_output=generation["raw_text"],
        parsed=generation["parsed"],
        latency_ms=latency_ms,
        prompt_tokens=generation["prompt_tokens"],
        completion_tokens=generation["completion_tokens"],
        estimated_cost_usd=generation["estimated_cost_usd"],
    )


_ALLOWED_SQL_PREFIXES = ("select", "with")


def _infer_sql_source(sql_query: str) -> str:
    lowered = sql_query.lower()
    for table in ["accounts", "tickets", "orders"]:
        if table in lowered:
            return f"SQL::{table}"
    return "SQL::query"


def ask_agentic(question: str, top_k: int | None = None, session_id: str | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    top_k = top_k or settings.top_k
    context = AgentContext()

    @tool
    def retrieve_support_docs(query: str, limit: int = 4) -> list[dict[str, Any]]:
        """Retrieve support docs, policies, runbooks, and FAQ chunks relevant to the query."""
        rows = get_vector_index().search(query, top_k=min(limit, top_k))
        records = []
        for row in rows:
            context.add_evidence(row)
            records.append(
                {
                    "source_id": row["source_id"],
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "text": row["text"],
                    "score": row["score"],
                }
            )
        context.add_tool_call("retrieve_support_docs", {"query": query, "limit": limit}, records)
        return records

    @tool
    def get_sql_schema() -> dict[str, Any]:
        """Return the SQLite schema for accounts, tickets, and orders tables."""
        schema = {
            "accounts": [
                "account_id", "company_name", "plan", "seats", "renewal_date",
                "region", "account_status", "owner_email",
            ],
            "tickets": [
                "ticket_id", "account_id", "severity", "status", "category",
                "opened_at", "last_updated_at", "assigned_to", "resolution_summary",
            ],
            "orders": [
                "order_id", "account_id", "sku", "quantity", "order_status",
                "tracking_number", "expected_delivery", "total_amount",
            ],
        }
        context.add_tool_call("get_sql_schema", {}, schema)
        return schema

    @tool
    def run_sql_query(sql_query: str) -> list[dict[str, Any]]:
        """Run a read-only SQL query against structured support data. Only SELECT or WITH queries are allowed."""
        cleaned = sql_query.strip().rstrip(";")
        if not cleaned.lower().startswith(_ALLOWED_SQL_PREFIXES):
            output = [{"error": "Only SELECT or WITH queries are allowed."}]
            context.add_tool_call("run_sql_query", {"sql_query": sql_query}, output)
            return output
        rows = query_all(cleaned)
        source_id = _infer_sql_source(cleaned)
        context.add_evidence(
            {
                "source_id": source_id,
                "doc_id": source_id,
                "title": source_id,
                "text": json.dumps(rows, ensure_ascii=False),
            }
        )
        context.add_tool_call("run_sql_query", {"sql_query": sql_query}, rows[:10])
        return rows[:10]

    @tool
    def lookup_ticket_status(ticket_id: str) -> dict[str, Any]:
        """Lookup the current ticket record by ticket_id."""
        row = query_one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)) or {"error": "Ticket not found"}
        context.add_evidence(
            {
                "source_id": f"API::ticket_status::{ticket_id}",
                "doc_id": "API::ticket_status",
                "title": "Ticket Status API",
                "text": json.dumps(row, ensure_ascii=False),
            }
        )
        context.add_tool_call("lookup_ticket_status", {"ticket_id": ticket_id}, row)
        return row

    @tool
    def lookup_order_status(order_id: str) -> dict[str, Any]:
        """Lookup the current order record by order_id."""
        row = query_one("SELECT * FROM orders WHERE order_id = ?", (order_id,)) or {"error": "Order not found"}
        context.add_evidence(
            {
                "source_id": f"API::order_status::{order_id}",
                "doc_id": "API::order_status",
                "title": "Order Status API",
                "text": json.dumps(row, ensure_ascii=False),
            }
        )
        context.add_tool_call("lookup_order_status", {"order_id": order_id}, row)
        return row

    agent = create_agent(
        model=settings.llm_model,
        tools=[
            retrieve_support_docs,
            get_sql_schema,
            run_sql_query,
            lookup_ticket_status,
            lookup_order_status,
        ],
        system_prompt=AGENT_SYSTEM_PROMPT,
    )
    agent_result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    draft = ""
    messages = agent_result.get("messages", [])
    if messages:
        draft = getattr(messages[-1], "content", str(messages[-1]))
        if isinstance(draft, list):
            draft = json.dumps(draft, ensure_ascii=False)

    if not context.evidence:
        keyword_hint = re.sub(r"\s+", " ", question).strip()
        fallback = get_vector_index().search(keyword_hint, top_k=top_k)
        for item in fallback:
            context.add_evidence(item)

    user_prompt = _build_user_prompt(question, context.evidence, draft=draft)
    generation = generate_grounded_answer(SYNTHESIS_SYSTEM_PROMPT, user_prompt)
    latency_ms = (time.perf_counter() - start) * 1000
    raw_output = json.dumps(
        {
            "agent_messages": _serialize_agent_messages(agent_result),
            "synthesis": generation["raw_text"],
        },
        ensure_ascii=False,
    )
    estimated_cost = generation["estimated_cost_usd"]
    return _finalize_result(
        mode="agentic",
        question=question,
        session_id=session_id,
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        evidence=context.evidence,
        tool_calls=context.tool_calls,
        raw_output=raw_output,
        parsed=generation["parsed"],
        latency_ms=latency_ms,
        prompt_tokens=generation["prompt_tokens"],
        completion_tokens=generation["completion_tokens"],
        estimated_cost_usd=estimated_cost,
    )


def ask_question(question: str, mode: str, top_k: int | None = None, session_id: str | None = None) -> dict[str, Any]:
    if mode == "simple":
        return ask_simple(question=question, top_k=top_k, session_id=session_id)
    if mode == "agentic":
        return ask_agentic(question=question, top_k=top_k, session_id=session_id)
    raise ValueError(f"Unsupported mode: {mode}")
