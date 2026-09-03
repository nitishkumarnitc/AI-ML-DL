"""LangGraph node functions for the agentic RAG pipeline.

Nodes that need external dependencies (the LLM, the retriever) are built by
small factory functions that close over injected objects. This keeps the graph
pure and makes it trivial to unit-test with fakes (see ``tests/test_graph.py``).

Each node is wrapped in an observability ``span`` so a request trace captures
per-node latency, token usage, and cost. Spans are no-ops when no trace is
active, so instrumentation never changes node behaviour (see ``observability``).
"""
from __future__ import annotations

from collections.abc import Callable

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage

from src.agent.config import get_settings
from src.agent.guardrails import validate_input, validate_output
from src.agent.observability import span
from src.agent.prompts import FALLBACK_ANSWER, REFUSAL_ANSWER, build_system_prompt
from src.agent.state import GraphState
from src.agent.tools import TOOLS

_TOOL_MAP = {t.name: t for t in TOOLS}


def get_default_llm():
    """Construct the default Anthropic chat model from settings (lazy import).

    Imported lazily so unit tests can build the graph with a fake LLM without
    requiring ``langchain-anthropic`` or an API key.
    """
    from langchain_anthropic import ChatAnthropic

    settings = get_settings()
    return ChatAnthropic(
        model=settings.model,
        temperature=settings.temperature,
        api_key=settings.anthropic_api_key or None,
        timeout=60,
        max_retries=2,
    )


def make_retrieve_node(retriever) -> Callable[[GraphState], dict]:
    """Build the ``retrieve`` node: input guardrails + RAG lookup."""

    def retrieve(state: GraphState) -> dict:
        settings = get_settings()
        question = state["question"]
        with span("retrieve", input_chars=len(question)) as sp:
            guard = validate_input(question, max_chars=settings.max_input_chars)
            flags: dict = {"input": guard.flags, "input_reason": guard.reason}
            if not guard.ok:
                # Defense in depth: skip retrieval and let the agent short-circuit.
                sp.set(input_blocked=True, n_context=0)
                return {"context": [], "guard_flags": {**flags, "input_blocked": True}}
            context = retriever.search(question)
            sp.set(input_blocked=False, n_context=len(context))
            return {"context": list(context), "guard_flags": {**flags, "input_blocked": False}}

    return retrieve


def make_agent_node(llm) -> Callable[[GraphState], dict]:
    """Build the ``agent`` node: a tool-calling LLM grounded in retrieved context."""

    def agent(state: GraphState) -> dict:
        if state.get("guard_flags", {}).get("input_blocked"):
            # Input was rejected upstream; refuse without calling the model.
            return {"messages": [AIMessage(content=REFUSAL_ANSWER)]}
        with span("agent") as sp:
            model = llm.bind_tools(TOOLS)
            system = SystemMessage(content=build_system_prompt(state.get("context", [])))
            history: list[BaseMessage] = state["messages"]
            response = model.invoke([system, *history])
            sp.record_llm_usage(response)
            sp.set(tool_calls=len(getattr(response, "tool_calls", None) or []))
            return {"messages": [response]}

    return agent


def make_tools_node() -> Callable[[GraphState], dict]:
    """Build the ``tools`` node: execute the tool calls emitted by the agent.

    Written explicitly for readability; ``langgraph.prebuilt.ToolNode`` is the
    production shortcut for the same behaviour.
    """

    def tools(state: GraphState) -> dict:
        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", None) or []
        with span("tools", n_tool_calls=len(tool_calls)) as sp:
            messages: list[BaseMessage] = []
            results: list[str] = []
            for call in tool_calls:
                tool = _TOOL_MAP.get(call["name"])
                if tool is None:
                    output = f"Unknown tool: {call['name']}"
                else:
                    output = str(tool.invoke(call.get("args", {})))
                results.append(output)
                messages.append(
                    ToolMessage(content=output, name=call["name"], tool_call_id=call["id"])
                )
            sp.set(tools=[c["name"] for c in tool_calls])
            return {"messages": messages, "tool_results": results}

    return tools


def guardrail_node(state: GraphState) -> dict:
    """Validate the final answer; substitute a safe fallback if it fails."""
    with span("guardrail") as sp:
        last = state["messages"][-1]
        answer = last.content if isinstance(last.content, str) else str(last.content)
        guard = validate_output(answer, state.get("context", []))
        final = answer if guard.ok else FALLBACK_ANSWER
        flags = dict(state.get("guard_flags", {}))
        flags["output"] = guard.flags
        flags["output_reason"] = guard.reason
        sp.set(output_ok=guard.ok)
        return {"answer": final, "guard_flags": flags}


def route_after_agent(state: GraphState) -> str:
    """Route to ``tools`` when the model requested tools, else to ``guardrail``."""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return "guardrail"
