# 13 · Production Concerns, and Choosing Between the Two

> ← [`12-prompt-management.md`](12-prompt-management.md) · **Back to** [`README.md`](README.md)

---

## 1. What carries over unchanged from the LangSmith folder

[`../30_langsmith/17-production-hardening.md`](../30_langsmith/17-production-hardening.md) is largely tool-independent, because the four defaults it warns about are properties of *any* payload-capturing tracer:

| Default | Still true here |
|---|---|
| **Full payloads captured** | ✅ Every prompt, retrieved chunk and completion |
| **100% sampling** | ✅ Fine at low volume, a real cost at scale |
| **Async batched upload** | ✅ Hence `flush()` (lesson 03 §5) |
| **Tracing failures swallowed** | ✅ An observability outage must not break your app — so you are not told |

So the sampling advice transfers verbatim: **sample by interest, not uniformly; never sample out errors; sample by session** (lesson 07 §2 gives the `session_id` hash); **record `sample_rate` in metadata** or every volume you compute later is wrong by an unknown factor.

And the silent-failure safeguards transfer: a **startup assertion** that ingestion works, plus a **traffic-floor alert** — the alert nobody writes, because every other alert fires when something is too *high*, and the symptom of losing instrumentation is silence.

This lesson covers what is **different** for LangFuse.

---

## 2. PII — the calculus genuinely changes

For LangSmith, §1 of that lesson was a warning: full payloads go to a third party, so mask them. Here you have an option that platform did not offer.

### The layers, weakest to strongest

**1. Turn off IO capture** (lesson 05 §4) — per decorator or globally:

```python
@observe(capture_input=False, capture_output=False)
def handle_patient_record(record_text: str, question: str) -> str: ...
```

```bash
LANGFUSE_OBSERVE_DECORATOR_IO_CAPTURE_ENABLED=false
```

Cheap and blunt: you keep structure, timing, tokens and cost; you lose the ability to answer "what did the retriever return?"

**2. Pass handles instead of content** — the architectural fix:

```python
# ❌ record text becomes trace data
def answer(record_text: str, question: str): ...

# ✅ the trace holds a reference; content resolved inside, untraced
def answer(record_id: str, question: str): ...
```

**3. Redact centrally at an OTel collector** (lesson 09 §5) — the one LangSmith cannot do:

```yaml
processors:
  attributes/redact:
    actions:
      - key: gen_ai.prompt
        action: delete
```

> **This is the strongest available *technical* control for a polyglot fleet**, because it is one enforcement point covering every service in every language. Per-SDK masking means N implementations and N chances to miss one.

**4. Self-host** (lesson 04) — the one that changes the question rather than answering it:

> With LangSmith, "can this text go to a vendor?" is a question you must answer *yes* to, then mitigate. **Self-hosted LangFuse means the text never leaves your network**, so full payloads — the maximum diagnostic value — become compatible with the strictest data policy.
>
> That is the single strongest argument for this tool, and it comes with lesson 04's honest bill: four stateful services, ClickHouse expertise, tested restores, and a named owner.

**5. Regional / HIPAA cloud** — the middle option people forget:

`jp.cloud.langfuse.com` or `hipaa.cloud.langfuse.com` satisfies a large share of residency and healthcare requirements **without you running anything.** Before committing to self-hosting, check whether a region solves it — the choice is not binary between "US SaaS" and "our own Kubernetes".

### Metadata discipline, restated because it is the most common self-inflicted leak

`user_id="u_4471"` ✅ · `user_id="nitish@example.com"` ❌

Identifiers, never content. Traces are immutable, so a leak into metadata is permanent for every trace that user generated.

---

## 3. Cost — a different shape

| | LangSmith | LangFuse |
|---|---|---|
| Cloud | Per-trace pricing, tiered, retention affects price | Tiered cloud plans |
| Self-host | Enterprise plan | **No licence cost for the open-source core**; some add-ons need a key |
| **The real self-host cost** | — | **Infrastructure + operations** |

I am not quoting numbers — they move, and a stale figure here would be worse than none. **Check current terms.** But the *shape* of the decision is stable and worth internalising:

```
Cloud cost      ≈ trace volume × per-unit price
Self-host cost  ≈ 4 stateful services
                + ClickHouse operational expertise
                + backup/restore, monitoring, upgrades
                + a named owner's time, ongoing
```

Two consequences:

**At low volume, cloud wins comfortably.** Self-hosting to save a small SaaS bill is a poor trade — you have swapped a line item for on-call burden and hidden the cost.

**At high volume, or under a hard data constraint, self-hosting wins** — and the crossover is a real calculation you should do rather than assume in either direction.

And the levers on both sides are the same as ever: **sampling rate** and **retention**. A low background sample with long retention plus **100% of errors and flagged sessions** is usually the informative-and-affordable combination; sampling everything at long retention is the expensive one that is rarely more useful.

---

## 4. Operational concerns unique to self-hosting

Beyond lesson 04's checklist, three that only appear once it is load-bearing:

**Your observability platform becomes a service you can page for.** When it goes down you lose visibility into everything else — which is precisely when you needed it. Monitor it with something *other than itself*.

**ClickHouse disk growth tracks your app's success.** More users → more traces → more disk, superlinearly if payloads grow too. Set a retention policy *before* you need one, because deleting under pressure is when mistakes happen.

**Upgrades cross two databases.** Schema migrations against Postgres and ClickHouse are not automatic and not trivially reversible. Rehearse on a copy; do not learn the procedure during a version bump you needed for a bug fix.

