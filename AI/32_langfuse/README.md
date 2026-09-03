# 🪁 LangFuse — Open-Source LLM Observability & Evaluation

> **Companion to [`../30_langsmith/`](../30_langsmith/).** Same job, different trade-offs: open source, self-hostable, OpenTelemetry-native, framework-neutral.
>
> **Sourcing:** written from the **official LangFuse documentation**, read September 2026, against **Python SDK v4**. Unlike `30_langsmith` this folder is **not transcript-derived** — there is no video behind it. Where the docs were ambiguous, the lesson says so and points at the [SDK reference](https://python.reference.langfuse.com/langfuse) rather than guessing a signature.
>
> **Prerequisite:** [`../30_langsmith/`](../30_langsmith/) lessons 01–04. **This folder does not re-argue why LLM observability is necessary** — that case is tool-independent and made there.

---

## ⚠️ Read this before any LangFuse tutorial, including this one

The Python SDK has changed API surface across major versions, and **most material online is v2**, which looks nothing like current code.

| Era | Shape |
|---|---|
| **v2** | `langfuse.trace(...)` → object, `trace.generation(...)`, manual `.end()` |
| **v3** | OpenTelemetry rewrite; context managers |
| **v4** ← this folder | `get_client()` · `start_as_current_observation(as_type=…)` · `propagate_attributes()` · `run_experiment()` |

```bash
pip show langfuse | grep -i version
```

Symptoms of following v2 material against v4: `langfuse.trace(...)` doesn't exist · manual `trace_id` threading everywhere · `LANGFUSE_HOST` in your `.env` (it is now **`LANGFUSE_BASE_URL`**).

---

## Lessons

| # | Lesson | Covers |
|---|---|---|
| 1 | [Why LangFuse, and How It Differs](01-why-langfuse-and-how-it-differs.md) | The three real differences · honest comparison table · picking one · the version trap |
| 2 | [Core Concepts and the Data Model](02-core-concepts-and-data-model.md) | **LangSmith "run" = LangFuse "observation"** · span/generation/event · **sessions** · users · scores |
| 3 | [Setup: Keys, Regions and the Client](03-setup-and-keys.md) | Key pair · `LANGFUSE_BASE_URL` · regions are separate instances · `get_client()` singleton · `flush()` |
| 4 | [Self-Hosting](04-self-hosting.md) | **4 stateful services** · the UTC requirement · Compose limits · licensing honestly · **when it's theatre** |
| 5 | [The `@observe` Decorator](05-the-observe-decorator.md) | Automatic nesting · `as_type` · IO capture · `set_current_trace_io` · worked RAG example |
| 6 | [Manual Observations](06-manual-observations.md) | `start_as_current_observation` · `usage_details` · **events turn a stopwatch into a narrative** |
| 7 | [Sessions, Users and Trace Attributes](07-sessions-users-and-trace-attributes.md) | `propagate_attributes` · why the **session** is the right unit · metadata schema · FastAPI wiring |
| 8 | [LangChain and LangGraph](08-langchain-and-langgraph.md) | `CallbackHandler` · **the three reserved metadata keys** · graph=trace, node=observation |
| 9 | [OpenTelemetry: Any Language](09-otel-and-any-language.md) | ⭐ **What LangSmith cannot do.** OTLP endpoint · no gRPC · Go example · collector pattern |
| 10 | [Scores and User Feedback](10-scores-and-user-feedback.md) | Four score types · **out-of-band feedback by `trace_id`** · implicit signals · judge validation |
| 11 | [Datasets and Experiments](11-datasets-and-experiments.md) | `run_experiment` · evaluators vs run_evaluators · **the refusal test case** · CI gating |
| 12 | [Prompt Management](12-prompt-management.md) | Labels as deployment · caching & fallback · **repo vs platform**, with a recommendation |
| 13 | [Production, and Choosing Between the Two](13-production-and-choosing.md) | PII layers · cost shape · the decision · full checklist |

---

## The vocabulary map — read this first

| LangSmith | LangFuse |
|---|---|
| Project | Project |
| Trace | Trace |
| **Run** | **Observation** ⚠️ the one rename |
| `run_type="chain"` | observation type **`span`** |
| `run_type="llm"` | observation type **`generation`** |
| — | observation type **`event`** |
| Feedback | **Score** (4 data types) |
| metadata convention | **`session_id`** ⭐ first-class |
| metadata convention | **`user_id`** ⭐ first-class |

---

## The three differences that decide it

1. **You can run it yourself.** Open-source core, self-hosting as a documented first-class path — not an enterprise escape hatch. If trace payloads legally cannot leave your infrastructure, masking is damage limitation and this is the answer.
2. **It's an OpenTelemetry backend.** Receives OTLP, so **any OTel-instrumented app in any language** can send traces — Go, Java, Rust, .NET. LangSmith has no equivalent.
3. **Framework-neutral.** LangChain/LangGraph are supported, but nothing else is a second-class path.

---

## Key facts

| | |
|---|---|
| SDK version here | **v4** |
| Keys | **Pair** — `pk-lf-…` public, `sk-lf-…` secret |
| Base URL var | **`LANGFUSE_BASE_URL`** (not `LANGFUSE_HOST`) |
| Cloud regions | EU · US · **JP** · **HIPAA** — separate instances, keys bound to one |
| Self-host stack | 2 app containers + **Postgres + ClickHouse + Redis/Valkey + blob storage** |
| Hard self-host requirement | **Postgres & ClickHouse must run in UTC** or queries fail |
| OTLP endpoint | `/api/public/otel` — HTTP/JSON or HTTP/protobuf, **no gRPC** |
| Score types | `NUMERIC` · `CATEGORICAL` · `BOOLEAN` · `TEXT` |
| Score attaches to | observation · trace · **session** |

---

## The gotchas most likely to cost you an afternoon

| Symptom | Cause |
|---|---|
| `langfuse.trace(...)` doesn't exist | You're reading v2 material |
| Auth fails and keys look right | **Region mismatch** — a key is bound to one instance |
| No traces from a short script | Missing **`flush()`** |
| Traces present but no tokens/cost | Model call typed **`span`** instead of `generation` |
| LangChain traces have no sessions/users | Missing the **three reserved metadata keys** (lesson 08 §2) |
| Half your traces lack `user_id` | **`propagate_attributes` called too late** — after work began |
| OTel exporter "succeeds", nothing arrives | **gRPC** — LangFuse needs HTTP |
| OTel spans arrive as generic work | **Attribute-name mismatch** — verify the mapping |
| Self-hosted dashboards return wrong windows | **Not UTC** |

---

## Related material

| Where | What |
|---|---|
| [`../30_langsmith/`](../30_langsmith/) | **The companion folder.** Concepts, the three failure stories, the tracing/monitoring/evaluation split |
| [`../16_evals/`](../16_evals/) | 16 lessons of evaluation **theory** — RAG Triad, G-Eval, judge design. Lesson 11 here is plumbing only |
| [`../../Shared/03_llmops/`](../../Shared/03_llmops/) | LLMOps — gateways, CI eval gates, drift, cost engineering |
| [`../11_langchain/`](../11_langchain/) · [`../12_rag/`](../12_rag/) · [`../13_langgraph/`](../13_langgraph/) | Assumed by lessons 05–08 |
| [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/) | Where observability requirements come from in real designs |

---

## Five things to carry away

1. **LangSmith "run" = LangFuse "observation".** Learn that one substitution and the rest of the model transfers.
2. **Type model calls as `generation`.** A `span` records the call and silently loses tokens and cost.
3. **Sessions are first-class, and often the right unit of analysis** — turn 3's failure was usually caused in turn 1.
4. **Self-hosting changes the question rather than mitigating it** — but check whether a **region** solves your constraint first, because that middle option gets forgotten.
5. **The concepts, failure modes and reading skills are portable across both tools. Not instrumenting is the only unportable mistake.**
