# 03 · Long-Term Memory in LangGraph

> Implementation notes. Assumes the concepts from
> [01 · Memory Foundations](01-memory-foundations.md) (episodic/semantic/procedural memory,
> the create→store→retrieve→inject workflow) and the LangGraph basics from
> [02 · Short-Term Memory](02-short-term-memory-langgraph.md) (checkpointer, thread_id).

**Source video:** *Long Term Memory in LangGraph* (Agentic AI using LangGraph playlist, by Nitesh)

**What this covers:**
1. The **Store** abstraction (`BaseStore`, `InMemoryStore`, namespaces, `put`/`get`/`search`)
2. **Semantic search** over memories (embeddings)
3. Connecting a store to a chatbot that **uses** existing memories
4. A node that **creates** new memories — plus a **deduplication** strategy
5. The **merged** chatbot (creates + uses memories in one flow)
6. **Production persistence** with `PostgresStore` (via Docker)

---

## Recap — why LTM

Short-term memory is **thread-scoped**, so it can't personalize across conversations. A user's
profile is assembled from *many* threads (one says they prefer Python, another that they're a
teacher…). Long-term memory lives in a **persistent memory store** *outside* any single thread,
so responses can be personalized. Retrieved LTM is **injected into short-term memory** (the
context window) — the LLM never touches the store directly.

---

## 1. The Store abstraction

In LangGraph the memory store is modeled by an **abstract class `BaseStore`** (it inherits
`ABC`). It defines what any memory store can do — its abstract methods:

- **`put`** — create/update memories
- **`get`** — fetch one exact memory
- **`search`** — search multiple memories
- (edit / delete existing memories)

Concrete implementations inherit from `BaseStore`:

| Store | Backend | Use |
|-------|---------|-----|
| **`InMemoryStore`** | RAM | quick prototyping / testing (volatile) |
| **`PostgresStore`** | PostgreSQL | production-grade persistence |
| **`RedisStore`** | Redis | production-grade persistence |

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()     # object with put / get / search capabilities
```

---

## 2. Namespaces — organizing memories

A **namespace** organizes memories inside the store, exactly like **folders in Google Drive**.
It is a **tuple of strings** of any length.

```python
("users", "U1")                 # top-level "users" folder, then "U1" for user U1
("users", "U2")                 # a separate folder for user U2
("users", "U1", "profile")      # deeper: U1's profile (name, profession, age, gender)
("users", "U1", "preferences")  # U1's preferences (dark mode, prefers Python, …)
```

Any memory you create lives inside some namespace.

### `put` — create a memory

`store.put(namespace, key, value)` — three inputs: the **namespace** (folder), a **unique key**,
and the memory **value** (a dict).

```python
ns1 = ("users", "U1")
store.put(ns1, "1", {"data": "User likes pizza"})
store.put(ns1, "2", {"data": "User prefers dark mode"})

ns2 = ("users", "U2")
store.put(ns2, "1", {"data": "User likes pasta"})
store.put(ns2, "2", {"data": "User prefers grid-style navigation"})
```

### `get` — fetch one exact memory

`store.get(namespace, key)` — needs the namespace **and** the key. Use it when you know
*exactly* which memory you want.

```python
store.get(ns1, "1")     # -> "User likes pizza"
store.get(ns2, "2")     # -> "User prefers grid-style navigation"
```

### `search` — fetch all memories in a namespace

```python
items = store.search(("users", "U1"))
for item in items:
    print(item)          # all of U1's memories
```

---

## 3. Semantic search

`get` (exact key) and `search` (everything) don't cover the common case: **"I don't know the
exact key, and I don't want *all* memories — I want the *few relevant* ones."**

**Example:** a user has 100 memories (name, profession, dark-mode, …). This turn is about a
**Mumbai travel plan**. Dumping all 100 into context just confuses the LLM. You want the
2–3 memories about the Mumbai plan. That requires **semantic search** — match the *meaning*
of the current conversation against the meaning of stored memories.

**Two changes** vs. plain search:

1. Give the store an **embedding model** when you create it.
2. Pass a **`query`** (and usually a **`limit`**) to `search`.

```python
from langgraph.store.memory import InMemoryStore
from langchain_openai import OpenAIEmbeddings

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

store = InMemoryStore(
    index={"embed": embedding_model, "dims": 1536}   # enables semantic search
)

ns = ("users", "U1")
# ... put ~10 memories, e.g. memory #5 = "User is learning machine learning" ...

# the query is embedded and compared against all memory embeddings
results = store.search(ns, query="What is the user currently learning?", limit=1)
# -> "User is learning machine learning"

