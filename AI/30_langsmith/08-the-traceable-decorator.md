# 08 · `@traceable`: Tracing Anything That Isn't a Runnable

> ← [`07-tracing-rag-what-auto-tracing-misses.md`](07-tracing-rag-what-auto-tracing-misses.md) · **Next:** [`09-one-trace-not-two.md`](09-one-trace-not-two.md) →

---

Problem 1 from lesson 07: LangSmith auto-traces only LangChain runnables, so PDF loading, chunking and embedding were invisible. This lesson fixes it with one decorator — and that decorator turns out to be the single most useful thing in the LangSmith SDK, because it works on *any* Python function, in *any* codebase, LangChain or not.

---

## The decorator

```python
from langsmith import traceable

@traceable(name="load_pdf")
def load_pdf(path):
    return PyPDFLoader(path).load()
```

That is the whole idea. `load_pdf` is a plain function — no runnable, no chain, no LangChain type anywhere in it — and it now appears as a run in your trace, with its input, its output and its latency.

> **The rule:** `@traceable` traces **any ordinary Python function**, with or without runnables inside.

---

## The refactor

Lesson 07's script had load/chunk/embed as bare module-level statements. To decorate them, they must first become functions. `03_rag_v2.py`:

```python
# 03_rag_v2.py
import os
from dotenv import load_dotenv
load_dotenv()
os.environ["LANGSMITH_PROJECT"] = "RAG Chatbot"

from langsmith import traceable
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
# … prompt / parser / runnable imports as before …

PDF_PATH = "islr.pdf"


@traceable(name="load_pdf", tags=["pdf", "loader"],
           metadata={"loader": "PyPDFLoader"})
def load_pdf(path):
    return PyPDFLoader(path).load()


@traceable(name="split_documents")
def split_documents(documents, chunk_size=1000, chunk_overlap=150):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)


@traceable(name="build_vector_store", tags=["embeddings", "vector_store"],
           metadata={"embedding_model": "text-embedding-3-small",
                     "dimensions": 1536})
def build_vector_store(chunks):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = FAISS.from_documents(chunks, embeddings)
    return store.as_retriever(search_kwargs={"k": 4})


@traceable(name="setup_pipeline")
def setup_pipeline(path=PDF_PATH, chunk_size=1000, chunk_overlap=150):
    docs      = load_pdf(path)
    chunks    = split_documents(docs, chunk_size, chunk_overlap)
    retriever = build_vector_store(chunks)
    return retriever


retriever = setup_pipeline()
chain = build_chain(retriever)          # parallel | prompt | model | parser

while True:
    q = input("\nAsk: ")
    if not q:
        break
    print(chain.invoke(q, config={"run_name": "pdf_rag_query"}))
```

Two changes beyond the decorators:

- **`setup_pipeline` is itself decorated**, so the three steps nest underneath it rather than floating as three unrelated roots.
- **`run_name="pdf_rag_query"`** on the chain invoke, replacing the auto-generated `RunnableSequence`.

---

## What you now see

**Two traces** in the project per session:

### Trace A — `setup_pipeline`

```
setup_pipeline                                        ~30 s
├── load_pdf              in: "islr.pdf"
│                         out: 441 Documents           15 s
├── split_documents       in: chunk_size, chunk_overlap
│                         out: N chunks                fast
└── build_vector_store    in: 441 docs → chunks
                          out: retriever object        slow ★
```

Everything lesson 07 couldn't see:

| Step | Latency | What you learn |
|---|---|---|
| `load_pdf` | **~15 s** | Parsing 441 PDF pages is not cheap |
| `split_documents` | negligible | Pure string work; never optimise this |
| `build_vector_store` | the bulk | Embedding every chunk is the real cost, in time and money |

That ranking is the payoff. Before, you knew a query took 202 s. Now you know **where** — and therefore what to fix.

### Trace B — `pdf_rag_query`

Exactly the chain trace from lesson 07, now sensibly named.

---

## Per-function tags and metadata

`@traceable` takes `tags` and `metadata` just like `config` does, but scoped to that function:

```python
@traceable(name="load_pdf", tags=["pdf", "loader"],
           metadata={"loader": "PyPDFLoader"})

@traceable(name="build_vector_store", tags=["embeddings", "vector_store"],
           metadata={"embedding_model": "text-embedding-3-small",
                     "dimensions": 1536})
```

### Why this is worth the keystrokes

**It makes traces searchable.** Once `embedding_model` is recorded on the run, you can ask questions of your trace history:

- *Which traces used `text-embedding-3-small`?* — you switched models three weeks ago and want a before/after quality comparison.
- *Which traces used `PyPDFLoader`?* — you're evaluating a different PDF parser and need the baseline.
- *Show me every `build_vector_store` run sorted by latency* — you're capacity-planning a re-index.

