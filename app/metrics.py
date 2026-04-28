from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "is", "are",
    "was", "were", "be", "by", "with", "that", "this", "it", "as", "at", "from",
    "within", "after", "before", "into", "than", "their", "its", "can", "do", "does",
    "what", "when", "how", "which", "who", "why", "your", "you", "we", "our",
}


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9:\-\.\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [tok for tok in normalize_text(text).split() if tok and tok not in STOPWORDS]


def token_f1(pred: str, gold: str) -> float:
    pred_tokens = tokenize(pred)
    gold_tokens = tokenize(gold)
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / max(len(pred_tokens), 1)
    recall = overlap / max(len(gold_tokens), 1)
    return 2 * precision * recall / max(precision + recall, 1e-8)


_ID_RE = re.compile(r"[A-Z]+-\d+")
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _extract_ids(text: str) -> set[str]:
    return set(_ID_RE.findall(text.upper()))


def _extract_numbers(text: str) -> set[str]:
    return set(_NUM_RE.findall(text))


def answer_correct(pred: str, gold: str) -> tuple[bool, float]:
    pred_norm = normalize_text(pred)
    gold_norm = normalize_text(gold)
    score = token_f1(pred, gold)
    ids_ok = True
    gold_ids = _extract_ids(gold)
    if gold_ids:
        ids_ok = gold_ids.issubset(_extract_ids(pred))
    nums_ok = True
    gold_nums = _extract_numbers(gold)
    if gold_nums:
        nums_ok = gold_nums.issubset(_extract_numbers(pred))
    contains = gold_norm in pred_norm or pred_norm in gold_norm
    correct = bool(contains or (score >= 0.72 and ids_ok and nums_ok) or (score >= 0.55 and ids_ok and nums_ok))
    return correct, round(score, 4)


def base_source_id(source_id: str) -> str:
    source_id = source_id.strip()
    if source_id.startswith("DOC-") and "::chunk_" in source_id:
        return source_id.split("::chunk_", 1)[0]
    if source_id.startswith("SQL::"):
        parts = source_id.split("::")
        return "::".join(parts[:2])
    if source_id.startswith("API::"):
        parts = source_id.split("::")
        return "::".join(parts[:2])
    return source_id


def parse_source_list(raw: str) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split("|") if item.strip()]


def citation_correct(pred_sources: list[str], gold_sources: list[str]) -> bool:
    gold = {base_source_id(item) for item in gold_sources}
    pred = {base_source_id(item) for item in pred_sources}
    if not gold:
        return True
    return bool(pred) and pred.issubset(gold) and bool(pred & gold)


def grounding_score(answer: str, evidence_texts: list[str]) -> float:
    answer_tokens = [tok for tok in tokenize(answer) if len(tok) > 2]
    if not answer_tokens:
        return 1.0
    support = set()
    for text in evidence_texts:
        support.update([tok for tok in tokenize(text) if len(tok) > 2])
    covered = sum(1 for tok in answer_tokens if tok in support)
    return round(covered / max(len(answer_tokens), 1), 4)


def hallucination_flag(answer: str, grounding: float, citation_ok: bool) -> int:
    if "i don't know" in answer.lower() or "insufficient" in answer.lower():
        return 0
    return int((grounding < 0.45) or (not citation_ok))


def failure_category(
    route: str,
    retrieval_hit: bool,
    answer_ok: bool,
    citation_ok: bool,
    hallucinated: bool,
) -> str:
    if route in {"docs", "hybrid"} and not retrieval_hit:
        return "retrieval_miss"
    if not citation_ok:
        return "wrong_citation"
    if hallucinated:
        return "hallucination"
    if not answer_ok:
        return "reasoning_error"
    return "pass"


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(float(np.percentile(values, 95)), 2)


def approximate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))
