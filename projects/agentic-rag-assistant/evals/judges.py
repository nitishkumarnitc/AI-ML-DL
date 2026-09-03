"""Scoring judges for the eval harness.

Combines cheap, deterministic heuristics (keyword inclusion/exclusion,
non-empty) with an optional LLM-as-judge that rates faithfulness and
helpfulness on a 0..1 scale.
"""
from __future__ import annotations

import json
import re


def heuristic_score(
    answer: str, must_include: list[str], must_not_include: list[str]
) -> tuple[float, dict]:
    """Return the fraction of deterministic checks that pass, plus a breakdown."""
    checks: list[bool] = []
    detail: dict = {"missing": [], "forbidden": []}
    lowered = (answer or "").lower()

    for term in must_include:
        present = term.lower() in lowered
        checks.append(present)
        if not present:
            detail["missing"].append(term)
    for term in must_not_include:
        absent = term.lower() not in lowered
        checks.append(absent)
        if not absent:
            detail["forbidden"].append(term)

    non_empty = bool((answer or "").strip())
    checks.append(non_empty)
    detail["non_empty"] = non_empty

    score = sum(checks) / len(checks) if checks else 0.0
    return score, detail


_JUDGE_PROMPT = """You are grading a customer-support assistant's answer.

Question:
{question}

Reference answer (ground truth):
{reference}

Assistant answer:
{answer}

Rate the assistant answer on two axes from 0.0 to 1.0:
- "faithfulness": is it consistent with the reference and free of invented facts?
- "helpfulness": does it clearly and directly answer the question?

Respond with ONLY a JSON object of the form:
{{"faithfulness": <float>, "helpfulness": <float>}}"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in judge response: {text!r}")
    return json.loads(match.group(0))


def _clamp(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def llm_as_judge(question: str, answer: str, reference: str, model=None) -> dict:
    """Score an answer with an LLM judge. Returns faithfulness/helpfulness (0..1).

    Args:
        model: An optional chat model exposing ``invoke``. Defaults to a
            ``ChatAnthropic`` built from settings; inject a fake in tests.
    """
    from src.agent.config import get_settings

    judge = model
    if judge is None:
        from langchain_anthropic import ChatAnthropic

        settings = get_settings()
        judge = ChatAnthropic(
            model=settings.model,
            temperature=0,
            api_key=settings.anthropic_api_key or None,
        )

    prompt = _JUDGE_PROMPT.format(question=question, reference=reference, answer=answer)
    response = judge.invoke(prompt)
    content = response.content if isinstance(response.content, str) else str(response.content)
    try:
        data = _extract_json(content)
    except (ValueError, json.JSONDecodeError):
        return {"faithfulness": 0.0, "helpfulness": 0.0}
    return {
        "faithfulness": _clamp(data.get("faithfulness")),
        "helpfulness": _clamp(data.get("helpfulness")),
    }
