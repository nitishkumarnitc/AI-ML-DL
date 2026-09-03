# Video 18 — Tools in LangGraph (tool binding, tool calling, ToolNode)

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `_UuUigoM9MA`
> **Watch:** https://www.youtube.com/watch?v=_UuUigoM9MA

## 🎯 Overview
Until now the chatbot could only *talk*; it could not *do*. This video gives it the ability to **perform actions** by adding tools. The instructor adds three tools — a **calculator**, an **internet search** (DuckDuckGo), and a **stock-price** lookup — and teaches the two LangGraph primitives that make tool use work: **`ToolNode`** (which holds and executes the tools) and **`tools_condition`** (a prebuilt conditional edge that decides whether to route to the tools or end). The video is split into two parts: first the tool-adding fundamentals on a standalone graph, then integrating the three tools into the existing chatbot project.

## 🧠 Key Concepts

### Why tools — talk vs. act
The chatbot is connected to an OpenAI LLM on the backend, so it converses well. But it cannot perform actions or fetch live information (e.g. "top news in India today"). Tools remove that limitation: with tools bound, the bot decides on its own whether a query needs a tool and, if so, which tool to invoke.

### Two types of tools: prebuilt vs. custom
- **Prebuilt tools** ship with LangChain — e.g. `DuckDuckGoSearchRun` for internet search. No code required.
- **Custom tools** are functions you write for your own use case, decorated with `@tool`. Example: the calculator and the stock-price tool.

### The naive workflow and why it's not enough
The simplest LangGraph flow is `START → chat_node → END`, where the chat node just runs an LLM. To support actions, the chat node must additionally do **decision making**: read the query and decide whether the user wants normal chatting or wants an action performed. If it's an action, control must go elsewhere — to the tools.

### ToolNode — the tool executor
A **`ToolNode`** is a **prebuilt node** provided by LangGraph that acts as a bridge between your graph and external tools. Normally you write a node function yourself (takes state, returns state). `ToolNode` is a ready-made node that knows how to handle a list of LangChain tools. All the tools you want are collected into one list and handed to the `ToolNode`, which then:
- listens for **tool calls** emitted by the LLM,
- routes each call to the **correct tool**,
- runs it with the input the LLM specified,
- and returns the tool's response.

In short, the `ToolNode` is where your tools reside and the thing that executes them.

### tools_condition — the routing decision
**`tools_condition`** is a **prebuilt conditional edge function**. Placed on the outgoing edge of the chat node, it inspects the chat node's output and decides whether the flow should go to the `ToolNode` (a tool call was requested) or to `END` (a normal answer). This is what makes the chat node's branch conditional.

### The critical fix — loop the tool output back to the LLM
A first attempt wires `chat_node → tools → END`. This has **two problems**:
1. **Raw, unpolished output.** The tool returns technical data (e.g. the stock tool returns raw JSON), which is shown directly to the user. Ideally the LLM should phrase it: "The current stock price of Apple is $X."
2. **No multi-step reasoning.** A query like "What is the stock price of Apple? How much would 15 shares cost?" needs two tools in sequence (fetch price, then multiply). With `tools → END`, the second step is impossible; you get garbled output.

The fix is to add an edge **back from the tools to the chat node**, forming a loop between the LLM and the tools:

```
START → chat_node → (tools_condition) → ToolNode → chat_node   # loop back
                                       ↘ END
```

Now the tool result returns to the chat node, which has the full history and can either polish the answer or invoke another tool. For a two-step query, the LLM fetches the stock price, sees the result, decides to call the calculator, multiplies, then produces the final answer and routes to `END`.

## 🔧 Code / Implementation

### Imports
```python
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
```

### Creating the three tools
```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import requests

load_dotenv()
llm = ChatOpenAI()

# 1) Prebuilt internet-search tool
search_tool = DuckDuckGoSearchRun()

# 2) Custom calculator tool
@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """Perform a basic arithmetic operation (add, sub, mul, div) on two numbers."""
    if operation == "add":
        result = first_num + second_num
    elif operation == "sub":
        result = first_num - second_num
    elif operation == "mul":
        result = first_num * second_num
    elif operation == "div":
        result = first_num / second_num
    else:
        return {"error": "Unsupported operation"}
    return {"first_num": first_num, "second_num": second_num,
            "operation": operation, "result": result}

# 3) Custom stock-price tool (Alpha Vantage API)
@tool
def get_stock_price(symbol: str) -> dict:
    """Fetch the latest stock price for a given ticker symbol using Alpha Vantage."""
    url = (f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
           f"&symbol={symbol}&apikey=YOUR_ALPHA_VANTAGE_KEY")
    response = requests.get(url)
    return response.json()
```