results = store.search(ns, query="What are the user's preferences?", limit=3)
# -> dark mode in application / bullet points over paragraphs / concise answers over long explanations
```

`limit` controls how many of the closest-matching memories come back.

---

## 4. Part A — a chatbot that USES existing memories

Goal: a simple `start → chat → end` graph, connected to a memory store that is **pre-filled**
with memories. When the user asks something, the chat node **reads** memories and personalizes
the reply. (This part only *uses* memories; it doesn't create them yet.)

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langchain_openai import ChatOpenAI

store = InMemoryStore()                 # no embeddings here — keep it simple
user_id = "U1"                          # normally comes dynamically from the frontend
namespace = ("users", user_id, "details")

# pre-fill some memories about U1
store.put(namespace, "1", {"data": "User's name is Nitesh"})
store.put(namespace, "2", {"data": "User teaches AI on YouTube"})
store.put(namespace, "3", {"data": "User likes concise answers"})
store.put(namespace, "4", {"data": "User likes examples in Python"})
store.put(namespace, "5", {"data": "User is building MCP servers in Python-based projects"})

SYSTEM_PROMPT = """You are a helpful assistant with memory capabilities.
If user-specific memory is available, use it to personalize your responses based on what
you know about the user. Your goal is to provide relevant, friendly and tailored assistance
that reflects the user's preferences, context and past interactions.

- If the user's name and relevant personal context is available, always personalize your
  response by addressing the user by name and referencing known projects, tools and preferences.
- Adjust the tone to feel friendly and natural, directly aimed at the user. Avoid generic
  phrasing when personalization is possible (e.g. instead of "in TypeScript", say "since your
  project is built with TypeScript").
- At the end, suggest three relevant follow-up questions based on the current response and the
  user profile.

Known user details:
{user_details_content}
"""

model = ChatOpenAI()

def chat_node(state: MessagesState, config: RunnableConfig, store: BaseStore):
    # config carries the user_id -> which gives us the namespace
    user_id = config["configurable"]["user_id"]
    namespace = ("users", user_id, "details")

    items = store.search(namespace)                     # all memories (no semantic search here)

    user_details_content = ""
    if items:
        user_details_content = "\n".join(f"- {item.value['data']}" for item in items)

    system_prompt = SYSTEM_PROMPT.format(user_details_content=user_details_content)
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = model.invoke(messages)                   # LTM injected via the system message
    return {"messages": response}

builder = StateGraph(MessagesState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)
graph = builder.compile(store=store)                    # <-- pass the STORE (not just a checkpointer)
```

The node signature gains **two extra arguments** beyond `state`:

- **`config: RunnableConfig`** — carries the `user_id` (→ the namespace). Passed at invoke time.
- **`store: BaseStore`** — the memory store, injected because we passed `store=` to `compile`.

**Run it:**

```python
config = {"configurable": {"user_id": "U1"}}
graph.invoke({"messages": "Explain GenAI in simple terms"}, config=config)
```

The reply starts *"Sure Nitesh…"* (it knows the name **from memory**), explains GenAI, and ends
with tailored follow-ups like *"Would you like to see specific examples of GenAI in Python?"*
and *"How would you like to incorporate GenAI concepts into your teaching material?"* — because
memory says the user likes Python and teaches on YouTube. **This is personalization via LTM.**

---

## 5. Part B — a node that CREATES new memories

Goal: `start → remember → end`. The **remember** node isn't a chatbot — it just takes the
user's message, decides whether it contains anything worth remembering, and if so stores it.
It needs an **extractor LLM** with **structured output** (via a Pydantic model).

```python
from pydantic import BaseModel, Field

class MemoryDecision(BaseModel):
    should_write: bool = Field(description="True if the message has anything worth remembering")
    memories: list[str] = Field(default_factory=list, description="Atomic facts worth storing")

extractor_llm = ChatOpenAI().with_structured_output(MemoryDecision)

MEMORY_SYSTEM = """Extract long-term memories from the user's message.
Only store stable, user-specific info: identity, preferences, ongoing projects.
Do NOT store transient info. Return should_write = False if nothing is worth storing.
Each memory should be a short, atomic sentence."""

def remember_node(state: MessagesState, config: RunnableConfig, store: BaseStore):
    user_id = config["configurable"]["user_id"]
    namespace = ("users", user_id, "details")

    last_message = state["messages"][-1]                # extract memory from the latest message
    decision = extractor_llm.invoke([
        SystemMessage(content=MEMORY_SYSTEM),
        last_message,
    ])

    if decision.should_write:
        for i, mem in enumerate(decision.memories):
            store.put(namespace, f"{user_id}-{i}", {"data": mem})   # unique key per memory

    return {"messages": [{"role": "assistant", "content": "Noted the memory."}]}
```

