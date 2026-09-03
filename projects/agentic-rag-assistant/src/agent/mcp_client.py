"""Load agent tools from the MCP server, with a fallback to local tools.

Demonstrates that the agent can consume the *same* tools over the Model Context
Protocol. Prefers the optional ``langchain-mcp-adapters`` package; if it (or the
server) is unavailable, it degrades gracefully to the in-process tools in
``src.agent.tools`` so the agent always runs.

    pip install -e ".[mcp-adapters]"   # enable the MCP-backed path
"""
from __future__ import annotations

import asyncio
import logging
import sys

from src.agent.tools import TOOLS as LOCAL_TOOLS

logger = logging.getLogger(__name__)


async def _load_from_mcp() -> list:
    """Start the stdio MCP server and load its tools as LangChain tools."""
    # Imported inside the function so the optional dependency is only required
    # when the MCP-backed path is actually used.
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "acme": {
                "command": sys.executable,
                "args": ["-m", "src.mcp_server.server"],
                "transport": "stdio",
            }
        }
    )
    return await client.get_tools()


def get_tools(prefer_mcp: bool = True) -> list:
    """Return tools for the agent, preferring MCP with a local fallback.

    Args:
        prefer_mcp: Try the MCP server first. On any failure (missing optional
            dependency, transport error) this falls back to local tools.
    """
    if prefer_mcp:
        try:
            return asyncio.run(_load_from_mcp())
        except Exception as exc:  # ImportError, transport failure, etc.
            logger.warning("Falling back to local tools (MCP unavailable): %s", exc)
    return list(LOCAL_TOOLS)


# TODO: wire get_tools() into build_graph() to run the agent fully MCP-backed.
#       It is kept opt-in here so the default graph and unit tests stay
#       hermetic and fully offline.
