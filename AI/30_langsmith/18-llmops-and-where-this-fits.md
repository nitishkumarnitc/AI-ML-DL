# 18 · LLMOps: Where All of This Fits

> ← [`17-production-hardening.md`](17-production-hardening.md) · **Back to** [`README.md`](README.md)

---

## The umbrella term

Everything after lesson 12 — monitoring, alerting, evaluation, prompt experimentation, datasets and annotation, user feedback, collaboration — sits under one heading:

> **LLMOps.** And it is becoming a specialised role in its own right.

The video's closing line is the honest summary of why the field exists:

> *Making it is one thing. Running it in production effectively, without problems, is a whole different game.*

Which is the same realisation that produced MLOps a decade ago, and DevOps before that: **the build is a fraction of the lifecycle, and the rest of the lifecycle needs its own discipline and its own tools.**

---

## The full surface, and what covers it

The video's own framing: everything read about here is *one perspective* on LangSmith — observability — and the rest are further aspects of the same platform.

| Capability | Lesson | Question it answers |
|---|---|---|
| **Observability / tracing** | 05–12 | *Why did **this** execution behave this way?* |
| **Monitoring & alerting** | 13 | *Is the system healthy, and tell me when it isn't* |
| **Evaluation** | 14 | *Is the output any **good**? Is the new version better?* |
| **Datasets & annotation** | 14 | *What do we measure against?* |
| **Prompt experimentation** | 15 | *Which prompt is better, on evidence?* |
| **User feedback** | 16 | *What do real users think?* |
| **Collaboration** | 16 | *How does a team debug this together?* |
| **Production hardening** | 17 | *What breaks when real data and real volume arrive?* |

---

## The three axes, and why you need all three

The mistake most teams make is buying one axis and assuming it covers the others. It doesn't — they detect **different failures**:

| Axis | Detects | Misses |
|---|---|---|
| **Observability** — one trace, deep | Why a known-bad execution went wrong | That anything is wrong at all |
| **Monitoring** — many traces, mechanical | Latency, cost, error-rate drift | Whether answers are **correct** |
| **Evaluation** — outputs vs expectations | Quality and regressions | Mechanical problems; needs a dataset to exist |

Map them back to lesson 01:

| Story | Symptom | Which axis catches it |
|---|---|---|
| **A** Cover letter | 2 min → 9 min | **Monitoring** raises it (p95 alert); **observability** localises it (stage 2) |
| **B** Research agent | 50 p → ₹2 on some runs | **Monitoring** raises it (cost-per-trace, iteration count); **observability** localises it (the loop) |
| **C** HR chatbot | Confidently wrong | **Neither.** Fast, cheap, error-free. Only **evaluation** and **user feedback** catch it |

> **Story C is the one to remember.** A confidently-wrong system is *invisible* to every mechanical metric. If you install tracing and monitoring and stop there, you have covered two of the three failure classes and left the most damaging one — the one that spreads misinformation with your team's name on it — entirely undetected.

---

## The maturity ladder

*Added, as a practical sequencing guide. Do these in order; each rung is cheap once the one below it exists.*

| Level | What you have | Cost to reach | You can now |
|---|---|---|---|
| **0** | `print()` statements | — | Nothing at scale |
| **1** | **Tracing on**, project per app | An afternoon | Debug any reported failure |
| **2** | + `run_name`, tags, metadata (`env`, `git_sha`, `prompt_version`, `tenant`, `session_id`) | A day | Filter, group, compare; answer *"is it one customer or everyone?"* |
| **3** | + Monitoring dashboards and **percentile alerts**, incl. a **traffic floor** | A day | Learn about A and B before your users do |
| **4** | + **Golden dataset** grown from real failing traces; offline eval | A week, then continuous | Catch quality regressions **before deploy**. Story C becomes detectable |
| **5** | + **CI gated** on evaluation | Days | Story C cannot reach production twice |
| **6** | + **User feedback** wired to `run_id`, feeding the dataset | Days | The loop closes: users report once, it stays fixed |
| **7** | + Online evaluation, prompt experimentation as routine, hardening (lesson 17) | Ongoing | Operate deliberately rather than reactively |

Two observations from the shape of that table:

**Level 2 is the highest-leverage rung and the most commonly skipped.** It costs a day and it is what makes every later level possible — you cannot group by `prompt_version` in production if you never wrote it, and you cannot add it retroactively because traces are immutable (lesson 06).

**Level 4 is where most teams stall**, because it needs a dataset and building one feels like a project. It isn't: `Add to Dataset` on ten real failing traces (lesson 14) is level 4 by Friday. The dataset doesn't need to be big; it needs to contain **your actual failures**.

---

## Related material in this repo

| Where | What it adds |
|---|---|
| [`AI/16_evals/`](../16_evals/) | **Sixteen lessons on evaluation.** RAG Triad, G-Eval, LLM-as-judge, offline vs online, operational evals (latency/cost/reliability), benchmark saturation. The theory behind lesson 14 |
| [`Shared/03_llmops/`](../../Shared/03_llmops/) | The LLMOps discipline: gateways, CI with eval gates, drift, cost engineering, incident response |
| [`Shared/03_llmops/05-observability-and-tracing.md`](../../Shared/03_llmops/05-observability-and-tracing.md) | Tracing from the platform side, vendor-neutral |
| [`Shared/02_mlops/`](../../Shared/02_mlops/) | Classical MLOps — the lineage LLMOps inherits from |
| [`AI/13_langgraph/`](../13_langgraph/) | LangGraph itself. Lesson 12 assumes it |
| [`AI/13_langgraph/16_langsmith-crash-course.md`](../13_langgraph/16_langsmith-crash-course.md) | **The single-file summary of this same video**, as playlist notes. Use it as a revision sheet; use this folder to learn from |
| [`AI/11_langchain/`](../11_langchain/) | LangChain fundamentals — runnables, chains, RAG |
| [`AI/12_rag/`](../12_rag/) | RAG in depth. Lessons 07–10 assume it |
| [`AI/28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/) | Where observability requirements come from in real system design |

---

## The five things worth carrying out of this tutorial

1. **LLM systems are non-deterministic, multi-stage, and fail behaviourally rather than exceptionally.** Every conventional debugging instinct assumes properties they don't have. That is the whole reason this tool category exists.

2. **Project → Trace → Run.** Underneath, only runs, forming a tree whose root is the trace. `parent_run_id` decides nesting, and nesting is decided by the **call stack at runtime** — which is why lesson 09's problem happens and how it's fixed.

3. **Tag and structure at write time.** Traces are immutable. Every metadata key you skip is an incident question you won't be able to answer, and you cannot go back and add it.

4. **Mechanical health is not correctness.** Story C is fast, cheap and error-free while telling employees there is no leave policy. Monitoring cannot see it. Only **evaluation** and **user feedback** can — which is why "observability *and* evaluation" is the product's actual shape, not a marketing pairing.

5. **The loop is the product.** Trace a failure → promote it to a dataset row → gate CI on it → ship → watch feedback → repeat. Every individual feature in LangSmith is in service of that loop, and a team that runs the loop with worse tools beats a team with better tools that doesn't.

---

**Back to** [`README.md`](README.md)