### Binding tools to the LLM
```python
tools = [search_tool, calculator, get_stock_price]
llm_with_tools = llm.bind_tools(tools)
```

### State, nodes, and graph (with the loop-back edge)
```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

def chat_node(state: ChatState):
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)   # LLM WITH tools, not plain llm
    return {"messages": [response]}

tool_node = ToolNode(tools)   # prebuilt node holding all three tools

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)  # → "tools" or END
graph.add_edge("tools", "chat_node")   # THE FIX: loop tool output back to the LLM

chatbot = graph.compile()
```

### Invoking
```python
chatbot.invoke({"messages": ["Hello"]})                     # normal chat → END
chatbot.invoke({"messages": ["What is the product of 2 x 3?"]})   # → calculator → chat_node → "The result of 2 * 3 is 6"
chatbot.invoke({"messages": ["What is the stock price of Apple?"]})
```

## 🪜 Step-by-Step Walkthrough

### Part 1 — Fundamentals (standalone graph)
1. Import `ToolNode` and `tools_condition` from `langgraph.prebuilt`, plus `DuckDuckGoSearchRun` and `@tool`.
2. Load `.env` and create the `ChatOpenAI` LLM.
3. Create the three tools (search = prebuilt; calculator and stock price = custom `@tool` functions with docstrings).
4. Put them in a `tools` list and call `llm.bind_tools(tools)`.
5. Define the `messages` state (same as the chatbot project).
6. Add two nodes: `chat_node` (runs `llm_with_tools`) and `tools` (a `ToolNode(tools)`).
7. Wire `START → chat_node`, then a conditional edge from `chat_node` via `tools_condition`.
8. Observe the first-attempt problems (raw JSON output; broken multi-step query).
9. Add `graph.add_edge("tools", "chat_node")` to loop back, recompile, and confirm polished answers and working two-step reasoning.
10. (Optional) Open LangSmith to visualize the three phases: chat_node → tools → chat_node, and see `tools_condition` deciding `tools` then `end`.

### Part 2 — Integrate into the chatbot project
1. Create a new backend file `langgraph_tool_backend.py` — essentially the old backend rewritten with the three tools, `bind_tools`, the `ToolNode`, the checkpointer, and the looped graph.
2. In the Streamlit frontend, change the import to point at the new backend file (`from langgraph_tool_backend import ...`); otherwise the frontend is unchanged.
3. Fix streaming: the backend now emits two message types — **AIMessage** (from the LLM) and **ToolMessage** (from the tool). Only stream AI messages.

```python
from langchain_core.messages import AIMessage
# in the streaming loop:
if isinstance(message_chunk, AIMessage):
    # stream / print it
    ...
```
4. (Optional UX) Use Streamlit's **status container** (the fourth chat element) to show which tool is being used behind the scenes. The instructor provides a separate frontend file for this rather than explaining the trickier status-container code line by line.

## ⚠️ Gotchas & Tips
- **Always add a docstring to custom tools.** The LLM reads the docstring to decide which tool fits a given problem statement.
- **Bind tools, then call the bound LLM.** The chat node must call `llm_with_tools`, not the plain LLM.
- **Loop the tools back to the chat node** — never `tools → END`. This is what enables polished answers and multi-step tool chaining.
- **Get your own Alpha Vantage API key** (it's free). Don't reuse someone else's; the free daily quota exhausts quickly.
- **Filter streaming by message type.** Stream `AIMessage` only; do not stream `ToolMessage`, or the raw tool output leaks into the UI.
- **DuckDuckGo results can be flaky** in the demo — the tool works, but result quality varies.
- Only two new concepts really matter here: **`ToolNode`** (holds/executes tools) and **`tools_condition`** (routes chat-vs-tool). Master these and the code is easy.
- Prior familiarity with tools/tool-calling from the instructor's LangChain playlist is assumed.

## 📌 Key Takeaways
- Tools let the chatbot *act*, not just talk; there's no limit to what tools you can attach.
- Tools are either **prebuilt** (LangChain-provided, e.g. `DuckDuckGoSearchRun`) or **custom** (`@tool`-decorated functions).
- **`ToolNode`** is a prebuilt node that stores a list of tools, listens for tool calls, routes to the right tool, and returns its output.
- **`tools_condition`** is a prebuilt conditional edge that decides: go to the `ToolNode` or go to `END`.
- Bind tools to the LLM with `llm.bind_tools(tools)`; the chat node must invoke the bound LLM.
- The essential graph shape is a **loop**: `chat_node → tools → chat_node`, with a conditional exit to `END`.
- Looping tool output back to the LLM fixes both unpolished output and multi-step reasoning.
- Integrating into the project = a new backend file, a one-line frontend import change, and an `AIMessage`-only streaming filter.
