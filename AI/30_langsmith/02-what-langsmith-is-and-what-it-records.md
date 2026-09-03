# 02 · What LangSmith Is, and Exactly What It Records

> ← [`01-why-llm-observability.md`](01-why-llm-observability.md) · **Next:** [`03-setup-and-environment.md`](03-setup-and-environment.md) →

---

## The definition

> **LangSmith** is a unified **observability and evaluation** platform where teams can **debug, test and monitor** AI application performance.

Four load-bearing words:

| Word | What it commits to |
|---|---|
| **unified** | Traces, evaluations, datasets, prompts and feedback share one data model. A trace can become a test case; a test case can be scored; a score can gate a deploy. This is the reason to prefer one platform over four tools. |
| **observability** | Record a single execution in full detail (lessons 05–12) |
| **evaluation** | Score outputs against datasets and rubrics (lessons 14–15) |
| **monitor** | Aggregate across many executions, alert on drift (lesson 13) |

The rest of this lesson is a precise inventory of what a trace contains, because "it traces your app" is not actionable and the details determine what you can and cannot diagnose later.

---

## What gets recorded, field by field

### 1. Inputs and outputs of the whole execution

The user asked *"What is the capital of India?"*, the app answered *"New Delhi."* Both recorded verbatim.

Deceptively simple, but note: this is the **application boundary**, not the LLM boundary. If your app takes a PDF and returns a JSON object, that PDF reference and that JSON are the trace's input and output.

### 2. Every intermediate step

This is the one that makes Story C in lesson 01 solvable. For a RAG application, all of the following are recorded as separate steps:

```
user question
   → retriever input  (the query as the retriever saw it)
   → retriever output (the actual chunks, full text)
   → prompt inputs    (question + context, separately)
   → prompt output    (the fully assembled prompt string sent to the model)
   → LLM input        (the message list)
   → LLM output       (the raw completion)
   → parser input / parser output
```

> **The assembled prompt is the single highest-value field in the whole system.** It is the exact string the model saw. Nine debugging sessions in ten end there: the context was empty, or truncated, or the wrong document, or the grounding instruction never made it in because of a template variable typo.

### 3. Latency — at two levels

| Level | Question it answers |
|---|---|
| **Application** | Is the product slow? |
| **Component** | *Which part* is slow? |

Story A needed the second one and had only the first.

### 4. Token usage and cost

Recorded per LLM call and rolled up to the trace. LangSmith knows the pricing of common models, so it converts tokens → currency for you. Input and output tokens are tracked separately because they are priced differently (output typically several times more expensive).

This is what makes Story B tractable: a trace that cost ₹2 and a trace that cost 50 paise sit side by side in a list, sorted by cost, and you open the expensive one.

### 5. Errors

If any component raised, the trace is flagged and the failing run carries the exception. Note what this does *not* cover: the behavioural failures from lesson 01 raise nothing. Error tracking is necessary and nowhere near sufficient.

### 6. Tags

Short labels attached to a trace or a run, used for filtering.

- **System-generated.** LangSmith is aware enough of the framework to tag automatically — the model name (`gpt-4o`), the sequence step position, and so on.
- **Custom.** You add your own: `report_generation`, `v2_prompt`, `experiment_a`. Lesson 06 covers the mechanics.

### 7. Metadata

Arbitrary key/value pairs, richer than tags.

- **System.** Which LangChain version, which dependency versions, the model and its parameters.
- **Custom.** Anything you want to filter or group by later: `{"tenant": "acme", "prompt_version": "v7", "embedding_model": "text-embedding-3-small"}`.

> **Tags vs metadata, practically:** tags are a flat set of strings you scan visually and filter on; metadata is structured and is what you use for *analysis* ("show me p95 latency grouped by `prompt_version`"). Use tags for coarse buckets, metadata for anything you will want to compare across.

### 8. User feedback

