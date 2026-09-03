# 09 · One Trace, Not Two: Nesting, Context and Explicit Roots

> ← [`08-the-traceable-decorator.md`](08-the-traceable-decorator.md) · **Next:** [`10-index-persistence-and-latency.md`](10-index-persistence-and-latency.md) →

---

## ⭐ A note on this lesson

**This lesson is largely added.** In the video, the author reaches exactly this problem, states clearly what the fix should look like — *"ideally it should have been our RAG application right at the top, and then setup pipeline inside that, and inside that a RAG query part… so next what we will do is modify our code in this way"* — and then moves on to the latency fix without ever coming back to it.

That is a perfectly reasonable editorial choice in a 2.5-hour crash course. But the problem is real, it recurs constantly the moment your application is more than one script, and the fix is genuinely worth knowing. So this lesson supplies it. The *problem statement* is the video's; the solutions are added.

---

## The problem

After lesson 08 the RAG project contains two traces per session:

```
RAG Chatbot
├── TRACE   setup_pipeline        ← load_pdf, split_documents, build_vector_store
└── TRACE   pdf_rag_query         ← parallel, prompt, model, parser
```

Two roots. Two `trace_id`s. Nothing connects them. But this is **one application** and, in the script, one user-visible operation. What you wanted:

```
TRACE  rag_application
├── RUN  setup_pipeline
│   ├── RUN  load_pdf
│   ├── RUN  split_documents
│   └── RUN  build_vector_store
└── RUN  pdf_rag_query
    ├── RUN  RunnableParallel
    ├── RUN  ChatPromptTemplate
    ├── RUN  ChatOpenAI
    └── RUN  StrOutputParser
```

### Why it happened

Lesson 04 gave the vocabulary. Every run carries a `parent_run_id`; a run with `parent_run_id = None` **is a root, and therefore starts a new trace**.

```python
retriever = setup_pipeline()                 # nothing active → root → TRACE 1
chain     = build_chain(retriever)
chain.invoke(q, config={"run_name": ...})    # nothing active → root → TRACE 2
```

Both calls happen at module level with no trace in progress. Each becomes a root. `@traceable` creates a run *inside whatever trace is currently active* — it does not invent a parent. When there is no active trace, it becomes one.

**Nesting is decided by what is on the stack when the call happens, not by which file the functions live in.**

---

## Fix 1 — nest by calling inside a decorated function

The simplest fix, and the one to reach for first: if A should be B's parent, call A from inside B.

```python
from langsmith import traceable

@traceable(name="rag_application")
def rag_application(question: str, path: str = PDF_PATH) -> str:
    retriever = setup_pipeline(path)          # nests: parent is rag_application
    chain     = build_chain(retriever)
    return chain.invoke(question)             # nests too


print(rag_application("Who is the author of this book?"))
```

One trace, three levels, exactly the shape asked for.

### How the nesting happens

`@traceable` stores the current run in a **`contextvars` context variable**. Any traced call made *while that variable is set* reads it and uses it as its parent. Because `setup_pipeline` and `chain.invoke` are now called during `rag_application`'s body, both see it and attach to it.

This is also why LangChain runnables nest correctly under a `@traceable` function: LangChain's tracer reads the same context variable. The two systems share one notion of "the current run".

> **The `contextvars` caveat, which will bite you eventually.** Context propagates into `await`ed coroutines and into `asyncio` tasks created from the current context. It does **not** propagate into a bare `threading.Thread` you start yourself. If you fan out with raw threads, the child runs become new roots. Two ways out:
>
> ```python
> # Option A — ThreadPoolExecutor with an explicitly copied context
> import contextvars, concurrent.futures
> ctx = contextvars.copy_context()
> with concurrent.futures.ThreadPoolExecutor() as pool:
>     futures = [pool.submit(ctx.run, work, item) for item in items]
>
> # Option B — pass the parent run tree explicitly (see Fix 3)
> ```
>
> LangChain's own `.batch()` and `RunnableParallel` handle this internally, so you only hit it in hand-rolled concurrency.

---

## Fix 2 — an explicit root with the `trace` context manager

Sometimes there is no natural function to wrap — a FastAPI handler, a CLI command, a notebook cell, a loop body. Use the `trace` context manager to open a root explicitly:

```python
from langsmith import trace

with trace(
    name="rag_application",
    run_type="chain",
    inputs={"question": question},
    project_name="RAG Chatbot",
    tags=["rag", "v2"],
    metadata={"pdf": PDF_PATH},
) as rt:
    retriever = setup_pipeline(PDF_PATH)      # nests
    chain     = build_chain(retriever)
    answer    = chain.invoke(question)        # nests
    rt.end(outputs={"answer": answer})
```

Everything inside the block nests under that root. `rt` is the run tree object (lesson 04) — `rt.end(outputs=...)` records the root's output, and `rt.id` is the run id you'll need for feedback in lesson 16.

**Use Fix 1 when a wrapping function is natural; Fix 2 when it isn't.** They are the same mechanism with different ergonomics.

---

## Fix 3 — pass the parent explicitly when context can't flow

When the parent and child are in different threads, processes or machines, `contextvars` cannot help. Pass the parent by hand.

### Same process, different thread

```python
from langsmith.run_helpers import get_current_run_tree, traceable

@traceable(name="parent")
def parent():
    rt = get_current_run_tree()
    run_in_thread(child, parent_run_tree=rt)

@traceable(name="child")
def child():
    ...

# at the call site inside the thread:
child(langsmith_extra={"parent": rt})
```

