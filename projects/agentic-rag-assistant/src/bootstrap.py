"""Shared graph bootstrap used by both the CLI (``src.app``) and the HTTP API
(``src.api``).

Building the graph and auto-ingesting the knowledge base on first run lives here
so both entrypoints behave identically and there is a single place to change how
the app is wired.
"""
from __future__ import annotations

import sys


def bootstrap_graph(*, verbose: bool = True):
    """Build the compiled agent graph, ingesting the KB if the index is empty.

    Ingestion is best-effort: if the vector store can't be reached (e.g. offline
    in a minimal environment) the graph is still returned so health checks pass.
    """
    from src.agent.graph import build_graph
    from src.agent.retrieval import get_retriever

    retriever = get_retriever()
    try:
        if retriever.count() == 0:
            count = retriever.ingest()
            if verbose:
                print(f"[setup] Ingested {count} knowledge chunks.", file=sys.stderr)
    except Exception as exc:  # pragma: no cover - best-effort bootstrap
        if verbose:
            print(f"[setup] Skipping ingestion ({exc}).", file=sys.stderr)
    return build_graph(retriever=retriever)
