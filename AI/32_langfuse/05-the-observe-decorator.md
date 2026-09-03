# 05 · The `@observe` Decorator

> ← [`04-self-hosting.md`](04-self-hosting.md) · **Next:** [`06-manual-observations.md`](06-manual-observations.md) →

---

`@observe` is the primary instrumentation tool and the one you will use most. It traces **any Python function**, framework or no framework.

If you read [`../30_langsmith/08-the-traceable-decorator.md`](../30_langsmith/08-the-traceable-decorator.md), this is LangFuse's `@traceable` — with one important difference in emphasis, covered in §5.

---

## 1. The basics

```python
from langfuse import observe

@observe()
def my_data_processing_function(data, parameter):
    return {"processed_data": data, "status": "ok"}
```

That function now appears as an observation with its input, output and duration.

Both call forms work:

```python
@observe          # bare
def f(): ...

@observe()        # called
def g(): ...
```

---

## 2. Nesting is automatic

```python
@observe
def my_data_processing_function(data, parameter):
    return {"processed_data": data, "status": "ok"}

@observe
def main_function(data, parameter):
    return my_data_processing_function(data, parameter)
```

Call `main_function` and the nested call appears beneath it. No ids threaded, no parent passed.

**The mechanism is OpenTelemetry context** (lesson 03 §4), and it carries the same caveat, for the same reason as [`../30_langsmith/09-one-trace-not-two.md`](../30_langsmith/09-one-trace-not-two.md):

| Concurrency | Nests? |
|---|---|
| Plain calls | ✅ |
| `await` / coroutines | ✅ |
| `asyncio` tasks created from the current context | ✅ |
| **Bare `threading.Thread` you start yourself** | ❌ **becomes a new root** |

```python
# ❌ the child becomes its own trace
threading.Thread(target=child_work).start()

# ✅ copy the context in
import contextvars, concurrent.futures
ctx = contextvars.copy_context()
with concurrent.futures.ThreadPoolExecutor() as pool:
    futures = [pool.submit(ctx.run, child_work, item) for item in items]
```

> **The outermost decorated function becomes the trace.** So "where does my trace begin?" has a precise answer: wherever the first `@observe` on the stack is. Put one on your request handler and the whole request is one trace.

---

## 3. Parameters

| Parameter | Effect |
|---|---|
| `name` | Observation name. Defaults to the function name |
| `as_type` | Observation type — `"span"` (default) or `"generation"` |
| `capture_input` | Capture arguments. Default `True` |
| `capture_output` | Capture the return value. Default `True` |

```python
@observe(name="llm-call", as_type="generation")
async def my_async_llm_call(prompt_text):
    return "LLM response"
```

### `as_type="generation"` is not cosmetic

Lesson 02 said it and it is worth repeating because it is the most common instrumentation mistake here: **a model call typed as a plain `span` does not get token/cost treatment.** The call is recorded; it just doesn't count toward any rollup. If you wrap a raw provider SDK call, set `as_type="generation"`.

### Async works

```python
@observe(name="llm-call", as_type="generation")
async def my_async_llm_call(prompt_text):
    return "LLM response"
```

> **Generators:** the documentation I read does not cover generator functions for `@observe`. I am not going to assert behaviour I could not confirm — if you are instrumenting a streaming generator, **test it and check the span closes**. The failure mode to watch for (from the equivalent LangSmith case) is an abandoned generator leaving a span that never ends.

---

## 4. Controlling IO capture — the PII lever

`capture_input=False` / `capture_output=False` per decorator:

```python
@observe(capture_input=False, capture_output=False)
def handle_patient_record(record_text: str, question: str) -> str:
    ...
```

You keep the structure, timing and nesting, and lose the payload — the surgical version of the blunt global switches in [`../30_langsmith/17-production-hardening.md`](../30_langsmith/17-production-hardening.md).

Globally, via environment:

```bash
LANGFUSE_OBSERVE_DECORATOR_IO_CAPTURE_ENABLED=false
```

> **The architectural version is better than either.** Rather than capturing the record text and hiding it, pass a **handle**:
>
> ```python
> # ❌ the record text exists in your process as a traced argument
> @observe(capture_input=False)
> def answer(record_text: str, question: str): ...
>
> # ✅ the trace holds a reference; content is resolved inside, untraced
> @observe()
> def answer(record_id: str, question: str): ...
> ```
>
> Same reasoning as the opaque citation handles in [`../28_ai-system-design-by-industry/04_healthcare_clinical_ai/`](../28_ai-system-design-by-industry/04_healthcare_clinical_ai/): you can see *which* record was used and how long it took, and the content never becomes trace data. Lesson 13 goes further.

---

## 5. Updating the current observation from inside

Where LangSmith's `@traceable` mostly takes what you declare at decoration time, LangFuse leans on **imperative updates from inside the function body** — and the client is the singleton, so you just fetch it.

```python
from langfuse import observe, get_client

langfuse = get_client()

@observe()
def my_llm_pipeline(user_question: str):
    result = call_llm(user_question)
    langfuse.set_current_trace_io(
        input={"question": user_question},
        output={"answer": result},
    )
    return result
```