The `langsmith_extra` keyword is accepted by every `@traceable`-decorated function and is stripped before your function sees it. It also takes `run_id`, `name`, `tags`, `metadata` and `project_name` for per-call overrides.

### Across services — distributed tracing

This is the shape that matters once you have a real architecture: a gateway service calls a retrieval service calls a generation service, and you want **one trace spanning all three**.

```python
# ---------- service A (caller) ----------
from langsmith.run_helpers import get_current_run_tree, traceable
import requests

@traceable(name="gateway_handler")
def handle(question):
    rt = get_current_run_tree()
    headers = rt.to_headers() if rt else {}
    return requests.post(
        "http://retrieval:8000/search",
        json={"q": question},
        headers=headers,          # carries langsmith-trace + baggage
    ).json()


# ---------- service B (callee) ----------
from fastapi import FastAPI, Request
from langsmith.run_helpers import traceable

app = FastAPI()

@traceable(name="retrieval_service")
def do_search(q: str):
    ...

@app.post("/search")
async def search(request: Request):
    body = await request.json()
    return do_search(
        body["q"],
        langsmith_extra={"parent": dict(request.headers)},
    )
```

`rt.to_headers()` serialises the trace context into HTTP headers; passing the received headers as `parent` on the far side re-attaches. Same idea as W3C trace-context propagation in OpenTelemetry, and for the same reason.

---

## ⭐ But: is the video's stated ideal actually what you want?

Worth pausing on, because the answer is **no — not in production**, and this is more useful than the fix itself.

The video wants setup nested under the same root as the query. For a **script**, that's right: one process, one PDF load, one question, one logical operation.

For a **server**, it is wrong:

```
Startup (once)         : load PDF → chunk → embed → build index      ~30 s
Request (10,000 times) : retrieve → prompt → generate                ~2 s
```

Nesting startup under a query trace would mean:

- The **first** request's trace shows 32 s and every later one shows 2 s. Your p50/p95 latency charts (lesson 13) are now polluted by a one-off that isn't a request at all.
- Setup is recorded **once**, under an arbitrary request that happened to be first — a fact about your deployment filed under a fact about a user.
- If you scaled to four replicas, four unrelated requests each carry a 30-second startup.

The correct production shape is **two trace families, deliberately separate**:

| Trace family | Frequency | Belongs in |
|---|---|---|
| `index_build` — load, chunk, embed, persist | On deploy or corpus change | Its own project, or the same project with tag `lifecycle` |
| `rag_query` — retrieve, prompt, generate | Per request | The project whose latency/cost charts you actually watch |

```python
# --- startup path, traced as its own root, deliberately ---
@traceable(name="index_build", tags=["lifecycle"])
def build_index_once(path):
    docs   = load_pdf(path)
    chunks = split_documents(docs)
    return build_vector_store(chunks)

retriever = build_index_once(PDF_PATH)      # one trace, at boot

# --- request path, one root per request ---
@traceable(name="rag_query", tags=["request"])
def answer(question: str) -> str:
    return build_chain(retriever).invoke(question)
```

> **The general principle, and it applies far beyond RAG: one trace should correspond to one unit of work you would want to measure a distribution over.** Requests, yes — you care about p95 across them. Process startup, no — there is one of it, and averaging it with requests corrupts both numbers.
>
> So the two-traces outcome the video treats as a defect is, for a server, the correct design. The defect is only that it happened **by accident** rather than by choice. **Make it a decision.**

---

## Decision table

| Situation | Do this |
|---|---|
| A should be nested under B, both in your code | **Fix 1** — call A inside a `@traceable` B |
| No natural wrapping function (handler, CLI, notebook cell) | **Fix 2** — `with trace(...) as rt` |
| Parent and child in different threads | **Fix 3** — `langsmith_extra={"parent": rt}` |
| Parent and child in different services | **Fix 3** — `rt.to_headers()` → headers → `parent` |
| One-time setup vs per-request work | **Keep them separate on purpose**, and tag them so you can tell why |

---

## Recap

- Two sibling traces happen because both calls ran with **no active trace**, so each became a root. `@traceable` inherits a parent; it never invents one.
- **Nesting is determined by the call stack at runtime**, not by code organisation.
- **Fix 1:** call the child inside a `@traceable` parent. Propagation is via `contextvars` — works across `await`, **not** across raw threads.
- **Fix 2:** `with trace(name=..., inputs=...) as rt:` for an explicit root; `rt.end(outputs=...)`; `rt.id` for feedback later.
- **Fix 3:** `langsmith_extra={"parent": ...}` for threads; `rt.to_headers()` for cross-service distributed traces.
- **The video's ideal hierarchy is right for a script and wrong for a server.** One trace = one unit of work you want a *distribution* over. Keep startup out of request traces.

---

## Self-check

1. Two decorated functions called one after another at module level. How many traces, and why?
2. Which propagation mechanism does `@traceable` use, and what is the one common concurrency pattern it does not survive?
3. You want one trace spanning three microservices. What crosses the network, and how does the receiver attach to it?
4. Argue *against* nesting index-build under a query trace, using p95 latency.

---

**Next:** [`10-index-persistence-and-latency.md`](10-index-persistence-and-latency.md) →
