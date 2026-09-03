# 10 · Scores and User Feedback

> ← [`09-otel-and-any-language.md`](09-otel-and-any-language.md) · **Next:** [`11-datasets-and-experiments.md`](11-datasets-and-experiments.md) →

---

Everything so far records **what happened**. Scores record **whether it was any good** — which, per [`../30_langsmith/13-monitoring-and-alerting.md`](../30_langsmith/13-monitoring-and-alerting.md), is the thing no mechanical metric can tell you.

Recall Story C: the HR chatbot that was fast, cheap, error-free, and telling employees there was no leave policy. Invisible on every latency and cost chart. Scores are the subsystem that sees it.

---

## 1. The score API

```python
langfuse.create_score(
    name="score_name",
    value=0.9,
    trace_id="trace_id_here",
    observation_id="observation_id_here",   # optional
    session_id="session_id_here",           # optional
    data_type="NUMERIC",                    # optional, can be inferred
    comment="Optional comment",
    score_id="unique_id",                   # optional, for idempotency
    config_id="config_id",                  # optional
)
```

Two arguments worth calling out:

**`score_id` gives you idempotency.** A feedback endpoint that retries — because a mobile client resent, or a queue redelivered — would otherwise create duplicate scores and skew the aggregate. Derive it from something stable: `sha256(trace_id + score_name + user_id)`.

**Attachment is three-level**, matching the data model from lesson 02:

| Pass | Score attaches to | Answers |
|---|---|---|
| `trace_id` | The trace | "Was this answer good?" |
| `trace_id` + `observation_id` | One observation | "Was the *retrieval* good?" |
| `session_id` | The session | **"Was this conversation successful?"** |

That third row has no LangSmith equivalent and it answers a question per-turn metrics cannot: a conversation where every individual reply scored fine but the user gave up after six turns is a failure, and only a session-level score records it.

---

## 2. Contextual scoring — from inside the code

When you are already inside a traced function, you don't need ids:

```python
langfuse.score_current_trace(name="trace_score", value=0.95, data_type="NUMERIC")
langfuse.score_current_span(name="score_name",  value=0.9,  data_type="NUMERIC")
```

Or on an observation object you hold:

```python
span.score(name="score_name", value=0.9, data_type="NUMERIC", comment="Optional")
span.score_trace(name="trace_score", value=0.95, data_type="NUMERIC")
```

Note `span.score()` scores **the span**, while `span.score_trace()` reaches up and scores **the trace** from inside a span. The second is what you want for a guardrail deep in a pipeline that has just made a judgement about the whole response.

---

## 3. The four data types, and choosing between them

| Type | Value | Use for |
|---|---|---|
| **`NUMERIC`** | float | Continuous quality — faithfulness 0.82, relevance, similarity |
| **`CATEGORICAL`** | string | Bucketed judgements — `"correct"` / `"partially_correct"` / `"wrong"` |
| **`BOOLEAN`** | `1` = true, `0` = false | Pass/fail — did it refuse when it should have? |
| **`TEXT`** | string, 1–500 chars | Qualitative note — a reviewer's reasoning |

### Pick the type that matches the judgement, not the one that's easiest to average

The temptation is `NUMERIC` for everything because numbers aggregate. It is usually wrong, and here is the concrete reason:

```
Reviewer A marks an answer "half right"        → 0.5
Reviewer B is unsure and splits the difference → 0.5

mean = 0.5, which means neither of those things.
```

With `CATEGORICAL` you get counts — 12 `correct`, 5 `partially_correct`, 3 `wrong` — which is a distribution you can act on, and it survives aggregation honestly.

| Judgement | Right type | Why |
|---|---|---|
| "Is every claim supported by the context?" | **`BOOLEAN`** | It either is or isn't. A 0.7-faithful answer is an unfaithful answer |
| "Did it correctly refuse an unanswerable question?" | **`BOOLEAN`** | Pass/fail by nature |
| "How relevant, on a scale?" | **`NUMERIC`** | Genuinely continuous |
| "Correct / partially / wrong" | **`CATEGORICAL`** | Three distinct states, not a number |
| "Why was this bad?" | **`TEXT`** | The reasoning is the value |

> **`BOOLEAN` for faithfulness is the one people get wrong.** A partly-hallucinated answer is not 70% good — it is an answer containing a fabrication, which is the failure. Scoring it 0.7 lets it average away against nine good answers into a healthy-looking 0.97.

---

## 4. ⭐ Out-of-band user feedback — the complete loop

The most valuable use of the score API, and the one worth wiring first.

Feedback arrives **seconds or hours after the trace closed**, from a different request. It attaches by `trace_id`:

```python
langfuse.create_score(
    name="user_feedback",
    value=1,                       # 1 positive, 0 negative
    trace_id="existing_trace_id",
    data_type="BOOLEAN",
    comment="User marked as helpful",
)
```

### The three pieces

**1. Return the trace id when you answer** (lesson 07 §6):

```python
@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    reply = handle_turn(**body)
    return {"reply": reply, "trace_id": langfuse.get_current_trace_id()}
```

**2. The client sends it back with the rating.**

**3. Score it:**

```python
import hashlib

@app.post("/feedback")
async def feedback(body: FeedbackBody):
    langfuse.create_score(
        trace_id=body.trace_id,
        name="user_feedback",
        value=1 if body.thumbs_up else 0,
        data_type="BOOLEAN",
        comment=body.comment,
        score_id=hashlib.sha256(
            f"{body.trace_id}:user_feedback".encode()
        ).hexdigest(),                       # idempotent under retry
    )
    return {"ok": True}
```

### Why this is worth more than it looks

A raw thumbs-down is nearly useless — *something* was wrong with *some* answer. A thumbs-down **attached to a trace** is a bug report that has already written itself:

