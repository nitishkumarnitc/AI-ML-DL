"""FastAPI serving surface for the agentic RAG assistant.

Endpoints:

* ``GET  /healthz``      — liveness (no dependencies).
* ``GET  /readyz``       — readiness (graph built + KB reachable).
* ``POST /ask``          — answer a question; response carries the trace id,
  latency, token usage, and estimated USD cost.
* ``POST /ask/stream``   — Server-Sent Events stream of the run.

Every request runs inside an observability trace (see ``src.agent.observability``),
so cost/latency are first-class in the response — the LLMOps "serving" lesson made
concrete. Requires the ``api`` extra::

    pip install -e ".[api]"
    uvicorn src.api:app --reload      # or: make serve
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, Field

from src.agent.observability import start_trace
from src.agent.state import initial_state


class AskRequest(BaseModel):
    """Request body for the ask endpoints."""

    question: str = Field(..., min_length=1, max_length=8000)


class AskResponse(BaseModel):
    """Answer plus per-request observability roll-up."""

    answer: str
    trace_id: str
    latency_ms: float
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int


def _run(graph: Any, question: str):
    """Run the graph to completion inside a trace; return (answer, trace)."""
    final: dict | None = None
    with start_trace("api.ask", sink="none") as trace:
        for event in graph.stream(initial_state(question), stream_mode="values"):
            final = event
    return (final or {}).get("answer", ""), trace


def create_app(graph: Any = None):
    """Build the FastAPI app.

    Args:
        graph: A compiled graph to serve. If omitted, one is bootstrapped on
            startup (auto-ingesting the KB). Inject a fake graph in tests to run
            the API fully offline.
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, StreamingResponse

    @asynccontextmanager
    async def lifespan(app: "FastAPI"):
        if getattr(app.state, "graph", None) is None:
            from src.bootstrap import bootstrap_graph

            app.state.graph = bootstrap_graph()
        yield

    app = FastAPI(title="Agentic RAG Assistant", version="0.1.0", lifespan=lifespan)
    if graph is not None:
        app.state.graph = graph

    @app.get("/healthz")
    def healthz() -> dict:
        """Liveness probe — the process is up."""
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz(request: Request):
        """Readiness probe — the graph is built and ready to serve traffic."""
        ready = getattr(request.app.state, "graph", None) is not None
        return JSONResponse({"ready": ready}, status_code=200 if ready else 503)

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest, request: Request) -> AskResponse:
        answer, trace = _run(request.app.state.graph, req.question)
        s = trace.summary()
        return AskResponse(
            answer=answer,
            trace_id=s["trace_id"],
            latency_ms=s["latency_ms"],
            total_cost_usd=s["total_cost_usd"],
            total_input_tokens=s["total_input_tokens"],
            total_output_tokens=s["total_output_tokens"],
        )

    @app.post("/ask/stream")
    def ask_stream(req: AskRequest, request: Request) -> "StreamingResponse":
        graph = request.app.state.graph

        def gen():
            with start_trace("api.ask.stream", sink="none") as trace:
                answer = ""
                for event in graph.stream(initial_state(req.question), stream_mode="values"):
                    if event.get("answer"):
                        answer = event["answer"]
                    yield f"data: {json.dumps({'event': 'update', 'answer': event.get('answer', '')})}\n\n"
                done = {
                    "event": "done",
                    "answer": answer,
                    "trace_id": trace.trace_id,
                    "total_cost_usd": round(trace.total_cost_usd, 6),
                }
                yield f"data: {json.dumps(done)}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


# Module-level ASGI app for ``uvicorn src.api:app``. Constructing it imports
# FastAPI (needs the ``api`` extra); the graph is bootstrapped on startup.
app = create_app()
