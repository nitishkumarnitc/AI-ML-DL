# 02 · Short-Term Memory in LangGraph

> Implementation notes. Assumes the concepts from
> [01 · Memory Foundations](01-memory-foundations.md) (stateless LLMs, conversation buffer,
> thread-scoped STM, context-window problem).

**Source video:** *How To Implement Short Term Memory Using LangGraph* (Agentic AI using LangGraph playlist, by Nitesh)

**What this covers:**
1. Implementing STM with a **Checkpointer** + **thread IDs**
2. **Persistence** with PostgreSQL (via Docker)
3. Solving the **context-overflow** problem: **Trimming**, **Deletion**, **Summarization**

---

## Quick recap

LLMs have no intrinsic memory; every `llm.invoke()` is treated as a fresh, stateless call.
To keep a conversation going we maintain a **conversation buffer** — with every message we
send not just the current user message but the **whole prior conversation concatenated**.
That buffer is **Short-Term Memory**. This note does exactly that inside LangGraph.

---

## 1. STM = Checkpointer + Thread ID

In LangGraph, short-term memory is provided by a **Checkpointer**.

- **Checkpointer** — stores the graph's **state at every super-step**.
- **Thread ID** — each conversation/thread gets its own ID; state is stored *against* that
  thread ID. Different thread → different (isolated) memory.

### Without a checkpointer — the graph forgets

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_openai import ChatOpenAI

model = ChatOpenAI()

