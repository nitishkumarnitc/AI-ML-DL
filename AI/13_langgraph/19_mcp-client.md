# Video 19 — How to build an MCP Client using LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `yZGjVA4uDc4`
> **Watch:** https://www.youtube.com/watch?v=yZGjVA4uDc4

## 🎯 Overview
This video introduces **MCP (Model Context Protocol)** — described as an *improved, standardized way to connect tools to LLM applications*. The instructor first explains **why plain tools are brittle** (the n×m maintenance problem), then how MCP fixes it via a clean **client/server separation of concerns**. The hands-on goal is to build an **MCP client** inside LangGraph (not a server) that talks to an existing MCP server, replacing a previously hand-written calculator tool. Along the way the code is converted from **synchronous to asynchronous** because the MCP client library only works in async mode, and a second (remote) MCP server is added to show the multi-server capability.

## 🧠 Key Concepts

### What MCP is and why it exists
MCP is not something completely new — it is a **standardized way to connect tools to your LLM applications**, i.e. "an improved version of tools." Tools solved the problem of making a chatbot capable of actions, but the tools approach has an **inherent flaw** that MCP is designed to fix.

### The problem with the plain-tools approach — brittleness
Suppose you write a custom tool to connect the chatbot to GitHub (e.g. list pull requests). The tool holds a large block of code: a GitHub token, headers, a hit to `api.github.com/repos/.../pulls`, JSON extraction, and field-by-field printing (PR number, title, author, state, URL). This works today, but there is **no guarantee it works tomorrow**:

- If GitHub bumps its API from v1.0 → v2.0, field names or URLs may change (e.g. `pulls` → `pull-requests`, `title` → `title_name`, `user` → `user_name`).
- The instant the API changes, your tool breaks and you must go study GitHub's docs and rewrite the tool code.

That is just **one** tool. A real GitHub integration might need ~10 tools (commits, files, etc.). One API change forces edits in all of them. Multiply by multiple chatbots in your company and multiple services (Gmail, Slack, Jira, ...) and you get an **n×m maintenance problem** (n tools × m chatbots). The root issue: **server-side changes leak into and break the client side.** That should not happen — and it's the biggest problem with the tools approach.

### How MCP solves it — separation of concerns
In MCP the two sides get clean roles:
- **Client** = the chatbot side.
- **Server** = the tool side.

All the heavy tool code lives on the **server**. The **client** only holds a small **config** block. Even if the server changes its API, the client config does **not** change. Once your chatbot is connected to the GitHub MCP server via config, GitHub's version changes require **zero client-side edits**. With that small config code, the client automatically discovers what tools the server exposes, their definitions, what they do, and when to use them. Eliminating the n×m maintenance burden is MCP's **biggest selling point** — and why even ChatGPT now implements it.

### Client vs. server — scope of this video
Writing MCP requires two pieces: an **MCP server** and an **MCP client** that talks to it. This video focuses **only on the client**. You cannot build MCP servers in LangGraph — there's a dedicated library (**FastMCP**) for that, covered in the instructor's separate MCP playlist. Here, a ready-made server already exists; LangGraph is used only to write the client.

### Why async is required
The whole existing chatbot code is **synchronous** (no `async`/`await`). But the MCP client library works **only in async mode**. So before writing the client, the sync code must be converted to **asynchronous** code. LangGraph supports async execution. (Async also gives a bonus: parallel/concurrent execution — e.g. fetching weather and cricket score simultaneously instead of sequentially — though the video doesn't dive deep into async programming.)

### Transports: stdio (local) vs. streamable HTTP (remote)
There are two kinds of MCP servers and matching transports:
- **Local server → `stdio`** (standard input/output). Used when the server file lives on your own machine and is launched by the client.
- **Remote server → `streamable_http`**. Used when the server is deployed somewhere and reached by URL.

### MultiServerMCPClient — connecting many servers
`MultiServerMCPClient` (from `langchain-mcp-adapters`) can connect to **more than one** MCP server at once. Adding a second server is just another entry in the config dict — no new tool functions to write. You can even mix plain tools and MCP servers in the same chatbot.

## 🔧 Code / Implementation

### Install the client library
```bash
pip install langchain-mcp-adapters
# or, with uv:
uv add langchain-mcp-adapters
```

### The MCP server (already built, shown for context — uses FastMCP)
```python
# main.py on the instructor's machine — a simple math MCP server
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
async def add(a: float, b: float) -> float:
    return a + b

@mcp.tool()
async def subtract(a: float, b: float) -> float:
    return a - b

# ... multiply, divide, power, modulus — all async tools
```

### Step 1 — Convert the chatbot to async
```python
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()
llm = ChatOpenAI()

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

# custom nodes MUST become async; ToolNode is already async internally
async def chat_node(state: ChatState):
    messages = state["messages"]
    response = await llm_with_tools.ainvoke(messages)   # async invoke + await
    return {"messages": [response]}
```

### Step 2 — Define the MCP client (replaces the old calculator tool)
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    # Local server over stdio — the client launches it
    "math": {
        "command": "python",
        "args": ["/Users/.../Desktop/mcp_math_server/main.py"],
        "transport": "stdio",
    },
    # A second, REMOTE server over streamable HTTP (added later in the video)
    "expense_tracker": {
        "url": "https://<your-remote-mcp-server-url>",
        "transport": "streamable_http",
    },
})
```

### Step 3 — Fetch tools from the server inside an async build_graph()
```python
async def build_graph():
    tools = await client.get_tools()          # discovers add, subtract, multiply, ...
    global llm_with_tools
    llm_with_tools = llm.bind_tools(tools)

    tool_node = ToolNode(tools)

    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")      # loop back, same as tools video
    return graph.compile()
