# Video 10 — How to build a Chatbot using LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `51Ve2tE3Zns`
> **Watch:** https://www.youtube.com/watch?v=51Ve2tE3Zns

## 🎯 Overview
This is the **first video of a multi-part series** on building a full-featured chatbot with LangGraph. Having finished the fundamentals (sequential, parallel, conditional and looping workflows), the series now shifts to building something useful. Over the coming videos the chatbot will grow to include RAG, tools, a UI, LangSmith integration, memory, persistence, human-in-the-loop, retry logic and fault tolerance. In *this* video we build a **simple chatbot that can chat with a user and remember previous conversation history**, and we discover why naive chat loses memory — introducing (at a high level) the persistence / `MemorySaver` solution.

## 🧠 Key Concepts

### A chatbot is just a simple LangGraph workflow
A chatbot is essentially an **LLM-based sequential workflow with a single node** (`chat_node`). The user's message goes from `START` into the chat node (which holds an LLM), the LLM generates a reply, and it flows to `END`. You repeat this in a loop as long as the user is chatting.

### What is the state? — Messages
For a chatbot, the important data is the **conversation** — every message exchanged between the user and the LLM. So the state holds a single attribute, `messages`, which is a **list of messages** accumulating the whole conversation history.

### Why `list[BaseMessage]` instead of `list[str]`
When you talk to an LLM you communicate in terms of **messages**, and LangChain defines several message types, all inheriting from `BaseMessage`:
- **HumanMessage** — what the human types (e.g., "What is the capital of India?").
- **AIMessage** — what the LLM replies (e.g., "New Delhi").
- **SystemMessage** — sets the LLM's role/behaviour.
- **ToolMessage** — output from a tool.

Typing `messages` as `list[BaseMessage]` lets the list hold any of these message types, giving full flexibility.

### Why a reducer (`add_messages`) is required
By default, LangGraph state **replaces** a value whenever a node writes to it. For messages that's wrong — each new message would overwrite the previous one, destroying history. To *append* instead of replace, you attach a **reducer**. Instead of `operator.add`, LangGraph provides a built-in reducer specialised for messages: **`add_messages`** (from `langgraph.graph.message`). It appends messages to the list and is optimised to work with `BaseMessage` objects, so it's the recommended choice.

### The big problem: no memory across `invoke` calls
Even though the chat loop feels like a real chatbot, it forgets everything. Reason: **every loop iteration calls `chatbot.invoke(...)` fresh**, and each invocation starts the state from scratch. The previous conversation lived only inside the prior invocation's state, which is erased when that workflow execution ends. So on the next turn the LLM only sees the single new message — hence it can't recall your name or a running calculation.

### The fix: Persistence via a checkpointer (`MemorySaver`)
**Persistence** changes LangGraph's default behaviour so that when execution reaches `END`, the state is **saved** (not erased) and **restored** on the next invocation. Storage options:
- **In-memory (RAM)** via `MemorySaver` — survives while the program is in memory. Good for demos/basic bots.
- **Database** — survives program restarts; used in production so a user can resume a conversation days later.

To use it you: (1) create a `MemorySaver` checkpointer, (2) pass it to `compile(checkpointer=...)`, and (3) supply a **thread_id** in a `config` dict on every `invoke`.

### Threads
A **thread** represents one interaction/conversation with the chatbot. Different users (or sessions) get different `thread_id`s so the chatbot can keep their conversations separate. The `thread_id` is how LangGraph knows *whose* saved state to load and append to.

## 🔧 Code / Implementation

### State + graph
```python
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver   # for persistence

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatOpenAI()   # default model

def chat_node(state: ChatState):
    messages = state["messages"]          # extract conversation so far
    response = llm.invoke(messages)       # send to LLM
    return {"messages": [response]}       # append (reducer merges into history)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

checkpointer = MemorySaver()
chatbot = graph.compile(checkpointer=checkpointer)
```

### One-shot invocation
```python
initial_state = {
    "messages": [HumanMessage(content="What is the capital of India?")]
}
final_state = chatbot.invoke(initial_state)

# extract just the answer
print(final_state["messages"][-1].content)   # -> "The capital of India is New Delhi."
```

### Chat loop WITH memory (thread_id via config)
```python
thread_id = "1"
config = {"configurable": {"thread_id": thread_id}}

while True:
    user_message = input("Type here: ")
    if user_message.strip().lower() in ["exit", "quit", "bye"]:
        break

    response = chatbot.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
    )
    print("AI:", response["messages"][-1].content)
```

### Inspecting stored state
```python
chatbot.get_state(config)   # returns the full saved state for that thread_id
```

## 🪜 Step-by-Step Walkthrough
1. Define `ChatState` with a single `messages` field typed `list[BaseMessage]`.
2. Attach the `add_messages` reducer so new messages append rather than overwrite.
3. Build a one-node graph: `START → chat_node → END`.
4. In `chat_node`, read `messages`, call `llm.invoke(messages)`, return the response wrapped in a list.
5. Compile to get the `chatbot` object and visualise (`START → chat_node → END`).
6. Test with a single `HumanMessage`; read the answer from `messages[-1].content`.
7. Wrap it in a `while True` loop to get a real chat feel, breaking on `exit`/`quit`/`bye`.
8. Observe the **memory failure** — the bot forgets your name / running totals because each `invoke` starts fresh.
9. Fix it: import `MemorySaver`, create a `checkpointer`, pass it to `compile(checkpointer=checkpointer)`.
10. On every `invoke`, pass `config={"configurable": {"thread_id": ...}}`.
11. Re-run — now the bot remembers ("Your name is Nitish") and chains calculations correctly.
12. Note: restarting the kernel wipes RAM-based memory; a database checkpointer would survive.

## ⚠️ Gotchas & Tips
- **Wrap the returned message in a list** (`{"messages": [response]}`) so the `add_messages` reducer merges it into the existing history.
- **Prefer `add_messages` over `operator.add`** for message lists — it's built-in and optimised for `BaseMessage` objects.
- **Naive loops lose memory**: calling `invoke` repeatedly resets state each time. Persistence (a checkpointer) is what carries history across invocations.
- **`thread_id` is mandatory once a checkpointer is set** — it identifies which conversation's state to load/save. Different users → different thread IDs.
- **`MemorySaver` stores in RAM only** — a kernel restart erases it. For durable, resumable chats use a database checkpointer (covered in production setups).
- Jupyter's input box can behave oddly (messages appearing out of order); this is a UI quirk, not a code bug.
- Persistence, checkpointers and threads are only *used* here — they get a dedicated deep-dive in the next video.

## 📌 Key Takeaways
- A LangGraph chatbot is a **single-node sequential workflow**; the state is the **message list**.
- Type messages as **`list[BaseMessage]`** to allow Human/AI/System/Tool messages, and use the **`add_messages` reducer** to accumulate history.
- Extract the reply with `state["messages"][-1].content`.
- A plain chat loop **forgets everything** because each `invoke` restarts the state from scratch.
- **Persistence** fixes this by saving and restoring state across invocations.
- Enable it with a **`MemorySaver` checkpointer** passed to `compile()`, plus a **`thread_id`** in the `config` on every `invoke`.
- **RAM-based memory is lost on restart**; production chatbots use **database checkpointers** for resumable conversations.
- This is Part 1 — persistence, checkpointers and threads are explained in depth in the next video.
