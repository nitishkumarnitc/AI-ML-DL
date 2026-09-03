# Video 24 — How To Implement Short Term Memory Using LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `FSBkTI1QuvY`
> **Watch:** https://www.youtube.com/watch?v=FSBkTI1QuvY

## 🎯 Overview
This is the hands-on follow-up to the conceptual memory video (Video 23). It shows **how to implement short-term memory in LangGraph** using a **checkpointer** and **thread IDs**, how to make it durable with **persistence** via a **PostgreSQL** database (run through Docker), and how to solve the **context-overflow problem** with **trimming**, **deletion**, and **summarization**. Prerequisite: watch Video 23 first, since the theory (stateless LLMs, conversation buffer) directly underpins this code.

## 🧠 Key Concepts

### Recap: why STM is needed
LLMs have **no intrinsic memory** — every `llm.invoke` call is treated as a **fresh, stateless** conversation. To keep a conversation going we maintain a **conversation buffer**: when sending any message to the LLM we include not only the user's current message but the **entire prior conversation concatenated**. This gives the LLM full context at every call, and that is short-term memory.

### The two LangGraph building blocks for STM
1. **Checkpointer** — a LangGraph concept that stores your **graph's state** at **every super-step**. This is what actually persists the conversation so it can be reloaded. Initially we store it in **RAM** (`InMemorySaver`), which is lost when the program exits; later we move to a database.
2. **Thread / thread ID** — each conversation gets a thread ID. State is stored **against** that thread ID, so each conversation (thread) has its own independent conversation buffer. Thread ID can be generated dynamically.

### The context-overflow problem
Every LLM has a **context window** = the maximum tokens it can process while generating a response. Because STM re-attaches the whole history on every call, a long conversation (500–1000+ messages, with long AI responses) can push input tokens **past the context window**. Then the LLM's responses degrade — it may hallucinate or give improper answers. Golden rule: **input tokens should be well below the context window.**

Three techniques address this: **trimming**, **deletion**, and **summarization**.

### Trimming
Set a **max token limit**. Before invoking the LLM, check the total token count of all messages. If it's under the limit, send everything. If it **exceeds** the limit, keep only the **most recent *n* messages** whose combined token count fits within the limit, and drop the older ones. Assumption: in a long chat, the active context lives in the recent ~50–100 messages; older ones aren't as useful.

**Important:** trimming does **not delete** anything — messages remain in state (and in the checkpointer/memory). You simply **don't show** the trimmed ones to the LLM on that call.

**Inherent flaw:** older messages are **completely ignored**, so in many real-world scenarios you lose useful context and the conversation hits a "breaking point." Summarization fixes this.

### Deletion
Permanently **remove messages from the state** using LangChain's `RemoveMessage`. This is a **prerequisite for summarization** (you delete the old raw messages once they've been summarized), so the video teaches deletion first.

### Summarization
Like trimming, you always send the most recent *n* messages — **but** instead of ignoring older messages, you send them to **another LLM to generate a summary**, then send *summary + recent n messages* to the main LLM. Context is preserved even for very long chats.

Example: after 500 messages, keep the recent 100 and summarize the older 400 → send *summary(400) + recent 100*. When 100 more arrive, keep the newest 100, summarize the next 100, and **merge** it into the existing summary → now you hold *summary(500) + recent 100*.

**Deletion + summarization operate together:** after generating the summary you **delete** the old raw messages from state. If you kept both the old messages **and** their summary, it would cause confusion — so keep only the summary.

## 🔧 Code / Implementation

### 1. Basic short-term memory (checkpointer + thread ID)

**Without STM (baseline) — the model forgets:**

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
model = ChatOpenAI()   # default chat model

def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": response}

builder = StateGraph(MessagesState)      # MessagesState is built-in; no custom state needed
builder.add_node("chat", call_model)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)
graph = builder.compile()                # NOTE: no checkpointer here

graph.invoke({"messages": [("user", "Hi, my name is Nitish")]})
graph.invoke({"messages": [("user", "What is my name?")]})
# -> "I'm sorry, I cannot know your name as I am a computer program."
```

**With STM — add an `InMemorySaver` checkpointer + a `thread_id`:**

```python
from langgraph.checkpoint.memory import InMemorySaver

builder = StateGraph(MessagesState)
builder.add_node("chat", call_model)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

checkpointer = InMemorySaver()                 # store checkpoints in RAM
graph = builder.compile(checkpointer=checkpointer)   # <-- the main difference

config = {"configurable": {"thread_id": "thread-1"}}

graph.invoke({"messages": [("user", "Hi, my name is Nitish")]}, config=config)
result = graph.invoke({"messages": [("user", "What is my name?")]}, config=config)
# -> "Your name is Nitish."