```

### Step 4 — Async main entry point
```python
async def main():
    chatbot = await build_graph()
    result = await chatbot.ainvoke({"messages": ["... your prompt ..."]})
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 🪜 Step-by-Step Walkthrough
1. Start from last video's simple sync LangGraph chatbot that used a single hand-written **calculator** tool.
2. **Convert sync → async** in a new file `chatbot_async.py`: import `asyncio`; make `chat_node` `async` and use `await llm_with_tools.ainvoke(...)`; move graph construction into an async `build_graph()`; add an async `main()` invoked via `asyncio.run(main())`. Keep the calculator tool for now and verify it still works.
3. Note: the **custom** `chat_node` must be made async, but the **`ToolNode` need not** be — its implementation is already async internally. You only async-ify your own nodes.
4. Look at the ready-made **MCP math server** (`main.py`, built with FastMCP, exposing add/subtract/multiply/divide/power/modulus).
5. In a new file `chatbot_mcp.py`, copy the async code, **remove the calculator tool**, and `pip install langchain-mcp-adapters`.
6. Create a `MultiServerMCPClient` with the local math server (`transport="stdio"`, `command="python"`, `args=[<path to main.py>]`).
7. Inside `build_graph`, call `await client.get_tools()`, bind the returned tools to the LLM, and build the `ToolNode` from them.
8. Run: the client **starts the server**, the tool list (add, subtract, divide, ...) is fetched and printed, and the query is answered correctly.
9. **Add a second, remote server** (`expense_tracker`) by adding another config entry with a `url` and `transport="streamable_http"`. No other code changes.
10. Test the remote server: "Add an expense 500 for a Udemy course on 10th November" → the `add_expenses`/`summarize`/`list_expenses` tools are discovered and used, with zero expense-tracking code written on the client.
11. (Project integration) Create `langgraph_mcp_backend.py` and `streamlit_frontend_mcp.py`. The backend uses **both** plain tools (search, get_stock_price) **and** MCP clients (math + expense tracker), merges all tools, and binds them. Because Streamlit is synchronous but the MCP client is async, the code also switches the DB to **aiosqlite** and the frontend from `stream` to `astream` inside an async loop — the instructor calls this "hacky."

## ⚠️ Gotchas & Tips
- **MCP fixes the n×m maintenance problem.** Server-side API changes should never force client-side rewrites.
- **You can't build MCP servers in LangGraph** — use FastMCP (see the instructor's MCP playlist). This video builds the **client** only.
- **The MCP client library is async-only** — that's the sole reason for the sync→async conversion.
- **Only async-ify your custom nodes.** `ToolNode` is already async internally; don't wrap it.
- **`await` requires an `async` function.** If `build_graph` uses `await client.get_tools()`, it must be `async`, and it must be `await`ed by its caller.
- **Match transport to server location:** `stdio` for local, `streamable_http` for remote.
- **`MultiServerMCPClient` supports many servers** — add servers by adding config entries; mixing plain tools and MCP is fine.
- **Don't use Streamlit for MCP front ends in production.** It's fundamentally synchronous; a better approach is FastAPI exposing APIs with a React/Next.js front end. The Streamlit integration shown is "hacky" and not production-compatible.
- For deep MCP theory (lifecycle, architecture), watch the instructor's dedicated 8-video MCP playlist first.

## 📌 Key Takeaways
- **MCP = a standardized, more robust, more future-proof way to connect tools to LLM apps** — an improved version of the tools approach.
- Plain tools are **brittle**: provider API changes break client code, creating an **n×m maintenance nightmare** across tools and chatbots.
- MCP enforces **client/server separation**: heavy tool code lives on the server; the client only holds a small **config**, immune to server-side changes.
- With one config block, the client **auto-discovers** the server's tools and their definitions.
- This video builds only the **MCP client** in LangGraph; servers are built separately with **FastMCP**.
- The MCP client library is **async-only**, so the chatbot code is converted to async (`ainvoke`/`await`, `asyncio.run`), async-ifying only custom nodes.
- **`MultiServerMCPClient`** connects to multiple servers; `stdio` = local, `streamable_http` = remote.
- You can freely **mix plain tools and MCP servers**, but the instructor recommends leaning toward MCP for future-proofing.