Optionally attached to a trace — the 👍/👎 you have seen under a ChatGPT reply. Because it lands on the trace, the feedback is tied to the exact prompt, model and retrieved context that produced the answer the user disliked. Lesson 16.

---

## The recording model, compressed

```
                       ┌─────────────────────────────────────────┐
   your app runs  ───► │ TRACE                                   │
                       │  input · output · total latency · cost  │
                       │  tags · metadata · error? · feedback?   │
                       │                                         │
                       │  ├── RUN: prompt    in/out/latency      │
                       │  ├── RUN: retriever in/out/latency      │
                       │  ├── RUN: llm       in/out/tokens/cost  │
                       │  └── RUN: parser    in/out/latency      │
                       └─────────────────────────────────────────┘
```

Lesson 04 makes *project / trace / run* precise. For now: a trace is one execution, a run is one component inside it.

---

## The property that makes adoption easy

**Tracing requires no change to your application code.** You set environment variables; LangChain's callback system does the rest. Lesson 05 demonstrates this on an unmodified script.

This matters more than it sounds. It means:

- Adding observability to an existing LangChain app is a config change, not a refactor.
- You can turn it off in one place (see lesson 17 for how, and why you'd want to).
- The *default* posture is instrumented, which is the right default — the alternative is remembering to instrument before you need it, which nobody does.

The exception, and it's a big one: **only LangChain runnables are auto-traced.** Plain Python functions are invisible until you decorate them. That is the subject of lessons 07 and 08, and it's the first real gotcha in the tool.

---

## ⭐ Beyond the video — how the data actually gets there

*Added. The video treats tracing as magic, which is fine pedagogically, but the mechanism explains several behaviours you will otherwise find surprising.*

LangSmith tracing is implemented as a **callback handler**. LangChain's runnable interface emits lifecycle events — `on_chain_start`, `on_llm_end`, `on_retriever_error`, and so on — and the tracer subscribes to them, assembles run records, and ships them to the LangSmith API.

Four consequences worth knowing before they bite you:

| Consequence | Why | What to do |
|---|---|---|
| **Uploads are batched and asynchronous** | Tracing must not sit on your request's critical path | In a short-lived script, Lambda, or a container that exits immediately, flush before exit or lose the tail of your traces (lesson 17) |
| **Tracing failures are swallowed** | An observability outage must never take down your app | Do not assume "no trace appeared" means "the code did not run" — check the API key and the project name first |
| **It follows the callback tree, not your call stack** | Parent/child comes from LangChain's run tree | This is exactly why the video ends up with two sibling traces in lesson 07 — the two halves of the app were never in the same run tree. Lesson 09 fixes it |
| **Payloads are sent in full by default** | The payload *is* the signal (lesson 01, §5) | Every prompt, document and completion leaves your process. If any of it is personal or regulated data, read lesson 17 **before** you enable this in production |

That last row is the single most important operational fact in this tutorial and the video does not mention it.

---

## Recap

- LangSmith = **unified** observability + evaluation. The unification is the point: a trace becomes a test case becomes a gate.
- A trace records: inputs/outputs, **every intermediate step**, latency at app *and* component level, tokens and cost, errors, tags, metadata, and optionally user feedback.
- The **assembled prompt** is the highest-value single field.
- Tags = coarse filtering; metadata = structured analysis.
- Tracing needs **no application code change** — but only auto-traces LangChain runnables.
- Under the hood it is a callback handler: batched, async, fail-silent, follows the run tree, and ships full payloads.

---

## Self-check

1. Why is "unified observability *and* evaluation" a meaningful claim rather than marketing? Give one concrete workflow it enables.
2. You have `k=5` retrieved chunks but the answer ignores them. Which recorded field settles whether the chunks reached the model?
3. Give one thing you would put in a tag and one you would put in metadata, and justify the split.
4. Your script runs, prints the right answer, exits — and no trace appears in the UI. Name two plausible causes.

---

**Next:** [`03-setup-and-environment.md`](03-setup-and-environment.md) →