| You get for free | From |
|---|---|
| The exact question | trace input |
| The exact retrieved chunks | retrieval observation |
| The exact assembled prompt | prompt observation |
| The exact model and parameters | generation observation |
| The whole conversation around it | `session_id` |
| Cost, latency, tokens | trace metrics |
| Prompt version, tenant, deploy | your metadata (lesson 07) |

No "can you reproduce it?", no "what did you ask exactly?". And then — lesson 11 — that trace becomes a **dataset item**, and the failure can never silently return. That is the complete loop, and it is the single highest-value thing in the platform:

```
user dislikes an answer
      │
      ▼
trace with full context, already captured
      │
      ▼
dataset item with the corrected expected output
      │
      ▼
CI gate — this specific failure cannot come back
```

### Go beyond the thumbs

Most users never click either button, so explicit ratings are a small and biased sample. **Implicit signals are often more honest:**

```python
langfuse.create_score(trace_id=tid, name="answer_copied",      value=1, data_type="BOOLEAN")
langfuse.create_score(trace_id=tid, name="user_rephrased",     value=1, data_type="BOOLEAN")
langfuse.create_score(trace_id=tid, name="escalated_to_human", value=1, data_type="BOOLEAN")
langfuse.create_score(trace_id=tid, name="session_abandoned",  value=1, data_type="BOOLEAN")
```

**A user who immediately rephrases the same question has given you a thumbs-down without clicking anything.** So has one who abandoned the session. These fire far more often than explicit feedback and require nothing of the user.

> **Treat `trace_id` as capability-bearing.** It is a UUID, but anyone holding one can attach scores. Rate-limit the feedback endpoint and don't let a client score arbitrary ids, or your quality metric is trivially pollutable — by a bot, or by one annoyed user with the developer console open.

---

## 5. LLM-as-a-judge and code evaluators

Per the docs, LangFuse supports automated scoring via **LLM-as-a-judge evaluators** configured in the UI, and code-based deterministic checks — both **online** (on production traces) and **offline** (against datasets, lesson 11).

Order of preference, same argument as [`../30_langsmith/14-evaluation-datasets-and-annotation.md`](../30_langsmith/14-evaluation-datasets-and-annotation.md):

**Reach for deterministic code first.** It is free, instant and perfectly reliable for everything mechanically checkable:

```python
@observe(name="answer")
def answer(question: str, context: str) -> str:
    out = call_model(question, context)

    # free, instant, exact
    langfuse.score_current_trace(
        name="has_citation", value=int("[" in out), data_type="BOOLEAN")
    langfuse.score_current_trace(
        name="within_length", value=int(len(out) < 2000), data_type="BOOLEAN")
    langfuse.score_current_trace(
        name="refused", value=int("i don't know" in out.lower()), data_type="BOOLEAN")

    return out
```

A large share of what teams pay a judge model to assess — is the JSON parseable, is there a citation, is it under the length limit, did it refuse — is a five-line assertion. **Save the judge for what genuinely needs judgement**, and when you use one, give it temperature 0 and structured output or your evaluation is itself non-deterministic.

For the theory — RAG Triad, G-Eval, reference-based vs reference-free, judge validation — see [`../16_evals/`](../16_evals/). This lesson is only the plumbing.

---

## 6. Annotation queues

Per the docs, LangFuse provides **annotation queues** and UI-based scoring for human review.

The workflow that makes them pay:

```
production traces
   │  filter: negative feedback · low judge score · high cost · flagged tag
   ▼
annotation queue
   │  human reviews and scores  (CATEGORICAL + TEXT)
   ▼
authoritative labels
   │
   ├──► dataset items          (lesson 11 — regression tests)
   └──► judge validation        (does the LLM judge agree with humans?)
```

> **That second output is the one people skip, and it is what makes an LLM judge trustworthy.** A judge is a model, so it has its own biases and failure modes. Sampling traces, having humans score them, and **measuring judge-vs-human agreement** is the only way to know whether your automated scores mean anything. An unvalidated judge is a number generator that everyone treats as ground truth.
>
> Queue the *interesting* traces, not random ones — negative feedback, judge/human disagreement, unusual cost. Human attention is the scarce resource in every one of these designs ([`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/) makes this the recurring theme), so spend it where it changes a decision.

---

## Recap

- `create_score(...)` attaches to a **trace**, an **observation**, or a **session** — three levels, three different questions.
- **`score_id` gives idempotency** — derive it, or retried feedback skews your aggregates.
- In-context helpers: `score_current_trace` · `score_current_span` · `span.score()` · `span.score_trace()`.
- Four types: **`NUMERIC` · `CATEGORICAL` · `BOOLEAN` · `TEXT`**. Match the type to the judgement, not to what averages easily.
- **`BOOLEAN` for faithfulness** — a partly-hallucinated answer is not 70% good.
- **Out-of-band feedback by `trace_id`** turns a thumbs-down into a complete bug report, and then into a dataset item. This is the whole loop.
- **Implicit signals beat explicit ones** — immediate rephrase, abandonment, escalation. Most users never click.
- Rate-limit the feedback endpoint; `trace_id` is capability-bearing.
- **Deterministic code before LLM judges.** Then validate the judge against human annotations, or it is a number generator.
- Queue **interesting** traces for annotation, not random ones.

---

## Self-check

1. Feedback arrives an hour after the trace closed. What makes that work?
2. Why is `BOOLEAN` better than `NUMERIC` for faithfulness?
3. Name two implicit feedback signals and say why they beat explicit ratings.
4. What is the risk of an unauthenticated `/feedback` endpoint?
5. What is the second, commonly-skipped output of an annotation queue, and why does it matter?

---

**Next:** [`11-datasets-and-experiments.md`](11-datasets-and-experiments.md) →
