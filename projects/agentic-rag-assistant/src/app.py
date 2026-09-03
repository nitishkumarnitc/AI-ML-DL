"""CLI entrypoint for the agentic RAG assistant.

Usage::

    python -m src.app "How long do I have to return an item?"
    python -m src.app            # interactive REPL

On first run it auto-ingests the knowledge base so the demo works end-to-end
once an API key is configured.
"""
from __future__ import annotations

import sys
from contextlib import nullcontext

from src.agent.config import get_settings
from src.agent.observability import start_trace
from src.agent.state import initial_state


def _trace_ctx():
    """A trace context for one request when TRACE_ENABLED, else a no-op."""
    if get_settings().trace_enabled:
        return start_trace("request")
    return nullcontext()


def _bootstrap_graph():
    """Build the graph, auto-ingesting the knowledge base on first run."""
    from src.bootstrap import bootstrap_graph

    return bootstrap_graph()


def answer_question(app, question: str) -> str:
    """Run the graph to completion and return the guardrail-approved answer."""
    final_state: dict | None = None
    with _trace_ctx():
        for event in app.stream(initial_state(question), stream_mode="values"):
            final_state = event
    return (final_state or {}).get("answer", "")


def _stream_and_print(app, question: str) -> str:
    """Stream state as the graph runs, then print the final answer."""
    answer = ""
    with _trace_ctx():
        for event in app.stream(initial_state(question), stream_mode="values"):
            if event.get("answer"):
                answer = event["answer"]
    print(answer)
    return answer


def _repl(app) -> None:
    print("Acme support assistant. Ask a question, or type 'exit' to quit.\n")
    while True:
        try:
            question = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        print(f"assistant > {answer_question(app, question)}\n")


def main(argv: list[str] | None = None) -> int:
    """Entry point. With a question arg, answer it; otherwise start a REPL."""
    argv = list(sys.argv if argv is None else argv)
    app = _bootstrap_graph()
    if len(argv) > 1:
        _stream_and_print(app, " ".join(argv[1:]))
    else:
        _repl(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
