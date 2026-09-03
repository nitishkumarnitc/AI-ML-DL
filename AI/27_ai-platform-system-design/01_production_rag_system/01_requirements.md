# 01 · Requirements — Production RAG System

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#1-production-grade-rag-system`](../00_requirements_all_systems.md#1-production-grade-rag-system) fixes the headline scope and NFRs. This file adds the depth a design review needs — the *reasoning* behind each number, not a restatement of it.

---

## 1.1 Problem & users

### What breaks today

An enterprise holds ~10M internal documents across SharePoint, Confluence, and S3. Existing search is
**lexical** — it matches keywords, so it returns *documents that contain your words*, not *answers to
your question*. Three consequences, in the order employees actually feel them:

1. **Rediscovery cost.** An employee asks a colleague rather than searching, because searching costs
   more time than interrupting someone.
2. **Stale answers propagate.** The person asked answers from memory, which may reflect a policy
   revised eighteen months ago.
3. **The corpus decays in value.** Documentation nobody can find stops being maintained, which makes
   it harder to find, which is a self-reinforcing loop.

### Users and their jobs

| User | Job | What "working" means to them |
|---|---|---|
| **Employee (primary)** | Get a correct answer to a question in seconds | The answer is right, *and* they can click through to verify it |
| Content owner | Have their documents actually used | Their edits are searchable within minutes |
| Compliance | Ensure nobody sees what they shouldn't | Retrieval respects document ACLs with zero exceptions |
| Platform team | Operate it without heroics | Bounded cost, observable failures, safe rollbacks |

### The non-obvious requirement

**Attribution is not a feature — it is the product.** An unverifiable answer is *worse than no
answer*, because an answer with no citation still gets trusted, quoted in a customer email, and
repeated in a meeting. The failure is silent and it compounds.