The methods available for this (per the docs):

| Method | Updates |
|---|---|
| `langfuse.update_current_span(...)` | The current `span` observation |
| `langfuse.update_current_generation(...)` | The current `generation` observation |
| `langfuse.set_current_trace_io(input=…, output=…)` | The **trace's** input/output |

> **Why `set_current_trace_io` earns its place.** The automatic capture records the *outermost function's* arguments and return value as the trace IO — which is often not what a reader wants to see in a trace list. A handler receiving `(request: Request)` and returning `JSONResponse(...)` produces a trace listed by two useless objects. Setting the trace's IO to the actual question and answer makes your trace list scannable, which is the difference between a searchable history and a wall of identical rows.

---

## 6. A worked example

Instrumenting a RAG pipeline with nothing but decorators:

```python
from langfuse import observe, get_client
from openai import OpenAI

langfuse = get_client()
oai = OpenAI()


@observe(as_type="span", name="retrieve")
def retrieve(question: str, k: int = 4) -> list[dict]:
    hits = vector_store.search(question, k=k)
    langfuse.update_current_span(
        metadata={"k": k, "hits": len(hits),
                  "top_score": hits[0]["score"] if hits else None}
    )
    return hits


@observe(as_type="generation", name="answer")     # ← generation, for tokens/cost
def answer(question: str, context: str) -> str:
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system",
             "content": "Answer ONLY from the context. If insufficient, say you don't know."},
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"},
        ],
    )
    return resp.choices[0].message.content


@observe(name="rag_pipeline")                     # ← the outermost one is the TRACE
def rag_pipeline(question: str) -> str:
    hits = retrieve(question)
    context = "\n\n".join(h["text"] for h in hits)
    result = answer(question, context)
    langfuse.set_current_trace_io(
        input={"question": question},
        output={"answer": result},
    )
    return result


print(rag_pipeline("What is the leave policy?"))
langfuse.flush()
```

Produces:

```
TRACE  rag_pipeline          in: {question}   out: {answer}
├── span        retrieve      metadata: k=4, hits=4, top_score=0.83
└── generation  answer        model · tokens · cost
```

**Three deliberate choices in twenty lines, and each maps to a lesson:**

| Choice | Why |
|---|---|
| `answer` is a **`generation`** | Otherwise tokens and cost are not recorded (lesson 02) |
| `retrieve` records **hit count and top score** in metadata | These are exactly the fields you open first when a RAG answer is wrong ([`../30_langsmith/07`](../30_langsmith/07-tracing-rag-what-auto-tracing-misses.md) §Beyond) |
| The trace's IO is **set explicitly** | So the trace list shows the question, not a `Request` object |

Note also what is *not* here: `retrieve` returns documents, and their **full text** lands in the observation output by default. That is the diagnostic gold from lesson 07 of the LangSmith folder — and it is also your corpus leaving the process. Deliberate either way; lesson 13.

---

## 7. When to decorate, and when not to

| Situation | Decorate? |
|---|---|
| Retrieval, re-ranking, filtering | **Yes** — the fields you debug from |
| A raw provider SDK call | **Yes**, `as_type="generation"` |
| Tool / API functions an agent calls | **Yes** |
| Pre/post-processing, validation, parsing | **Yes** |
| Business logic wrapping the LLM call | **Yes** — the LLM is rarely the whole story |
| A one-line helper in a tight loop | **No** — you'll bury the trace in noise |
| Anything already traced by the LangChain handler | **No** — double-counts (lesson 08) |

> **Calibration, same as the LangSmith folder: decorate at the level you'd want to see in a waterfall.** Eight meaningful observations is readable; four hundred `format_string` observations is not. Instrument **decisions and I/O**, not every function call.

---

## Recap

- `from langfuse import observe` — traces **any** Python function.
- **Nesting is automatic** via OpenTelemetry context: survives `await`, **not** bare threads.
- **The outermost decorated function becomes the trace.**
- Parameters: `name` · `as_type` · `capture_input` · `capture_output`.
- **`as_type="generation"` for model calls**, or you silently lose tokens and cost.
- IO capture is togglable per-decorator or globally via `LANGFUSE_OBSERVE_DECORATOR_IO_CAPTURE_ENABLED` — but **passing a handle instead of content is better than hiding content**.
- Update from inside with `update_current_span` / `update_current_generation` / **`set_current_trace_io`** — the last one is what makes trace lists scannable.
- Generator support is **not documented**; test it rather than assuming.

---

## Exercise

1. Instrument a two-step pipeline and confirm one trace with two nested observations.
2. Change the model call from `span` to `generation` and compare what the UI shows. Note exactly what appears.
3. Remove `set_current_trace_io` and look at the trace list. Would you find that trace among a thousand?
4. Fan out with a bare `threading.Thread` and observe the orphaned trace. Fix it with `contextvars.copy_context()`.
5. Add `capture_input=False` to one function and verify structure survives while payload doesn't.

---

**Next:** [`06-manual-observations.md`](06-manual-observations.md) →
