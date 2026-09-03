# 07 · Sessions, Users and Trace Attributes

> ← [`06-manual-observations.md`](06-manual-observations.md) · **Next:** [`08-langchain-and-langgraph.md`](08-langchain-and-langgraph.md) →

---

This is where LangFuse's data model pays off relative to LangSmith, and where a few lines written at instrumentation time decide which questions you can answer during an incident.

---

## 1. `propagate_attributes` — the mechanism

Trace-level attributes are set with a context manager, and everything inside inherits them:

```python
from langfuse import observe, propagate_attributes

@observe()
def my_llm_pipeline(user_id: str, session_id: str):
    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        metadata={"pipeline": "main"},
    ):
        result = call_llm()
        return result
```

Per the docs, this propagates to **all nested observations**:

| Attribute | Purpose |
|---|---|
| `user_id` | Who |
| `session_id` | Which conversation |
| `metadata` | Arbitrary structured values |
| `version` | Your app/prompt version |
| `environment` | `production` / `staging` / `development` |
| `trace_name` | Overrides the trace's name |

> **Call it early in the outermost function.** Observations created *before* the `with` block will not carry the attributes — they were created in a context that didn't have them yet. This is the most common way these fields end up half-populated, and it looks like a bug in LangFuse rather than an ordering mistake.

---

## 2. Sessions — the multi-turn question

Lesson 02 introduced this. Here is why it changes what you can do.

```python
@observe(name="chat_turn")
def chat_turn(session_id: str, user_id: str, message: str) -> str:
    with propagate_attributes(session_id=session_id, user_id=user_id):
        reply = agent.run(message)
        get_client().set_current_trace_io(
            input={"message": message}, output={"reply": reply}
        )
        return reply
```

One line — `session_id=session_id` — and the UI gains a session view:

```
SESSION  sess_8f21          user: u_4471
├── TRACE  turn 1  "what's the leave policy?"      2.1 s   $0.0004   👍
├── TRACE  turn 2  "and for contractors?"          1.8 s   $0.0005   👍
├── TRACE  turn 3  "can I carry it over?"          2.4 s   $0.0011   👎  ← reported
└── TRACE  turn 4  "never mind"                    0.9 s   $0.0002
```

**Why the session is frequently the right unit of analysis.** Turn 3 is the reported failure, and the cause is often upstream: context accumulated across turns, a misunderstanding from turn 2 that stuck, a document retrieved in turn 1 that anchored the model. Open turn 3 alone and you see a wrong answer with no visible reason.

Note the cost column too — turn 3 cost 2–3× the others, which is the [Story B](../30_langsmith/01-why-llm-observability.md) signature at conversation scale: growing context, or a loop.

> **In LangSmith this requires duplicating `thread_id` into metadata** purely so the question is answerable ([`../30_langsmith/12-tracing-langgraph.md`](../30_langsmith/12-tracing-langgraph.md) §Beyond). Here it is a field with a UI behind it. Small difference in effort, real difference in whether anyone actually does it.

### Sessions are also the right sampling unit

From [`../30_langsmith/17-production-hardening.md`](../30_langsmith/17-production-hardening.md) §2: sample by **session**, not by request. A conversation with turns 2 and 5 traced and 1, 3, 4 missing is nearly unreadable. `session_id` gives you the natural hash key:

```python
import hashlib

def should_trace(session_id: str, rate: float = 0.05) -> bool:
    h = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)
    return (h % 10_000) < rate * 10_000        # whole conversations, in or out
```

---

## 3. Users

```python
with propagate_attributes(user_id="u_4471"):
    ...
```

Buys three questions:

| Question | Value |
|---|---|
| **"Is this one customer or everyone?"** | The first triage question in any incident |
| "What has this user's experience been?" | Every trace, cost, score for them |
| "Who are our expensive users?" | Cost per user, for pricing and abuse detection |

> **Pseudonymous ids only.** `u_4471`, not `nitish@example.com`. The field name invites a human-readable value and you must not give it one — same rule as [`../30_langsmith/06-tags-metadata-and-run-names.md`](../30_langsmith/06-tags-metadata-and-run-names.md): identifiers in, content out. A `user_id` containing an email address is a PII leak into every trace that user ever generates, and traces are immutable.

---

## 4. Tags and metadata

Same division of labour as the LangSmith folder:

| | Shape | For |
|---|---|---|
| **Tags** | Flat list of strings | Coarse buckets you filter on |
| **Metadata** | Structured key/value | Values you **group and compare** by |

### A schema worth writing down before you need it