# Inspect the stored state for this thread:
graph.get_state(config).values["messages"]
# -> the 4 messages: Hi/my name is Nitish, Hi nice to meet you, What is my name?, Your name is Nitish
```

**Different thread = different (empty) buffer:**

```python
config2 = {"configurable": {"thread_id": "thread-2"}}
graph.invoke({"messages": [("user", "What is my name?")]}, config=config2)
# -> "I'm sorry, I do not have the ability to know your name."  (new conversation)
```

**The fragility problem:** `InMemorySaver` stores state in **RAM**, which is **volatile**. Restart the program and `get_state` for thread-1/thread-2 returns nothing — all past messages are lost. For production, use a production-grade database instead.

### 2. Persistence with PostgreSQL (via Docker)
LangGraph docs recommend PostgreSQL. Docker avoids the installation issues of a local Postgres install.

**Setup steps (run as-is):**
1. Install Docker (from docker.com) and start Docker Desktop.
2. Verify: `docker --version`.
3. Create a `docker-compose.yml` that loads a PostgreSQL image with env vars (username, password, DB name) and port mapping.
4. Start it: `docker compose up -d`.
5. Verify the container is running: `docker ps`.
6. Install Python dependencies: `langgraph`, `langgraph-checkpoint-postgres`, `langchain-openai` (install from a terminal if the notebook errors).

**Code — use `PostgresSaver` inside a context manager:**

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_openai import ChatOpenAI

model = ChatOpenAI()

def call_model(state: MessagesState):
    return {"messages": model.invoke(state["messages"])}

# (Build the same single-node graph structure as before, via `builder`.)

DB_URI = "postgresql://<user>:<password>@localhost:<port>/<dbname>?sslmode=disable"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()                       # first-time table setup
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "thread-1"}}
    graph.invoke({"messages": [("user", "Hi my name is Nitish")]}, config=config)
    response = graph.invoke({"messages": [("user", "What is my name?")]}, config=config)
    print(response)                            # knows the name within the same thread
```

**Proving persistence:** restart the shell, re-open the context manager with the **same** `DB_URI` and a thread ID, and — **without invoking any new message** — just fetch state:

```python
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "thread-1"}}
    print(graph.get_state(config).values["messages"])   # last messages still there!
```

Even after removing the program from RAM, the past conversation is retrieved from Postgres. That's a production-grade setup: just swap `InMemorySaver` for `PostgresSaver` and use it inside a context manager.

### 3. Trimming with `trim_messages`
LangChain provides `trim_messages` to do the heavy lifting. Trim **before** sending to the LLM; the messages remain in state — they're just not shown to the model.

```python
from langchain_core.messages import trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.checkpoint.memory import InMemorySaver

model = ChatOpenAI()
MAX_TOKENS = 150   # never send more than ~150 tokens of history to the LLM

def call_model(state: MessagesState):
    trimmed = trim_messages(
        state["messages"],
        max_tokens=MAX_TOKENS,
        token_counter=count_tokens_approximately,   # LangChain's heuristic counter
        strategy="last",                            # keep the most recent messages
    )
    response = model.invoke(trimmed)                # send only the trimmed messages
    return {"messages": response}

# ... build graph, compile with InMemorySaver checkpointer ...
```

Observed behaviour with `MAX_TOKENS = 150`:
- Msg 1 "Hi my name is Nitish" → current token count ~10, no trim.
- Add "I am learning LangGraph" → ~40 tokens, no trim.
- Add "Can you explain short term memory?" → ~108 tokens, no trim (full history sent).
- Then "What is my name?" pushes the total **over 150** → trimming keeps only the last message(s) that fit; the "my name is Nitish" message is dropped from what the LLM sees, so it replies *"I'm sorry, I don't know your name."*

`count_tokens_approximately` is a heuristic (it also counts things like the `role`), so don't fixate on exact numbers. The main knob you control is `MAX_TOKENS`, tuned by experimentation for your app.

### 4. Deletion with `RemoveMessage`
Two nodes: a normal `chat` node and a `delete_old_messages` cleanup node. Cleanup runs only when the conversation exceeds a threshold.

```python
from langchain_core.messages import RemoveMessage

def delete_old_messages(state: MessagesState):
    messages = state["messages"]
    if len(messages) > 10:                 # more than 10 messages in the conversation
        # remove the FIRST 6, keeping only the last 4
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:6]]}
    return {}

builder = StateGraph(MessagesState)
builder.add_node("chat", call_model)
builder.add_node("cleanup", delete_old_messages)
builder.add_edge(START, "chat")
builder.add_edge("chat", "cleanup")
builder.add_edge("cleanup", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

Test: 7 separate invokes → after all run there should be 14 messages (7 user + 7 AI). But since 14 > 10, the **first 6** are deleted, leaving **8** messages in state (the oldest three exchanges — "Hi I'm Nitish", "Tell me about LangGraph", "Explain checkpointers" and their answers — are gone). `RemoveMessage(id=...)` performs the actual permanent deletion from state.

### 5. Summarization (deletion + summary combined)
Workflow: run normally while state has ≤ 6 messages; once it exceeds 6, summarize. The summarizer keeps only the **most recent 2 messages** and summarizes everything before them, attaching the summary going forward. So summarization triggers **only when state has more than 6 messages**.

Graph: `START → chat →` conditional edge `should_summarize` → `summarize` (if True) or `END` (if False); `summarize → END`.

**Custom state — need an extra `summary` key** (plain `MessagesState` isn't enough):

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import RemoveMessage, SystemMessage

class State(TypedDict):
    messages: Annotated[list, add_messages]
    summary: str
```

