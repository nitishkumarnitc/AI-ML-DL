# 01 · Requirements — Recommendation System

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#6-ai-recommendation-system`](../00_requirements_all_systems.md#6-ai-recommendation-system)

---

## 1.1 Problem & users

### What breaks today

A platform with 10M monthly actives and a 5M-item catalogue shows everyone the same
popularity-ordered home feed. Consequences, in the order the business feels them:

1. **Discovery collapses to the head.** The top ~1,000 items absorb nearly all engagement; 4.99M items
   are effectively invisible, so the catalogue's cost isn't earning anything.
2. **New users see nothing relevant.** Without personalization, a first session is a generic feed, and
   first-session quality dominates retention.
3. **Supply side suffers.** Sellers/creators outside the head get no exposure, which reduces their
   incentive to publish — shrinking the catalogue over time.

### Users and jobs

| User | Job | What "working" means |
|---|---|---|
| **End user (primary)** | Find something worth engaging with | The feed contains something they want, fast enough not to notice loading |
| Seller / creator | Get exposure | Non-head items receive impressions |
| Business | Grow engagement | Measurable lift on the true objective — see [Q1](#open-questions) |
| ML engineer | Ship model improvements safely | Offline metrics predict online outcomes; A/B framework available |

### Why this is not an LLM problem

The prompt says "AI recommendation system," and the correct answer includes **not** using an LLM in the
serving path. The arithmetic in [§1.6](#16-capacity--cost-estimation) forces it, but the reasoning is
worth stating plainly:

| Consideration | Why an LLM fails here |
|---|---|
| **Volume** | 216 billion item scorings/day. An LLM call per candidate is off by ~6 orders of magnitude |
| **Latency** | 150 ms total for the *whole* request; a single LLM call typically exceeds it |
| **Task shape** | Ranking is a well-posed supervised problem with abundant labels (clicks). LLMs excel where labels are scarce and language matters — neither applies |
| **Cost** | ~1000× a gradient-boosted tree per scoring |

**Where LLMs *do* belong here** — all offline, none in the hot path:

- Generating item embeddings from titles/descriptions (a batch job, once per item).
- Cold-start enrichment: inferring attributes for a new item with no interaction history.
- Explanation text ("because you viewed X"), generated asynchronously and cached.

> **Mental model:** recommendation is a **funnel**, not a judgement — narrow 5M to 500 cheaply, then
> spend real compute on the 500.
>
> *Where the analogy breaks:* a physical funnel loses nothing, but candidate generation *does* — anything
> it misses is unrecoverable no matter how good the ranker is. That's why recall@500 is an NFR
> ([§1.3](#quality)) and why multiple independent generators run in parallel rather than one.

---

## 1.2 Functional requirements

### Serving

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | Return top-N personalized recommendations | p95 < 150 ms |
| **FR-2** | P0 | **Multi-source candidate generation** — collaborative, content, trending, recent | Recall@500 ≥ 0.80 vs the engaged set |
| **FR-3** | P0 | ML ranking over candidates | **+≥ 10% CTR** vs popularity baseline |
| **FR-6** | P0 | Cold start for new users **and** new items | Content-based fallback; no empty feed |
| FR-7 | P1 | Business rules: dedup, diversity, blocklists, freshness | Post-ranking layer |
| FR-11 | P2 | Explanations ("because you viewed X") | Generated async, cached |

**Why four candidate sources rather than one good one.** Each has a blind spot that the others cover:
collaborative filtering can't handle items with no interactions; content-based can't capture "people who
liked this also liked that"; trending covers neither personalization nor tail; recently-viewed covers
session intent only. **Running them in parallel and merging is what gets recall@500 to 0.80** — and
because they run concurrently, four sources cost the same latency as the slowest one
([§1.5](#15-latency-budget)).

### Data & features

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-4** | P0 | Feature store with **train/serve consistency** | **Zero training-serving skew** on shared features |
| **FR-5** | P0 | Log impressions + engagements for training | No loss; **exactly-once** into the warehouse |
| FR-8 | P1 | Near-real-time features (last-N interactions) | Reflected < 30 s |

**FR-4 is the requirement that quietly breaks most recommender projects.** If a feature is computed one
way in the training pipeline (SQL over the warehouse) and another way at serving time (application code
over Redis), the model is served inputs it was never trained on. The symptom is a model that looks
excellent offline and mediocre online, with **no error anywhere** — see
[F2](02_hld.md#25-failure-modes--blast-radius).

**FR-5 says exactly-once deliberately.** Duplicated impressions inflate the denominator of CTR and bias
training labels; lost impressions mean the model never learns from items it showed. Neither produces an
error — both quietly degrade the model.

### Learning loop

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-9** | P1 | A/B framework with **guardrail metrics** | Can't ship a CTR win that tanks retention |
| FR-10 | P1 | Daily retrain + **shadow eval before promotion** | Blocked on offline regression |
| **FR-12** | P0 | **Exploration** — deliberate impressions on unranked items | ≥ ε% of slots; catalogue coverage monitored |

**FR-12 is P0 despite looking like a refinement**, because it's the only defence against the feedback
loop. Without exploration, the ranker only ever sees labels for items it already chose to show, so it
narrows its own world and popular items entrench — while offline metrics *improve*. Exploration
deliberately spends a small amount of engagement to keep the training distribution honest.

---

## 1.3 Non-functional requirements

### Latency

| NFR | Target | Why this number |
|---|---|---|
| **Serving** | p95 < 150 ms · p99 < 250 ms | The feed **blocks page paint** — this is in the critical rendering path, unlike an async answer |
| Behaviour freshness | < 30 s | Session relevance: viewing three cameras should influence the next request |
| Model freshness | Daily retrain | Catalogue and taste drift; hourly would add cost for marginal gain |

**150 ms total is the tightest budget in this set apart from [08](../00_requirements_all_systems.md#8-real-time-ai-voice-assistant)**,
and it's tighter than it looks: [01](../01_production_rag_system/README.md) gets 1.5 s for TTFT *alone*.
The difference is that a feed request blocks rendering, so the user perceives it as page load rather than
as a response.

### Quality

| NFR | Target | Why this number |
|---|---|---|
| **Recall@500** | ≥ 0.80 | **The ceiling on the whole system** — the ranker cannot surface what candidate generation missed |
| CTR lift | ≥ +10% vs popularity | The threshold that justifies the project's existence |
| **Offline/online parity** | Offline AUC lift ⇒ online CTR lift, **sign-consistent** | Without this, offline eval is worthless and only A/B tests can gate — which slows iteration to a crawl |
| **Catalogue coverage** | ≥ X% of items receive impressions weekly | The feedback-loop guardrail ([FR-12](#learning-loop)) |
| Fallback quality | Popularity list always available | **A blank feed is a broken product** |

**Why recall is measured at 500 rather than at the final N.** 500 is the candidate-generation output —
the point past which loss is unrecoverable. Measuring recall at the final 10 conflates two independent
failures (bad recall vs bad ranking) into one number and makes the system undebuggable.

**Offline/online parity is a *system* requirement, not a model property.** It's listed as an NFR because
if it fails, the entire development workflow changes: every change needs a multi-week A/B test rather
than a same-day offline evaluation.

### Capacity, availability, cost

| NFR | Target | Why |
|---|---|---|
| Throughput | 5k QPS sustained · 20k peak | 10M MAU with session patterns |
| Availability | 99.95% | A blank feed is indistinguishable from a broken site |
| Cost | ≤ $0.30 per 1k requests | Unit economics ceiling — **375× headroom in practice** |

---

## 1.4 Non-goals

| Out of scope | Why | What would bring it in |
|---|---|---|
| **LLM in the ranking hot path** | ~1000× the cost, exceeds the entire latency budget with one call | Never at this scale. LLMs stay offline: embeddings, cold-start enrichment, explanations |
| **Real-time (online) model training** | Daily batch + NRT features captures most of the value at a fraction of the complexity | Intraday taste shifts prove material — e.g. live events |
| Cross-device identity resolution | v1 treats devices independently | Identity graph exists and is reliable |
| **Full causal uplift modelling** | v1 ranks by predicted engagement, which is correlational | Proven that ranking is recommending what users would have found anyway |
| Sequence/session transformers | GBDT first; establish the baseline | GBDT plateaus below the CTR target ([§2.2](02_hld.md#the-ranking-tier)) |

**"Correlational, not causal" is worth stating explicitly.** A ranker trained on clicks learns what
people click, which includes items they would have found regardless. The model can look excellent while
delivering little incremental value. Proper uplift modelling is a substantially harder problem, and
naming it as deferred is more honest than implying the CTR lift is causal.

---

## 1.5 Latency budget

SLO: p95 < 150 ms. **The tightest budget in this set apart from voice**, and parallelism is load-bearing.

| # | Stage | Budget (p95) | Notes |
|---|---|---:|---|
| 1 | Request parse + auth | 10 ms | |
| 2 | Fetch user features (online store) | 20 ms | Single Redis round trip, pipelined |
| 3 | **Candidate generation — 4 sources IN PARALLEL** | **40 ms** | **Max, not sum.** Serially this would be ~110 ms and blow the budget |
| 4 | Dedup + merge to ~500 | 10 ms | |
| 5 | Feature hydration for 500 candidates | 25 ms | Batched multi-get; the reason item features are denormalized |
| 6 | **Ranker inference (batch of 500)** | **30 ms** | ⇒ **~0.06 ms/candidate** — the constraint that picks the model class |
| 7 | Business rules + diversity | 10 ms | |
| 8 | Exploration slot injection | 2 ms | |
| | **Total** | **≈ 147 ms** | vs 150 ms SLO → **~3 ms headroom** ⚠️ |

> **⚠️ 3 ms of headroom is uncomfortably tight, and worth saying so rather than presenting 147 < 150 as
> success.** Three consequences:
>
> 1. **Parallel candidate generation is not an optimization, it's mandatory.** Serialized, the budget
>    fails outright.
> 2. **Feature hydration for 500 candidates must be one batched call.** 500 individual lookups at even
>    0.2 ms each is 100 ms.
> 3. **There is no room for a network hop to an external service.** This is a second, independent reason
>    an LLM can't be in this path — not just cost, but that the budget has no space for it.
>
> **Mitigations if it proves too tight:** reduce candidates to 300 (costs recall), cache full responses
> for repeat requests within a session, or move diversity into the ranker's objective rather than a
> post-processing stage.

---

## 1.6 Capacity & cost estimation

### The arithmetic that forces the architecture

```
Traffic:  5,000 QPS × 86,400 s = 432,000,000 requests/day

Scorings: 432M requests × 500 candidates = 216,000,000,000 scorings/day

Now test model classes against the 30 ms / 500 candidates budget:

  Transformer @ ~1 ms/candidate:
      216e9 × 1 ms = 216e9 ms = 60,000 hours of compute PER DAY
      ⇒ ~2,500 machines running continuously. ABSURD.

  Required: 30 ms ÷ 500 = 0.06 ms per candidate

  GBDT (e.g. ~500 trees, depth 6), batched, SIMD-friendly:
      ~0.05–0.08 ms/candidate on CPU  ✅ FITS
```

**The model class is forced by arithmetic, not chosen by preference.** And the same arithmetic forces the
two-stage shape: scoring 5M items per request would be `432M × 5M = 2.16 × 10^15` scorings/day, which no
model class survives.

### Single-stage is not merely worse — it's impossible

```
Cheapest conceivable scorer at 0.01 ms/candidate over the full catalogue:
  432M × 5M × 0.01 ms = 2.16e13 ms = 6 MILLION compute-hours/day
⇒ Two-stage isn't an optimization. It's the only shape that exists.
```

### Serving cost

```
Ranking inference:
  216e9 scorings × 0.06 ms = 1.3e10 ms = 3,600 compute-hours/day
  at ~$0.04/CPU-hour ≈ $144/day
  (Assumption A2 — benchmark; GBDT throughput varies with feature count)

Candidate generation (ANN over 5M items):
  Item embeddings: 5M × 256 dims × 4 B = 5 GB ⇒ fits in memory on EVERY serving node
  ⇒ no network hop, no separate service. ~$60/day amortized

Feature store (Redis):
  Users: 10M × 256 × 4 B = 10 GB, plus behavioural features ≈ 40 GB total
  ⇒ ~$200/day for a replicated cluster

Event logging: 432M impressions/day × ~200 B ≈ 86 GB/day  ⇒ ~$100/day
                                                            ─────────
Total                                                     ≈ $504/day

Per 1k requests: $504 / 432,000 ≈ $0.0012      ✅ vs the $0.30 ceiling — 250× headroom
```

**The 5 GB embedding table fitting in node memory is a genuinely important consequence.** It means
candidate generation needs no network call — which is what makes the 40 ms budget in
[§1.5](#15-latency-budget) achievable. At 50M items (250 GB) that stops being true and candidate
generation becomes a separate sharded service with a network hop, which is the main thing that breaks at
10× ([§2.6](02_hld.md#26-scale-plan)).

### Training cost

```
Daily retrain on ~30 days of impressions:
  432M/day × 30 = ~13B rows, sampled to ~500M for training
  GBDT training on 500M × ~200 features: ~4-6 hours on a large machine ≈ $50/run
Embedding refresh (matrix factorization / two-tower): ~2 hours GPU ≈ $30/run
                                                                    ────────
                                                                    ≈ $80/day
```

**Training is ~16% of serving cost** — worth noting because the instinct is to assume training dominates.
At this scale, serving 432M requests/day dwarfs retraining once.

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | ~500 candidates suffice for recall@500 ≥ 0.80 | Medium | More candidates scale ranking cost and latency **linearly** — and the budget has only 3 ms of slack |
| **A2** | GBDT achieves ~0.06 ms/candidate batched | Medium | **Benchmark first.** If it's 0.15 ms, ranking alone is 75 ms and the budget fails |
| **A3** | GBDT-class model meets the +10% CTR target | Medium | A DNN needs GPU serving and a re-derived latency budget |
| **A4** | **Offline AUC predicts online CTR directionally** | **Low** | **If not, only A/B tests can gate releases** — iteration slows from days to weeks. The most damaging assumption to be wrong about |
| A5 | 5M items; embeddings fit in node memory | Medium | Above ~50M, candidate generation becomes a sharded service with a network hop |
| A6 | 30-day training window is sufficient | Medium | Longer windows raise training cost and may include stale taste |

**A4 is the assumption that changes the *workflow*, not just the numbers.** Offline/online parity is what
makes fast iteration possible; without it every change needs a multi-week experiment. It's also
genuinely common for it to fail, because offline evaluation replays logged impressions that a *different*
ranker chose — the feedback loop again.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | **What is the true objective — CTR, watch time, revenue, or retention?** | Changes labels, loss function, and guardrails entirely. **Optimizing CTR can actively harm retention** via clickbait | Product — **resolve first** |
| **Q2** | Are there fairness/exposure constraints for sellers or creators? | Adds constraints to ranking; may mandate guaranteed exposure | Legal / Marketplace |
| **Q3** | What is the acceptable exploration cost? | ε% of slots is a direct, measurable engagement cost paid for long-term catalogue health | Product |
| Q4 | Is a blank feed ever acceptable, or is popularity fallback mandatory? | Determines fallback engineering depth | Product |
| Q5 | Who owns blocklists and content policy? | Post-ranking rules are policy, not engineering | Trust & Safety |

**Q1 is genuinely blocking, not a formality.** CTR is the easiest label to collect and frequently the
wrong objective: a model optimizing clicks learns to promote clickbait, which raises CTR while lowering
satisfaction and retention. Watch time has its own pathology (rewarding length over quality). **Every
downstream choice — labels, loss, guardrails, A/B success criteria — depends on the answer**, so building
before it's settled means building the wrong thing efficiently.

---

**Next:** [02_hld.md →](02_hld.md) — the two-stage architecture, model choices, feature store and train/serve skew, exploration, failure modes, and the scale plan.