```python
with propagate_attributes(
    user_id=user.pseudo_id,
    session_id=session.id,
    environment=os.getenv("APP_ENV", "development"),
    version=os.getenv("GIT_SHA", "dev"),
    metadata={
        # --- who ---
        "tenant":            org.slug,
        # --- what ran ---
        "prompt_version":    "support_v3",
        "retriever_config":  "hybrid_k8_rerank",
        "embedding_model":   "text-embedding-3-small",
        "model":             "gpt-4o-mini",
        # --- how it was sampled ---
        "sample_rate":       0.05,
    },
):
    ...
```

Every key buys one incident question:

| Question during an incident | Key |
|---|---|
| "Is it one customer or everyone?" | `tenant` / `user_id` |
| "Did this start with the deploy?" | `version` |
| "Is the new prompt worse?" | `prompt_version` |
| "Is staging polluting prod metrics?" | `environment` |
| "Show me this whole conversation" | `session_id` |
| "Did the retriever change help?" | `retriever_config` |
| "What's the true volume behind these traces?" | `sample_rate` |

> **Traces are immutable.** You cannot add a field retroactively to traces already written, so every key you skip is a question you will not be able to answer about the past. Ten minutes of schema design now against a blind incident later is not a close trade.
>
> `sample_rate` is the one people omit and then miscount. If you sample at 5% and later compute volumes from trace counts, you are wrong by 20× — and nobody remembers the rate six months on.

---

## 5. `environment` — use it instead of splitting projects

```python
with propagate_attributes(environment=os.getenv("APP_ENV", "development")):
    ...
```

The alternative — a project per environment — looks tidy and is worse: it fragments datasets, prompts and score history across projects that cannot be compared. **One project with an environment dimension** keeps your golden dataset and prompt history in one place while still letting you exclude staging noise from production dashboards.

Cheap to do now, annoying to retrofit, and impossible for existing traces.

---

## 6. ⭐ A FastAPI wiring that gets all of this right

The pattern worth copying, because it puts every field in exactly one place:

```python
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from langfuse import get_client, observe, propagate_attributes
import os

@asynccontextmanager
async def lifespan(app):
    yield
    get_client().flush()              # lesson 03 §5

app = FastAPI(lifespan=lifespan)
langfuse = get_client()


@observe(name="chat_turn")
def handle_turn(*, message: str, user_id: str, session_id: str, tenant: str) -> str:
    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        environment=os.getenv("APP_ENV", "development"),
        version=os.getenv("GIT_SHA", "dev"),
        metadata={"tenant": tenant, "prompt_version": PROMPT_VERSION},
    ):
        reply = rag_pipeline(message)
        langfuse.set_current_trace_io(
            input={"message": message}, output={"reply": reply}
        )
        return reply


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    reply = handle_turn(
        message=body["message"],
        user_id=body["user_id"],          # pseudonymous
        session_id=body["session_id"],
        tenant=body["tenant"],
    )
    # return the trace id so feedback can attach later — lesson 10
    return {"reply": reply, "trace_id": langfuse.get_current_trace_id()}
```

Four things this does deliberately:

1. **`@observe` on the handler function**, not the route — so the trace covers the work, and FastAPI's `Request` object never becomes the traced input.
2. **`propagate_attributes` immediately**, before any work — so nothing is created outside the context (§1).
3. **`set_current_trace_io`** so the trace list shows the message and reply, not a `Request` and a `JSONResponse`.
4. **The trace id is returned to the client**, which is what makes out-of-band user feedback possible at all (lesson 10). Without this, a thumbs-down has nothing to attach to.

> On point 4 — `get_current_trace_id()` is the accessor I would reach for, but **confirm the exact method name against the [SDK reference](https://python.reference.langfuse.com/langfuse) for your version.** This is one of the accessors that moved across major versions, and I would rather flag that than have you debug a name I half-remembered.

---

## Recap

- **`propagate_attributes(...)`** sets `user_id` · `session_id` · `metadata` · `version` · `environment` · `trace_name` on the trace and all nested observations.
- **Call it early** — observations created before the block don't inherit.
- **`session_id` is the multi-turn primitive.** The session is often the right unit of analysis, because turn 3's failure was caused in turn 1. It's also the correct **sampling** key.
- **`user_id`** answers "one customer or everyone?" — **pseudonymous ids only**.
- Tags = coarse buckets; metadata = structured comparison. **Design the schema before you need it; traces are immutable.**
- Record **`sample_rate`** or every volume you compute later is wrong by an unknown factor.
- Use **`environment`** rather than a project per environment.
- Return the **trace id** to the client so feedback can attach out of band.

---

## Self-check

1. Half your traces have no `user_id` despite the code setting it. What's the likely ordering mistake?
2. Why sample by session rather than by request?
3. Name two things you must never put in `user_id`, and why the field name is a trap.
4. You sample at 5% and someone reports monthly volume from trace counts. What did they get wrong?
5. Why is one project with `environment` better than three projects?

---

**Next:** [`08-langchain-and-langgraph.md`](08-langchain-and-langgraph.md) →