Send three messages ("Hi, my name is Nitesh", "I teach AI on YouTube", "My favorite
programming language is Python") and `store.search(namespace)` shows **all three** memories
stored.

### The flaw: duplicates

Resend those same three messages and you get **duplicate** memories — this code has no
**deduplication**. Redundant memories pile up.

### Deduplication strategy

When extracting, also send the **existing memories** to the LLM and ask it to flag, for each
extracted item, whether it is **new** vs. already present. Only write the new ones.

```python
class MemoryItem(BaseModel):
    text: str = Field(description="A short atomic memory sentence")
    is_new: bool = Field(description="True only if it adds new info vs. current user details")

class MemoryDecision(BaseModel):
    should_write: bool
    memories: list[MemoryItem]          # now a list of items, each with an is_new flag

extractor_llm = ChatOpenAI().with_structured_output(MemoryDecision)

DEDUP_SYSTEM = """You are responsible for updating and maintaining accurate user memory.
You will be given the current user details. Review the user's latest message and extract
user-specific info worth storing long-term. For each extracted item, set is_new = True only
if it adds new information compared to the current user details; if it is basically already
present, set is_new = False. Keep each memory a short atomic sentence. No speculation — only
facts stated by the user. If there is nothing, return an empty list."""

def remember_node(state: MessagesState, config: RunnableConfig, store: BaseStore):
    user_id = config["configurable"]["user_id"]
    namespace = ("users", user_id, "details")

    existing = store.search(namespace)
    current_details = "\n".join(f"- {item.value['data']}" for item in existing)
    last_message = state["messages"][-1]

    decision = extractor_llm.invoke([
        SystemMessage(content=f"{DEDUP_SYSTEM}\n\nCurrent user details:\n{current_details}"),
        last_message,
    ])

    for i, item in enumerate(decision.memories):
        if item.is_new:                                 # <-- only add genuinely new memories
            store.put(namespace, f"{user_id}-{i}", {"data": item.text})

    return {"messages": [{"role": "assistant", "content": "Noted the memory."}]}
```

Now resending the same messages produces **no duplicates**. (This is one dedup strategy; there
are others.)

---

## 6. Merged chatbot — creates AND uses memories

Combine both flows: `start → remember → chat → end`.

- **remember** — extract memories from the user's most recent message (with dedup) and **write**.
- **chat** — **read** memories and deliver a contextual, personalized reply.

```python
builder = StateGraph(MessagesState)
builder.add_node("remember", remember_node)     # writes memories (Part B, deduped)
builder.add_node("chat", chat_node)             # reads memories + personalizes (Part A)
builder.add_edge(START, "remember")
builder.add_edge("remember", "chat")
builder.add_edge("chat", END)
graph = builder.compile(store=store)            # two LLMs in play: extractor + chat
```

**Demo:**

```python
config = {"configurable": {"user_id": "U1"}}
graph.invoke({"messages": "Hi my name is Nitesh"},        config=config)  # stores "name is Nitesh"
graph.invoke({"messages": "I teach AI on YouTube"},       config=config)  # stores that fact + asks follow-ups
graph.invoke({"messages": "Explain GenAI simply"},        config=config)  # "Sure Nitesh…", bullet points; nothing new stored
```

The third message stores **nothing new** (it has nothing worth remembering) but the reply is
still personalized ("Sure Nitesh", bullet points — because memory says the user prefers concise,
bulleted answers).

---

## 7. Production persistence — `PostgresStore`

**The flaw:** `InMemoryStore` keeps memories in **RAM** → volatile → restart and all memories
vanish. Not usable in production. Use a **persistent store** — `PostgresStore` (built on
Postgres) or `RedisStore`.

### Same Docker setup as short-term memory

```bash
docker --version
docker run --name langgraph-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16
docker ps        # confirm postgres:16 is running
```

### Compile the graph with `PostgresStore`

Everything else (system prompt, memory LLM, Pydantic models, remember node, chat node, graph)
stays **identical** — only the store changes, inside a context manager:

```python
from langgraph.store.postgres import PostgresStore

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()                                   # first run: create tables
    graph = builder.compile(store=store)            # <-- PostgresStore instead of InMemoryStore

    config = {"configurable": {"user_id": "U1"}}
    graph.invoke({"messages": "Hi. My name is Nitesh and I teach AI on YouTube"}, config=config)
    graph.invoke({"messages": "Explain GenAI simply"}, config=config)

    print(store.search(("users", "U1", "details")))
    # stored: "User's name is Nitesh", "User teaches AI on YouTube"
```

**Proof of persistence:** restart the kernel, run only the read code, and the memories are
**still there**. Postgres-backed memories persist for days/months, even across machine
shutdowns. This is the setup for a production-grade chatbot.

---

## TL;DR

| Concern | LangGraph tool |
|---------|----------------|
| Memory store abstraction | **`BaseStore`** (`put` / `get` / `search`) |
| Prototype store | `InMemoryStore` (RAM, volatile) |
| Production store | `PostgresStore` / `RedisStore` |
| Organize memories | **namespaces** — tuples of strings, like folders |
| Retrieve *relevant* memories | **semantic search** — embedding model + `search(ns, query=, limit=)` |
| Wire store into graph | `compile(store=store)`; node gets `config` + `store` args |
| Create memories reliably | extractor LLM + **structured output** (Pydantic) + **dedup** (`is_new`) |
| Inject LTM | build it into the **system prompt** → part of short-term memory / context window |

**Prev:** [← 02 · Short-Term Memory in LangGraph](02-short-term-memory-langgraph.md) ·
**Up:** [README](README.md)
