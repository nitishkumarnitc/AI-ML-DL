"""MCP stdio server exposing Acme support tools over the Model Context Protocol.

Run it directly::

    python -m src.mcp_server.server

It exposes the same two tools the in-process agent uses (sharing the core
implementations from ``src.agent.tools``), so any MCP-capable client — Claude
Desktop, another agent, or ``langchain-mcp-adapters`` — can call them.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.agent.tools import create_ticket, current_datetime, kb_search, order_status

mcp = FastMCP("acme-support-tools")


@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """Search the Acme support knowledge base and return relevant passages."""
    return kb_search(query)


@mcp.tool()
def get_current_datetime() -> str:
    """Return the current UTC date and time in ISO 8601 format."""
    return current_datetime()


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Look up the current status of an Acme order by its id (e.g. 'AC-1001')."""
    return order_status(order_id)


@mcp.tool()
def create_support_ticket(subject: str, description: str, email: str = "") -> str:
    """Create an Acme support ticket and return its id."""
    return create_ticket(subject, description, email)


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
