"""Deterministic, LLM-free guardrails.

Pure functions (fast, offline, trivially unit-testable) that validate agent
input and output. Input guards reject empty/oversized prompts and flag obvious
prompt-injection attempts; the output guard rejects empty answers and reports a
lightweight grounding signal for observability.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_MAX_INPUT_CHARS = 4000

# Heuristic prompt-injection patterns. Intentionally simple and explainable;
# a production system would layer a trained classifier on top of these.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|the\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(the\s+)?(system|previous|above)\s+(prompt|instructions)",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"you\s+are\s+now\s+",
    r"pretend\s+to\s+be\s+",
    r"act\s+as\s+(an?\s+)?(unrestricted|jailbroken|dan)\b",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z0-9]+")

# Minimum answer/context word overlap to consider an answer "grounded".
_GROUNDING_THRESHOLD = 0.15


@dataclass
class GuardResult:
    """Outcome of a single guardrail check."""

    ok: bool
    reason: str = "ok"
    flags: dict = field(default_factory=dict)


def validate_input(text: str | None, max_chars: int = DEFAULT_MAX_INPUT_CHARS) -> GuardResult:
    """Validate a user question before it reaches the model."""
    if text is None or not text.strip():
        return GuardResult(False, "empty_input", {"empty": True})
    if len(text) > max_chars:
        return GuardResult(
            False,
            "input_too_long",
            {"too_long": True, "length": len(text), "max": max_chars},
        )
    if _INJECTION_RE.search(text):
        return GuardResult(False, "possible_prompt_injection", {"injection_suspected": True})
    return GuardResult(True, "ok", {"length": len(text)})


def _grounding_score(answer: str, context: list[str]) -> float:
    """Fraction of the answer's words that also appear in the context (0..1)."""
    answer_words = set(_WORD_RE.findall(answer.lower()))
    context_words = set(_WORD_RE.findall(" ".join(context).lower()))
    if not answer_words or not context_words:
        return 0.0
    return len(answer_words & context_words) / len(answer_words)


def validate_output(answer: str | None, context: list[str] | None = None) -> GuardResult:
    """Validate a model answer before returning it to the user."""
    if answer is None or not answer.strip():
        return GuardResult(False, "empty_answer", {"empty": True})
    flags: dict = {"length": len(answer)}
    if context:
        score = _grounding_score(answer, context)
        flags["grounding_score"] = round(score, 3)
        # Soft signal only: paraphrased-but-correct answers shouldn't be blocked,
        # so grounding is reported, not enforced. Only emptiness is a hard fail.
        flags["grounded"] = score >= _GROUNDING_THRESHOLD
    return GuardResult(True, "ok", flags)
