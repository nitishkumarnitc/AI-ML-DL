# 08 · LangChain and LangGraph

> ← [`07-sessions-users-and-trace-attributes.md`](07-sessions-users-and-trace-attributes.md) · **Next:** [`09-otel-and-any-language.md`](09-otel-and-any-language.md) →

---

LangFuse traces LangChain and LangGraph through a callback handler — the same mechanism LangSmith uses natively. The difference is one line of code instead of zero, and in exchange the traces land somewhere you can own.

---

## 1. Setup

```python
from langfuse import get_client
from langfuse.langchain import CallbackHandler

langfuse = get_client()
langfuse_handler = CallbackHandler()
```

The handler takes **no constructor arguments** in Python — configuration comes from the client, which reads `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` from the environment (lesson 03).

Pass it via `config`:

```python
chain.invoke(
    {"input": user_input},
    config={"callbacks": [langfuse_handler]},
)
```

That is the whole integration. Every runnable in the chain becomes an observation.

> **Contrast with LangSmith honestly:** there, tracing is zero code — env vars only ([`../30_langsmith/05-your-first-trace.md`](../30_langsmith/05-your-first-trace.md)). Here it is one import and one `config` argument per invocation. That is a genuine, if small, ergonomic win for LangSmith on LangChain apps, and it is the price of the handler not being built into LangChain itself.

---

## 2. ⭐ Trace attributes through the handler — the magic metadata keys

This is the detail that is easy to miss and annoying to discover: with the callback handler you cannot call `propagate_attributes` (you are not inside your own function), so LangFuse reads **reserved keys out of LangChain's `metadata`**:

```python
response = chain.invoke(
    {"topic": "cats"},
    config={
        "callbacks": [langfuse_handler],
        "metadata": {
            "langfuse_user_id": "random-user",
            "langfuse_session_id": "random-session",
            "langfuse_tags": ["tag-1", "tag-2"],
        },
    },
)
```

| Reserved key | Sets |
|---|---|
| `langfuse_user_id` | The trace's `user_id` |
| `langfuse_session_id` | The trace's `session_id` |
| `langfuse_tags` | The trace's tags |

> **Without these three keys, a LangChain app gets none of lesson 07's benefits** — no session grouping, no user view, no tag filtering. The traces arrive and are individually fine and collectively unqueryable. It is the single highest-value thing to add to a LangChain integration, and it is three dictionary entries.
>
> Any *other* metadata key you pass is kept as ordinary trace metadata, so `prompt_version` and `tenant` from lesson 07's schema go in the same dict alongside them.

### JS/TS takes them as constructor options instead

```typescript
import { CallbackHandler } from "@langfuse/langchain";

const langfuseHandler = new CallbackHandler({
  sessionId: "user-session-123",
  userId: "user-abc",
  tags: ["langchain-test"],
});
```

And per-invocation:

```typescript
await chain.invoke(
  { animal: "dog" },
  {
    callbacks: [langfuseHandler],
    runName: "trace_name",
    tags: ["tag-1", "tag-2"],
    metadata: {
      langfuseUserId: "user-id",
      langfuseSessionId: "session-id",
    },
  }
);
```

Note the asymmetry: **the JS handler accepts these at construction, the Python one does not.** If you are porting between the two SDKs, this is a real difference rather than a stylistic one.

---

## 3. A complete LangChain RAG example

Bringing lesson 07's schema together with the handler:

```python
import os
from dotenv import load_dotenv
load_dotenv()

from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda

langfuse = get_client()
handler = CallbackHandler()

retriever = FAISS.load_local(
    "faiss_index", OpenAIEmbeddings(model="text-embedding-3-small"),
    allow_dangerous_deserialization=True,          # see the warning below
).as_retriever(search_kwargs={"k": 4})

prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer ONLY from the provided context. "
               "If the context is insufficient, say you don't know."),
    ("human", "Question: {question}\n\nContext:\n{context}"),
])
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

chain = (
    RunnableParallel({
        "context": retriever | RunnableLambda(lambda ds: "\n\n".join(d.page_content for d in ds)),
        "question": RunnablePassthrough(),
    })
    | prompt | model | StrOutputParser()
)


def answer(question: str, *, user_id: str, session_id: str, tenant: str) -> str:
    return chain.invoke(
        question,
        config={
            "callbacks": [handler],
            "run_name": "rag_query",
            "metadata": {
                # the three reserved keys — without these, no session/user/tags
                "langfuse_user_id": user_id,
                "langfuse_session_id": session_id,
                "langfuse_tags": ["rag", "prod"],
                # ordinary metadata, per lesson 07's schema
                "tenant": tenant,
                "prompt_version": "support_v3",
                "retriever_config": "faiss_k4",
                "embedding_model": "text-embedding-3-small",
                "version": os.getenv("GIT_SHA", "dev"),
            },
        },
    )


print(answer("What is the leave policy?",
             user_id="u_4471", session_id="sess_8f21", tenant="acme"))
langfuse.flush()
```

> **`allow_dangerous_deserialization=True` is pickle**, exactly as flagged in [`../30_langsmith/10-index-persistence-and-latency.md`](../30_langsmith/10-index-persistence-and-latency.md). Safe for an index your own process wrote to your own disk; **not** safe for one downloaded or restored from anywhere you don't control. For a multi-tenant or user-uploadable corpus, use a store that doesn't pickle.

