# 01 · Why LangFuse, and How It Differs from LangSmith

> **Sourcing note:** this folder is written from the **official LangFuse documentation**, read September 2026, against **Python SDK v4**. It is not transcript-derived like [`../30_langsmith/`](../30_langsmith/). Where I could not confirm something from the docs, it says so rather than guessing.
>
> **Prerequisite:** [`../30_langsmith/01-why-llm-observability.md`](../30_langsmith/01-why-llm-observability.md) through [`04-project-trace-run.md`](../30_langsmith/04-project-trace-run.md). **This folder does not re-argue why LLM observability is necessary** — that case is made there with the three failure stories, and it is tool-independent. Start here only if you already accept the premise.
>
> **Next:** [`02-core-concepts-and-data-model.md`](02-core-concepts-and-data-model.md) →

---

## The one-line positioning

> **LangFuse is an open-source, self-hostable LLM observability and evaluation platform, built on OpenTelemetry.**

Every word in that sentence is a differentiator from LangSmith, and each one decides a real case.

---

## 1. The three differences that actually matter

### Difference 1 — you can run it yourself

This is the headline and it is the reason most teams end up here.

LangSmith is a hosted service. There is a self-hosted option on its enterprise plan, but the default and the assumption is that your traces — **which contain your full prompts, retrieved documents and completions** — go to a vendor.

LangFuse's default is that you *can* keep them. The core is open source, and a self-hosted deployment is a documented, supported first-class path rather than an enterprise escape hatch.

Recall the four rows from [`../30_langsmith/17-production-hardening.md`](../30_langsmith/17-production-hardening.md):

| Application | What lands in a trace |
|---|---|
| HR policy chatbot | Employee questions about their own salary, notice period, medical leave |
| Support assistant | Customer names, emails, order numbers, complaint text |
| Clinical / insurance assistant | Health information |
| Document RAG | **The full text of every retrieved chunk** |

If your answer to *"can this text go to a third-party SaaS?"* is a hard no — because of GDPR, DPDP, HIPAA, a customer DPA, or an internal policy — then the LangSmith chapter's masking advice is damage limitation, and **self-hosting is the actual answer.** That is the case LangFuse exists for.

### Difference 2 — it is an OpenTelemetry backend

LangSmith's tracing is implemented as a **LangChain callback handler** (see [`../30_langsmith/02-what-langsmith-is-and-what-it-records.md`](../30_langsmith/02-what-langsmith-is-and-what-it-records.md) §Beyond). That makes it superb inside LangChain and progressively more manual outside it.

LangFuse instead **receives OTLP** on a public endpoint and maps incoming OpenTelemetry spans onto its own data model. Two consequences:

| Consequence | Why it matters |
|---|---|
| **Any OTel-instrumented app can send traces** | Including Go, Java, Rust, .NET — languages with no LangFuse SDK at all |
| **It composes with tracing you already run** | If your platform team already runs OTel collectors, LLM spans become one more signal rather than a parallel stack |

The Python SDK is itself built on OpenTelemetry — the docs are explicit that *"the Python SDK automatically sets up OpenTelemetry when initializing the client"* and that its spans are **native OTel spans** wrapped with LangFuse conveniences for scoring and media. So the SDK is not a separate mechanism bolted next to OTel; it *is* OTel. Lesson 09 covers this.

### Difference 3 — framework-neutral by construction

LangSmith is built by the LangChain team, and the coupling is deliberate and valuable: zero-config tracing for LangChain, and the two-rule LangGraph integration from [`../30_langsmith/12-tracing-langgraph.md`](../30_langsmith/12-tracing-langgraph.md).

LangFuse integrates with LangChain and LangGraph too (lesson 08), but it has no home framework. If your stack is raw provider SDKs, LlamaIndex, Pydantic AI, DSPy, a mix, or something you wrote, LangFuse does not treat you as the non-default path.

---

## 2. The honest comparison

Both tools do the same *job*. Choosing between them is about constraints, not features.

| | **LangSmith** | **LangFuse** |
|---|---|---|
| **Licence** | Proprietary, hosted | **Open source core**, self-hostable |
| **Self-hosting** | Enterprise plan | **Documented default path** |
| **Tracing mechanism** | LangChain callbacks | **OTLP / OpenTelemetry** |
| **Framework affinity** | LangChain / LangGraph — best-in-class | Neutral |
| **Language reach** | Python, JS/TS | Python, JS/TS, **+ any OTel language** |
| **Zero-config on LangChain** | ✅ env vars only | Callback handler — one line |
| **Prompt management** | ✅ + LangChain Hub | ✅ with labels, caching, fallback |
| **Datasets / experiments** | ✅ | ✅ `run_experiment` |
| **LLM-as-a-judge** | ✅ | ✅ |
| **Annotation queues** | ✅ | ✅ |
| **Sessions (multi-turn)** | Via metadata convention | **First-class `session_id`** |
| **Data residency** | US / EU cloud | US / EU / **JP / HIPAA** cloud, or **your own hardware** |