With a handful of traces you can eyeball. With thousands, filtering on tags and metadata is the only way in. **Tag at write time so you can search at read time** — the same immutability point as lesson 06.

---

## ⭐ Beyond the video — the `@traceable` options that matter

*Added. The video uses `name`, `tags` and `metadata`. Three more options do real work.*

### `run_type` — earn the right UI

```python
@traceable(run_type="retriever", name="hybrid_search")
def hybrid_search(query: str) -> list[dict]:
    ...

@traceable(run_type="tool", name="get_weather")
def get_weather(city: str) -> dict:
    ...

@traceable(run_type="llm", name="call_local_model")
def call_local_model(messages): ...
```

Valid values: `chain` (default) · `llm` · `tool` · `retriever` · `prompt` · `parser` · `embedding`.

This is not cosmetic. Lesson 04 established that `run_type` drives rendering: a `retriever` run gets the document viewer, an `llm` run gets the token/cost panel and message formatting, a `tool` run is styled as a tool call in agent traces. **If you instrument a non-LangChain RAG stack and leave everything as `chain`, you get a wall of identical grey boxes.** One argument per function buys you the whole purpose-built UI.

### `process_inputs` / `process_outputs` — redact before it leaves the process

```python
def strip_pii(inputs: dict) -> dict:
    return {**inputs, "user_email": "<redacted>", "raw_document": "<omitted>"}

@traceable(name="answer_ticket", process_inputs=strip_pii)
def answer_ticket(user_email: str, raw_document: str, question: str):
    ...
```

The function runs on the payload **before it is sent**. Use it for PII, for secrets, and for pruning payloads that would otherwise be enormous (don't ship a 40 MB base64 image into a trace). This is the surgical tool; lesson 17 covers the blunt global switches.

### Async and generators work

```python
@traceable(name="async_step")
async def async_step(x):
    return await do_work(x)

@traceable(name="streamer")
def streamer(prompt):
    for tok in model.stream(prompt):
        yield tok
```

Both are handled — the async run closes when the coroutine completes, and the generator's run closes when the generator is exhausted, with the yielded values aggregated. **The generator case has a trap:** if you abandon a generator part-way, the run may never close cleanly and shows as still-running. Consume streams fully, or wrap them so you always drain to completion.

### The one real limitation

`@traceable` gives you a run **inside the currently active trace**. It does not, by itself, decide *which* trace that is. Which is exactly why we still have two sibling traces instead of one — and why lesson 09 exists.

---

## When to reach for `@traceable`

| Situation | Decorate? |
|---|---|
| Custom retrieval, re-ranking, filtering | **Yes** — and set `run_type="retriever"` |
| Tool/API functions an agent calls | **Yes** — `run_type="tool"` |
| Pre/post-processing: cleaning, validation, parsing | **Yes** |
| Business logic wrapping the LLM call | **Yes** — the LLM is rarely the whole story |
| A non-LangChain LLM SDK call (raw `openai`, Anthropic, a local model) | **Yes** — `run_type="llm"` |
| A pure one-line helper called in a tight loop | **No** — you'll drown the trace in noise |
| Anything already a runnable | **No** — it's traced already; decorating double-counts |

> **Calibration.** Decorate at the level you would want to see in a waterfall. A trace with eight meaningful runs is readable; one with four hundred `format_string` runs is not. Instrument **decisions and I/O**, not every function call.

---

## Recap

- `@traceable` traces **any Python function**, runnable or not — this is what makes LangSmith usable outside LangChain entirely.
- To decorate, you must first refactor bare statements into functions. That is a good change regardless.
- Result: `load_pdf` (~15 s), `split_documents` (fast), `build_vector_store` (dominant) — the latency ranking that tells you what to fix.
- Per-function `tags` and `metadata` make traces **searchable**; write them now, you cannot add them later.
- **`run_type`** earns you the purpose-built UI. Set it.
- **`process_inputs` / `process_outputs`** redact payloads before they leave your process.
- Async and generators are supported; drain generators fully.
- Still two sibling traces — `@traceable` creates runs but does not choose their parent. Next lesson.

---

## Exercise

1. Decorate `format_docs` and observe where it lands in the tree. Was that worth a row?
2. Add `run_type="retriever"` to a custom search function and compare the rendering against the default.
3. Write a `process_inputs` that truncates any string argument over 500 characters, and verify the trace is trimmed.
4. Decorate a function that raises. What does the run look like, and is the parent still recorded?

---

**Next:** [`09-one-trace-not-two.md`](09-one-trace-not-two.md) →
