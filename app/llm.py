from __future__ import annotations

import json
import re
from typing import Any

from langchain.chat_models import init_chat_model

from app.config import settings
from app.metrics import approximate_tokens


JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def get_chat_model():
    if not settings.llm_model:
        raise ValueError(
            "LLM_MODEL is empty. Put a provider:model string in .env, for example openai:gpt-4.1-mini"
        )
    return init_chat_model(settings.llm_model, temperature=0)


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def parse_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    try:
        return json.loads(candidate)
    except Exception:
        match = JSON_RE.search(text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {
        "answer": text.strip(),
        "citations": [],
        "confidence": 0.0,
    }


def read_usage(response) -> tuple[int, int]:
    usage = getattr(response, "usage_metadata", None) or getattr(response, "response_metadata", {}).get("token_usage", {})
    prompt_tokens = 0
    completion_tokens = 0
    if isinstance(usage, dict):
        prompt_tokens = int(
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or usage.get("input_token_count")
            or 0
        )
        completion_tokens = int(
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("output_token_count")
            or 0
        )
    return prompt_tokens, completion_tokens


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    prompt_cost = (prompt_tokens / 1000.0) * settings.prompt_cost_per_1k
    completion_cost = (completion_tokens / 1000.0) * settings.completion_cost_per_1k
    return round(prompt_cost + completion_cost, 6)


def generate_grounded_answer(
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    model = get_chat_model()
    response = model.invoke([
        ("system", system_prompt),
        ("user", user_prompt),
    ])
    raw_text = content_to_text(response.content)
    payload = parse_json_object(raw_text)
    prompt_tokens, completion_tokens = read_usage(response)
    if prompt_tokens == 0:
        prompt_tokens = approximate_tokens(system_prompt + "\n" + user_prompt)
    if completion_tokens == 0:
        completion_tokens = approximate_tokens(raw_text)
    return {
        "parsed": payload,
        "raw_text": raw_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "estimated_cost_usd": estimate_cost(prompt_tokens, completion_tokens),
    }
