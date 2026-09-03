# Video 25 — Long Term Memory in LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `KrXBcokM3Tc`
> **Watch:** https://www.youtube.com/watch?v=KrXBcokM3Tc

## 🎯 Overview
This video is the third in the memory sub-series and is dedicated to **long-term memory** — the persistent, cross-conversation memory that lets a chatbot remember facts about a user forever and personalize its answers. It builds up from scratch: first learning the raw memory-store API (create / get / search / semantic search), then wiring a store into a LangGraph chatbot that both **reads** existing memories and **writes** new ones, and finally swapping the volatile in-memory store for a production-grade **Postgres** store so memories survive restarts.

## 🧠 Key Concepts

### Why long-term memory exists
In a ChatGPT-style app, a user talks across **many separate threads** — a technical topic in one, travel plans in another, philosophical musings in a third. Important facts about the user (they're a programmer who prefers Python, they're moving to Mumbai in two months, they lean spiritual) are scattered across threads and don't live in any single conversation. To personalize responses, the product extracts these important pieces of information and saves them into a **persistent memory store** (think: a database). On every new question the LLM first checks this store for anything that helps tailor the answer, then answers. Because the store is persistent, closing a chat window does not erase it. This persistent store *is* long-term memory.

### The `BaseStore` abstraction
In LangGraph the memory-store concept is implemented as an **abstract class `BaseStore`**. It defines what a memory store can do — create new memories, search existing memories, edit them, delete them. Concrete implementations inherit from it:
- **`InMemoryStore`** — stores memories in RAM. Fast, great for prototyping, but **volatile** (lost on restart). Not for production.
- **`PostgresStore`** — persists memories in a PostgreSQL database. Production-grade.
- **`RedisStore`** — persists in Redis. Also production-grade.

The key abstract methods you'll actually use: `get` (fetch one memory), `search` (fetch many), `put` (create a memory).

