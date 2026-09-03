"""LangGraph state definition.

The graph threads a single typed ``GraphState`` dict between nodes. ``messages``
uses the ``add_messages`` reducer (append semantics for the chat history) and
``tool_results`` accumulates across tool loops; the rest are plain values that
each node may overwrite.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """State passed between graph nodes."""

    # Chat history (Human/AI/Tool messages); appended to via the reducer.
    messages: Annotated[list[BaseMessage], add_messages]
    # The original user question for this turn.
    question: str
    # Retrieved knowledge-base passages used to ground the answer.
    context: list[str]
    # Raw string outputs of any tools executed (accumulated across loops).
    tool_results: Annotated[list[str], operator.add]
    # The final, guardrail-approved answer.
    answer: str
    # Observability: input/output guardrail flags recorded during the run.
    guard_flags: dict[str, Any]


def initial_state(question: str) -> GraphState:
    """Build the initial state for a single question turn."""
    from langchain_core.messages import HumanMessage

    return {
        "question": question,
        "messages": [HumanMessage(content=question)],
        "context": [],
        "tool_results": [],
        "answer": "",
        "guard_flags": {},
    }