**Chat node — two cases (with vs. without an existing summary):**

```python
def chat_node(state: State):
    messages = []
    summary = state.get("summary", "")
    if summary:                                  # Case 2: a summary already exists
        messages.append(SystemMessage(content=f"Conversation summary: {summary}"))
    messages += state["messages"]                # Case 1 (no summary) or Case 2, append all
    response = model.invoke(messages)
    return {"messages": [response]}
```

- **Case 1** — no summary yet (conversation just started, ≤ 6 messages): send only the current messages.
- **Case 2** — a summary exists (state exceeded 6 messages at some point): send **messages + summary** so the model has both recent context and the summarized past.

**Summarize node — summarize old, then delete old (keep only the last 2):**

```python
def summarize_node(state: State):
    existing_summary = state.get("summary", "")

    if existing_summary:
        # extend the existing summary with the new conversation
        prompt = (f"This is the existing summary: {existing_summary}\n"
                  "Extend this summary using the new conversation above.")
    else:
        # first-ever summary
        prompt = "Summarize the conversation above."

    messages_for_summary = state["messages"] + [("user", prompt)]
    summary = model.invoke(messages_for_summary).content

    # keep only the most recent 2 messages; delete everything before them
    messages_to_delete = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]

    return {"summary": summary, "messages": messages_to_delete}
```

**Conditional edge — only summarize past 6 messages:**

```python
def should_summarize(state: State):
    return len(state["messages"]) > 6           # True -> "summarize", False -> END

builder = StateGraph(State)
builder.add_node("chat", chat_node)
builder.add_node("summarize", summarize_node)
builder.add_edge(START, "chat")
builder.add_conditional_edges("chat", should_summarize,
                              {True: "summarize", False: END})
builder.add_edge("summarize", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

**Observed run:** ask about quantum physics → 2 messages, summary empty. Ask how Einstein relates to quantum physics → 4 messages, still empty. Ask about Einstein's famous works → 6 messages, still empty (needs **more than** 6 to trigger). Ask to explain special relativity → total becomes 8 (> 6) → summarization fires: state now holds only the **2 most recent** messages (the special-relativity Q and its answer) and a generated `summary` ("The conversation above discusses Albert Einstein's contributions to physics…").

## 🪜 Step-by-Step Walkthrough
1. Build a simple `START → chat → END` graph over `MessagesState`.
2. Show that **without** a checkpointer the model forgets across invokes.
3. Add `InMemorySaver` as the checkpointer and pass a `thread_id` in the config → STM works within a thread.
4. Confirm different thread IDs have independent buffers, and that RAM storage is lost on restart.
5. Replace `InMemorySaver` with `PostgresSaver` (Docker Postgres) inside a context manager (`setup()` + compile) → state survives restarts.
6. Add `trim_messages` before `model.invoke` to cap history at `MAX_TOKENS` (non-destructive).
7. Add a cleanup node using `RemoveMessage` to permanently delete old messages beyond a length threshold.
8. Combine deletion + a second LLM summary in a `summarize` node gated by a conditional edge → summarization preserves context for long chats.

## ⚠️ Gotchas & Tips
- STM requires **both** a checkpointer and a `thread_id` passed in the run config.
- `InMemorySaver` is **RAM-only and volatile** — fine for demos, never for production. Use `PostgresSaver` (or another DB) for persistence.
- Use `PostgresSaver` **inside a context manager** and call `checkpointer.setup()` once for first-time table creation.
- **Trimming ≠ deletion:** `trim_messages` keeps messages in state and just hides them from the LLM; `RemoveMessage` permanently removes them.
- `count_tokens_approximately` is a **heuristic** (counts roles etc.) — treat token numbers as approximate; tune `MAX_TOKENS` by experimentation.
- **Deletion is a prerequisite for summarization** — after summarizing, delete the raw old messages so you don't keep both the messages and their summary (which confuses the model).
- Summarization > trimming for real-world chats because it **preserves** older context instead of discarding it.
- Summarization needs a **custom state with a `summary` key**; plain `MessagesState` isn't sufficient.

## 📌 Key Takeaways
- Short-term memory in LangGraph = a **checkpointer** (stores state each super-step) + a **thread ID** (per-conversation buffer).
- Without a checkpointer the LLM is stateless and forgets; adding `InMemorySaver` + a `thread_id` gives per-thread memory.
- `InMemorySaver` is volatile → use **`PostgresSaver`** (Docker Postgres, via a context manager + `setup()`) for durable **persistence** that survives restarts.
- The **context-overflow problem**: re-sending full history can exceed the context window, causing hallucination/incoherence.
- **Trimming** (`trim_messages`, `count_tokens_approximately`) caps history to recent tokens without deleting; its flaw is losing older context entirely.
- **Deletion** (`RemoveMessage`) permanently removes messages from state and is the prerequisite step for summarization.
- **Summarization** keeps recent messages + an LLM-generated (and continually merged) summary of the rest, then deletes the raw old messages — the most robust fix for long conversations.
