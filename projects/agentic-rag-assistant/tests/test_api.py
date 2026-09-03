"""API tests. Skipped unless the ``api`` extra (fastapi) is installed.

Fully offline: a fake LLM + retriever are injected, so no key or network is
needed. Run with ``pip install -e ".[api,dev]"``.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from src.agent.graph import build_graph  # noqa: E402
from src.api import create_app  # noqa: E402


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def bind_tools(self, tools):  # noqa: ARG002
        return self

    def invoke(self, messages):  # noqa: ARG002
        response = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return response


class FakeRetriever:
    def __init__(self, docs):
        self._docs = list(docs)

    def search(self, query, k=None):  # noqa: ARG002
        return self._docs

    def count(self):
        return len(self._docs)


def _client() -> TestClient:
    llm = ScriptedLLM([AIMessage(content="You can return items within 30 days of delivery.")])
    graph = build_graph(llm=llm, retriever=FakeRetriever(["Acme accepts returns within 30 days."]))
    return TestClient(create_app(graph=graph))


def test_healthz():
    r = _client().get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_readyz():
    r = _client().get("/readyz")
    assert r.status_code == 200 and r.json()["ready"] is True


def test_ask_returns_answer_and_observability():
    r = _client().post("/ask", json={"question": "What is the return window?"})
    assert r.status_code == 200
    body = r.json()
    assert "30 days" in body["answer"]
    assert body["trace_id"]
    assert "total_cost_usd" in body and body["latency_ms"] >= 0


def test_ask_rejects_empty_question():
    r = _client().post("/ask", json={"question": ""})
    assert r.status_code == 422  # pydantic validation


def test_ask_stream_emits_answer():
    r = _client().post("/ask/stream", json={"question": "What is the return window?"})
    assert r.status_code == 200
    assert "30 days" in r.text
    assert "done" in r.text