def call_model(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": response}

builder = StateGraph(MessagesState)
builder.add_node("chat", call_model)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

graph = builder.compile()                      # <-- no checkpointer

graph.invoke({"messages": "Hi, my name is Nitesh"})
graph.invoke({"messages": "What is my name?"})
# -> "I'm sorry, I can't know your name as I'm a computer program."
```

`MessagesState` is a built-in state with a `messages` key — no need to define your own.

### With a checkpointer — the graph remembers

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()                 # stores checkpoints in RAM
graph = builder.compile(checkpointer=checkpointer)   # <-- THE main difference

config = {"configurable": {"thread_id": "thread-1"}}

graph.invoke({"messages": "Hi, my name is Nitesh"}, config=config)   # "Nice to meet you"
graph.invoke({"messages": "What is my name?"},      config=config)   # "Your name is Nitesh"
```

Every invoke passes both the message **and** the `thread_id` (so LangGraph knows which
thread the message belongs to). You can inspect the stored state:

```python
graph.get_state(config).values["messages"]
# 4 messages: [Human "Hi...Nitesh", AI "Nice to meet you", Human "What is my name?", AI "Your name is Nitesh"]
```

### Threads are isolated

```python
config2 = {"configurable": {"thread_id": "thread-2"}}
graph.invoke({"messages": "What is my name?"}, config=config2)
# -> "I'm sorry, I do not have the ability to know your name."
```

Switching to `thread-2` is effectively starting a **new conversation** — the `thread-1`
messages were never sent, so the model doesn't know the name. This is STM being
**thread-scoped**.

---

## 2. Persistence — from RAM to PostgreSQL

**The problem with `InMemorySaver`:** it stores state in **RAM**, which is **volatile**.
Restart the program and everything is gone — `get_state` on either thread returns nothing.
Never use `InMemorySaver` in production.

**Solution:** save state in a **production-grade database**. LangGraph docs recommend
**PostgreSQL**.

### Set up Postgres via Docker (recommended)

Two possible setups: install Postgres directly on the machine, or run it via **Docker**
(chosen here — avoids installation issues).

```bash
# 1. Install Docker Desktop (https://www.docker.com/) and start it
# 2. Verify Docker is installed
docker --version

# 3. Pull + run a Postgres image as a container
docker run --name langgraph-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:16

# 4. Confirm it's running
docker ps        # should show the postgres:16 container
```

### Use `PostgresSaver` as the checkpointer

```python
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()                                  # first run: create tables
    graph = builder.compile(checkpointer=checkpointer)    # <-- Postgres instead of InMemorySaver

    config = {"configurable": {"thread_id": "thread-1"}}
    graph.invoke({"messages": "Hi, my name is Nitesh"}, config=config)
```

Now state survives restarts — the only change from the in-memory version is swapping
`InMemorySaver()` for `PostgresSaver`. (Redis is another production-grade option.)

---

## 3. The context-overflow problem

Because STM resends the **entire** history each turn, a very long conversation (500–1000+
messages, with long AI responses) can push the token count **past the model's context
window**. The response then degrades. This is the **context-overflow problem**. Two
techniques fight it: **trimming** and **summarization** (with **deletion** as a helper).

---

### 3a. Trimming

Set a **max token limit**. Before each invoke, check the buffer's total token count:
- under the limit → send everything;
- over the limit → keep only the most recent messages that fit, drop the older ones.

LangChain provides **`trim_messages`** to do the heavy lifting.

```python
from langchain_core.messages import trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langchain_openai import ChatOpenAI

model = ChatOpenAI()
MAX_TOKENS = 150

def call_model(state: MessagesState):
    trimmed = trim_messages(
        state["messages"],
        max_tokens=MAX_TOKENS,
        strategy="last",                       # keep the most recent messages
        token_counter=count_tokens_approximately,
        allow_partial=False,
    )
    response = model.invoke(trimmed)           # send the TRIMMED history, not the full one
    return {"messages": response}
```

**Behavior as the conversation grows** (with `MAX_TOKENS = 150`):

| Turn | Messages in state | Approx. token count | Trimmed? |
|------|-------------------|---------------------|----------|
| "Hi, my name is Nitesh" | 1 | ~10 | no |
| "I am learning LangGraph" | 3 | ~40 | no |
| "Can you explain short-term memory?" | 5 | ~108 | no |
| "What is my name?" | 7 | > 150 | **yes** → only the last message survives → "I don't know your name" |

> `count_tokens_approximately` is LangChain's heuristic — it counts roles etc. too, so don't
> read the exact numbers literally.

**Key point:** trimming does **not** delete anything. All messages stay in state (and in the
checkpointer). You simply **don't show** the old ones to the LLM on this call. You tune
`MAX_TOKENS` per application.

**Flaw of trimming:** it **completely ignores** older messages — the LLM doesn't even know
they exist. The assumption "only the last N messages matter" fails in many real scenarios,
causing broken continuity.

---

### 3b. Deletion (prerequisite for summarization)

To *permanently* remove messages from state, use **`RemoveMessage`** with the message IDs.

```python
from langchain_core.messages import RemoveMessage

def delete_old_messages(state: MessagesState):
    messages = state["messages"]
    if len(messages) > 10:                     # keep only the last 4
        to_delete = messages[:-4]              # the first (oldest) messages
        return {"messages": [RemoveMessage(id=m.id) for m in to_delete]}
    return {}
```

Two-node graph — `chat` then `clean_up` (the clean-up node only acts when >10 messages):

```python
builder = StateGraph(MessagesState)
builder.add_node("chat", call_model)
builder.add_node("clean_up", delete_old_messages)
builder.add_edge(START, "chat")
builder.add_edge("chat", "clean_up")
builder.add_edge("clean_up", END)
graph = builder.compile(checkpointer=InMemorySaver())
```

If you run 7 user+AI exchanges you'd expect **14** messages in state — but because 14 > 10,
the **first 6** are removed, leaving **8**. `RemoveMessage` makes state-level deletion trivial.

---

### 3c. Summarization

Like trimming, you keep the most recent *N* messages — but instead of ignoring the older
ones you send them to **another LLM** to produce a **summary**, then send
`summary + recent N`. Context is preserved no matter how long the chat gets.

- Merge rolling summaries: e.g. 500 messages → summarize the first 400, keep the recent 100;
  100 more arrive → summarize those, **merge** into the existing summary → now you carry a
  summary of 500 + the recent 100.
- **After summarizing, delete the old messages** (don't just ignore them). Keeping both the
  raw old messages *and* their summary is redundant and confusing — so **deletion +
  summarization operate together**.

**Custom state** — `MessagesState` isn't enough; we need a `summary` key too:

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    summary: str
```

**Chat node** — inject the summary as a `SystemMessage` when one exists:

```python
from langchain_core.messages import SystemMessage

def chat_node(state: State):
    messages = []
    summary = state.get("summary", "")
    if summary:                                            # case 2: a summary exists
        messages.append(SystemMessage(content=f"Conversation summary so far: {summary}"))
    messages.extend(state["messages"])                     # case 1 & 2: append actual messages
    response = model.invoke(messages)
    return {"messages": response}
```

**Summary node** — summarize (create or extend), then delete all but the last 2 messages:

```python
def summarize_node(state: State):
    existing_summary = state.get("summary", "")
    if existing_summary:
        prompt = (f"This is the existing summary: {existing_summary}\n"
                  f"Extend it using the new conversation above.")
    else:
        prompt = "Summarize the conversation above."

    messages_for_summary = state["messages"] + [SystemMessage(content=prompt)]
    summary = model.invoke(messages_for_summary).content

    # keep only the 2 most recent messages, delete the rest
    to_delete = state["messages"][:-2]
    return {
        "summary": summary,
        "messages": [RemoveMessage(id=m.id) for m in to_delete],
    }
```

**Conditional edge** — only summarize when the state has **more than 6** messages:

```python
def should_summarize(state: State):
    return len(state["messages"]) > 6

builder = StateGraph(State)
builder.add_node("chat", chat_node)
builder.add_node("summarize", summarize_node)
builder.add_edge(START, "chat")
builder.add_conditional_edges("chat", should_summarize, {True: "summarize", False: END})
builder.add_edge("summarize", END)
graph = builder.compile(checkpointer=InMemorySaver())
```

**Walkthrough** (threshold = 6):

| Turn (message sent) | Messages after turn | Summary |
|---------------------|---------------------|---------|
| "Quantum physics" | 2 | empty (≤ 6) |
| "How is Albert Einstein related to quantum physics?" | 4 | empty (≤ 6) |
| "What are some of Einstein's famous works?" | 6 | empty (= 6) |
| "Explain the special theory of relativity" | 8 → **trimmed to 2** | **generated** — "The conversation above discusses Albert Einstein's contribution to physics…" |

When the 4th turn pushes it to 8 (> 6), summarization fires: the 2 most recent messages are
kept, the rest are summarized into `summary` and deleted. This is, in principle, how real
chatbots manage long conversations.

---

## TL;DR

| Concern | LangGraph tool |
|---------|----------------|
| STM (remember within a thread) | **Checkpointer** + **`thread_id`** in `config` |
| Prototype checkpointer | `InMemorySaver` (RAM, volatile) |
| Production persistence | `PostgresSaver` (Postgres via Docker) / Redis |
| Cap context size, cheaply | **`trim_messages`** (`max_tokens`, keeps last N — doesn't delete) |
| Permanently drop messages | **`RemoveMessage`** (by message ID) |
| Cap context *and* keep context | **Summarization** (recent N + rolling summary; deletes the rest) |

**Prev:** [← 01 · Memory Foundations](01-memory-foundations.md) ·
**Next:** [03 · Long-Term Memory in LangGraph →](03-long-term-memory-langgraph.md)
