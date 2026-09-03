"""Observability tests. Fully offline: fake LLM + retriever, trace sink 'none'.

Proves the tracer records a span per node with latencies, that spans are safe
no-ops outside a trace, and that the tool loop produces a 'tools' span.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage

from src.agent.graph import build_graph
from src.agent.observability import cost_from_usage, span, start_trace
from src.agent.state import initial_state


class ScriptedLLM:
    """Minimal chat-model stand-in: replays queued responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def bind_tools(self, tools):  # noqa: ARG002 - signature parity with ChatAnthropic
        return self

    def invoke(self, messages):  # noqa: ARG002 - ignores input, replays script
        response = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return response


class FakeRetriever:
    def __init__(self, docs):
        self._docs = list(docs)

    def search(self, query, k=None):  # noqa: ARG002 - returns fixed docs
        return self._docs

    def count(self):
        return len(self._docs)


def test_trace_records_a_span_per_node():
    llm = ScriptedLLM([AIMessage(content="Returns are accepted within 30 days of delivery.")])
    retriever = FakeRetriever(["Acme accepts returns within 30 days of delivery."])
    app = build_graph(llm=llm, retriever=retriever)

    with start_trace("test", sink="none") as trace:
        app.invoke(initial_state("What is the return window?"))

    names = [s.name for s in trace.spans]
    assert names == ["retrieve", "agent", "guardrail"]
    assert trace.latency_ms >= 0
    assert all(s.latency_ms >= 0 for s in trace.spans)

    summary = trace.summary()
    assert summary["trace_id"]
    assert len(summary["spans"]) == 3
    # The retrieve span recorded how many context chunks it found.
    retrieve_span = next(s for s in trace.spans if s.name == "retrieve")
    assert retrieve_span.attrs.get("n_context") == 1


def test_tool_loop_produces_a_tools_span():
    tool_call = AIMessage(
        content="", tool_calls=[{"name": "get_current_datetime", "args": {}, "id": "call_1"}]
    )
    final = AIMessage(content="The current time has been retrieved.")
    app = build_graph(llm=ScriptedLLM([tool_call, final]), retriever=FakeRetriever(["ctx"]))

    with start_trace("t", sink="none") as trace:
        app.invoke(initial_state("What time is it?"))

    assert "tools" in [s.name for s in trace.spans]


def test_span_is_a_safe_noop_without_active_trace():
    # No start_trace(): span must still be usable and swallow calls harmlessly.
    with span("orphan") as sp:
        sp.set(foo=1).record_llm_usage(AIMessage(content="hi"))
    assert sp.attrs["foo"] == 1
    assert sp.cost_usd == 0.0  # fake message has no usage metadata


def test_cost_from_usage_math():
    # 1M input @ $3 + 1M output @ $15 = $18.
    assert cost_from_usage(1_000_000, 1_000_000, 3.0, 15.0) == 18.0
    assert cost_from_usage(0, 0, 3.0, 15.0) == 0.0