The trace you get mirrors the chain, same as the LangSmith equivalent:

```
TRACE  rag_query          user: u_4471 · session: sess_8f21 · tags: rag, prod
└── span  RunnableSequence
    ├── span  RunnableParallel
    │   ├── span  VectorStoreRetriever   → 4 documents      ★
    │   └── span  RunnableLambda
    ├── span  ChatPromptTemplate         → the full prompt  ★
    ├── generation  ChatOpenAI           → tokens + cost
    └── span  StrOutputParser
```

The two starred observations are the RAG diagnosis, unchanged from [`../30_langsmith/07-tracing-rag-what-auto-tracing-misses.md`](../30_langsmith/07-tracing-rag-what-auto-tracing-misses.md): **the retrieved documents** and **the assembled prompt**. That reading skill transfers between platforms entirely — it is a property of RAG, not of the tool.

---

## 4. LangGraph

The handler works the same way. Pass it in `config` on `graph.invoke(...)`:

```python
result = graph.invoke(
    {"essay": essay_text},
    config={
        "callbacks": [handler],
        "run_name": "essay_evaluation",
        "metadata": {
            "langfuse_session_id": thread_id,
            "langfuse_tags": ["langgraph"],
        },
        "configurable": {"thread_id": thread_id},     # LangGraph's own checkpointing
    },
)
```

The two rules from [`../30_langsmith/12-tracing-langgraph.md`](../30_langsmith/12-tracing-langgraph.md) hold identically, because they are properties of LangGraph rather than of the observability tool:

> 1. **One graph execution = one trace.**
> 2. **Each node = one observation.**

Branching, parallelism, subgraphs and loops all come through.

> **⭐ Note the `thread_id` appears twice, and here that duplication is finally not a workaround.** In `configurable` it drives LangGraph's checkpointing; in `langfuse_session_id` it groups the turns into a session. In LangSmith you duplicate `thread_id` into *metadata* and then build the grouping yourself; here the second copy lands in a first-class field with a session view behind it. Same two lines, better payoff.

### Structured output looks the same

`model.with_structured_output(Schema)` still expands into a model call followed by a coercion step, so a node using it shows a nested sequence while a plain model call doesn't — the shape-tells-you-the-code observation from the LangSmith lesson. And schema-coercion failures still live in the **coercion** observation, not the model one, which is the practically useful half.

---

## 5. Mixing the handler with `@observe`

They compose, because both ride the same OTel context:

```python
@observe(name="support_request")
def support_request(question: str, *, user_id: str, session_id: str) -> str:
    with propagate_attributes(user_id=user_id, session_id=session_id):
        # your own instrumented pre-work
        cleaned = normalise(question)              # @observe'd separately

        # the LangChain part nests underneath
        answer = chain.invoke(cleaned, config={"callbacks": [handler]})

        get_client().set_current_trace_io(
            input={"question": question}, output={"answer": answer}
        )
        return answer
```

Two payoffs from this pattern:

**`propagate_attributes` covers the LangChain part too**, so you can skip the reserved metadata keys when the chain is invoked inside a decorated function — the attributes are already on the context. Use the reserved keys when LangChain is your *outermost* layer; use `propagate_attributes` when your own code is.

**Non-LangChain work appears in the same trace.** The pre-processing, validation, business logic and post-processing that LangChain never sees are exactly what [`../30_langsmith/07`](../30_langsmith/07-tracing-rag-what-auto-tracing-misses.md) called out as invisible under callback-only tracing. Decorating them fixes that here for the same reason.

> **Don't double-instrument.** A runnable already traced by the handler should not also be wrapped in `@observe` — you get two observations for one piece of work and the durations nest confusingly.

---

## Recap

- `from langfuse.langchain import CallbackHandler`; `CallbackHandler()` takes **no args** in Python and reads config from the client.
- Pass via `config={"callbacks": [handler]}` — **one line**, against LangSmith's zero. That's the real trade.
- **The three reserved metadata keys** — `langfuse_user_id`, `langfuse_session_id`, `langfuse_tags` — are how a LangChain app gets sessions, users and tags. **Without them the traces are individually fine and collectively unqueryable.**
- The **JS handler accepts these at construction**; the Python one doesn't.
- LangGraph: **graph execution = trace, node = observation**, unchanged. And `thread_id` duplicated into `langfuse_session_id` is a first-class field here rather than a metadata workaround.
- RAG reading skill transfers unchanged: **retrieved documents** and **assembled prompt** are still the two fields that split the diagnosis.
- Mix the handler with `@observe` to catch the non-LangChain work — but never wrap an already-traced runnable.

---

## Self-check

1. Your LangChain traces have no session grouping. What's missing, and exactly where does it go?
2. What can `@observe` capture in a LangChain app that the handler alone cannot?
3. Why does `thread_id` appear twice in the LangGraph config, and why is the second copy better here than in LangSmith?
4. When would you use the reserved metadata keys instead of `propagate_attributes`, and vice versa?

---

**Next:** [`09-otel-and-any-language.md`](09-otel-and-any-language.md) →
