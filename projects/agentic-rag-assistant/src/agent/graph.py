"""Assemble and compile the agentic RAG graph.

Flow::

    START -> retrieve -> agent -> (tools -> agent)* -> guardrail -> END

``retrieve`` runs input guardrails + RAG, ``agent`` is a tool-calling LLM,
``tools`` executes any requested tools and loops back, and ``guardrail``
validates the final answer before END.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agent.nodes import (
    guardrail_node,
    make_agent_node,
    make_retrieve_node,
    make_tools_node,
    route_after_agent,
)
from src.agent.state import GraphState


def build_graph(llm=None, retriever=None):
    """Build and compile the agent graph.

    Args:
        llm: A chat model exposing ``bind_tools(tools)`` and ``invoke(messages)``.
            Defaults to the configured ``ChatAnthropic`` model. Inject a fake in
            tests to run fully offline.
        retriever: An object exposing ``search(query) -> list[str]``. Defaults to
            the local Chroma-backed retriever. Inject a fake in tests.

    Returns:
        A compiled LangGraph application (supports ``.invoke`` / ``.stream``).
    """
    if retriever is None:
        from src.agent.retrieval import get_retriever

        retriever = get_retriever()
    if llm is None:
        from src.agent.nodes import get_default_llm

        llm = get_default_llm()

    builder = StateGraph(GraphState)
    builder.add_node("retrieve", make_retrieve_node(retriever))
    builder.add_node("agent", make_agent_node(llm))
    builder.add_node("tools", make_tools_node())
    builder.add_node("guardrail", guardrail_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "guardrail": "guardrail"},
    )
    builder.add_edge("tools", "agent")
    builder.add_edge("guardrail", END)

    return builder.compile()
