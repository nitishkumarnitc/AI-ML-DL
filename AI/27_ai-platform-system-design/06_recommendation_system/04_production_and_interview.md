# 04 · Production & Interview — Recommendation System

> **Phase 4 of 4** · [← LLD](03_lld.md) · [README](README.md)

---

## 4.1 ML-specific concerns

This section is deliberately headed *ML*-specific rather than *AI*-specific: the concerns that matter here
are classical ML failure modes — skew, leakage, feedback loops, position bias — not token cost or
hallucination.

### Cost

| Cost centre | Daily | Share |
|---|---:|---:|
| Ranking inference (CPU) | $144 | 25% |
| Feature store (Redis) | $200 | 34% |
| Event logging | $100 | 17% |
| Candidate generation (amortized) | $60 | 10% |
| Training + embedding refresh | $80 | 14% |
| **Total** | **≈ $584** | ≈ **$0.0014 / 1k requests** |

**Cost is not the constraint** — there's ~215× headroom against the $0.30/1k ceiling. Note what
*dominates*: the **feature store**, not inference. That's a useful corrective to the instinct that model
serving is where the money goes, and it means Redis sizing deserves more design attention than shaving
tree count.

### Latency — 3 ms of slack

The tightest budget in this set apart from [08](../00_requirements_all_systems.md#8-real-time-ai-voice-assistant).
Three properties carry it, and all three are load-bearing rather than optimizations:

| Property | Without it |
|---|---|
| **Parallel candidate generation** | ~110 ms instead of 40 ms — budget fails |
| **In-process ANN index** (5 GB fits in node memory) | A network hop the 3 ms cannot absorb |
| **One batched feature multi-get** | 500 sequential lookups ≈ 100 ms — two-thirds of the budget |

**Per-stage latency headers** (`X-Latency-Breakdown`) exist because with 3 ms of slack, a p95 breach must
be attributable immediately rather than bisected during an incident.

### Evaluation — the discipline that differs most from LLM systems

| Layer | What's measured | Gate |
|---|---|---|
| **Recall@500** | vs the engaged set, **per candidate source** | Blocks below 0.80 |
| Ranking | AUC, NDCG@10, calibration of predicted CTR | Blocks on regression vs current |
| **Train/serve skew** | Logged served features vs offline recompute | **Blocks on any mismatch above threshold** |
| **Leakage** | Held-out-by-time evaluation | Blocks if temporal split ≫ random split performance |
| **Online A/B** | CTR **plus guardrails**: retention, dwell, coverage, latency | Blocks promotion on any guardrail breach |
| Coverage | % of catalogue receiving impressions weekly | Alerts on decline |
| Score variance | Distribution of predicted scores | Alerts on collapse ([E17](03_lld.md#36-edge-cases--correctness)) |

**Three properties specific to recommenders:**

1. **Offline metrics are a *filter*, not a decision.** They cheaply reject bad models; only an A/B can
   confirm a good one, because offline evaluation replays impressions a *different* ranker chose. This is
   assumption [A4](01_requirements.md#assumptions) and the reason two gates exist
   ([§3.5](03_lld.md#model-promotion)).
2. **Per-source recall attribution matters.** Aggregate recall@500 can look healthy while one source has
   silently died. Measuring each source's unique contribution is also how you decide whether a source
   earns its latency.
3. **A temporal split is mandatory, not preferred.** A random train/test split on interaction data leaks
   the future: the model sees a user's later behaviour while predicting their earlier clicks. Random-split
   AUC materially exceeding time-split AUC is the leakage signature.

### The feedback loop — the defining ML risk

Not hallucination. **The system trains on data it generated.**

```
Ranker shows items → impressions logged → model trained on those impressions
  → items never shown have no positive labels → they score lower
  → they are shown even less → ... 

Meanwhile offline AUC IMPROVES: the model gets better at predicting clicks
within the ever-narrower distribution it created.
```

| Control | Mechanism |
|---|---|
| **Exploration** | ε% of slots to unranked, low-impression items ([FR-12](01_requirements.md#learning-loop), P0) |
| **Coverage as a first-class metric** | Alerts on decline — the *only* reliable detection |
| Re-exploration of stale items | `stale → exploring` transition ([§3.5](03_lld.md#item-lifecycle-cold-start)) |
| Gini coefficient of impression distribution | Detects rich-get-richer concentration |
| Optional exposure floors | Guaranteed minimum impressions per seller ([Q2](01_requirements.md#open-questions)) |

**The reason this needs structural defence rather than monitoring alone:** every conventional metric moves
in the *right* direction while the failure progresses. Accuracy improves, CTR may improve, latency is
unaffected. Only coverage reveals it.

### Position bias

A close cousin of the feedback loop, and equally circular if untreated: an item in slot 1 is clicked far
more than the *same* item in slot 20, so raw clicks conflate item quality with the previous ranker's
layout.

| Treatment | How |
|---|---|
| **Position as a training feature, zeroed at inference** | The model attributes part of the click rate to position; scoring every candidate as slot-1 ranks by item quality ([§3.3](03_lld.md#ranking)) |
| Inverse propensity weighting | Weight labels by 1/P(shown at that position) — more principled, harder to tune |
| Exploration at varied positions | Generates less position-confounded labels |

### Drift

| Drift type | Detection | Response |
|---|---|---|
| **Taste drift** | Rolling CTR of a fixed model | Daily retrain absorbs most of it |
| Catalogue drift | Item-embedding distribution shift | Daily embedding refresh |
| **Feature drift** | Per-feature distribution monitoring | Investigate upstream; a changed producer often breaks a definition |
| Cold-start ratio shift | % of requests with sparse features | Onboarding or acquisition-mix change |
| **Skew appearing over time** | Continuous skew sampling | A feature producer changed on one side only ([F2](02_hld.md#25-failure-modes--blast-radius)) |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Metrics | Alert |
|---|---|---|
| **Latency** | p50/p95/p99 + **per-stage breakdown** | p95 > 150 ms · any stage above its budget |
| **Coverage** | % catalogue with impressions (7d); Gini | **Decline > 5% week over week** ⚠️ |
| **Skew** | Sampled mismatch rate by feature | **Any mismatch above threshold** |
| Quality | CTR by cohort; recall@500 **per source**; NDCG | CTR drop > 5% · any source contribution collapse |
| **Guardrails** | Retention, dwell, sessions/user, seller exposure | Any regression during a canary |
| Fallback | Fallback rate + reason | Any sustained fallback |
| Model | Active `ranker_version`; canary %; **score variance** | Variance collapse ([E17](03_lld.md#36-edge-cases--correctness)) |
| Feature store | Hit rate, p99 read, memory | p99 > 20 ms · memory > 80% |
| Freshness | NRT feature lag; embedding age | Lag > 30 s · embeddings > 36 h old |
| Exploration | ε actual vs configured; exploration CTR | ε drifting from target |

**Coverage decline and skew mismatch are the two alerts nobody thinks to build**, and they're the two that
catch the failures no other signal reveals.

### Triage order

1. **Is it a fallback?** `fallback_reason` explains it instantly and points at a dependency, not the model.
2. **Per-stage latency.** With 3 ms of slack, one stage is almost always the culprit.
3. **Score variance.** Collapse ⇒ corrupt or mis-loaded model — every request "succeeds" and the feed is
   random.
4. **Skew check** (`/internal/v1/skew`). Ruling skew in or out early saves days; "excellent offline,
   mediocre online" is its signature.
5. **Per-source recall.** A dead source degrades quality with no error.
6. **Coverage trend.** Rules in the feedback loop.
7. **Model version + canary state.** Rules out a bad promotion.
8. **Feature freshness.** Stale NRT features degrade personalization silently.
9. **Only then** suspect model quality itself.

**Step 3 before step 9 is deliberate.** A corrupt model is far more common than a genuinely worse model,
and it presents identically from the user's side while being trivially detectable from score variance.

### Rollback

| Change | Rollback | Speed |
|---|---|---|
| **Ranker model** | Repin `ranker_version` | **Instant** |
| Embeddings | Repoint `embed_version` — **both partial indexes coexist** | Instant ([E7](03_lld.md#36-edge-cases--correctness)) |
| Feature definition | Revert version; **rebuild both materializations together** | Minutes — **never revert one side only** |
| Business rules / diversity | Config push | Seconds |
| Exploration ε | Config push | Seconds |
| Candidate source weights | Config push | Seconds |

**"Never revert one side only" is the important line.** Reverting the offline feature definition without
the online materialization *creates* skew — turning a rollback into a new incident.

---

## 4.3 Common mistakes

> **Mistake:** Using an LLM to rank candidates.
> **Why it's wrong:** ~1000× the cost per scoring, and a single call exceeds the entire 150 ms budget.
> 216B scorings/day makes it off by ~6 orders of magnitude.
> **Do instead:** GBDT at ~0.06 ms/candidate; keep LLMs offline for embeddings and cold-start enrichment
> ([§1.1](01_requirements.md#why-this-is-not-an-llm-problem)).

> **Mistake:** Scoring the whole catalogue with one model.
> **Why it's wrong:** ~6M compute-hours/day. Not expensive — **impossible**.
> **Do instead:** two-stage retrieve-then-rank ([§1.6](01_requirements.md#single-stage-is-not-merely-worse--its-impossible)).

> **Mistake:** Separate feature implementations for training and serving.
> **Why it's wrong:** guarantees train/serve skew. The model is served inputs it never trained on, and it
> fails **silently** — great offline, mediocre online, no error.
> **Do instead:** one definition, two generated materializations ([§3.1](03_lld.md#feature-definitions--the-artifact-that-prevents-skew)).

> **Mistake:** Joining features at their latest value for training.
> **Why it's wrong:** leaks the future — the feature includes behaviour that happened *after* the
> impression. Inflates offline metrics.
> **Do instead:** point-in-time correct features `as_of` the impression timestamp.

> **Mistake:** Random train/test split on interaction data.
> **Why it's wrong:** same leakage in a different guise — the model sees later behaviour while predicting
> earlier clicks.
> **Do instead:** temporal split; compare against random-split performance as a leakage detector.

> **Mistake:** No exploration.
> **Why it's wrong:** the ranker narrows its own training distribution; popular items entrench and the
> long tail becomes permanently invisible — **while offline metrics improve.**
> **Do instead:** ε exploration to low-impression items, with coverage monitored ([F1](02_hld.md#25-failure-modes--blast-radius)).

> **Mistake:** Training on raw clicks without treating position.
> **Why it's wrong:** the model learns "items we ranked highly get clicked" — circular and
> self-reinforcing.
> **Do instead:** position as a training feature, zeroed at inference ([§3.3](03_lld.md#ranking)).

> **Mistake:** Returning `503` when personalization is unavailable.
> **Why it's wrong:** a blank feed is indistinguishable from a broken site.
> **Do instead:** `200` with a popularity fallback and `fallback:true`, excluded from CTR
> ([§3.2](03_lld.md#post-v1recommendations)).

> **Mistake:** Optimizing CTR by default.
> **Why it's wrong:** rewards clickbait — CTR rises while satisfaction and retention fall.
> **Do instead:** settle the true objective first ([Q1](01_requirements.md#open-questions)) and put
> retention in the A/B guardrails.

> **Mistake:** Shipping on offline metrics alone.
> **Why it's wrong:** offline evaluation replays impressions a *different* ranker chose; it cannot measure
> guardrails or parity.
> **Do instead:** shadow eval as a filter, A/B as the decision ([§3.5](03_lld.md#model-promotion)).

> **Mistake:** Measuring recall at the final N.
> **Why it's wrong:** conflates candidate-generation loss with ranking quality, making the system
> undebuggable.
> **Do instead:** recall@500 at the candidate-generation boundary, per source.

> **Mistake:** Sequential candidate generation.
> **Why it's wrong:** ~110 ms instead of 40 ms; the budget fails outright.
> **Do instead:** concurrent with `return_exceptions=True` so one dead source degrades rather than fails.

---

## 4.4 Interview follow-ups

### "Why not use an LLM here? The prompt says 'AI recommendation system'."

Because the arithmetic rules it out by about six orders of magnitude. 5k QPS × 500 candidates is 216
billion scorings a day; at roughly 1 ms per candidate that's 2.5 million CPU-hours daily. And the entire
request budget is 150 ms — less than a single LLM call typically takes, so there's no room even for one.
Beyond that, ranking is a well-posed supervised problem with abundant labels, which is where GBDTs are
strongest; LLMs earn their cost where labels are scarce and language matters. I'd still use an LLM here,
but offline: generating item embeddings from descriptions, enriching cold-start items, and producing
explanation text asynchronously.

### "Walk me through why the architecture has to be two-stage."

Budget backwards. 30 ms for ranking across 500 candidates is 0.06 ms per candidate, which admits a GBDT
and essentially nothing else. Then ask what happens without the first stage: scoring 5M items per request
is 432M × 5M scorings a day — about 6 million compute-hours even at 0.01 ms per item. So a single stage
isn't merely inefficient, it's arithmetically impossible. That forces cheap recall over millions and
expensive ranking over hundreds. It's the same shape as
[01](../01_production_rag_system/02_hld.md#retrieval-tier)'s ANN-then-rerank, for the same reason.

### "What's train/serve skew and why does it matter so much?"

It's when a feature is computed differently in training than at serving — typically SQL over the warehouse
for training and application code over Redis at serving. The model then receives inputs it was never
trained on. What makes it dangerous is the signature: excellent offline metrics, mediocre online
performance, and **no error anywhere**, so teams spend weeks debugging the model when the problem is the
data path. The structural fix is a single feature definition compiled to both materializations, so
divergence becomes a build failure. I also log the feature values actually *served* with each impression,
which makes skew detectable after the fact by recomputing and diffing.

### "How would you know your recommender is stuck in a feedback loop?"

By watching catalogue coverage, because every other signal moves the *wrong* way. The mechanism: the model
only ever sees labels for items it chose to show, so unshown items accumulate no positive signal, score
lower, and get shown less — a self-reinforcing narrowing. Meanwhile offline AUC *improves*, because the
model is getting better at predicting clicks within the narrower distribution it created. Accuracy, CTR,
and latency all look fine. So coverage is a first-class metric with an alert on decline, and exploration
is P0 — ε% of slots deliberately given to low-impression items to keep the training distribution honest.

### "Your latency budget has 3 ms of slack. Isn't that too tight?"

It is uncomfortably tight, and I'd say so rather than presenting 147 under 150 as a win. Three
consequences follow. Parallel candidate generation stops being an optimization and becomes mandatory —
serialized it's ~110 ms and the budget fails. Feature hydration for 500 candidates must be one batched
call, since 500 sequential lookups would eat two-thirds of the budget. And there's no room for a network
hop to any external service, which is a second independent reason an LLM can't live in this path. If it
proved too tight I'd cut candidates from 500 to 300 and accept the recall cost, or move diversity into the
ranker's objective instead of a post-processing pass.

### "Offline AUC improved 3%. Do you ship it?"

No — offline metrics are a filter, not a decision. They cheaply reject bad models, but they can't confirm
a good one, because offline evaluation replays impressions that a *different* ranker chose, so it's
measuring performance on a distribution the new model wouldn't have produced. It also can't measure the
things that actually matter for shipping: retention, dwell, catalogue coverage, latency. So I'd use the
offline result to pass the shadow-eval gate, then canary at 1% and ramp, with automatic rollback on any
guardrail breach. A model that passes shadow eval and gets rolled back in canary is the system working
correctly.

### "CTR went up 8% but retention dropped 2%. What do you do?"

Don't ship, and treat it as evidence the objective is wrong rather than the model. That pattern is the
clickbait failure mode: the ranker learned to promote items that attract clicks without delivering
satisfaction. It's exactly why retention is a mandatory guardrail in every A/B and why
[Q1](01_requirements.md#open-questions) — what the true objective actually is — blocks the design.
Optimizing CTR because clicks are the easiest label to collect is the most common way recommender projects
deliver a metric win and a product loss.

### "What breaks first if the catalogue grows to 50M items?"

The in-process ANN index. At 5M items the embedding table is 5 GB and fits in every serving node's memory,
which is what makes 40 ms candidate generation possible with no network hop. At 50M it's 250 GB, so
candidate generation has to become a sharded service — and that introduces an RPC into a budget with 3 ms
of slack. So the honest answer isn't "add a service": it's that **the latency budget must be re-derived**,
most likely by cutting candidates to 300 and accepting lower recall, or by caching aggressively within a
session.

### "Why GBDT rather than a neural ranker?"

Primarily the 0.06 ms per candidate constraint, which a DNN at roughly 1 ms doesn't come close to meeting.
But three secondary reasons matter too: the features are overwhelmingly tabular — counts, rates,
categoricals, recency — which is where GBDTs are genuinely competitive; there's no GPU in the serving path,
so ranking is a library call rather than a service with its own failure modes; and feature importance gives
interpretability that matters when a seller asks why their item stopped being shown. The honest limitation
is that GBDTs can't learn from raw interaction sequences the way a session transformer can, so if
sequential intent turns out to dominate the signal, I'd revisit — with a re-derived latency budget, most
likely by shrinking the candidate set.

### "A user reports the feed looks random. How do you debug it?"

Check predicted-score variance first, before anything else. A corrupt or mis-loaded model — wrong feature
width, truncated file — typically returns near-constant scores for every candidate, so every request
succeeds, latency is normal, no error is logged, and the ranking is effectively arbitrary. It's more common
than a genuinely worse model and trivially detectable from variance, yet invisible to error-rate
monitoring. After that I'd check whether the response was a fallback, then run the skew check, then
per-source recall to see whether candidate generation has partially died.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Two-stage retrieval** | Cheap candidate generation, then expensive ranking | **Arithmetically mandatory** — single-stage needs ~6M compute-hours/day |
| **Candidate generation** | Narrowing 5M items to ~500 | Its recall is the **ceiling** on the whole system |
| **Recall@500** | Fraction of relevant items in the candidate set | Measured at the candidate boundary, where loss becomes unrecoverable |
| **Ranker** | Model scoring candidates | GBDT, forced by the 0.06 ms/candidate budget |
| **GBDT** | Gradient-Boosted Decision Trees | Strong on tabular features, cheap, interpretable, no GPU |
| **ANN** | Approximate Nearest Neighbour search | In-process at 5 GB ⇒ **no network hop** in a 3 ms-slack budget |
| **Two-tower model** | Separate user and item encoders into one space | Produces the embeddings candidate generation searches |
| **Feature store** | System serving consistent features to train and serve | Prevents skew; **the largest cost line**, not inference |
| **Train/serve skew** | Features computed differently in training vs serving | Silent: great offline, mediocre online, no error |
| **Point-in-time correctness** | Features as of the impression timestamp | Prevents leaking the future into training |
| **Label leakage** | Training on information unavailable at prediction time | Inflates offline metrics; detected by temporal-vs-random split gap |
| **NRT features** | Near-real-time aggregates (< 30 s) | Captures in-session intent |
| **Feedback loop** | Model trains on data it generated | **The defining ML risk** — accuracy improves while coverage collapses |
| **Catalogue coverage** | % of items receiving impressions | The **only** reliable feedback-loop detector |
| **Exploration (ε-greedy)** | Deliberately showing unranked items | A measurable engagement cost paid for long-term catalogue health |
| **Position bias** | Higher slots get clicked more regardless of quality | Untreated, the model learns "what we ranked highly gets clicked" |
| **Inverse propensity weighting** | Weighting labels by 1/P(shown) | A more principled position-bias correction than a feature |
| **MMR** | Maximal Marginal Relevance — relevance minus redundancy | The diversity pass; bounded to top-100 for the 10 ms budget |
| **Cold start** | New user or item with no interaction history | Content-based + exploration; first sessions dominate retention |
| **Shadow eval** | Offline comparison against the live model | A **filter** — cheaply rejects bad models |
| **Guardrail metric** | Non-target metric that can block a ship | Stops a CTR win that costs retention |
| **Score variance collapse** | Ranker returning near-constant scores | A corrupt model that looks healthy on every other signal |
| **Popularity fallback** | Static non-personalized list | A blank feed is a broken product; fallback returns `200` |

---

**Files:** [README](README.md) · [Requirements](01_requirements.md) · [HLD](02_hld.md) · [LLD](03_lld.md) · **Production & interview** (this file)
