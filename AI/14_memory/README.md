# Memory in LLMs & LangGraph — Study Notes

Notes distilled from the **Agentic AI using LangGraph** playlist (by Nitesh), covering how
memory works around LLMs and how to implement short- and long-term memory in **LangGraph**.

> Source playlist: <https://www.youtube.com/playlist?list=PLKnIA16_RmvbtL3dyYE7s-GFna48trwfK>
> Notes generated from the video transcripts (raw transcripts kept in [`transcripts/`](transcripts/)).

---

## Read in this order

The playlist lists videos newest-first; these notes follow the **teaching order** — concept
first, then the two implementations.

| # | Note | Video | What you'll learn |
|---|------|-------|-------------------|
| 01 | [Memory Foundations](01-memory-foundations.md) | *LLMs Don't Have Memory — So How Do They Remember?* | Why LLMs are stateless, context window, in-context learning, short- vs long-term memory, the 3 LTM types, the create→store→retrieve→inject workflow |
| 02 | [Short-Term Memory in LangGraph](02-short-term-memory-langgraph.md) | *How To Implement Short Term Memory Using LangGraph* | Checkpointer + thread IDs, persistence with Postgres, trimming, deletion, summarization |
| 03 | [Long-Term Memory in LangGraph](03-long-term-memory-langgraph.md) | *Long Term Memory in LangGraph* | `BaseStore`, namespaces, semantic search, memory-creating chatbot, deduplication, `PostgresStore` |

---

## The big picture in one page

**An LLM at inference is a stateless function** `y = f_θ(x)` — it has **no built-in memory**.
Yet almost every GenAI app needs memory. So we build memory **externally** around the LLM.

```
                          ┌─────────────────────────────┐
   user prompt  ──────▶   │  build context (x)          │
                          │   • conversation history    │◀── Short-Term Memory (thread-scoped)
                          │   • retrieved facts         │◀── Long-Term Memory (cross-thread)
                          └──────────────┬──────────────┘
                                         ▼
                              y = f_θ(x)   (stateless LLM)
                                         │
                                         ▼
                                    response  ──▶ (extract new long-term memories)
```

| | Short-Term Memory | Long-Term Memory |
|--|-------------------|------------------|
| **What** | the conversation buffer resent each turn | selective, durable facts/events/procedures |
| **Scope** | one thread / conversation | across all conversations (per user/app/agent) |
| **Lifetime** | dies with the conversation | persists for days/months |
| **LangGraph** | **Checkpointer** + `thread_id` | **Store** (`BaseStore`) + namespaces |
| **Prototype** | `InMemorySaver` | `InMemoryStore` |
| **Production** | `PostgresSaver` / Redis | `PostgresStore` / `RedisStore` |
| **Main problems** | fragility (→ persistence), context overflow (→ trimming + summarization) | what to remember, what to retrieve, dedup, orchestration |

**LTM is always injected *through* STM** — retrieved memories become part of the prompt
(context window); the LLM never queries the store directly.

**Three types of long-term memory:** **episodic** (past events), **semantic** (facts about
user/system — most common), **procedural** (how-to strategies & learned behaviors).

---

## LangGraph cheat sheet

```python
# ── Short-Term Memory: checkpointer + thread_id ──────────────────────────────
from langgraph.checkpoint.memory import InMemorySaver          # prototype (RAM)
from langgraph.checkpoint.postgres import PostgresSaver        # production

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "thread-1"}}
graph.invoke({"messages": "..."}, config=config)

# context overflow
from langchain_core.messages import trim_messages, RemoveMessage   # trim / delete
# + summarization node that keeps recent N and merges a rolling summary

# ── Long-Term Memory: store + namespaces ─────────────────────────────────────
from langgraph.store.memory import InMemoryStore               # prototype (RAM)
from langgraph.store.postgres import PostgresStore             # production

store = InMemoryStore()
ns = ("users", "U1", "details")
store.put(ns, "1", {"data": "User's name is Nitesh"})          # create
store.get(ns, "1")                                             # exact fetch
store.search(ns)                                               # all in namespace
store.search(ns, query="what is the user learning?", limit=3)  # semantic (needs embeddings)

graph = builder.compile(store=store)                           # node gets (state, config, store)
```

---

## Managed memory layers (mentioned in the videos)

Instead of building the whole create/store/retrieve pipeline yourself:

- **LangMem** — LangChain family; integrates with LangGraph.
- **Mem0** — popular managed memory layer for GenAI apps.
- **Supermemory** — managed LTM for GenAI apps.

Research toward LLMs with **intrinsic** memory: Google's **Titans + MIRAGE** line of work.

---

## Files

```
memory/
├── README.md                          # this index
├── 01-memory-foundations.md           # concepts (framework-agnostic)
├── 02-short-term-memory-langgraph.md  # STM implementation
├── 03-long-term-memory-langgraph.md   # LTM implementation
└── transcripts/                       # cleaned raw transcripts
    ├── 01-memory-foundations.hinglish.txt
    ├── 02-short-term-memory.hinglish.txt
    └── 03-long-term-memory.english.txt
```

> Code snippets are reconstructed from the instructor's spoken walkthroughs to match the APIs
> described (LangGraph `Checkpointer`/`Store`, `trim_messages`, `RemoveMessage`, Pydantic
> structured output). Treat them as faithful study references and verify against the current
> LangGraph docs before using in production, since APIs evolve.