---

## 5. The decision, honestly

Both tools do the job. Here is how I would actually choose.

### Choose LangSmith when

- You are all-in on **LangChain / LangGraph** and hosted SaaS is acceptable — the integration is genuinely zero-config and the LangGraph story is excellent
- You want the shortest path from nothing to a trace
- You do not want to run infrastructure, and no policy forces you to
- Your team is small and observability ops time is the scarce resource

### Choose LangFuse when

- **Trace payloads cannot leave your infrastructure.** Decisive, and the main reason this tool exists
- You need traces from **Go / Java / Rust / .NET** — via OTLP, which LangSmith has no answer for
- Your platform team **already runs OpenTelemetry** and you want LLM spans in that pipeline
- You want **no vendor dependency** on a load-bearing tool, long-horizon
- **Sessions** are central — multi-turn conversation analysis is first-class here and a convention there
- Trace volume makes per-unit cloud pricing worse than running it

### Genuinely close calls

| Situation | Lean |
|---|---|
| LangChain app, moderate volume, no data constraint | **LangSmith** — the integration depth is real |
| Non-LangChain Python app (raw SDKs, LlamaIndex, custom) | **LangFuse** — no home-framework disadvantage |
| Regulated industry, hosted acceptable with the right region | **LangFuse regional/HIPAA cloud** — the middle option |
| Multi-turn chatbot as the core product | **LangFuse** — sessions |
| You want to learn the concepts | **Either, then the other.** They are 80% the same idea |

> **And the meta-point, which is the real reason both folders exist:** the concepts are portable — trace, span/observation, session, score, dataset, experiment, prompt version. The failure modes are portable: Story A latency, Story B cost, Story C confident wrongness. The reading skills are portable: retrieved documents and assembled prompt are still the two fields that split a RAG diagnosis.
>
> **What is *not* portable is a habit of not instrumenting.** Either tool, used, beats the better tool unused — and a team that runs the loop from [`10-scores-and-user-feedback.md`](10-scores-and-user-feedback.md) §4 (failure → trace → dataset item → CI gate) with the worse tool will beat a team with the better tool that doesn't.

---

## 6. Production checklist

**Data protection**
- [ ] Someone has answered: **is it lawful to send this payload to this destination?**
- [ ] Decision recorded: cloud region · self-host · IO capture off · handles instead of content
- [ ] Collector-level redaction if polyglot (lesson 09 §5)
- [ ] Metadata audited — identifiers only, **no emails, no content**
- [ ] `user_id` is pseudonymous

**Instrumentation correctness**
- [ ] **Startup assertion** that ingestion works
- [ ] **`flush()`** on every short-lived entry point — Lambda, CLI, cron, CI
- [ ] **Traffic-floor alert** — silence is the symptom of lost instrumentation
- [ ] `session_id` and `user_id` set (and the **three reserved keys** if using the LangChain handler — lesson 08 §2)
- [ ] `environment` set, not one project per environment
- [ ] Model calls typed **`generation`**, not `span` — or cost analytics silently under-report

**Volume and cost**
- [ ] Sampling by **interest**, and by **session**; errors never sampled out
- [ ] **`sample_rate` in metadata**
- [ ] Retention chosen deliberately
- [ ] Oversized payloads trimmed

**Closing the loop**
- [ ] **Trace id returned to the client**; feedback endpoint accepts it and is rate-limited
- [ ] `score_id` derived for idempotency
- [ ] Golden dataset exists, including **refusal cases**
- [ ] **CI gated** on `run_experiment`, strictness matched to failure cost
- [ ] Prompts: repo by default; if hosted, **version pinned** and label moves treated as deploys
- [ ] LLM judge **validated against human annotations**

**If self-hosting** (lesson 04)
- [ ] Kubernetes, not Compose
- [ ] **UTC on Postgres and ClickHouse**
- [ ] All `CHANGEME` secrets replaced
- [ ] Backups **and tested restores** for both databases
- [ ] ClickHouse disk growth monitored; retention policy in place
- [ ] Monitored by something other than itself
- [ ] Upgrade rehearsed
- [ ] **A named owner**

---

## Recap

- The four production defaults — full payloads, 100% sampling, async upload, silent failure — are **the same for any tracer**. That advice transfers verbatim.
- **PII is where the calculus differs:** five layers, and **self-hosting changes the question** rather than mitigating it. But check a **region** first — it is the forgotten middle option.
- **Collector-level redaction** is a control LangSmith cannot offer, and the only sane one for a polyglot fleet.
- **Cost shape:** cloud ≈ volume × price; self-host ≈ infrastructure + ClickHouse expertise + a named owner's ongoing time. Low volume favours cloud; a hard data constraint or high volume favours self-hosting. Do the arithmetic.
- **Monitor a self-hosted instance with something other than itself.**
- Choose **LangSmith** for LangChain depth and hosted convenience; **LangFuse** for residency, ownership, polyglot reach and first-class sessions.
- **The concepts, the failure modes and the reading skills are all portable. Not instrumenting is the only unportable mistake.**

---

## Self-check

1. Which PII control is available here and not in LangSmith, and why is it the right one for five languages?
2. What is the middle option between US SaaS and your own Kubernetes?
3. Your colleague wants to self-host to save money at 50k traces/month. What do you say?
4. Name the two levers that set your bill on either platform.
5. Give the one mistake that is worse than picking the wrong tool.

---

**Back to** [`README.md`](README.md)
