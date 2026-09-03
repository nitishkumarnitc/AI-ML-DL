"""Lightweight, dependency-free observability for the agent.

This gives every request a **trace** made of **spans** (one per graph node /
tool / LLM call), each recording latency, token usage, and estimated cost —
the LLMOps unit of observability. It is intentionally stdlib-only so it works
offline and in CI with zero extra dependencies.

Design:

* ``start_trace()`` opens a trace and stores it in a ``ContextVar``. Nodes call
  ``span(...)`` without any handle-threading; the span attaches to whatever
  trace is active.
* When **no** trace is active (e.g. the offline unit tests that call
  ``graph.invoke`` directly), ``span()`` yields a harmless no-op span, so
  instrumenting the nodes never changes their behaviour or breaks tests.
* Cost is estimated from the model's ``usage_metadata`` and the per-1M-token
  prices in :class:`~src.agent.config.Settings` (set them to your model's rates).

Native tracing (opt-in): set ``LANGCHAIN_TRACING_V2=true`` and
``LANGSMITH_API_KEY`` and LangChain/LangGraph will export full traces to
LangSmith automatically. This module complements that with offline,
cost-aware spans you can assert on in tests and print anywhere.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

_current_trace: contextvars.ContextVar[Optional["Trace"]] = contextvars.ContextVar(
    "current_trace", default=None
)


def cost_from_usage(
    input_tokens: int, output_tokens: int, price_in_per_mtok: float, price_out_per_mtok: float
) -> float:
    """USD cost for a call given token counts and per-1M-token prices."""
    return (input_tokens / 1_000_000) * price_in_per_mtok + (
        output_tokens / 1_000_000
    ) * price_out_per_mtok


def _extract_usage(message: Any) -> Optional[dict]:
    """Pull ``{input_tokens, output_tokens}`` from a LangChain AI message, if present."""
    um = getattr(message, "usage_metadata", None)
    if isinstance(um, dict) and um:
        return {
            "input_tokens": int(um.get("input_tokens", 0) or 0),
            "output_tokens": int(um.get("output_tokens", 0) or 0),
        }
    rm = getattr(message, "response_metadata", None)
    if isinstance(rm, dict):
        u = rm.get("usage") or rm.get("token_usage")
        if isinstance(u, dict):
            return {
                "input_tokens": int(u.get("input_tokens", u.get("prompt_tokens", 0)) or 0),
                "output_tokens": int(u.get("output_tokens", u.get("completion_tokens", 0)) or 0),
            }
    return None


@dataclass
class Span:
    """A single timed step within a trace (a node, tool, or LLM call)."""

    name: str
    attrs: dict = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0

    def set(self, **attrs: Any) -> "Span":
        """Attach arbitrary (non-sensitive) attributes; returns self for chaining."""
        self.attrs.update(attrs)
        return self

    def record_llm_usage(
        self,
        message: Any,
        *,
        price_in_per_mtok: Optional[float] = None,
        price_out_per_mtok: Optional[float] = None,
    ) -> "Span":
        """Accumulate token usage + estimated cost from an LLM response message.

        No-ops safely when the message carries no usage metadata (e.g. fakes in
        tests), so it is always safe to call.
        """
        usage = _extract_usage(message)
        if not usage:
            return self
        it, ot = usage["input_tokens"], usage["output_tokens"]
        self.input_tokens += it
        self.output_tokens += ot
        if price_in_per_mtok is None or price_out_per_mtok is None:
            from src.agent.config import get_settings

            s = get_settings()
            price_in_per_mtok = s.price_input_per_mtok if price_in_per_mtok is None else price_in_per_mtok
            price_out_per_mtok = (
                s.price_output_per_mtok if price_out_per_mtok is None else price_out_per_mtok
            )
        self.cost_usd += cost_from_usage(it, ot, price_in_per_mtok, price_out_per_mtok)
        return self


@dataclass
class Trace:
    """A request-scoped collection of spans, with roll-up totals."""

    name: str
    trace_id: str
    spans: list[Span] = field(default_factory=list)
    started_at: float = 0.0
    latency_ms: float = 0.0

    @property
    def total_input_tokens(self) -> int:
        return sum(s.input_tokens for s in self.spans)

    @property
    def total_output_tokens(self) -> int:
        return sum(s.output_tokens for s in self.spans)

    @property
    def total_cost_usd(self) -> float:
        return sum(s.cost_usd for s in self.spans)

    def summary(self) -> dict:
        """A JSON-serializable summary of the trace (safe to log)."""
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "latency_ms": round(self.latency_ms, 1),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "spans": [
                {
                    "name": s.name,
                    "latency_ms": round(s.latency_ms, 1),
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cost_usd": round(s.cost_usd, 6),
                    **s.attrs,
                }
                for s in self.spans
            ],
        }


def _emit(trace: Trace, sink: Optional[str]) -> None:
    """Write the trace summary to the configured sink (``stderr`` or ``none``)."""
    if sink is None:
        try:
            from src.agent.config import get_settings

            sink = get_settings().trace_sink
        except Exception:  # pragma: no cover - config should always load
            sink = "stderr"
    if sink == "none":
        return
    print(f"[trace] {json.dumps(trace.summary(), default=str)}", file=sys.stderr)


@contextlib.contextmanager
def start_trace(name: str = "request", *, sink: Optional[str] = None) -> Iterator[Trace]:
    """Open a trace for the duration of the ``with`` block.

    Nested spans created inside attach to this trace. On exit the trace's total
    latency is recorded and its summary emitted to ``sink`` (defaults to the
    configured ``trace_sink``; pass ``sink="none"`` to stay silent, e.g. in tests).
    """
    trace = Trace(name=name, trace_id=uuid.uuid4().hex[:12], started_at=time.time())
    token = _current_trace.set(trace)
    t0 = time.perf_counter()
    try:
        yield trace
    finally:
        trace.latency_ms = (time.perf_counter() - t0) * 1000
        _current_trace.reset(token)
        _emit(trace, sink)


@contextlib.contextmanager
def span(name: str, **attrs: Any) -> Iterator[Span]:
    """Time a step and attach it to the active trace (no-op if none is active)."""
    sp = Span(name=name, attrs=dict(attrs))
    trace = _current_trace.get()
    if trace is None:
        # No active trace: yield a usable-but-unattached span so callers are safe.
        yield sp
        return
    t0 = time.perf_counter()
    try:
        yield sp
    finally:
        sp.latency_ms = (time.perf_counter() - t0) * 1000
        trace.spans.append(sp)
