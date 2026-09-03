# 04 · Production & Interview — Production RAG System

> **Phase 4 of 4** · [← LLD](03_lld.md) · [README](README.md)
> The section that separates an **AI** system design from a generic backend design, plus the operational and interview material.

---

## 4.1 AI-specific concerns

A correct-looking architecture that ignores these is incomplete. Each row states the mechanism, not the aspiration.

### Token cost

Fully worked in [§1.6](01_requirements.md#16-capacity--cost-estimation). The operational summary:

| Lever | Mechanism | Where it lives |
|---|---|---|
| Prompt caching | Static 1,200-token system prefix cached provider-side | Prompt assembly |
| Semantic cache | ~30% near-duplicate hit rate | Before the orchestrator ([§2.1](02_hld.md#21-architecture)) |
| Model routing | ~70% to small tier | [`route()`](03_lld.md#complexity-routing) |
| Context trimming | 8 → 5 chunks via better reranking | `max_context_tokens` |
| Output cap | 250 tokens | Request parameter |
| **Cancellation propagation** | Abort provider call on client disconnect | [E12](03_lld.md#full-edge-case-register) |

**Per-tenant attribution is mandatory, not optional.** Without `cost_usd` on every trace row keyed by
`tenant_id`, you cannot answer "which team is spending the money?" — and at a bill in the tens of
thousands per month, that question arrives within the first week.

### Latency

TTFT is the metric ([§1.5](01_requirements.md#15-latency-budget)). Two properties worth restating
because they're easy to lose in implementation:

- **The output guardrail is overlapped, not sequential.** Buffering the full answer to scan it would add ~100 ms to TTFT *and* defeat streaming. The trade-off is explicit: the guardrail can truncate mid-stream but cannot prevent an already-sent token.
- **Embedding ∥ ACL resolution.** Free parallelism; both ~60 ms, neither depends on the other. If ACLs ever require a per-document service call, this becomes serial and the budget breaks — assumption [A3](01_requirements.md#17-assumptions--open-questions).

### Evaluation

| Layer | What runs | Gate |
|---|---|---|
| **Retrieval** | recall@20, contextual precision, MRR on the golden set | Blocks deploy on > 3-point drop |
| **Generation** | groundedness, answer relevance, citation accuracy | Blocks deploy on > 3-point drop |
| **E2E** | correctness, refusal precision on the unanswerable set | Blocks deploy |
| **Operational** | p95 TTFT, cost/query on the eval set | Blocks on > 20% regression |
| **Online** | groundedness + citation accuracy on 1% sampled production traffic | Alerts, doesn't block |

**Two properties this eval design depends on:**

1. **The judge must be stabilized**, or the 3-point gate is noise. A raw "score this 0–10" prompt swings several points across identical reruns. G-Eval-style stabilization — chain-of-thought evaluation steps generated once and reused, plus probability-weighted scoring over the top candidate score tokens — brings run-to-run variance under ~0.05. See [`../../16_evals/15-mastering-g-eval-deterministic-judge.md`](../../16_evals/15-mastering-g-eval-deterministic-judge.md).
2. **Retrieval evals must not use chunk IDs as ground truth.** A golden set of (question → correct chunk IDs) is invalidated by *any* chunking-parameter change, which is precisely the parameter you most want to tune. Use (question → ideal answer) and score whether the ideal answer's claims are supported by what was retrieved. This is the single most important practical lesson in RAG evaluation.

### Hallucination & groundedness

Defence is layered, because no single mechanism is sufficient:

| Layer | Mechanism |
|---|---|
| Prompt | Answer *only* from the fenced context; say so explicitly when it's insufficient |
| **Retrieval gate** | `min_rerank_score` → refuse before the LLM is ever called ([§3.3](03_lld.md#retrieve--rerank--assemble)) |
| Citation enforcement | Every factual claim carries a marker; markers validated server-side against real chunk IDs |
| Post-generation | Groundedness scored on sampled traffic; `citation.hallucinated` counted continuously |
| UI | Citations are clickable, so verification cost is one click — the cheapest hallucination defence available |

**The refusal path is the load-bearing one.** Prompting alone doesn't reliably produce refusals; a
model handed 8 irrelevant chunks will usually synthesize something. Deciding *before* the LLM call —
based on rerank scores — makes refusal deterministic.

### Prompt injection

**Retrieved content and user queries are data. Never instructions.**

| Vector | Risk | Control |
|---|---|---|
| **Query injection** ("ignore previous instructions…") | Lower | Structural separation of system prompt from user turn; no tool access on this path |
| **Retrieved-document injection** | **Higher** | Retrieved text fenced and explicitly labelled untrusted; model instructed never to follow instructions found inside it |

**Why the document vector is worse** ([E14](03_lld.md#full-edge-case-register)): a poisoned document
sits in the corpus for months, carries the implicit authority of "our internal documentation," and
reaches every user who asks a related question. A query injection affects one request by one user who
already had whatever permissions they had.

**This system's saving grace is that it has no tools.** Read-only retrieval plus text generation means
a successful injection can distort an answer but cannot *act*. The moment tool-calling is added, this
becomes the dominant threat and needs the privilege separation described in
[`../00_requirements_all_systems.md#10-enterprise-ai-agent-platform`](../00_requirements_all_systems.md#10-enterprise-ai-agent-platform).

### Prompt & model versioning

| Artifact | Practice |
|---|---|
| Prompts | Versioned in git; `prompt_version` on every trace; canary before full rollout |
| Model | **Pin explicit versions** — never a floating alias. A provider silently updating a model behind `latest` changes behaviour with no deploy on your side |
| Embeddings | `embed_version` in every index predicate ([§3.1](03_lld.md#chunks--the-table-the-whole-system-turns-on)) |
| Cache | Both versions in the cache key, so either change invalidates cleanly |

### Drift

| Drift type | Detection | Response |
|---|---|---|
| Query distribution | Weekly clustering of query embeddings; new-cluster alert | Add golden-set coverage for the new topic |
| Corpus drift | Retrieval score distribution over time | Investigate; may need re-chunking |
| **Silent provider change** | Golden-set score drop with **no deploy on our side** | Pin versions; this is the failure that pinning prevents |
| Cache staleness | Hit rate vs. thumbs-down correlation | Tighten TTL |

### Observability

Every LLM call traces: prompt version, model version, retrieved chunk IDs, reranked IDs, tokens in/out, cost, per-stage latency, cache hit, refusal flag, citation report. Written **asynchronously** — never on the request path.

**The question this exists to answer is "why did it say that?"** Reconstructing an answer requires the
exact chunks *and* the exact prompt and model versions. Store all of it, or accept that you cannot
debug your own system.

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Metrics | Alert |
|---|---|---|
| Latency | TTFT p50/p95/p99; per-stage breakdown | p95 > 1.5 s for 5 min |
| Quality | Online groundedness, citation accuracy, refusal rate, 👎 rate | groundedness < 0.93; **refusal rate jump > 2×** |
| Cost | $/query, daily burn, per-tenant top 10 | daily burn > 1.3× 7-day average |
| Retrieval | Candidate count, rerank score distribution, zero-result rate | zero-result rate > 5% |
| Cache | Hit rate, size, eviction rate | hit rate < 15% |
| Ingestion | Queue depth, DLQ depth, freshness lag p95 | **DLQ depth > 0**; freshness > 10 min |
| Providers | Error rate, circuit state, fallback invocations | circuit open |

**A refusal-rate spike is the highest-signal alert in the system.** It usually means retrieval broke —
an embedding-version mismatch, an index problem, a collapsed ACL filter — and it surfaces *before*
users complain about wrong answers, because the system correctly declines instead of guessing.

### Triage order when quality complaints arrive

Ordered by frequency and by cheapness to check:

1. **Did retrieval work?** Pull the trace; inspect `retrieved_ids` and rerank scores. Most quality complaints are retrieval failures wearing a generation costume.
2. **Embedding version consistent?** `SELECT DISTINCT embed_version FROM chunks` — more than one active version in the searched index is [F3](02_hld.md#25-failure-modes--blast-radius).
3. **Was it a cache hit?** A stale cached answer looks exactly like a model regression.
4. **Prompt or model version changed?** Compare `prompt_version` / `model_version` against the last known-good.
5. **Is the document actually indexed and current?** Check `indexed_at` vs `source_modified_at`.
6. **Only then** suspect the model.

### Rollback

| Change | Rollback |
|---|---|
| Prompt | Revert `prompt_version`; invalidate affected cache entries |
| Model | Repin the previous version |
| **Embedding model** | Point queries back at the previous `embed_version` partial index — **instant, because both indexes coexist** ([E9](03_lld.md#full-edge-case-register)) |
| Chunking | Requires reindex; blue/green, hours |
| Code | Standard deploy rollback |

The embedding rollback being instant is the direct payoff of the blue/green index design. Without it, a bad embedding-model rollout means hours of degraded retrieval.

---

## 4.3 Common mistakes

> **Mistake:** Post-filtering ACLs after the ANN search.
> **Why it's wrong:** the search returns the globally most-similar 50 chunks; dropping unauthorized ones can leave 3, or zero, while authorized chunks sat at ranks 51–100 unconsidered. Recall silently degrades *most for the most-restricted users*.
> **Do instead:** push the filter into the query as a predicate ([§3.3](03_lld.md#retrieve--rerank--assemble)).

> **Mistake:** Caching on the query embedding alone.
> **Why it's wrong:** users with different permissions share cache entries → **silent permission leak**, no error, no audit trail.
> **Do instead:** include `acl_scope_hash`, `corpus_version`, `prompt_version`, and `model_version` in the key ([§3.6](03_lld.md#the-permission-leak-through-cache-problem)).

> **Mistake:** Mixing embedding versions in one index.
> **Why it's wrong:** cross-model cosine similarity is meaningless, not merely worse. Retrieval collapses with **no error anywhere**.
> **Do instead:** `embed_version` as a mandatory index predicate; blue/green reindex ([F3](02_hld.md#25-failure-modes--blast-radius)).

> **Mistake:** Using chunk IDs as retrieval-eval ground truth.
> **Why it's wrong:** any chunking change invalidates the entire golden set — and chunking is the parameter you most want to tune.
> **Do instead:** (question → ideal answer) pairs; score claim support against retrieved text.

> **Mistake:** Treating "no relevant results" as an empty-list edge case.
> **Why it's wrong:** the pipeline returns the 8 least-bad chunks and the model synthesizes a confident answer from irrelevant text.
> **Do instead:** a relevance floor that triggers refusal before the LLM is called ([§3.3](03_lld.md#retrieve--rerank--assemble)).

> **Mistake:** Not propagating client cancellation.
> **Why it's wrong:** you pay full price for tokens nobody receives; at ~30% abandonment on slow queries it's a material cost line.
> **Do instead:** abort the provider call on disconnect ([E12](03_lld.md#full-edge-case-register)).

> **Mistake:** Buffering the answer to run output guardrails.
> **Why it's wrong:** adds ~100 ms to TTFT and defeats streaming — the thing that makes a 6 s answer feel fast.
> **Do instead:** scan inline with truncate-on-violation, and document the residual risk.

> **Mistake:** Caching degraded answers.
> **Why it's wrong:** a 30-second provider outage poisons the cache for hours ([F6](02_hld.md#25-failure-modes--blast-radius)).
> **Do instead:** never cache when `degraded: true`.

> **Mistake:** Floating model aliases (`latest`).
> **Why it's wrong:** behaviour changes with no deploy on your side; you debug your own code for days.
> **Do instead:** pin versions; treat a provider bump as a deliberate, evaluated change.

---

## 4.4 Interview follow-ups

### "Why not just use a bigger `top_k` and skip reranking?"

You can, and it's the right call under a tight enough latency budget. The trade is ~12 points of
precision@5 for 180 ms. Precision matters disproportionately here because citations are the product —
a low-precision context set produces answers padded with tangential claims that each need a citation,
and citation accuracy is what user trust rests on. Also, a bigger `top_k` doesn't just cost search
time: more chunks means more input tokens, so it moves cost too. I'd revisit below a ~1 s TTFT
budget, where the reranker stops fitting.

### "How do you know retrieval is the bottleneck rather than the model?"

Measure them separately, which is why the eval suite has distinct retrieval and generation tiers.
Feed the generator **golden context** and score groundedness and answer relevance — if those are high
in isolation but the end-to-end answer is poor, the fault is retrieval. Conversely, high recall@20
with low groundedness points at the generator or the prompt. Conflating them into one end-to-end score
makes the system undebuggable.

### "The cost is 12× over budget after every optimization. What do you actually do?"

Go back to the business with three options and a recommendation ([§1.6](01_requirements.md#16-capacity--cost-estimation)).
My recommendation is to **measure the traffic assumption first** — the 130M queries/month figure is
derived from 50 QPS sustained around the clock, which 5,000 employees don't generate. At a realistic
8 queries/day/employee it's ~13M/month and lands **inside** budget at ~$9.5k. That's a two-week pilot
to resolve, versus committing to an architecture built for a number that's probably wrong by 10×.
Measure before you optimize; optimize before you procure.

### "A user says the answer is wrong. Walk me through debugging it."

The triage order in [§4.2](#42-operations--runbook). Concretely: pull the trace by `trace_id`, look at
`retrieved_ids` and the rerank score distribution first — most "the model is wrong" reports are
retrieval failures. Then check for multiple active `embed_version`s, then whether it was a cache hit,
then whether prompt/model versions changed. The model is the *last* suspect because it's the component
that changed least.

### "How do you handle a document that contradicts another?"

Surface both with citations rather than silently choosing ([E17](03_lld.md#full-edge-case-register)).
Enterprise corpora genuinely contain superseded policy alongside current policy, and a system that
silently picks one is confidently wrong half the time. Showing the conflict lets the user apply
judgement the system doesn't have — and it surfaces a real corpus problem that document owners should
fix.

### "Why pgvector rather than a dedicated vector database?"

Two reasons, both about *this* scale. First, ACLs and metadata live in the same Postgres transaction as
the vectors, so filtered search is a local predicate rather than a cross-system join — and filtered
search is mandatory here ([FR-4](01_requirements.md#12-functional-requirements)), not optional. Second,
115 GB of quantized index fits one large instance, so we get no sharding benefit from a distributed
store. I'd move past ~50M vectors after quantization, or if per-tenant namespace isolation became a
hard requirement, or if write throughput outgrew a single primary.

### "What breaks first if traffic 10×'s tomorrow?"

The pgvector primary, on memory — 800M chunks exceeds single-instance RAM
([§2.6](02_hld.md#26-scale-plan)). The fix is sharding by `tenant_id`, which is clean here because
queries are always tenant-scoped, so no scatter-gather is needed. The *second* thing is HNSW rebuild
time, which becomes a multi-day job and forces reindexing to be a rolling per-shard operation.

### "You've got no tools in this system. What changes when you add them?"

Prompt injection goes from "can distort an answer" to "can take an action," and that reprioritizes the
whole security model. Retrieved content is already treated as untrusted data, but with tools you also
need privilege separation (the agent acts as the *user*, not a service account), tool allow-lists,
human approval for side-effecting calls, and the rule that **no tool invocation may be derived solely
from retrieved text**. That's the design in
[`../00_requirements_all_systems.md#10-enterprise-ai-agent-platform`](../00_requirements_all_systems.md#10-enterprise-ai-agent-platform).

### "Is 99.9% availability achievable?"

For our own components, yes — stateless services, multi-AZ, read replicas. But the honest answer is
that **our ceiling is the LLM provider's SLA**, typically 99.9%, so 99.9% end-to-end is only
achievable *because* of the fallback chain and the degraded extractive path
([F1](02_hld.md#25-failure-modes--blast-radius)). Promising 99.99% while depending on a single
provider would be a number I couldn't defend.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **RAG** | Retrieval-Augmented Generation — retrieve relevant text, then generate an answer grounded in it | The whole architecture |
| **Embedding** | A vector encoding the *meaning* of text; similar meanings land near each other | Makes semantic retrieval possible |
| **Cosine similarity** | Similarity as the angle between two vectors, ignoring magnitude | Length-invariant, so a long and short passage on the same topic still match |
| **Bi-encoder** | Encodes query and document *independently* | Precomputable ⇒ indexable ⇒ fast over 80M chunks |
| **Cross-encoder** | Encodes query and document *jointly* | Far more accurate, not precomputable ⇒ runs on 50 candidates, not 80M |
| **ANN** | Approximate Nearest Neighbour — trades exactness for speed | Exact search over 80M vectors is arithmetically impossible in 120 ms |
| **HNSW** | Hierarchical Navigable Small World — graph-based ANN index | Best recall/latency at this scale; supports predicate pushdown |
| **IVF** | Inverted File index — clusters vectors, searches nearest clusters | Faster to build than HNSW; the alternative when rebuild time dominates |
| **Quantization** | Storing vectors at lower precision (int8, binary) | 4× memory reduction for ~1–2% recall loss at 80M vectors |
| **`embed_version`** | Which embedding model produced a vector | **Mixing versions makes similarity meaningless with no error** |
| **Chunking** | Splitting documents into retrievable passages | Determines what can be retrieved and cited at all |
| **Neighbour expansion** | Pulling adjacent chunks from the same document | Restores continuity that chunking broke |
| **Reranking** | Re-scoring retrieved candidates with a stronger model | +~12 points precision@5 — the basis of citation trust |
| **Recall@k** | Fraction of relevant chunks appearing in the top *k* | **The ceiling on the whole system** — unretrieved content is unanswerable |
| **Precision@k** | Fraction of the top *k* that are relevant | Drives citation quality and context efficiency |
| **Groundedness** | Whether the answer's claims are supported by the supplied context | Distinct from correctness — you can be grounded in a wrong document |
| **Citation accuracy** | Whether a citation resolves to a passage actually containing the claim | A wrong citation is worse than none — it manufactures confidence |
| **Semantic cache** | Cache keyed by query *meaning*, not exact string | ~27× latency win; **and a permission-leak risk if keyed carelessly** |
| **Prompt caching** | Provider-side reuse of a repeated prompt prefix | The static system prompt is 1,200 of 1,800 input tokens |
| **TTFT** | Time To First Token | With streaming, this *is* perceived latency |
| **Model routing** | Sending easy queries to a cheaper model | The single largest cost lever (~80% reduction) |
| **Blue/green reindex** | Building a new index alongside the live one, then cutting over | Zero-downtime embedding-model changes, instant rollback |
| **Tombstone** | Marking a row deleted before physically purging it | Makes deletion instant while purge runs async |
| **DLQ** | Dead-Letter Queue — messages that failed permanently | Prevents silent document loss |
| **Fail-open / fail-closed** | On dependency failure: serve anyway, or deny | A *product* decision that must be made explicitly, not defaulted |
| **G-Eval** | LLM-as-judge stabilized with fixed CoT steps + probability-weighted scoring | Without it, a 3-point regression gate is noise |
| **Deadly-silent failure** | A failure with no error signal, only degraded quality | The class [F3](02_hld.md#25-failure-modes--blast-radius) belongs to — and the reason for defensive index predicates |

---

**Files:** [README](README.md) · [Requirements](01_requirements.md) · [HLD](02_hld.md) · [LLD](03_lld.md) · **Production & interview** (this file)