This single observation drives three otherwise-surprising decisions later:
- Citations are a **P0** functional requirement, not a P1 polish item ([FR-2](#12-functional-requirements)).
- The system must **refuse** rather than guess ([FR-5](#12-functional-requirements)).
- **Citation accuracy** gets its own NFR separate from groundedness — a *plausible but wrong* citation
  is the worst possible output, because it manufactures confidence.

> **Mental model:** treat the system as a *research assistant who must show their sources*, not an
> oracle.
>
> *Where the analogy breaks:* a human assistant knows when they're out of their depth and says so
> unprompted. An LLM's confidence is uncorrelated with its correctness, so "knowing when to refuse"
> has to be engineered in ([FR-5](#12-functional-requirements)) rather than assumed.

---

## 1.2 Functional requirements

Prioritized **P0** (v1 is unusable without it) / **P1** (needed for production launch) / **P2**
(explicitly deferrable). Every requirement has a testable acceptance criterion — *"the system should
be accurate"* is not a requirement, because nothing can falsify it.

### Retrieval & answering

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | Answer a natural-language question using only corpus content | Groundedness ≥ 0.95 on the 200-case golden set |
| **FR-2** | P0 | Attach **inline citations** resolvable to a source passage | ≥ 90% of factual claims carry a citation that resolves to a chunk containing that claim |
| **FR-5** | P0 | **Refuse when retrieval is insufficient** | On the 30-case unanswerable set, ≥ 95% produce an explicit "not found in the documents" rather than an answer |
| FR-7 | P1 | Stream the answer token-by-token | TTFT within the [§1.5](#15-latency-budget) budget |
| FR-10 | P2 | Multi-turn follow-ups with query rewriting | Resolves pronouns/ellipsis against the prior 3 turns |

**Why FR-5 is P0 and not P1.** A RAG system that always answers is a hallucination engine with extra
steps. The refusal path is *harder* to build than the answer path (it requires calibrated confidence
in retrieval sufficiency), and teams that defer it never come back to it.

### Ingestion

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-3** | P0 | Ingest PDF, DOCX, HTML, Markdown, plain text | ≥ 99% parse success on a 10k-doc stratified corpus sample |
| FR-6 | P1 | Incremental re-ingest on source change | New/changed document searchable < 5 min (p95) |
| **FR-9** | P1 | Hard-delete a document from index, caches, and object store | Fully purged < 15 min, verified by a search returning zero hits |

**FR-9 is a legal requirement wearing engineering clothes.** GDPR right-to-erasure means a deletion
that removes the row but leaves the vector in an HNSW graph, or the text in a semantic cache entry,
is **non-compliance**. Caches make this genuinely hard — see [§3.6](03_lld.md#36-edge-cases--correctness).

### Access control

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-4** | P0 | Enforce per-user document ACLs **at query time** | Zero cross-permission leaks across the 500-case ACL suite |

**Why "at query time" is load-bearing.** ACLs change constantly — someone leaves a project on Tuesday
and their access should vanish on Tuesday. Baking permissions into the index at ingestion time means
every ACL change requires a reindex, which is both infeasible at 80M chunks and a guaranteed source
of stale-permission leaks.

### Evaluation & feedback

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-8 | P1 | Offline eval suite wired into CI as a **regression gate** | Blocks deploy on > 3-point drop in any tier-1 metric |
| FR-11 | P2 | Feedback capture (👍/👎) feeding the golden set | Thumbs-down conversations reviewable and promotable to test cases |

**The 3-point threshold is a deliberate compromise.** Tighter (1 point) and normal LLM-judge variance
blocks every deploy, teams disable the gate, and you have no gate. Looser (10 points) and real
regressions ship. 3 points sits above the judge's measured noise floor while catching genuine
degradation — and it presumes the judge is stabilized ([§4.1](04_production_and_interview.md#41-ai-specific-concerns)).

---

## 1.3 Non-functional requirements

Every target carries a **percentile where applicable** and the *reason* for the number. A latency
target without a percentile is not a target.

### Latency

| NFR | Target | Why this number |
|---|---|---|
| **TTFT** | p95 < 1.5 s | Users tolerate ~2 s of silence before perceiving a hang; 1.5 s leaves margin for network variance |
| **E2E answer** | p95 < 6 s | Enough for a ~400-token grounded answer at typical streaming rates |
| Ingestion freshness | p95 < 5 min from source change to searchable | Contractual promise to content owners |
| Deletion | p95 < 15 min to fully purged | Legal (FR-9); 15 min is defensible as "prompt" |

**TTFT is the metric that matters, not E2E.** With streaming, perceived responsiveness is governed
almost entirely by time-to-first-token; a 6-second full answer feels fast if the first word lands in
1 second. Optimizing E2E at the expense of TTFT would be optimizing the wrong number.

### Throughput & scale

| NFR | Target | Derivation |
|---|---|---|
| Sustained throughput | 50 QPS | 5k daily-active employees × ~8 queries/day ÷ 8-hour workday ≈ 1.4 QPS avg — **50 QPS is deliberately overprovisioned** for burst |
| Peak throughput | 200 QPS | 4× sustained, from the observed diurnal pattern (Monday 09:00 spike) |
| Corpus | 10M docs / ~80M chunks | Sizing driver for the retrieval tier ([§1.6](#16-capacity--cost-estimation)) |
| Tenants | 5k | Multi-tenant isolation driver |

> **⚠️ An assumption worth surfacing early.** The 130M-queries/month figure that drives the cost model
> in [§1.6](#16-capacity--cost-estimation) comes from 50 QPS *sustained around the clock*, which is
> not what 5k employees generate. Realistic engagement is likely **5–10× lower**. I keep the high
> number for capacity planning (you must survive peak) but flag it explicitly for the cost model,
> because using a peak-derived number for cost is how budgets get overstated by an order of magnitude.
> This is assumption **A5** in [§1.7](#17-assumptions--open-questions).

### Quality

| NFR | Target | Why this number |
|---|---|---|
| **Retrieval recall@20** | ≥ 0.90 | **The hard ceiling on the whole system** — the generator cannot answer from a chunk that was never retrieved |
| Groundedness | ≥ 0.95 | Below this, users encounter unsupported claims often enough to stop trusting the tool |
| **Citation accuracy** | ≥ 0.90 | A citation pointing at the wrong passage is worse than no citation — it manufactures false confidence |
| Answer relevance | ≥ 0.90 | Guards against faithful-but-off-topic answers |
| Refusal precision | ≥ 0.95 on the unanswerable set | Over-refusing is annoying; under-refusing is dangerous |

**Why recall@20 and not recall@8.** The reranker sees 50 candidates and selects 8. Recall must be
measured at the *retriever's* output (top-50 → measured at 20 as a practical proxy), not the
reranker's, because a chunk missing from the candidate set is unrecoverable no matter how good the
reranker is. Measuring recall@8 would conflate two independent failure modes.

### Cost, availability, security

| NFR | Target | Why |
|---|---|---|
| Cost | ≤ $0.02/query · ≤ $8k/month | Business-set unit-economics ceiling — **shown to be unsatisfiable in [§1.6](#16-capacity--cost-estimation)** |
| Availability | 99.9% (≈43 min/month) | Internal tool; **and ceilinged by the LLM provider's own SLA regardless of our engineering** |
| Tenant + ACL isolation | Filter pushed **into** the ANN query | Post-filtering both leaks and silently destroys recall — see below |
| PII | Redacted before egress to third-party providers | Policy |
| Audit | Query + retrieved chunk IDs retained 1 yr | Investigate "why did it say that?" |

**Why post-filtering is a correctness bug, not just a performance issue.** If you retrieve top-50 by
similarity and *then* drop the ones the user can't see, a user with narrow permissions may be left
with 3 chunks — or zero — while the chunks they *could* have seen sat at ranks 51–100 and were never
considered. Recall silently degrades as a function of how restricted the user is, and it degrades
most for the users with the least access. The filter must be a predicate **inside** the search.

---

## 1.4 Non-goals

Stated as scoping, not omission. Each pre-empts a "but what about…" and names what would change.

| Out of scope | Why | What would bring it in |
|---|---|---|
| Model training / fine-tuning | We consume hosted models; fine-tuning a retriever is a large separate project with its own eval loop | Domain retrieval quality plateaus below the recall target despite chunking and reranking work |
| Multi-modal input (images, audio) | Text-only v1; image understanding needs a different embedding stack and eval harness | Scanned-document volume becomes material — routes to [`../05_document_intelligence/`](../00_requirements_all_systems.md#5-large-scale-document-intelligence-system) |
| Writing back to source systems | Read-only removes an entire class of authorization and conflict problems | A confirmed use case for agent-driven edits — routes to [`../10_enterprise_agent_platform/`](../00_requirements_all_systems.md#10-enterprise-ai-agent-platform) |
| Cross-lingual retrieval | English-only corpus in v1 | Non-English document share exceeds ~5% |
| Real-time collaborative editing | Not a search concern | — |
| Self-hosting the LLM | Adds GPU operations for no v1 benefit | Cost or data-residency forces it — see [`../04_llm_inference_platform/`](../00_requirements_all_systems.md#4-llm-inference-platform), which shows self-hosting is **~10× more expensive** at small-model scale |

---

## 1.5 Latency budget

The SLO is p95 TTFT < 1.5 s. **A budget that doesn't sum to the SLO is the most common quantitative
error in AI system design**, so the arithmetic is explicit.

### Cache-miss path (the path that must fit)

| # | Stage | Budget (p95) | Notes |
|---|---|---:|---|
| 1 | Auth + request validation | 20 ms | JWT verify against cached JWKS; no DB round trip |
| 2 | Semantic cache lookup | 30 ms | Embed-and-search against a small cache index; short-circuits everything below on hit |
| 3 | ACL resolution | *0 ms* | **Overlapped** with step 4 — see note |
| 4 | Query embedding | 60 ms | Small embedding model, single item (no batching benefit on the read path) |
| 5 | Vector search, top-50, ACL-filtered | 120 ms | HNSW with `tenant_id` + ACL + `embed_version` predicates |
| 6 | Cross-encoder rerank 50 → 8 | 180 ms | GPU-served, batch of 50 pairs |
| 7 | Prompt assembly | 20 ms | Template fill + context packing + token counting |
| 8 | **LLM TTFT** | **900 ms** | Frontier tier, ~1.8k-token prompt. **60% of the entire budget** |
| 9 | Output guardrail | *0 ms* | **Overlapped** with streaming generation |
| | **Total** | **≈ 1,330 ms** | vs 1,500 ms SLO → **~170 ms headroom** ✅ |

**Two stages are overlapped, and that's a real design decision, not budget arithmetic sleight of
hand:**

- **ACL resolution (3)** runs concurrently with query embedding (4). Both take ~60 ms and neither
  depends on the other, so running them in parallel is free. If ACLs required a per-document service
  call instead of a cached filter expression, this becomes serial and the budget breaks — assumption
  **A3** in [§1.7](#17-assumptions--open-questions).
- **Output guardrail (9)** scans tokens as they stream rather than buffering the full answer. Buffering
  would add ~100 ms to TTFT *and* defeat streaming entirely. The trade-off: a violating token can
  reach the user before detection, so the guardrail can only *truncate mid-stream*, not prevent. For
  an internal tool over an internal corpus that's acceptable; for a customer-facing product it may
  not be.

### Cache-hit path

| Stage | Budget |
|---|---:|
| Auth + validation | 20 ms |
| Semantic cache hit | 30 ms |
| **Total** | **≈ 50 ms** |

**~27× faster than the miss path.** This is why the cache sits *before* the orchestrator rather than
inside it, and why its hit rate dominates the cost model in [§1.6](#16-capacity--cost-estimation).

### Where the budget is fragile

| Risk | Impact | Mitigation |
|---|---|---|
| LLM TTFT variance (provider-side) | It's 60% of budget; a p99 spike to 2 s blows the SLO outright | Provider fallback on timeout; TTFT alerting; consider the small tier for simple queries (which routing already does for cost) |
| Reranker under load | Queueing pushes 180 ms → 400 ms+ | Autoscale on queue depth; **degrade by skipping rerank** and taking ANN top-8 directly, accepting the precision loss |
| Long context | Higher LLM TTFT | Hard cap on packed context tokens ([§3.3](03_lld.md#33-core-algorithms)) |

---

## 1.6 Capacity & cost estimation

Arithmetic shown; every assumption labelled. Rates are the **assumed** figures from
[`../00_requirements_all_systems.md#cost-baseline-used-throughout`](../00_requirements_all_systems.md#shared-conventions) —
verify against current provider pricing before quoting any of this.

### Traffic

```
Sustained:  50 QPS  → 50 × 86,400        ≈ 4.3M requests/day  ≈ 130M/month
Peak:      200 QPS  → sizing the serving tier, not the cost model

⚠️  See assumption A5: 130M/month derives from 50 QPS around the clock, which 5k
    employees do not generate. Realistic engagement is likely 5–10× lower.
    Capacity planning uses the high number; the cost conversation must not.
```

### Token cost — the naive design

```
Tokens per request  (assumption A1: measured from a prototype)
  input   1,800   =  1,200 system prompt + 8 chunks × ~75 tokens
  output    400

Frontier tier ($3.00 in / $15.00 out per 1M):
  input:   1,800/1e6 × $3.00  = $0.0054
  output:    400/1e6 × $15.00 = $0.0060
  per query                   ≈ $0.0114

Monthly: 130M × $0.0114 ≈ $1,482,000/month
Ceiling:                     $8,000/month
                             ────────────
                             185× OVER  ⇒ REDESIGN REQUIRED
```

**This is the single most valuable output of the requirements phase.** A design that draws a clean
architecture without running this number is confidently wrong.

### Optimization levers, cheapest-to-implement first

| # | Lever | Mechanism | Assumed effect | Running total |
|---|---|---|---:|---:|
| 0 | *(naive)* | — | — | $1,482k |
| 1 | **Prompt caching** | 1,200 of 1,800 input tokens are a static system prompt; providers cache repeated prefixes at ~10% of input rate | input −55% | ~$1,085k |
| 2 | **Semantic cache** | ~30% of queries are near-duplicates of a recent query (assumption A2) | total −30% | ~$760k |
| 3 | **Model routing** | Route ~70% of queries to the small tier at 1/20th the price (assumption A4) | blended −80% | ~$152k |
| 4 | **Context trimming** | Better reranking → 5 chunks instead of 8 | input −25% | ~$124k |
| 5 | **Output cap** | Cap answers at 250 tokens | output −38% | ~$95k |

**Result: ~$95k/month — still ~12× over the $8k ceiling.**

### The honest conclusion

**The stated requirements are mutually unsatisfiable.** Rather than pretend otherwise, three options
go back to the business:

| Option | What it means | Trade-off |
|---|---|---|
| **1. Raise the ceiling to ~$100k/month** | ≈ $0.0008/query — defensible for a tool serving 5k employees at ~$20/employee/month | Needs budget approval; compare against the loaded cost of the time it saves |
| **2. Revisit the traffic assumption** | If real usage is 8 queries/day/employee (≈13M/month, not 130M), cost lands ≈ **$9.5k** — **inside budget** | Requires measuring actual demand; run a pilot before committing to capacity |
| **3. Self-host the simple tier** | Serve the 70% small-tier traffic on own GPUs | Trades API cost for GPU + operations cost — and [`../04`](../00_requirements_all_systems.md#4-llm-inference-platform) shows this is **~10× worse** at small-model scale unless utilization exceeds ~80% with reserved pricing |

> **Recommendation: option 2 first, then option 1.** The traffic number is an assumption, not a
> measurement, and it's the single largest term in the model. Measuring it costs a two-week pilot;
> being wrong about it costs an order of magnitude. **Measure before you optimize, and optimize before
> you procure.**

### Storage & memory sizing

```
Chunks:  10M docs × 8 chunks/doc = 80M chunks     (assumption A1)

Embeddings @ 1,024 dimensions:
  float32:  80M × 1,024 × 4 B = 327 GB    ← the wrong default at this scale
  int8:     80M × 1,024 × 1 B =  82 GB    ← quantize; ~1-2% recall loss, acceptable vs the 4× saving
  + HNSW graph overhead ~40%              ≈ 115 GB
  ⇒ budget ~128 GB RAM, or disk-backed IVF if that's unavailable

Raw text:      80M × ~300 B ≈  24 GB   (object store — cheap, keep it)
Metadata rows: 80M × ~200 B ≈  16 GB   (Postgres)
Cache index:   ~1M entries × 1,024 × 4 B ≈ 4 GB  (small; keep float32 for cache precision)
```

**The int8 decision is the interesting one.** 4× memory reduction for ~1–2% recall loss is
straightforwardly worth it at 80M vectors — the alternative is a machine class that costs several
times more, or the operational complexity of disk-backed indexing. **It would be the wrong call at
1M vectors**, where 4 GB vs 16 GB is immaterial and you should keep the precision.

### Ingestion capacity

```
Initial backfill:  10M docs
  Parse:  assume 20 docs/s/worker → 10M/20 = 500k worker-seconds = 139 worker-hours
          at 20 workers ≈ 7 hours
  Embed:  80M chunks, batch 256, assume 40ms/batch → 312k batches × 0.04s ≈ 3.5 hours
          at 4 parallel embedders ≈ 52 min
  Index:  HNSW build on 80M vectors — HOURS, and the real constraint
  ⇒ Initial backfill is an overnight job, not a deploy step. Plan it as such.

Steady state:  assume 1% of corpus changes/day = 100k docs/day ≈ 1.2 docs/s
  Trivially within a single worker's capacity ⇒ size ingestion for BACKFILL, not steady state.
```

**Design consequence:** ingestion is sized by the one-time backfill and by *reindex* events, not by
daily churn. Since reindexing is unavoidable (new embedding model, changed chunking), it must be a
**routine, rehearsed operation** rather than an emergency — hence blue/green indexing in
[§2.5](02_hld.md#25-failure-modes--blast-radius).

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | 8 chunks/doc, ~1,800 input / 400 output tokens | Medium — prototype-measured | Cost and storage scale ~linearly; re-measure on the real corpus |
| **A2** | 30% semantic-cache hit rate | **Low** — no production data | Cost model degrades ~linearly. Measure on real traffic before relying on it |
| **A3** | ACLs resolve to a filter expression at query time | Medium | If a per-document service call is needed, the [§1.5](#15-latency-budget) overlap breaks and the budget fails ⇒ requires a denormalized ACL cache |
| **A4** | 70% of queries answerable by the small tier | **Low** | The largest single lever in the cost model. If it's 40%, cost roughly doubles |
| **A5** | 130M queries/month | **Low — likely wrong high** | Directly proportional; see option 2 in [§1.6](#16-capacity--cost-estimation). **The highest-value number to measure** |
| A6 | Documents are mostly text-extractable | Medium | Scanned PDFs push work into an OCR pipeline (a different system) |
| A7 | int8 quantization costs ≤ 2% recall | Medium — published benchmarks | Revert to float32 and pay for larger instances |

**Ranked by value-of-information: A5 > A4 > A2.** All three are low-confidence and all three move cost
by multiples. A5 is measurable with a two-week pilot; A4 and A2 need production traffic. **This
ranking is what to say when asked "what would you measure first?"**

### Open questions

| # | Question | Why it blocks | Who owns it |
|---|---|---|---|
| **Q1** | Are stale answers acceptable during a reindex? | Determines dual-write vs. blue/green cutover — materially different complexity | Product |
| **Q2** | Is the 5-min freshness SLA per-document or per-source-sync? | Changes ingestion batching strategy | Content owners |
| **Q3** | What is the actual query volume? | The largest term in the cost model (A5) | Product — **resolve first** |
| **Q4** | Can ACLs be denormalized into the index, or must they be live? | Decides whether the latency budget holds (A3) | Security |
| **Q5** | Is a third-party LLM provider permitted to see corpus content? | If not, self-hosting becomes mandatory and the whole cost model changes | Legal / Security |

**Q5 is the one that could invalidate the design.** It's listed last but should be asked first — a
"no" moves this from a RAG design into a RAG-plus-inference-platform design and roughly triples the
scope. **In an interview, asking this early is a strong signal.**

---

**Next:** [02_hld.md →](02_hld.md) — architecture, component choices with rejected alternatives, failure modes, and the 10×/100× scale plan.
