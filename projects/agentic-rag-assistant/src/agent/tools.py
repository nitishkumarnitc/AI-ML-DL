"""Agent tools.

Each tool is defined once as a plain "core" function and exposed on two
surfaces:
  * to the LangGraph agent as a LangChain ``@tool`` object (below), and
  * over the Model Context Protocol via ``src/mcp_server/server.py``.

Sharing the core implementation keeps the in-process agent and the MCP server
behaviourally identical — add a core function here and it is exposable on both.

The order-status and ticketing tools use small in-memory mocks so the demo runs
with no external systems; the ``# TODO`` markers show where a real integration
(order DB, ticketing API) would slot in.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from langchain_core.tools import tool

# --- Mock backends (stand-ins for real systems) ----------------------------
# TODO: replace with a real order service (DB / OMS API).
_SAMPLE_ORDERS: dict[str, dict] = {
    "AC-1001": {"status": "shipped", "carrier": "UPS", "eta": "2 business days", "items": 2},
    "AC-1002": {"status": "processing", "carrier": None, "eta": "not yet shipped", "items": 1},
    "AC-1003": {"status": "delivered", "carrier": "FedEx", "eta": "delivered", "items": 3},
    "AC-1004": {"status": "cancelled", "carrier": None, "eta": "n/a", "items": 1},
}


# --- Core implementations (shared by the LangChain tools and the MCP server) -
def kb_search(query: str) -> str:
    """Core knowledge-base search shared by the LangChain tool and MCP server."""
    from src.agent.retrieval import get_retriever

    results = get_retriever().search(query)
    if not results:
        return "No relevant information was found in the knowledge base."
    return "\n\n".join(results)


def current_datetime() -> str:
    """Core datetime implementation shared by the LangChain tool and MCP server."""
    return datetime.now(timezone.utc).isoformat()


def order_status(order_id: str) -> str:
    """Core order-status lookup. Returns a concise human-readable status line."""
    key = (order_id or "").strip().upper()
    if not key:
        return "Please provide an order id (they look like 'AC-1001')."
    order = _SAMPLE_ORDERS.get(key)
    if order is None:
        return f"No order found with id '{order_id}'. Order ids look like 'AC-1001'."
    parts = [f"Order {key}: {order['status']}"]
    if order.get("carrier"):
        parts.append(f"carrier {order['carrier']}")
    parts.append(f"ETA: {order['eta']}")
    parts.append(f"{order['items']} item(s)")
    return "; ".join(parts) + "."


def create_ticket(subject: str, description: str, email: str = "") -> str:
    """Core support-ticket creation. Returns a confirmation with a stable id.

    The id is a deterministic hash of subject+description, so the same request
    yields the same id (handy for idempotency and for asserting in tests).
    """
    subject = (subject or "").strip()
    description = (description or "").strip()
    if not subject or not description:
        return "A support ticket needs both a subject and a description."
    digest = hashlib.sha1(f"{subject}|{description}".encode()).hexdigest()[:8].upper()
    ticket_id = f"TKT-{digest}"
    # TODO: replace with a real ticketing API call (Zendesk / Jira / etc.).
    who = f" for {email}" if email else ""
    return (
        f"Created support ticket {ticket_id}{who} with subject '{subject}'. "
        "Our team will follow up by email."
    )


# --- LangChain tool objects (bound to the model in the agent node) ----------
@tool
def search_knowledge_base(query: str) -> str:
    """Search the Acme support knowledge base and return relevant passages.

    Use this for any question about Acme products, orders, returns, shipping,
    warranty, or accounts.
    """
    return kb_search(query)


@tool
def get_current_datetime() -> str:
    """Return the current UTC date and time in ISO 8601 format."""
    return current_datetime()


@tool
def get_order_status(order_id: str) -> str:
    """Look up the current status of an Acme order by its id (e.g. 'AC-1001').

    Returns the fulfilment status, carrier, and ETA. Use when a customer asks
    where their order is or whether it has shipped.
    """
    return order_status(order_id)


@tool
def create_support_ticket(subject: str, description: str, email: str = "") -> str:
    """Create an Acme support ticket and return its id.

    Use when the knowledge base can't resolve an issue and the customer needs a
    human follow-up. Provide a short ``subject`` and a ``description``; ``email``
    is optional.
    """
    return create_ticket(subject, description, email)


# The tool set bound to the model in the agent node.
TOOLS = [
    search_knowledge_base,
    get_current_datetime,
    get_order_status,
    create_support_ticket,
]