### Picking one

| If… | Pick |
|---|---|
| You are all-in on LangChain/LangGraph and hosted SaaS is fine | **LangSmith.** The integration depth is real and you should use it |
| Trace payloads cannot leave your infrastructure | **LangFuse, self-hosted.** This is not close |
| You need traces from Go / Java / Rust services | **LangFuse.** Via OTLP |
| Your platform team already runs OpenTelemetry | **LangFuse.** It composes instead of duplicating |
| You want to own the tool long-term with no vendor risk | **LangFuse.** Open source is the whole argument |
| You want the shortest path from zero to a trace on a LangChain app | **LangSmith** by a small margin — env vars vs one callback |

> **And the case for learning both, which is why this folder sits next to the other one:** the *concepts* are portable — trace, span/observation, session, score, dataset, experiment. The vendor is a detail. Having implemented the same instrumentation twice against two data models is the fastest way to see which parts of your understanding were about observability and which were about LangSmith.

---

## 3. ⭐ The version trap — read this before any tutorial you find online

The single most likely thing to waste your afternoon.

**The LangFuse Python SDK has changed API surface across major versions**, and a large share of blog posts, videos and Stack Overflow answers are written against **v2**, which looks nothing like current code.

| Era | Shape of the code |
|---|---|
| **v2** | Explicit object graph — `langfuse.trace(...)` returns a trace, `trace.generation(...)` returns a generation, you thread and `.end()` them by hand |
| **v3** | OpenTelemetry-based rewrite; context managers; `langfuse.start_as_current_span(...)` |
| **v4** (current, this folder) | `get_client()` singleton · `start_as_current_observation(as_type=...)` · `propagate_attributes()` · `run_experiment()` |

Three symptoms of following v2 material against a v4 install:

- `langfuse.trace(...)` — the method is not there
- Manual `trace_id` threading everywhere — v4 propagates via OTel context
- `LANGFUSE_HOST` in the `.env` — the current variable is **`LANGFUSE_BASE_URL`**

**Check the version before trusting any example**, including this folder:

```bash
pip show langfuse | grep -i version
```

Everything here is written against **v4** and the doc pages linked per lesson. Where the docs themselves were ambiguous, the lesson says so instead of inventing a signature.

---

## 4. What this folder covers, and what it deliberately doesn't

**Covers:** the LangFuse data model and how it maps onto LangSmith vocabulary · setup on cloud and self-hosted · `@observe` · manual observations · sessions and users · LangChain/LangGraph · OTLP from any language · scores and feedback · datasets and experiments · prompt management · production concerns.

**Deliberately doesn't:**

- **Re-argue why observability matters.** [`../30_langsmith/01`](../30_langsmith/01-why-llm-observability.md) does it, tool-independently, and repeating it would drift out of sync.
- **Re-teach evaluation theory.** [`../16_evals/`](../16_evals/) is sixteen lessons on RAG Triad, G-Eval, LLM-as-judge and offline vs online. Lesson 11 here is the *platform mechanics* only.
- **Quote pricing.** Cloud tiers and per-unit prices move; self-hosting is free of licence cost for the open-source core with some add-ons gated behind a key. **Check current terms** — I am not putting a number here that will be wrong by the time you read it.
- **Claim a definitive OSS-vs-Enterprise feature split.** The docs mark some features "(EE)" and note that *"some add-on features require a license key"*, but the overview page I read does not enumerate them. Verify against the licensing page for anything you intend to depend on.

---

## Recap

- **Open source · self-hostable · OpenTelemetry-based · framework-neutral.** Four words, four differentiators.
- **Self-hosting is the real answer** when trace payloads cannot leave your infrastructure — masking is damage limitation.
- **OTLP ingestion** means any OTel-instrumented app in any language can send traces, and LLM spans compose with tracing you already run.
- The choice between LangSmith and LangFuse is about **constraints, not features**: framework depth and hosted convenience vs ownership, residency and language reach.
- **The concepts are portable.** Learn them once; the vendor is a detail.
- **Mind the SDK version.** Most material online is v2 and will not run. This folder is v4.

---

## Self-check

1. Your RAG corpus is customer support tickets containing names and order numbers. Which tool, and why is masking not a sufficient answer?
2. What does "LangFuse is an OpenTelemetry backend" let you do that a callback-based tracer cannot?
3. Give one case where LangSmith is the better pick, and defend it.
4. You find a tutorial using `langfuse.trace(...)`. What has gone wrong and how do you check?

---

**Next:** [`02-core-concepts-and-data-model.md`](02-core-concepts-and-data-model.md) →