### Namespaces = folders inside the store
A **namespace** organizes memories exactly like folders organize files in Google Drive. It is written as a **tuple of strings**, and can be any depth:
- `("users", "U1")` — top folder `users`, subfolder `U1` (all of user 1's memories)
- `("users", "U2")` — user 2's memories
- `("users", "U1", "profile")` — user 1's profile facts (name, profession, age…)
- `("users", "U1", "preferences")` — user 1's preferences (dark mode, prefers Python…)

Every memory you create lives inside some namespace.

### Create / retrieve
- **`put(namespace, key, value)`** inserts a new memory. `key` must be unique; `value` is a dict (e.g. `{"data": "user likes pizza"}`).
- **`get(namespace, key)`** fetches one specific memory — used when you know exactly which memory you want.
- **`search(namespace)`** fetches **all** memories in a namespace (returns a list you loop over) — used when you want everything.

### Semantic search
`get` needs an exact key; `search` returns everything. Neither helps when you need a *specific but unknown* memory — e.g. a user has 100 stored memories and the current conversation is about a Mumbai trip; dumping all 100 into context just confuses the LLM. You want only the 2–3 memories whose **meaning** matches the current conversation. That is **semantic search**. It also uses `search`, with two changes:
1. When creating the store, pass an **embedding model** via the `index` argument so embeddings are generated for every memory.
2. Call `search(namespace, query=..., limit=...)` — the query is embedded, compared against stored memory embeddings, and the top-`limit` closest memories are returned.

## 🔧 Code / Implementation

### Part 1 — working with the memory store directly
```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# a namespace is a "folder" — a tuple of strings
namespace = ("users", "U1")

# create memories: put(namespace, key, value)
store.put(namespace, "1", {"data": "user likes pizza"})
store.put(namespace, "2", {"data": "user prefers dark mode"})

# a second user in a second namespace
namespace2 = ("users", "U2")
store.put(namespace2, "1", {"data": "user likes pasta"})
store.put(namespace2, "2", {"data": "user prefers grid-style navigation"})

# fetch ONE specific memory
item = store.get(namespace, "1")        # -> "user likes pizza"

# fetch ALL memories in a namespace
items = store.search(namespace)          # returns a list
for item in items:
    print(item)
```

### Semantic search over memories
```python
from langchain_openai import OpenAIEmbeddings
from langgraph.store.memory import InMemoryStore

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

# pass an embedding model + dimension so the store can do semantic search
store = InMemoryStore(index={"embed": embedding_model, "dims": 1536})

namespace = ("users", "U1")
# ... put ~10 assorted memories here, e.g. memory #5 = "user is learning machine learning"

# now search by MEANING, not by key
results = store.search(namespace, query="What is user currently learning?", limit=1)
# -> "user is learning machine learning"

results = store.search(namespace, query="What are user's preferences?", limit=3)
# -> top-3 preference memories (dark mode, bullet points over paragraphs, concise answers)
```
The only two differences vs. normal search: an **embedding model at store-creation** and a **`query` + `limit`** at search time.

### Part 2a — a chatbot that READS existing memories
```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

store = InMemoryStore()                    # no embedding model -> no semantic search here
user_id = "U1"
namespace = ("users", user_id, "details")

# pre-fill some memories manually
store.put(namespace, "1", {"data": "User's name is Nitish"})
store.put(namespace, "2", {"data": "User teaches AI on YouTube"})
store.put(namespace, "3", {"data": "User prefers concise answers"})
store.put(namespace, "4", {"data": "User likes examples in Python"})
store.put(namespace, "5", {"data": "User is building Python-based MCP server projects"})

SYSTEM_PROMPT = """You are a helpful assistant with memory capabilities.
If user-specific memories are available, use them to personalize your responses based on
what you know about the user. Your goal is to provide relevant, friendly and tailored
assistance that reflects the user's preferences, context and past interactions.

If the user's name or relevant personal context is available, always personalize by:
- addressing the user by name
- referencing known projects, tools and preferences
- adjusting the tone to feel friendly, natural and directly aimed at the user
Avoid generic phrasing when personalization is possible
(e.g. instead of "in TypeScript apps" say "since your project is built with TypeScript").

At the end, suggest three relevant further questions based on the current response and
the user profile.

User details:
{user_details_content}
"""

llm = ChatOpenAI(model="gpt-4.1-mini")

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

# note the THREE inputs: state, config, store
def chat_node(state: ChatState, config: RunnableConfig, store: BaseStore):
    user_id = config["configurable"]["user_id"]      # config comes from graph.invoke
    namespace = ("users", user_id, "details")

    items = store.search(namespace)                   # ALL memories (no semantic search yet)
    if items:
        user_details_content = "\n".join("- " + i.value["data"] for i in items)
    else:
        user_details_content = "No user details available."

    system_prompt = SYSTEM_PROMPT.format(user_details_content=user_details_content)
    response = llm.invoke([SystemMessage(content=system_prompt)] + state["messages"])
    return {"messages": [response]}

builder = StateGraph(ChatState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)
graph = builder.compile(store=store)                  # store injected at compile time

config = {"configurable": {"user_id": "U1"}}
graph.invoke({"messages": [HumanMessage("Explain GenAI in simple terms")]}, config=config)
```
Where do `config` and `store` come from? `config` is passed at `graph.invoke(...)` (it hides the `user_id`, from which we build the namespace). `store` is passed at `builder.compile(store=store)`. Result: the reply opens with *"Sure Nitish"*, answers in bullet points (a stored preference), and ends with follow-up questions referencing Python and teaching material — all pulled from memory.

### Part 2b — a flow that WRITES new memories (with de-duplication)
```python
import uuid
from typing import List
from pydantic import BaseModel, Field

# a single extracted memory + whether it is genuinely new
class MemoryItem(BaseModel):
    text: str
    is_new: bool = Field(description="True only if it adds new info vs current user details")

class MemoryDecision(BaseModel):
    should_write: bool
    memories: List[MemoryItem]

extractor_llm = ChatOpenAI(model="gpt-4.1-mini")
memory_extractor = extractor_llm.with_structured_output(MemoryDecision)

MEMORY_SYSTEM_PROMPT = """You are responsible for updating and maintaining accurate user memory.
Current user details (existing memory) will be given to you. Your task:
- Review the user's latest message.
- Extract user-specific info worth storing long-term (identity, preferences, ongoing projects).
- For each extracted item set is_new=True ONLY if it adds new info vs current user details;
  if it is basically the same as something already present, set is_new=False.
Keep each memory a short atomic sentence. No speculation, only facts stated by the user.
If there is nothing memory-worthy, return an empty list.
"""

def remember_node(state, config, store):
    user_id = config["configurable"]["user_id"]
    namespace = ("users", user_id, "details")

    existing = store.search(namespace)
    current_user_details = "\n".join("- " + i.value["data"] for i in existing)

    last_message = state["messages"][-1].content

    decision = memory_extractor.invoke([
        SystemMessage(content=MEMORY_SYSTEM_PROMPT + "\nCurrent user details:\n" + current_user_details),
        HumanMessage(content=last_message),
    ])

    if decision.should_write:
        for mem in decision.memories:
            if mem.is_new:                             # ONLY store new memories -> no duplicates
                store.put(namespace, str(uuid.uuid4()), {"data": mem.text})

    return {"messages": [{"role": "assistant", "content": "Noted."}]}
```
Before de-duplication (v1 of this node), the pydantic model was simply `should_write: bool` + `memories: List[str]` and it stored everything — re-sending the same message created **duplicate memories**. The fix: also feed the *existing* memories to the extractor and have it flag each item with `is_new`; only persist the new ones.

### The merged chatbot (read + write)
```python
builder = StateGraph(ChatState)
builder.add_node("remember", remember_node)   # extracts & writes memories from the last message
builder.add_node("chat", chat_node)           # reads memories, replies with personalization
builder.add_edge(START, "remember")
builder.add_edge("remember", "chat")
builder.add_edge("chat", END)
graph = builder.compile(store=store)
```
Two separate LLMs are used: an **extractor LLM** in `remember` and a **chat LLM** in `chat`.

### Production persistence with Postgres
`InMemoryStore` lives in RAM, so a restart wipes every memory. For production use `PostgresStore` (or `RedisStore`).

Docker setup (same as the short-term-memory video):
1. Install **Docker Desktop**; verify with `docker --version`.
2. Run the provided command to pull and start a Postgres image (container named `langgraph-postgres`, `postgres:16`). Representative:
   ```bash
   docker run --name langgraph-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16
   ```
3. Verify with `docker ps`.

Then use the Postgres store inside a context manager:
```python
from langgraph.store.postgres import PostgresStore

DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()                        # one-time table setup
    graph = builder.compile(store=store) # everything else is identical
    config = {"configurable": {"user_id": "U1"}}
    graph.invoke(
        {"messages": [HumanMessage("Hi, my name is Nitish and I teach AI on YouTube")]},
        config=config,
    )
```
After a **kernel restart**, running only a `store.search(namespace)` still returns the stored memories — proving persistence.

## 🪜 Step-by-Step Walkthrough
1. Learn the store API standalone: `InMemoryStore()`, then `put` / `get` / `search`.
2. Add an embedding model and use `search(namespace, query, limit)` for semantic retrieval.
3. Build a `chat` node that reads all memories for the user, injects them into the system prompt, and answers — personalized.
4. Build a `remember` node that extracts memories from the last message via a structured-output LLM and writes them.
5. Add de-duplication by feeding existing memories to the extractor and flagging `is_new`.
6. Merge into one graph: `START → remember → chat → END`.
7. Swap `InMemoryStore` for `PostgresStore` (Docker) to make memories persistent.

## ⚠️ Gotchas & Tips
- **`InMemoryStore` is volatile** — never use it in production; memories vanish on restart.
- **Namespaces are tuples of strings** and can be arbitrarily deep; use them to organize per-user / per-category memories.
- The graph node receives **three** things — `state`, `config` (source of `user_id` → namespace), and `store` (source of memories). `config` arrives via `invoke`, `store` via `compile`.
- **Always de-duplicate** when auto-writing memories, or repeated messages bloat the store with redundant entries.
- Inject long-term memories into the LLM's context by **prepending a system message** built from the retrieved memories.
- Use `with_structured_output(PydanticModel)` to force the extractor to return clean, controlled memory objects.
- For real chatbots with memory, **semantic search is essential** — never dump all memories into context.

## 📌 Key Takeaways
- Long-term memory is a **persistent store** of user facts extracted across conversations, used to personalize LLM responses.
- LangGraph models it with the abstract **`BaseStore`**; `InMemoryStore` (prototype), `PostgresStore` and `RedisStore` (production) are concrete implementations.
- **Namespaces** (tuples of strings) organize memories like folders; `put`, `get`, `search` create and retrieve them.
- **Semantic search** (embedding model + `query`/`limit`) fetches only the memories whose meaning matches the current conversation.
- A memory-aware chatbot has two jobs: a **remember** node that writes memories and a **chat** node that reads them into the prompt.
- **De-duplication** (flagging `is_new` against existing memories) prevents redundant entries.
- Use structured output for reliable extraction, and **Postgres/Redis** for persistence in real systems.
