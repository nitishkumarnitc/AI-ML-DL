# 00 — Requirements for All 10 Systems

> **This file is the contract every design in this folder must satisfy.** Scope, quantified NFRs, latency budgets, and capacity arithmetic for all twelve systems.
>
> **Read this before any HLD.** Never draw a box before scope, scale, and SLOs are written down — an unscoped design is unfalsifiable, and in an interview, jumping to boxes is the single most common failure.

Prices and availability arithmetic resolve against the **shared assumptions register** in [`README.md`](README.md#-shared-assumptions-register). Numbers are not restated here; where a system's estimate depends on a rate, it names the tier.

---

## Table of contents

| # | System | Archetype | Jump |
|---|---|---|---|
| 1 | E-commerce AI Shopping Agent | C · Transactional agent | [↓](#1-e-commerce--ai-shopping-agent) |
| 2 | Banking Fraud Detection | A · Real-time scoring | [↓](#2-banking--fraud-detection--transaction-monitoring) |
| 3 | Automotive Predictive Maintenance | F · Sensor & edge | [↓](#3-automotive--predictive-maintenance) |
| 4 | Healthcare Clinical AI | B · Grounded RAG | [↓](#4-healthcare--clinical-decision-support--medical-documents) |
| 5 | Logistics Forecasting + Optimisation | E · Forecast + optimise | [↓](#5-logistics--demand-forecasting--route-optimisation) |
| 6 | Manufacturing CV Quality Inspection | F · Sensor & edge | [↓](#6-manufacturing--computer-vision-quality-inspection) |
| 7 | Insurance Claims Automation | G · Document workflow | [↓](#7-insurance--claims-automation) |
| 8 | Media Content Recommendation & Ranking | D · Retrieval & ranking | [↓](#8-media--content-recommendation--ranking) |
| 9 | Real-Estate Search, Valuation & Recommendation | D · Retrieval & ranking | [↓](#9-real-estate--property-search-valuation--recommendation) |
| 10 | Travel Planning & Booking Assistant | C · Transactional agent | [↓](#10-travel--planning--booking-assistant) |
| 11 | HR Recruitment & Candidate Matching | D · Retrieval & ranking | [↓](#11-hr--recruitment--candidate-matching) |
| 12 | Developer Tools — AI Coding Agent | C · Transactional agent | [↓](#12-developer-tools--ai-coding-assistant--swe-agent) |

> **Three candidate systems were cut** because this repo has deeper treatments — lending credit risk
> ([`21/08`](../21_ai-system-design-deep-dives/08_credit_risk_scoring_engine.md)), voice agent
> ([`27/08`](../27_ai-platform-system-design/08_realtime_voice_assistant/README.md)), and enterprise RAG
> ([`27/01`](../27_ai-platform-system-design/01_production_rag_system/README.md)). The findings that came
> out of scoping them are preserved in [cross-system observations](#cross-system-observations).


---

## Shared conventions

### Priority scheme

| Tag | Meaning |
|---|---|
| **P0** | Must exist for v1 to be usable at all. Cutting it cancels the project. |
| **P1** | Needed for production launch. Can ship a private beta without it. |
| **P2** | Wanted; explicitly deferrable. |

### Latency vocabulary

| Term | Meaning | Why it matters |
|---|---|---|
| **p50 / p95 / p99** | Median / 95th / 99th percentile | **A latency target without a percentile is not a target.** p99 is where users churn |
| **TTFT** | Time To First Token | For streaming UIs this *is* perceived latency; total time matters far less |
| **E2E** | End-to-end, request in → last token out | Governs cost and concurrency, not perceived speed |

### How to read a requirements block

Seven subsections per system. The two that decide whether the design is defensible:

- **`.3` NFRs** — every row has a number, a percentile where applicable, and *the reason for that number*. A target without a justification is a guess wearing a suit.
- **`.5` Latency budget / critical arithmetic** — the per-stage decomposition **must sum to the SLO**, with headroom shown. Budgets that don't sum are the most common quantitative error in AI system design.

Where a system's binding constraint isn't latency (e.g. `3` automotive, `5` logistics, `6` manufacturing, `9` valuation), `.5` becomes the arithmetic that *does* size the system, and says so.

---

# 1. E-commerce — AI Shopping Agent

> **Archetype C · Transactional agent.** The one that can spend the user's money.

## 1.1 Problem & users

Shoppers on a large marketplace can't find products through keyword search when their need is expressed as intent rather than keywords ("something warm for a toddler that survives a washing machine, under ₹2,000"). They bounce, or buy the wrong thing and return it. Returns cost more than the lost sale.

**Primary user:** a logged-in retail shopper on mobile, mid-session, with a fuzzy need.
**Primary job:** go from vague intent → a small, comparable, in-stock, in-budget shortlist → purchase, without leaving the conversation.
**"Working" means:** shortlist relevance high enough that add-to-cart rate beats keyword search, and return rate does **not** rise.

## 1.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Accept a natural-language shopping intent and return ≤ 5 candidate products | Each candidate carries title, price, image, stock status, and why-this-matched text |
| **FR-2** | P0 | Ground every product claim in catalogue data | Zero product attributes in the response that aren't in the catalogue record (measured by attribute-level groundedness eval) |
| **FR-3** | P0 | Apply hard constraints exactly | Budget, size, and availability filters are applied as **filters**, never as soft preferences — 100% compliance on an eval set |
| **FR-4** | P0 | Multi-turn refinement with retained context | "Cheaper" / "in blue" / "not that brand" correctly modify the prior shortlist across ≥ 6 turns |
| **FR-5** | P0 | Explicit confirmation before any side-effecting action | Add-to-cart, checkout, and address change each require a distinct user confirmation event; **never inferred from conversational assent** |
| **FR-6** | P1 | Structured comparison of 2–4 products | Returns an attribute-aligned table, not prose |
| **FR-7** | P1 | Personalisation from purchase/browse history | Measurable lift over the non-personalised arm in A/B |
| **FR-8** | P1 | Graceful no-result path | When nothing matches, says so and relaxes exactly one named constraint — **never invents a product** |
| **FR-9** | P2 | Image input ("something like this") | Multimodal retrieval |
| **FR-10** | P2 | Order status / returns via the same agent | Requires auth-scoped order tools |

## 1.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| TTFT | p95 < 1.2 s | Mobile shoppers abandon a silent screen around 2 s; 1.2 s leaves margin for network |
| Full response | p95 < 4 s | Beyond this the conversation feels slower than just scrolling search results |
| Throughput | 200 QPS sustained · 1,200 QPS peak | Peak = 6× from festival-sale diurnal pattern *(assumption)* |
| Availability | 99.9% | Assistant is an enhancement, not the only path — keyword search remains as fallback |
| Constraint compliance | 100% on budget/size/stock | A single wrong-price recommendation is a trust event and a support ticket |
| Groundedness | ≥ 0.98 attribute-level | Product attributes are factual; hallucinating "waterproof" is a returns and liability problem |
| Cost | ≤ ₹1.5 (~$0.018) per conversation | Must sit below contribution margin per incremental order *(assumption)* |
| Catalogue freshness | Price/stock < 60 s stale | Showing an out-of-stock item at a stale price is the worst failure mode |
| Scale | 50M SKUs · 8M DAU | Sizing driver for the retrieval tier |

## 1.4 Non-goals

- **Not** building the payment/checkout system — the agent calls existing checkout APIs.
- **Not** generating product content or images.
- **Not** dynamic pricing — the agent reads prices, never sets them.
- **Not** autonomous purchasing without confirmation (FR-5 is a hard boundary, not a v1 cut).
- **Not** seller-side tooling.

## 1.5 Latency budget (TTFT, p95)

| Stage | Budget |
|---|---|
| Auth + request validation | 20 ms |
| Intent parse + constraint extraction (small model, structured output) | 180 ms |
| Query embedding | 40 ms |
| Candidate retrieval (ANN, top-200, tenant/category filtered) | 90 ms |
| Hard-constraint filter + stock/price join (live) | 110 ms |
| Rerank (cross-encoder, 200 → 20) | 150 ms |
| Prompt assembly | 30 ms |
| **LLM TTFT** (frontier, streaming) | **520 ms** |
| Output guardrail (overlapped with stream) | 60 ms (overlapped) |
| **Total** | **~1,140 ms** — SLO 1,200 ms ✅ **60 ms headroom** |

> Headroom is thin. The first lever if it breaches is a **semantic cache** on common intents (§1.6), which removes the retrieval + rerank + LLM legs entirely on a hit.

## 1.6 Capacity & cost

```
Assumptions: 200 QPS avg · 8 turns/conversation · 25 QPS of *conversations*
             2.16M conversations/day  (25 × 86,400)

Per turn (measured-from-prototype shape, ASSUMPTION):
  input   1,400 tokens  (system prompt 600 + 20 reranked products ~700 + history 100)
  output    280 tokens

Frontier tier, per turn:
  (1400/1e6 × $3.00) + (280/1e6 × $15.00) = $0.0042 + $0.0042 = $0.0084
Per conversation (8 turns):                 ≈ $0.067
Monthly: 2.16M × 30 × $0.067              ≈ $4.34M/month   ← ~50× over the ceiling ⇒ REDESIGN
```

**Levers, cheapest first:**

| Lever | Mechanism | Est. effect |
|---|---|---|
| **Prompt caching** | 600-token system prompt is identical every turn | −35% input cost |
| **Model routing** | ~70% of turns are simple refinements ("cheaper", "in blue") → small model | −60% blended |
| **Semantic cache** | Head intents repeat heavily; assume 25% hit rate | −25% total |
| **Trim context** | Send 8 reranked products to the LLM, not 20 | −30% input |
| **Shorter outputs** | Cap at 150 tokens; the shortlist is UI-rendered, not prose | −45% output |

```
Combined (multiplicative, rounded): $0.067 → ≈ $0.010 / conversation
Monthly: 2.16M × 30 × $0.010 ≈ $648k/month
```

> **Still over.** The honest conclusion: **the agent cannot run on every session at this scale.** Design implication — gate it to *high-intent* sessions (search-with-no-click, or explicit "ask" entry point), assume ~8% of sessions qualify ⇒ **~$52k/month**, which is defensible against 2.16M × 8% × incremental margin. **This is the kind of finding requirements work is for**: the cost ceiling changed the product's triggering rule, not just its implementation.

**Storage:**
```
50M SKUs × 1 embedding × 1024 dims × 4 bytes = 205 GB (float32)
  → int8 quantization → ~51 GB, +HNSW overhead ~40% ⇒ budget ~72 GB RAM
  → shard by category; hot categories (top 20%) resident, tail on disk-backed IVF
```

## 1.7 Assumptions & open questions

**Assumptions:** 8 turns/conversation; 70% of turns are simple; 25% semantic-cache hit rate; 6× festival peak; token shape from a prototype, not production.

**Open questions:**
1. Is the ₹1.5/conversation ceiling per *conversation* or per *converted* conversation? If the latter, the budget roughly 10×'s and the gating rule relaxes.
2. Does the catalogue expose a reliable real-time stock API, or must we tolerate a 60 s cache? Determines whether FR-3 is achievable at 110 ms.
3. Who owns the returns metric? FR-2's groundedness bar is justified by return rate, and if nobody measures that attribution, the bar is unenforceable.

---


# 2. Banking — Fraud Detection & Transaction Monitoring

> **Archetype A · Real-time scoring.** See also [`21/05_fraud_anomaly_detection`](../21_ai-system-design-deep-dives/05_fraud_anomaly_detection.md) — that design goes deeper on explainability for loan-application fraud; this one is transaction-stream and regulatory-reporting driven.

## 2.1 Problem & users

A retail bank must block fraudulent transactions in-flight **and** satisfy AML (Anti-Money Laundering) obligations that require detecting, documenting, and *reporting* suspicious patterns. Rules-only systems produce false-positive rates high enough that analysts can't keep up, and genuine customers get declined.

**Primary users:** (a) the *payment authorisation path* — a machine consumer with a hard timeout; (b) the *fraud analyst* working a queue; (c) the *compliance officer* filing SARs (Suspicious Activity Reports).
**Primary job:** decide approve / decline / step-up in real time, and independently surface suspicious *patterns* for investigation.
**"Working" means:** fraud basis points down, false-positive rate down, and every decision reconstructable months later for a regulator.

> **The structural insight that shapes this design:** these are **two systems**, not one. Real-time authorisation is latency-bound and per-transaction. AML monitoring is pattern-bound, operates over windows of days-to-months, and is throughput-bound. Conflating them is the classic mistake — they share features and share nothing else.

## 2.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Score every transaction in the authorisation path | 100% coverage; a scoring failure must **fail-open to rules**, never block the payment rail |
| **FR-2** | P0 | Return approve / decline / step-up with a reason code | Every decision carries a machine-readable reason code and top-5 contributing features |
| **FR-3** | P0 | Real-time behavioural features | Velocity (txn count/amount over 1 min, 1 h, 24 h, 7 d), device, geo-velocity, merchant-risk |
| **FR-4** | P0 | Full decision audit trail | Model version, feature values, score, threshold, and outcome retained ≥ 7 years, replayable |
| **FR-5** | P0 | Analyst queue with case management | Cases ranked by score × exposure; analyst disposition feeds back as labels |
| **FR-6** | P1 | AML pattern detection (batch/near-real-time) | Structuring, round-tripping, mule-network patterns detected over multi-day windows |
| **FR-7** | P1 | Graph-based ring detection | Shared device/IP/beneficiary linkage surfaces connected-account clusters |
| **FR-8** | P1 | Analyst-facing explanation | SHAP contributions rendered per case, in business language |
| **FR-9** | P1 | Threshold tuning without redeploy | Ops can move the decline threshold per segment via config, with an audit record |
| **FR-10** | P2 | SAR draft generation | LLM drafts the narrative from case evidence; **a human always files** |

## 2.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| Scoring latency | **p99 < 60 ms** (in-path) | Card-network authorisation budget is typically ~500 ms end-to-end; fraud scoring gets a small slice of it |
| Availability (in-path) | 99.99% | Being down blocks payments; this is revenue-critical, hence a rules fallback (FR-1) |
| Throughput | 3,000 TPS sustained · 15,000 TPS peak | Peak = 5× (salary day + festival) *(assumption)* |
| Fraud recall | ≥ 0.85 at ≤ 0.5% FPR | Below 0.85 recall the losses exceed the programme's budget; above 0.5% FPR analyst capacity saturates |
| Analyst capacity | ≤ 1,200 cases/day queue | 40 analysts × 30 cases/day *(assumption)* — **this caps the achievable FPR, not the model** |
| Feature freshness | Velocity features < 2 s stale | A fraudster's second transaction arrives seconds after the first |
| Explainability | 100% of declines have reason codes | Regulatory requirement, not a nicety |
| Audit retention | 7 years, replayable | AML statutory retention *(jurisdiction-dependent — verify)* |
| AML detection latency | Patterns surfaced < 24 h | Aligns with reporting-clock obligations |

> **Note the interaction between rows 4 and 5.** Analyst capacity (1,200 cases/day) against 3,000 TPS × 86,400 = 259M transactions/day means the queue can absorb **0.0005%** of transactions. That, not model quality, is what sets the operating threshold. Designs that quote an FPR target without checking it against review capacity are quoting a number nobody can staff.

## 2.4 Non-goals

- **Not** replacing the rules engine — the ML score is an input; deterministic rules remain for known-fraud and sanctions.
- **Not** sanctions/PEP screening (separate regulated system).
- **Not** card-issuance or chargeback processing.
- **Not** autonomous SAR filing (FR-10 keeps a human in the loop by design).
- **Not** merchant-side fraud tooling.

## 2.5 Latency budget (in-path scoring, p99)

| Stage | Budget |
|---|---|
| Request deserialise + validate | 3 ms |
| Feature fetch — precomputed (feature store, Redis) | 8 ms |
| Feature compute — streaming velocity aggregates | 12 ms |
| Model inference (GBDT, ~500 trees, depth 6) | 6 ms |
| Rules evaluation (parallel with model) | 5 ms (overlapped) |
| Decision combine + reason codes | 4 ms |
| Async audit write (fire-and-forget) | 0 ms (off-path) |
| **Total** | **~33 ms** — SLO 60 ms ✅ **27 ms headroom** |

> Generous headroom is deliberate: p99 in a payment path must survive GC pauses, cache misses, and a noisy neighbour. **Budget for the bad case, not the median.** Note the audit write is explicitly off-path — making it synchronous is a tempting correctness argument that would blow the budget.

## 2.6 Capacity & cost

```
Assumptions: 3,000 TPS avg · 259M transactions/day
Model: GBDT (see ../24_xgboost/) — NOT an LLM. This is the right call:
       tabular features, 60ms budget, explainability mandated ⇒ trees, not tokens.

Inference compute:
  6 ms CPU per score × 259M = 1.55M CPU-seconds/day = 432 CPU-hours/day
  ÷ 24 h ⇒ ~18 vCPU sustained; ×5 peak headroom + HA ⇒ ~120 vCPU provisioned
  120 × $0.04 × 730 h ≈ $3.5k/month                    (CPU tier)

Feature store (Redis):
  Hot keys: 40M active cards × ~2 KB of aggregates = 80 GB
  ⇒ ~$4-6k/month managed, replicated                   (ASSUMPTION: managed pricing)

Audit storage:
  259M/day × 2 KB × 365 × 7 years = 1.32 PB
  ⇒ tiered: 90 days hot (Postgres/OLAP), rest to object storage
  1.32 PB × $0.023/GB ≈ $31k/month at full retention
  ⇒ compress + columnar (Parquet, ~8× ) ⇒ ≈ $4k/month
```

**LLM cost appears only in FR-10 (SAR drafting):**
```
~200 SAR drafts/month × (6,000 in + 1,500 out) tokens, frontier tier
= 200 × [(6000/1e6 × $3) + (1500/1e6 × $15)] = 200 × $0.0405 ≈ $8/month  (negligible)
```

> **The cost story here is the opposite of system 1.** Compute is cheap; **audit storage is the dominant line item**, and 7-year retention is what makes it so. The design lever is compression and tiering, not model choice.

## 2.7 Assumptions & open questions

**Assumptions:** 5× peak; 40 analysts × 30 cases/day; 2 KB per audit record; 40M active cards; managed-Redis pricing.

**Open questions:**
1. What is the **actual** authorisation timeout from the card network, and what slice is allocated to fraud? The 60 ms target is derived from a typical ~500 ms budget — if the real allocation is 30 ms, the feature-fetch strategy changes materially.
2. Is the 7-year retention statutory in every operating jurisdiction? Retention drives the largest cost line.
3. Can analyst headcount flex? If not, FPR is capacity-capped and the model's job changes from "maximise recall" to "maximise recall *at fixed queue depth*" — a different optimisation.
4. Are labels reliable? Confirmed-fraud labels lag 30–90 days (chargeback cycle), which affects retraining cadence — see [`../24_xgboost/`](../24_xgboost/README.md) on delayed labels.

---


# 3. Automotive — Predictive Maintenance

> **Archetype F · Sensor & edge.** Minimal overlap with existing folders — the distinctive constraints are intermittent connectivity and labels that arrive months after the prediction.

## 3.1 Problem & users

A connected-vehicle fleet generates continuous telemetry (CAN bus, ECU diagnostic codes, sensor streams). Component failures currently surface as roadside breakdowns or as warranty claims after the fact. The goal is to predict specific component failures far enough ahead to schedule service, without generating so many false alarms that drivers and dealers ignore them.

**Primary users:** (a) the vehicle owner, who gets a service prompt; (b) the dealer service network, which must be able to act on it; (c) the OEM's warranty and engineering functions.
**Primary job:** for a given vehicle and component, estimate the probability of failure within a horizon (e.g. 30 days / 1,000 km) and trigger a service action when it's actionable.
**"Working" means:** roadside breakdowns down, warranty cost down, and the false-alarm rate low enough that dealers trust the alerts.

> **Two constraints make this unlike the earlier systems.** First, **connectivity is intermittent** — vehicles are off, in basements, or out of coverage, so the edge must buffer and the cloud must tolerate late, out-of-order, gap-ridden data. Second, **ground truth is slow**: whether a prediction was right may not be known for months, and only if the vehicle is actually serviced. That makes the eval strategy the hard part of this design, not the model.

## 3.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Ingest vehicle telemetry with gap tolerance | Handles out-of-order, duplicated, and delayed batches; no data loss on reconnect |
| **FR-2** | P0 | Per-component failure risk with a horizon | Outputs P(failure within 30 days) per monitored component, with a confidence band |
| **FR-3** | P0 | Edge-side pre-aggregation | Vehicle uploads summarised features, not raw high-frequency signals, within a bandwidth budget |
| **FR-4** | P0 | Actionable alert with evidence | Alert names the component, the horizon, the contributing signals, and a recommended action |
| **FR-5** | P0 | Suppress non-actionable alerts | No alert unless a service action exists and the dealer network can fulfil it |
| **FR-6** | P1 | Feedback loop from service outcomes | Dealer disposition (found/not-found, part replaced) returns as a label |
| **FR-7** | P1 | Fleet-level analytics | Cohort failure rates by model/build/geography, for engineering |
| **FR-8** | P1 | Model deployment to edge | Signed OTA model updates, staged rollout, rollback |
| **FR-9** | P2 | Remaining-useful-life estimate | Continuous RUL, not just a binary horizon |
| **FR-10** | P2 | Driver-behaviour context | Driving-style features improve component-specific models |

## 3.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| Prediction cadence | Daily batch per vehicle | Failures develop over weeks; real-time inference buys nothing here |
| Edge → cloud bandwidth | ≤ 5 MB/vehicle/day | Cellular data cost across a large fleet *(assumption)* — this is the binding edge constraint |
| Ingestion throughput | 2M vehicles × ~1 upload/day, bursty on reconnect | Reconnect storms after outages are the real load pattern |
| Alert precision | ≥ 0.70 at the alerting threshold | Below ~0.7, dealers stop trusting alerts — a **socio-technical** limit, not a statistical one |
| Alert lead time | ≥ 14 days median before failure | Shorter than this and there's no time to schedule service |
| Availability (ingest) | 99.9% | Edge buffering absorbs short outages, so ingest availability is less critical than it looks |
| Model staleness | Retrain ≤ monthly | Fleet composition and build changes drift the population |
| Label latency | Accept 30–180 days | Structural, not a target — the eval design must live with it |
| Data retention | 24 months telemetry, 7 years for warranty-relevant events | Warranty and product-liability exposure |

> **Alert precision at 0.70 is the number to defend.** It looks low next to a fraud model's targets. The justification is behavioural: a dealer who investigates three alerts and finds nothing twice stops investigating. The threshold is set by **trust economics**, and the design must therefore make precision tunable per component and per dealer region.

## 3.4 Non-goals

- **Not** safety-critical real-time intervention (no braking/steering) — this is advisory maintenance only, which keeps it out of functional-safety certification scope.
- **Not** the OTA infrastructure itself (consumed, per FR-8).
- **Not** dealer scheduling/DMS integration beyond emitting an alert.
- **Not** autonomous parts ordering in v1.
- **Not** raw-signal cloud storage — FR-3 exists specifically to avoid it.

## 3.5 The arithmetic that actually sizes this system (bandwidth, not latency)

Latency is not the binding constraint — daily batch means seconds don't matter. **Bandwidth and storage do.**

```
Raw telemetry, if uploaded naively:
  ~200 signals × 10 Hz × 86,400 s/day × 4 bytes = 691 MB/vehicle/day
  × 2M vehicles = 1.38 PB/day                          ← impossible on cellular, and unaffordable

Edge pre-aggregation (FR-3) — what the edge computes locally:
  per signal: rolling mean, std, min, max, p95, drift slope, threshold-crossing counts
  ~200 signals × 8 stats × 4 bytes × 24 hourly buckets = 153 KB/vehicle/day
  + DTC (diagnostic trouble code) events, ~2 KB
  + trip summaries, ~10 KB
  ⇒ ~165 KB/vehicle/day  ⇒ well inside the 5 MB budget ✅ (33× headroom)

Cloud ingestion:
  2M × 165 KB = 330 GB/day = ~9.9 TB/month
  Retention 24 months ⇒ ~238 TB
  × $0.023/GB-month (object storage tier) ⇒ ≈ $5.5k/month at full retention
  → columnar + compression (~5×) ⇒ ≈ $1.1k/month
```

> **This is the design decision, and it's made in requirements, not architecture:** a 4,000× reduction comes from deciding *what the edge computes* — not from a better cloud pipeline. Choosing the aggregation window and statistic set **is** the system design. Get it wrong and you either blow the bandwidth budget or discard the signal the model needed.

**Compute:**
```
Daily scoring: 2M vehicles × ~15 components = 30M predictions/day
GBDT/survival model, ~2 ms each = 60,000 CPU-s = 16.7 CPU-h/day
⇒ trivially ~2 vCPU sustained; batch window of 2 h ⇒ ~10 vCPU
10 × $0.04 × 730 ≈ $290/month                        (CPU tier)
```

> **Compute is a rounding error; data movement is the whole problem.** The opposite of system 1, and worth internalising as a pattern for sensor systems.

## 3.6 Cost summary

| Line | Est. monthly |
|---|---|
| Cellular data *(carrier-dependent — excluded, but the 5 MB budget exists to bound it)* | — |
| Telemetry storage (compressed, 24 mo) | ~$1.1k |
| Scoring compute | ~$0.3k |
| Training compute (monthly retrain, ~40 GPU-h) | ~$40 |
| **AI/infra total** | **~$1.5k/month** ⇒ ~$0.0007/vehicle/month |

No LLM in the serving path. An LLM is optional for FR-4's natural-language alert text, at negligible cost (templated text is likely sufficient and more predictable).

## 3.7 Assumptions & open questions

**Assumptions:** 2M vehicles; 200 signals at 10 Hz; 15 monitored components; 5 MB/day bandwidth budget; 165 KB aggregate size; 30-day horizon.

**Open questions:**
1. **What fraction of alerts get serviced?** This determines label availability and therefore whether supervised retraining is even viable, or whether we're stuck with semi-supervised/anomaly methods.
2. Can the edge compute be updated independently of vehicle firmware? If edge aggregation is frozen at build time, the feature set is fixed for the vehicle's life — a severe constraint that would push more logic to the cloud and raise the bandwidth budget.
3. Is 30 days the right horizon for all components? Brake pads and batteries have very different degradation curves; a single horizon is probably wrong.
4. Who owns the false-alarm cost? Without an owner, the 0.70 precision floor won't be enforced.

---


# 4. Healthcare — Clinical Decision Support & Medical Documents

> **Archetype B · Grounded RAG.** Extraction-pipeline depth lives in [`21/02_document_intelligence_agent`](../21_ai-system-design-deep-dives/02_document_intelligence_agent.md) and [`27/05_document_intelligence`](../27_ai-platform-system-design/05_document_intelligence/README.md). This block is about what sits *after* extraction: clinical liability.

## 4.1 Problem & users

Clinicians spend a large share of their time reading and writing documentation, and relevant patient history is scattered across notes, labs, imaging reports, and discharge summaries. The goal is to summarise a patient's record and surface guideline-relevant considerations at the point of care — **without ever making a clinical decision.**

**Primary user:** a physician, mid-consultation, with minutes per patient.
**Primary job:** given a patient and a clinical question, produce a **cited** summary of relevant record content plus applicable guideline references.
**"Working" means:** the clinician reads it, trusts it enough to act, and every statement can be traced to a source document or guideline.

> **The framing that governs every subsequent decision:** this is a **decision *support*** system. The system advises; a licensed clinician decides. That is not a disclaimer — it is an architectural constraint that produces: mandatory citations, a hard refuse path, no autonomous action, and an audit trail proving what the clinician was shown and when.

## 4.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Patient-record summarisation with inline citations | Every clinical assertion links to a specific source document + span; **zero uncited clinical claims** |
| **FR-2** | P0 | Retrieval scoped strictly to the patient in context | 100% — a cross-patient leak is a reportable breach, tested adversarially |
| **FR-3** | P0 | Refuse when evidence is insufficient | Explicit "insufficient information in record" response; **must fire rather than infer** |
| **FR-4** | P0 | Guideline retrieval with provenance and version | Cited guideline, version, and publication date — outdated guidance is a safety issue |
| **FR-5** | P0 | No autonomous clinical action | No orders, prescriptions, or record writes; output is read-only advisory |
| **FR-6** | P0 | Full disclosure audit | What was shown, to whom, when, from which model/prompt version — retained per statute |
| **FR-7** | P1 | Structured extraction from clinical documents | Problems, medications, allergies, labs with units and reference ranges |
| **FR-8** | P1 | Drug-interaction and allergy surfacing | From a maintained clinical knowledge base, **not** from LLM parametric memory |
| **FR-9** | P1 | Ambient documentation draft | Draft note from consultation transcript; clinician edits and signs |
| **FR-10** | P2 | Multilingual patient-facing summaries | Discharge instructions in the patient's language, clinician-approved |

## 4.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| TTFT | p95 < 2 s | Clinician has the patient in front of them; slower and the tool goes unused |
| Full summary | p95 < 8 s | Fits a consultation workflow |
| Availability | 99.9% | Degraded mode = direct record access (the status quo), so not life-critical |
| **Citation accuracy** | **≥ 0.99** | A citation pointing at the wrong span is worse than no citation — it manufactures false confidence |
| Groundedness | ≥ 0.98 | Clinical hallucination is a patient-safety event |
| Refuse-path recall | ≥ 0.95 on unanswerable eval set | FR-3 is only real if it actually fires; this must be measured |
| Cross-patient leakage | **0**, tested | Breach exposure |
| PHI handling | No PHI to third-party providers without BAA + zero-retention | HIPAA *(US; verify per jurisdiction)* |
| Audit retention | Per statute (commonly 6–10 yrs) | Medical-record retention law |
| Cost | ≤ $0.40 per patient summary | *(assumption — must be below the clinician-minute value it saves)* |

> **Citation accuracy at 0.99 is the strictest NFR in this entire folder, and deliberately so.** In a consumer product a bad citation is an annoyance. Here, a summary asserting "no known allergies" with a citation to a document that says otherwise can cause direct harm. This single number forces span-level citation verification as a pipeline stage, not a prompt instruction.

## 4.4 Non-goals

- **Not** diagnosis or treatment recommendation — bounded by FR-5.
- **Not** an autonomous agent with write access to the EHR.
- **Not** a medical device seeking regulatory clearance in v1 *(and note: scope creep here can cross a regulatory line — a stated non-goal with teeth)*.
- **Not** replacing clinical judgement or existing CDS alerting.
- **Not** billing/coding automation.
- **Not** imaging interpretation.

## 4.5 Latency budget (TTFT, p95)

| Stage | Budget |
|---|---|
| Auth + clinician/patient context resolution | 60 ms |
| **Patient-scope authorisation check** (hard gate) | 80 ms |
| Query embedding | 50 ms |
| Retrieval — patient record (filter pushed into ANN query) | 140 ms |
| Retrieval — guideline corpus (separate index) | 120 ms (parallel) |
| Rerank (clinical cross-encoder, 60 → 12) | 220 ms |
| Citation pre-binding (map chunks → source spans) | 90 ms |
| Prompt assembly | 40 ms |
| **LLM TTFT** (frontier) | **900 ms** |
| Output guardrail — PHI + uncited-claim check | 180 ms (overlapped with stream) |
| **Total** | **~1,700 ms** — SLO 2,000 ms ✅ **300 ms headroom** |

> The patient-scope check is **on-path and blocking** at 80 ms. It cannot be overlapped or cached optimistically, because FR-2 admits no failure. Note also that the output guardrail is overlapped with streaming — but if it *fails*, the stream must be **retracted**, which requires the UI to support it. That's a requirement the architecture has to honour, discovered here in the budget.

## 4.6 Capacity & cost

```
Assumptions: 5,000 clinicians · 25 patient-summaries/clinician/day = 125k summaries/day
             (ASSUMPTION: a large hospital network)

Per summary (frontier tier):
  input  6,000 tokens  (12 reranked record chunks ~3,600 + guidelines ~1,600 + prompt 800)
  output   700 tokens
  (6000/1e6 × $3.00) + (700/1e6 × $15.00) = $0.018 + $0.0105 = $0.0285

Retrieval per summary: embedding ~$0.000002 + rerank ~$0.001 ⇒ ~$0.001
Guardrail pass (small tier, 700 in / 50 out): ~$0.00014
Total ≈ $0.030 / summary   ← well inside the $0.40 ceiling ✅

Monthly: 125k × 30 × $0.030 ≈ $112k/month
```

> **Comfortably inside budget — which is itself the finding.** Unlike system 1, cost is not the constraint here; **correctness and compliance are.** The right move is therefore to *spend* the headroom on safety: a second-pass citation verifier, a stricter guardrail model, and self-consistency checks on high-risk claims. Recognising when you have budget to spend on correctness is as much a design skill as cutting cost.

**Storage:**
```
Patient records: 2M patients × 400 documents × 6 chunks = 4.8B chunks   ← too large for one index
  → per-patient scoping means we never search globally: partition by patient_id
  → hot set only (patients with activity in 90 days, assume 8%) = 384M chunks
  384M × 1024 dims × 4 bytes = 1.57 TB float32
  → int8 → 393 GB; partitioned, disk-backed, per-patient sub-index
Guideline corpus: ~200k chunks — small, fully in-memory, replicated
```

> **The partitioning insight:** because FR-2 forbids cross-patient retrieval, this is not a 4.8-billion-vector ANN problem. It's 2 million tiny ANN problems. **That reframing collapses the hardest-looking scaling requirement into an easy one** — and it comes from reading the requirements, not from a better index.

## 4.7 Assumptions & open questions

**Assumptions:** 5,000 clinicians; 25 summaries/day each; 400 documents/patient; 8% 90-day-active; token shape; $0.40 ceiling.

**Open questions:**
1. **Does a BAA with zero-retention exist with the chosen LLM provider?** If not, the design changes fundamentally — self-hosted models only, which alters cost, latency, and quality simultaneously. This is the single highest-leverage open question.
2. Where is the regulatory line between "decision support" and "medical device" in the target jurisdiction? FR-5 is drawn to stay clearly on one side, but FR-8 (drug interactions) edges toward it.
3. Who signs off on the clinical eval set? A groundedness benchmark authored without clinician review isn't a safety argument.
4. Is the guideline corpus versioned and dated at source? FR-4 is unimplementable if the corpus itself has no version metadata.

---


# 5. Logistics — Demand Forecasting + Route Optimisation

> **Archetype E · Forecast + optimise.** Minimal overlap with existing folders. The distinctive difficulty is that **two** hard problems are chained, and the first one's *uncertainty* must survive into the second.

## 5.1 Problem & users

A distribution business must decide, each day, how much inventory to position where, and how to route a finite vehicle fleet to serve the resulting demand. Forecasting and routing are usually built by separate teams, so the router consumes a point forecast and silently inherits all of its error.

**Primary users:** (a) the planner setting inventory positions; (b) the dispatcher who must release routes by a fixed cut-off; (c) drivers executing them.
**Primary job:** produce a demand forecast per SKU × location × day, then a fleet routing plan that respects vehicle capacity, time windows, and driver-hours rules — released before the dispatch deadline.
**"Working" means:** service level maintained at lower total cost (inventory + transport), with plans that survive contact with reality.

> **The design insight that distinguishes a good answer here:** do **not** pass a point forecast to the optimiser. A point forecast tells the router the expected demand and nothing about the risk, so the router optimises confidently against a number that is wrong. Passing **quantiles** (or scenarios) lets the optimiser make an explicit service-level-vs-cost trade-off. Most candidates miss this, and it's the highest-signal thing in the design.

## 5.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Probabilistic demand forecast | Per SKU × location × day, outputs **quantiles** (p10/p50/p90), not a point estimate |
| **FR-2** | P0 | Forecast horizon and granularity | 14-day daily horizon, refreshed daily |
| **FR-3** | P0 | Routing plan respecting hard constraints | Vehicle capacity, delivery time windows, driver hours-of-service, vehicle-site compatibility — **100% feasible plans only** |
| **FR-4** | P0 | Meet the dispatch deadline | Plan released by the cut-off; **a good-enough plan on time beats an optimal plan late** |
| **FR-5** | P0 | Explain the plan to a dispatcher | Per-route cost, load, slack; and why a stop was dropped or deferred |
| **FR-6** | P1 | Re-optimise intraday on disruption | Vehicle breakdown or new priority order triggers partial re-plan without invalidating executed stops |
| **FR-7** | P1 | Service-level control | Planner sets a target fill rate; the system chooses the forecast quantile accordingly |
| **FR-8** | P1 | Forecast accuracy monitoring by segment | WAPE/pinball loss by SKU class, location, horizon |
| **FR-9** | P2 | Promotion/event awareness | Known campaigns and holidays as forecast features |
| **FR-10** | P2 | Driver-preference and fairness terms | Soft constraints on route equity |

## 5.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| **Optimisation wall-clock** | **< 25 min** | Hard dispatch cut-off; this is a deadline, not a target — the solver must be anytime-interruptible |
| Forecast job wall-clock | < 90 min | Must complete before the routing window opens |
| Routing solution quality | Within 8% of best-known bound | Diminishing returns beyond this; feasibility and timeliness matter more |
| Forecast accuracy | WAPE ≤ 22% at SKU×location×day | *(assumption — beats the incumbent statistical baseline)* |
| Pinball loss (p90) | Improves on baseline by ≥ 15% | Quantile quality is what FR-7 depends on; point accuracy alone is insufficient |
| Plan feasibility | **100%** | An infeasible plan is worse than no plan — dispatchers lose trust immediately |
| Availability (batch) | 99.5% within the daily window | Batch, so retry capacity exists; missing the window is the real failure |
| Intraday re-plan | < 3 min | Dispatcher is waiting, on the phone to a driver |
| Scale | 2,000 SKUs × 150 locations × 14 days = 4.2M series · 800 vehicles · 25k stops/day | Sizing driver |

## 5.4 Non-goals

- **Not** the WMS/TMS of record — this produces plans those systems execute.
- **Not** real-time vehicle tracking (consumed for FR-6).
- **Not** long-range network design or facility location (strategic, not daily).
- **Not** procurement or supplier ordering.
- **Not** last-mile crowd-sourced dispatch.

## 5.5 The two-stage arithmetic that sizes this system

Latency isn't the constraint; **the dispatch deadline** is. Two chained jobs must fit inside one window.

```
STAGE 1 — Forecasting
  4.2M series (2,000 SKUs × 150 locations × 14 horizons)
  Global model (single GBDT/DeepAR-style model over all series) — NOT 4.2M per-series models
    → per-series models: 4.2M fits, unaffordable and worse (no cross-series learning)
    → global model: one training run, batch inference over 4.2M rows
  Inference: 4.2M rows × 3 quantiles = 12.6M predictions
    GBDT ~1 ms per row (batched, vectorised: far less) ⇒ ~10 min on 16 vCPU  ✅
  Training (nightly incremental / weekly full): ~6 GPU-h or ~40 CPU-h weekly

STAGE 2 — Routing (the hard one)
  25,000 stops/day · 800 vehicles ⇒ a Vehicle Routing Problem with Time Windows (VRPTW)
  VRPTW is NP-hard. Exact solving at this size is impossible.
  ⇒ Decompose: cluster stops geographically into ~60 regions (≈420 stops each)
                solve each region independently, in parallel
                then a light cross-region repair pass for boundary stops
  Per region: metaheuristic (LNS / guided local search), 60 vehicles × 420 stops
    ~90 s to reach within 8% of bound (ASSUMPTION — must be benchmarked)
  60 regions in parallel on 60 workers ⇒ ~90 s + repair ~120 s ⇒ ~4 min  ✅
  Sequentially it would be 90 min ❌ — parallel decomposition is what makes the deadline
```

**Window arithmetic:**

| Stage | Budget |
|---|---|
| Data extraction + feature build | 25 min |
| Forecast inference (4.2M × 3 quantiles) | 10 min |
| Inventory positioning / order quantities | 5 min |
| Stop-set finalisation | 5 min |
| **Routing (parallel, 60 regions)** | **4 min** |
| Cross-region repair | 2 min |
| Feasibility validation (hard-constraint re-check) | 3 min |
| Plan publication | 2 min |
| **Total** | **~56 min** — window 90 min ✅ **34 min headroom** |

> Headroom exists specifically to absorb a solver that fails to converge and needs its **anytime** best-so-far solution taken at the cut-off. That's why FR-4 says "good-enough on time" — the architecture must be able to interrupt the optimiser and still emit a feasible plan.

## 5.6 Cost

```
Forecasting:  16 vCPU × 1 h/day  = 16 CPU-h/day  ⇒ 480/month × $0.04 ≈ $19
Training:     40 CPU-h/week                       ⇒ 174/month × $0.04 ≈ $7
Routing:      60 workers × 0.2 h/day = 12 CPU-h/day ⇒ 360/month × $0.04 ≈ $14
Intraday re-plan: ~20/day × 3 min × 8 workers      ⇒ ~80 CPU-h/month ≈ $3
Storage (features, forecasts, plans, ~2 TB)                            ≈ $46
                                                     TOTAL ≈ $90/month
```

> **~$90/month — the cheapest system in this folder by two orders of magnitude, and the one with the most engineering difficulty.** No LLM anywhere in the critical path, and adding one would be a mistake. This is worth saying out loud in an interview: **cost and difficulty are uncorrelated**, and reaching for an LLM here would add expense, latency, and non-determinism to a problem that solvers handle optimally.
>
> The only defensible LLM use is FR-5's dispatcher explanation — and templated text from solver output is likely better, because it's deterministic and auditable.

## 5.7 Assumptions & open questions

**Assumptions:** 2,000 SKUs × 150 locations; 25k stops/day; 800 vehicles; 60-region decomposition; 90 s per-region solve time; 90-min window; WAPE 22% baseline.

**Open questions:**
1. **What is the actual dispatch cut-off, and is it negotiable?** Every number in §5.5 derives from a 90-minute window. A 30-minute window forces a different decomposition and a worse solution quality target.
2. Does geographic clustering respect real operational boundaries (depots, driver domiciles, union territories)? Naive k-means clustering produces plans dispatchers reject.
3. How is demand *censoring* handled? Observed sales ≠ demand when stock-outs occurred; training on sales teaches the model to forecast the stock-out, not the demand. **This is the most common silent error in retail forecasting.**
4. What is the true cost asymmetry between under- and over-forecasting? FR-7's quantile selection is meaningless without it.

---


# 6. Manufacturing — Computer Vision Quality Inspection

> **Archetype F · Sensor & edge.** Minimal overlap with existing folders. Distinctive constraints: line-rate inference at the edge, and a defect class that is both rare and constantly evolving.

## 6.1 Problem & users

A production line produces units faster than human inspectors can examine them, so inspection is sampled and defects escape to customers. The goal is 100% automated visual inspection at line rate, catching defects without stopping the line for false positives.

**Primary users:** (a) the line itself — a machine consumer with a fixed cycle time; (b) the quality engineer who reviews flagged units and manages defect taxonomy; (c) plant management, who own scrap and escape rates.
**Primary job:** for each unit, classify pass / fail / review, and localise the defect when failing.
**"Working" means:** escape rate down substantially with a false-reject rate low enough that scrap and line stoppages don't eat the benefit.

> **Two constraints define this system.** First, **inference must complete within the line's cycle time**, on-premises — a cloud round trip is not available at 200 ms/unit, and network loss must not stop production. Second, **defects are rare and open-ended**: you may see 50 examples of a defect class per year, and new defect modes appear when a supplier or tool changes. That pushes the design toward anomaly detection over pure supervised classification.

## 6.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Inspect every unit at line rate | 100% coverage within cycle time; **never** become the line bottleneck |
| **FR-2** | P0 | Pass / fail / review classification | Three-way output; ambiguous units go to human review, not a forced binary |
| **FR-3** | P0 | Defect localisation | Bounding box or mask on the defect, for engineer review and root-cause work |
| **FR-4** | P0 | Operate without network | Full local inference; network loss degrades telemetry and model updates only, never inspection |
| **FR-5** | P0 | Detect novel defect types | Anomaly score independent of the supervised classes; flags unfamiliar appearance as review |
| **FR-6** | P0 | Full traceability per unit | Image, score, model version, decision, and disposition retained and linked to the unit serial |
| **FR-7** | P1 | Human-review feedback loop | Engineer disposition becomes a label; supports few-shot addition of new defect classes |
| **FR-8** | P1 | Staged model rollout to edge | Shadow mode → canary line → fleet, with one-click rollback |
| **FR-9** | P1 | Drift detection on the image distribution | Lighting, lens contamination, or fixture drift detected before accuracy degrades |
| **FR-10** | P2 | Cross-plant model federation | Learn from defects seen at other plants without shipping raw images |

## 6.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| **Inference latency** | **p99 < 150 ms** | Line cycle time is 200 ms/unit *(assumption)*; inspection must fit with margin for image capture |
| Throughput | 5 units/s per line · 12 lines | Sizing driver |
| **Escape rate (false negative)** | ≤ 0.2% of defective units | Customer-facing quality target; the reason the system exists |
| **False reject rate** | ≤ 1.5% | Above this, scrap cost and line interruptions exceed the escape-rate benefit |
| Review queue volume | ≤ 3% of units | Bounded by one quality engineer per line *(assumption)* — **this caps the review threshold** |
| Availability (edge) | 99.9% per line | Downtime = uninspected units or a stopped line |
| Network independence | Full function offline ≥ 72 h | Plant network outages *(assumption)* |
| Model update cadence | ≤ weekly, staged | New defect modes appear with process changes |
| Image retention | 100% of fails + 2% sample of passes, 2 yrs | Traceability and retraining; retaining all passes is unaffordable |
| Traceability | 100% linked to unit serial | Warranty and recall obligations |

> **Escape rate ≤ 0.2% and false reject ≤ 1.5% together are the design.** They're in direct tension: pushing the threshold to catch more defects raises false rejects. Because defects are rare, this is a precision-recall trade-off on a heavily imbalanced problem, and the **review** class exists precisely to relieve the tension — it converts a hard binary decision into a deferred one, at the cost of human capacity (capped at 3%).

## 6.4 Non-goals

- **Not** controlling the line (no actuation) — the system emits a verdict; PLC/MES acts on it.
- **Not** dimensional metrology (separate, higher-precision instruments).
- **Not** root-cause analysis of process drift (surfaces evidence for engineers, doesn't diagnose).
- **Not** cloud inference — FR-4 forbids dependence on it.
- **Not** replacing final human QA on safety-critical units.

## 6.5 Latency budget (per unit, p99)

| Stage | Budget |
|---|---|
| Trigger + image capture (multi-camera) | 25 ms |
| Pre-processing (undistort, crop, normalise) | 15 ms |
| **Supervised defect model (CNN/ViT, edge GPU, INT8)** | **45 ms** |
| Anomaly model (autoencoder / feature-distance) — parallel | 30 ms (overlapped) |
| Decision fusion + thresholding | 5 ms |
| Localisation (only if failing, ~2% of units) | 20 ms (conditional) |
| Verdict emit to PLC/MES | 10 ms |
| Async: image + telemetry write (off-path) | 0 ms |
| **Total (typical)** | **~100 ms** — SLO 150 ms ✅ **50 ms headroom** |
| **Total (failing unit, with localisation)** | **~120 ms** ✅ |

> Running the anomaly model **in parallel** with the supervised model rather than in series is what makes FR-5 free. In series it would add 30 ms to every unit; overlapped, it costs nothing and buys novel-defect detection. Note also that localisation is **conditional** — paying 20 ms only on the 2% of units that fail rather than on all of them.

## 6.6 Capacity & cost

```
Assumptions: 12 lines × 5 units/s × 16 h/day = 3.46M units/day  (ASSUMPTION)

Edge compute (capex-like, amortised):
  1 edge GPU box per line × 12 = 12 boxes
  A10G-class equivalent on-prem ⇒ treat as ~$1.00/h × 24 × 730 × 12 ≈ $210k/month if rented
  → but this is on-prem hardware: assume ~$8k/box capex, 3-yr amortisation
    12 × $8k ÷ 36 months ≈ $2.7k/month  ✅ (the correct framing for edge)

Image storage:
  fails: 2% × 3.46M = 69k/day × 400 KB = 27.6 GB/day
  pass sample: 2% × 3.46M = 69k/day × 400 KB = 27.6 GB/day
  ⇒ 55 GB/day = 1.65 TB/month; 2-yr retention ⇒ ~40 TB
  40 TB × $0.023/GB ≈ $940/month                    (object storage tier)

Training (cloud, weekly):
  ~30 GPU-h/week ⇒ 130 GPU-h/month × $1.00 ≈ $130/month

Central telemetry/monitoring infra                   ≈ $400/month
                                          TOTAL ≈ $4.2k/month ⇒ ~$0.00004/unit
```

> **The cost framing itself is the lesson.** Renting cloud GPUs for edge inference would cost ~$210k/month; **amortised on-prem hardware costs ~$2.7k/month.** For continuous, high-duty-cycle, latency-bound inference, owning the hardware is roughly 75× cheaper — the opposite of the usual cloud-first default. Recognising when duty cycle inverts the build-vs-rent decision is a real design skill.

## 6.7 Assumptions & open questions

**Assumptions:** 12 lines; 200 ms cycle time; 5 units/s; 2% fail rate; 400 KB/image; $8k/edge box; 3-yr amortisation; 16 h/day operation.

**Open questions:**
1. **What is the true cycle time, and is it fixed?** Every latency number derives from 200 ms. A 100 ms cycle time forces model compression or multiple inference boxes per line.
2. How many labelled examples exist per defect class *today*? If it's single digits for most classes, v1 must be anomaly-detection-led with supervised classification added incrementally — a materially different architecture.
3. Is the false-reject cost actually scrap, or rework? If units can be reworked, the 1.5% ceiling loosens considerably and the threshold moves.
4. Who maintains the defect taxonomy? FR-7 assumes an owner for class definitions; without one, labels drift and the model degrades silently.

---


# 7. Insurance — Claims Automation

> **Archetype G · Document workflow.** Extraction depth in [`21/02`](../21_ai-system-design-deep-dives/02_document_intelligence_agent.md) and [`27/05`](../27_ai-platform-system-design/05_document_intelligence/README.md). This block is about the **workflow and the regulated clock**.

## 7.1 Problem & users

Claims arrive as unstructured bundles (forms, photos, invoices, police/medical reports). Manual processing is slow and inconsistent, while regulated settlement timelines run regardless. Fraud detection and fast settlement pull in opposite directions: investigating everything blows the clock; investigating nothing invites loss.

**Primary users:** (a) the claimant, waiting; (b) the claims handler working a queue; (c) the fraud/SIU investigator; (d) compliance, who own the statutory clock.
**Primary job:** ingest a claim, extract the facts, validate against policy coverage, score fraud risk, and route to straight-through settlement, handler review, or investigation.
**"Working" means:** cycle time and cost per claim down, leakage (overpayment) down, and no statutory deadline missed.

> **The tension that defines this design:** regulated timelines are **hard deadlines with penalties**, and fraud investigation is **inherently slow**. A design that maximises fraud detection will miss deadlines; one that maximises speed will pay fraudulent claims. The resolution is **triage** — classify early into fast / review / investigate, and make the routing decision itself the highest-value model in the system.

## 7.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Ingest multi-format claim bundles | PDF, images, email, structured FNOL; assembled into one claim record |
| **FR-2** | P0 | Extract claim facts with confidence | Loss date, cause, amounts, parties, policy number — ≥ 0.96 field F1; **confidence-gated** |
| **FR-3** | P0 | Automated coverage validation | Policy in force at loss date, peril covered, limits/deductibles applied, exclusions checked |
| **FR-4** | P0 | Fraud risk score with reasons | Score + top contributing indicators, routable to SIU |
| **FR-5** | P0 | Triage routing | Straight-through / handler review / SIU investigation, with an audit reason |
| **FR-6** | P0 | Statutory clock tracking | Per-claim deadline tracking with escalation before breach; **no silent breaches** |
| **FR-7** | P0 | Full decision audit | Every extraction, validation, score, and routing decision retained with model/rule versions |
| **FR-8** | P1 | Damage estimation from photos | CV-based repair-cost estimate for motor/property, as a handler aid |
| **FR-9** | P1 | Duplicate & prior-claim linkage | Same-loss and claim-history linkage across the book |
| **FR-10** | P2 | Claimant-facing status assistant | Answers "where is my claim" from the workflow state |

## 7.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| Straight-through rate | ≥ 35% of claims | *(assumption)* — the business case; low-complexity claims settled without human touch |
| Extraction accuracy | ≥ 0.96 field-level F1 | Below this, coverage validation errors create leakage and rework |
| Triage precision (fraud → SIU) | ≥ 0.40 | SIU capacity is scarce; below 0.4 investigators lose confidence in referrals |
| Fraud recall | ≥ 0.60 of known fraud | *(assumption)* — measured against retrospectively confirmed cases |
| Ingestion-to-triage latency | p95 < 15 min | Enables same-day settlement for simple claims |
| **Statutory deadline breaches** | **0** | Regulatory penalties and reputational exposure |
| Handler queue SLA | 95% of reviews actioned within 2 business days | Capacity planning input |
| Availability | 99.9% | Degraded mode = manual intake, which exists today |
| Throughput | 25k claims/day peak (catastrophe events) | **CAT surge is 10× normal** — the real capacity driver |
| Audit retention | Per statute (commonly 7–10 yrs) | Regulatory |

> **The capacity number that matters is the catastrophe surge, not the average.** A hailstorm produces 10× normal claim volume in 48 hours. A system sized for the average collapses exactly when it's most needed, and the statutory clock keeps running. Autoscaling and queue-priority design are therefore functional concerns, not operational afterthoughts.

## 7.4 Non-goals

- **Not** the policy administration system (consumed for coverage data).
- **Not** payment disbursement (hands off to treasury).
- **Not** autonomous denial of claims — denials always require human authorisation.
- **Not** SIU investigation tooling itself (referral only).
- **Not** underwriting (see §3).

## 7.5 Latency budget (ingestion → triage decision, p95)

| Stage | Budget |
|---|---|
| Intake, virus scan, format normalisation | 30 s |
| Document classification (which doc is what) | 25 s |
| OCR (bundle, avg 14 pages, parallel) | 3.5 min |
| Field extraction (VLM/layout, parallel per doc) | 4 min |
| Extraction confidence gate + cross-document reconciliation | 45 s |
| Policy lookup + coverage validation (rules) | 20 s |
| Prior-claim / duplicate linkage | 40 s |
| Fraud scoring (GBDT + graph features) | 15 s |
| Triage decision + routing | 10 s |
| Audit record write (synchronous) | 15 s |
| **Total** | **~10.5 min** — SLO 15 min ✅ **4.5 min headroom** |

> Headroom is sized for CAT surge, when queue depth adds latency that per-stage budgets don't capture. Note extraction is the dominant leg (~7.5 of 10.5 min) — which is where optimisation effort belongs, and where [`27/05`](../27_ai-platform-system-design/05_document_intelligence/README.md) goes deeper.

## 7.6 Capacity & cost

```
Assumptions: 8,000 claims/day normal · 25,000/day CAT peak · 14 pages/claim avg  (ASSUMPTION)
             240k claims/month

OCR:
  240k × 14 pages = 3.36M pages/month
  self-hosted, ~0.8 s/page GPU ⇒ 747 GPU-h/month × $1.00 ≈ $747

Field extraction (VLM, frontier — ASSUMPTION on token shape):
  per claim: 9,000 in (image+text tokens across bundle) + 1,200 out
  240k × [(9000/1e6 × $3.00) + (1200/1e6 × $15.00)] = 240k × $0.045 = $10.8k/month

Document classification (small tier): 240k × 14 × ~$0.00005 ≈ $168
Fraud scoring (GBDT): negligible
Damage estimation CV (FR-8, ~40% of claims): 96k × ~0.5 GPU-s ≈ 13 GPU-h ≈ $13
Claimant assistant (FR-10, small tier, ~2 queries/claim): 480k × $0.0002 ≈ $96

Storage: documents 240k × 14 × 300 KB = 1 TB/month; 10-yr retention ⇒ ~120 TB
  120 TB × $0.023/GB ≈ $2.8k/month (tiered to cold after 1 yr ⇒ ~$900)

                                        TOTAL ≈ $12.7k/month ⇒ ~$0.053 per claim
```

**Levers, if the per-claim ceiling is tighter:**

| Lever | Mechanism | Est. effect |
|---|---|---|
| Layout model for standard forms | FNOL forms are templated | −60% on those pages |
| Route only low-confidence pages to VLM | Cheap extractor first | −45% blended |
| Extract only fields the triage decision needs | Full extraction is wasted on straight-through claims | −30% |

> **The last lever is the interesting one.** For a claim heading to straight-through settlement, you need coverage-relevant fields — not every field on every document. **Extracting lazily, driven by what the decision requires, is a bigger saving than any model swap** and comes from reading the workflow, not the model card.

## 7.7 Assumptions & open questions

**Assumptions:** 8k claims/day normal, 25k CAT; 14 pages/claim; 35% straight-through; token shape; 10-yr retention; VLM extraction cost.

**Open questions:**
1. **What are the actual statutory deadlines per product and jurisdiction?** FR-6 is unimplementable without a definitive clock table, and they differ by line of business.
2. What is SIU's real capacity? Triage precision ≥ 0.40 is only meaningful against a fixed referral budget — the same capacity-caps-the-model dynamic as §2.
3. Is retrospective fraud labelling reliable enough to train on? Confirmed-fraud labels are sparse and biased toward what SIU chose to investigate — a **selection-bias** problem that makes naive recall estimates optimistic.
4. Can coverage validation be fully rule-based? If policy wordings vary too much to encode, FR-3 needs an LLM-assisted path with human confirmation, which changes both cost and the straight-through rate.

---

# 8. Media — Content Recommendation & Ranking

> **Archetype D · Retrieval & ranking.** **Heavy overlap with [`27/06_recommendation_system`](../27_ai-platform-system-design/06_recommendation_system/README.md), which is the reference recsys design in this repo** (candidate generation → ranking → serving). This block's distinctive contribution is the **multi-objective problem**: optimising engagement alone is a known harm, so the objective function itself is the design.

## 8.1 Problem & users

A social/media platform's feed decides what hundreds of millions of people see. Chronological ordering buries relevant content; naive engagement optimisation reliably amplifies outrage, misinformation, and compulsive use — which is a product, regulatory, and reputational problem, not merely an ethical footnote.

**Primary users:** (a) the consumer scrolling a feed; (b) the creator whose reach depends on ranking; (c) trust-and-safety, who own harm outcomes; (d) advertisers, whose inventory is interleaved.
**Primary job:** given a user and a context, select and order ~20 items from a corpus of hundreds of millions, within a page-load budget.
**"Working" means:** long-term retention improves while measured harm indicators do **not** — and creators see a distribution that isn't degenerate.

> **The design point that separates a good answer here:** a single-objective ranker trained on clicks will find that outrage and cliffhangers maximise clicks. **The objective must be multi-term with explicit negative weights** (reports, "see less", regret surveys, session-end dissatisfaction), and the trade-off weights are a *product* decision recorded in config — not something a modeller quietly picks.

## 8.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Rank a personalised feed within the page-load budget | ≤ 20 items returned, p95 within §8.5 budget |
| **FR-2** | P0 | Multi-stage retrieval → ranking | Candidate generation from ~500M items → ~1,000 → ~200 → 20 |
| **FR-3** | P0 | Multi-objective ranking function | Score combines predicted engagement **and** explicit negative signals, with weights in versioned config |
| **FR-4** | P0 | Integrity filtering before ranking | Policy-violating and demoted content removed/downranked **before** the ranker sees it, not after |
| **FR-5** | P0 | Diversity and source constraints | No more than *k* consecutive items from one author/topic; enforced as a post-ranking constraint |
| **FR-6** | P0 | Cold-start for new users and new items | New user gets a non-degenerate feed; new item gets exploration impressions |
| **FR-7** | P1 | Real-time signal incorporation | An interaction affects the next feed load within 30 s |
| **FR-8** | P1 | Creator-side transparency | Why a post did/didn't get distribution, at aggregate level |
| **FR-9** | P1 | Online experimentation | Ranker changes ship behind A/B with guardrail metrics that can auto-halt a rollout |
| **FR-10** | P2 | User-facing controls | "Show me less of this" measurably alters subsequent ranking |

## 8.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| Feed latency | p95 < 350 ms · p99 < 600 ms | Feed is the app's first screen; above ~500 ms scroll-start feels laggy |
| Throughput | 60k feed requests/s peak | *(assumption — large platform)* |
| Availability | 99.95% | The feed *is* the product; degraded mode = cached/chronological feed |
| Corpus scale | 500M candidate items · 300M DAU | Sizing driver for retrieval |
| Signal freshness | Interaction → next load < 30 s | Below this users notice the feed "not reacting" |
| **Harm guardrails** | Reported-content rate, "see less" rate, and regret-survey score must not regress beyond agreed thresholds | **These are release-blocking**, equal in status to engagement metrics |
| Diversity | ≤ 3 consecutive items per author | Prevents single-source domination |
| Cost | ≤ $0.00012 per feed request | *(assumption)* — must sit far below per-impression ad revenue |
| Model refresh | Ranker retrained ≥ daily | Content and interest distributions shift fast |
| Integrity coverage | 100% of served items pass policy filter | A single amplified violation is a reputational event |

> **The NFR that makes this design honest is row 6.** If harm indicators are merely "monitored," engagement optimisation wins every time, because it's the metric with a dashboard. Making them **release-blocking guardrails with thresholds** is the mechanism that converts an intention into an architecture — it forces the experimentation platform (FR-9) to be able to halt a rollout automatically.

## 8.4 Non-goals

- **Not** content moderation classification itself (consumed from the integrity platform, per FR-4).
- **Not** ad auction/pricing — ads are interleaved by a separate system.
- **Not** creator monetisation logic.
- **Not** chronological-only feed (that's the degraded fallback, not the product).
- **Not** cross-platform identity resolution.

## 8.5 Latency budget (feed request, p95)

| Stage | Budget |
|---|---|
| Auth + request context assembly | 15 ms |
| User embedding / feature fetch (feature store) | 30 ms |
| **Candidate generation** — ANN two-tower + several heuristic sources, parallel | **70 ms** |
| Integrity filter (policy + demotion lists) | 25 ms |
| Feature hydration for ~1,000 candidates | 55 ms |
| **Lightweight ranker** (1,000 → 200) | 40 ms |
| **Heavy ranker** (200 → 20, DNN) | 65 ms |
| Diversity / constraint re-ranking | 20 ms |
| Response assembly | 15 ms |
| **Total** | **~335 ms** — SLO 350 ms ✅ **15 ms headroom** |

> Headroom is very thin, which is why the **two-stage ranker** exists: scoring 1,000 candidates with the heavy model would cost ~325 ms alone and blow the budget. Cascading a cheap model then an expensive one on a shortlist is the standard resolution, and the ratio (1,000 → 200 → 20) is tuned against exactly this budget.

## 8.6 Capacity & cost

```
Assumptions: 300M DAU · 12 feed loads/user/day = 3.6B requests/day  (ASSUMPTION)
             peak 60k RPS

NOTE: no LLM in the serving path. This is a DNN-ranker + ANN-retrieval system.
      An LLM at 60k RPS and a 350 ms budget is neither affordable nor fast enough.

Heavy ranker inference:
  200 candidates × ~150 MFLOPs = 30 GFLOPs per request  (ASSUMPTION on model size)
  3.6B requests/day ⇒ served on GPU inference fleet
  assume 1 A10G-class GPU sustains ~1,200 req/s at this budget  (ASSUMPTION — must benchmark)
  60k peak ÷ 1,200 = 50 GPUs; ×2 for HA/regional ⇒ ~100 GPUs
  100 × $1.00/h × 730 ≈ $73k/month                                  (GPU tier)

Candidate generation (ANN over 500M items):
  500M × 256 dims × 4 bytes = 512 GB float32
    → int8 → 128 GB; sharded across ~16 nodes with replicas ⇒ ~48 nodes
    ≈ $25k/month  (ASSUMPTION: managed/self-hosted vector serving)

Feature store reads: 3.6B × ~2 KB ⇒ high-QPS KV; assume ~$30k/month  (ASSUMPTION)
Training (daily retrain + experiments): ~4,000 GPU-h/month ≈ $4k
                                            TOTAL ≈ $132k/month
⇒ per request ≈ $132k / (3.6B × 30) = $0.0000012   ← 100× inside the ceiling ✅
```

> **Cost per request is trivially inside budget; total cost is large.** That inversion matters: at this scale the lever is *not* per-request efficiency but **fleet utilisation and model size**. A 20% ranker-size reduction is worth ~$15k/month — which is why quantisation and distillation are first-class concerns here, not optimisations.

## 8.7 Assumptions & open questions

**Assumptions:** 300M DAU; 12 loads/day; 60k peak RPS; ranker FLOPs and GPU throughput; 500M-item corpus; per-request cost ceiling.

**Open questions:**
1. **Who owns the multi-objective weights, and how are they changed?** FR-3 is only meaningful if there's a named owner and a change-control process. Without one, weights drift toward whatever metric is on the exec dashboard.
2. Are regret/dissatisfaction surveys actually instrumented at sufficient volume to serve as a release guardrail? If not, the harm NFR is unenforceable and needs a proxy.
3. What is the true cost of a delayed signal? FR-7's 30 s target is asserted; if 5 minutes is imperceptible, the real-time infrastructure simplifies enormously.
4. Is creator-side transparency (FR-8) legally required in any operating market? That changes it from P1 to P0 and requires per-item logging at 3.6B/day scale.

---

# 9. Real Estate — Property Search, Valuation & Recommendation

> **Archetype D · Retrieval & ranking**, with a **regression** problem bolted on. Partial overlap with [`27/06_recommendation_system`](../27_ai-platform-system-design/06_recommendation_system/README.md) on the ranking half; the **valuation (AVM)** half is distinctive and carries direct legal exposure.

## 9.1 Problem & users

Buyers can't express what they want in filter terms ("a quiet family house within 30 minutes of the office, near a good school, that won't need a new roof"). Simultaneously, both buyers and sellers need a defensible price estimate. These are two different ML problems sharing one product surface.

**Primary users:** (a) the buyer searching; (b) the seller/agent pricing a listing; (c) the lender or internal risk function consuming valuations.
**Primary job:** (i) retrieve and rank properties against a fuzzy, multi-constraint preference; (ii) produce a point valuation **with an uncertainty interval**.
**"Working" means:** more enquiries per search session, and valuations whose errors are small, unbiased across neighbourhoods, and honestly bounded.

> **The two halves must be designed separately, and saying so is the signal.** Search is a ranking problem where being approximately right is fine. **Valuation is a regression problem where the interval matters as much as the point estimate**, and where systematic error across neighbourhoods is a fair-lending and fair-housing exposure. Conflating them into "an AI property platform" is how these designs go wrong.

## 9.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Natural-language property search | Free-text intent → structured filters + semantic ranking; hard constraints (budget, beds, area) applied as **filters** |
| **FR-2** | P0 | Automated valuation (AVM) with interval | Point estimate **plus** a calibrated prediction interval; interval width reported, never hidden |
| **FR-3** | P0 | Valuation explainability | Top contributing factors and comparable sales ("comps") shown for every estimate |
| **FR-4** | P0 | Refuse to value when data is insufficient | Explicit "insufficient comparable evidence" rather than a wide-interval guess presented as a number |
| **FR-5** | P0 | Fair-housing-safe ranking | **No use of protected characteristics or close proxies** (e.g. demographic composition) in ranking or valuation; tested and documented |
| **FR-6** | P1 | Commute / amenity-aware ranking | Travel time to a user-specified location; school and amenity proximity as features |
| **FR-7** | P1 | Personalised recommendations | Based on saved/viewed properties, with an explicit "why this" |
| **FR-8** | P1 | Valuation drift monitoring | Error tracked by geography and price band; alert on segment-level degradation |
| **FR-9** | P2 | Image-based condition assessment | CV signals from listing photos as valuation features |
| **FR-10** | P2 | Market-trend forecasting | Neighbourhood price-trend projections |

## 9.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| Search latency | p95 < 500 ms | Interactive search; users re-filter constantly |
| Valuation latency | p95 < 2 s | Can be slower than search — it's a considered, single-shot action |
| Availability | 99.9% | Degraded mode = filter-only search; valuation can queue |
| **AVM accuracy (MdAPE)** | ≤ 6% median absolute percentage error | *(assumption)* — industry-competitive; above ~10% users stop trusting it |
| **Interval calibration** | 90% prediction interval contains truth 88–92% of the time | An interval that doesn't cover at its stated rate is worse than no interval |
| **Segment fairness** | No systematic bias > 2 pp in MdAPE across neighbourhood cohorts | **Fair-housing exposure** — systematic under-valuation by area is a legal risk, not a metric miss |
| Refuse rate | Report it; expect 3–8% of requests | FR-4 must fire; a 0% refuse rate means the model is guessing |
| Corpus scale | 8M active listings · 60M historical transactions | Sizing driver |
| Freshness | New listing searchable < 5 min | Competitive listings market |
| Cost | ≤ $0.01 per search · ≤ $0.05 per valuation | *(assumption)* |

> **Interval calibration is the requirement most designs omit, and it's the one that matters most.** A point estimate of ₹1.2 crore is useless without knowing whether the model means ±3% or ±25%. And an *uncalibrated* interval is actively harmful: users treat a stated 90% interval as a 90% interval. This forces conformal prediction or quantile regression rather than a bare point model — a genuine architectural consequence of one NFR row.

## 9.4 Non-goals

- **Not** a formal/regulated appraisal — the AVM is an estimate and must be labelled as such (this boundary keeps the system out of appraisal licensing regimes).
- **Not** mortgage underwriting (see [`21/08`](../21_ai-system-design-deep-dives/08_credit_risk_scoring_engine.md)).
- **Not** transaction/conveyancing workflow.
- **Not** rental yield modelling in v1.
- **Not** ingesting demographic data (deliberately excluded to satisfy FR-5).

## 9.5 Latency budget (search, p95)

| Stage | Budget |
|---|---|
| Auth + request parse | 15 ms |
| Intent → structured filters (small model, structured output) | 140 ms |
| Geo + hard-filter query (Postgres/PostGIS) | 80 ms |
| Semantic ANN over filtered candidate set | 90 ms |
| Commute-time enrichment (cached isochrones) | 60 ms |
| Ranking model (GBDT over ~500 candidates) | 55 ms |
| Diversity + response assembly | 30 ms |
| **Total** | **~470 ms** — SLO 500 ms ✅ **30 ms headroom** |

> **Commute enrichment at 60 ms only works because isochrones are pre-computed and cached.** A live routing API call per candidate would cost hundreds of milliseconds and break the budget — the kind of dependency that looks free in a diagram and isn't. Pre-computation is the design decision hiding in that row.

## 9.6 Capacity & cost

```
Assumptions: 4M searches/day · 200k valuations/day  (ASSUMPTION)

Search:
  intent parse (small tier): 4M × (400 in + 80 out)
    = 4M × [(400/1e6 × $0.15) + (80/1e6 × $0.60)] = 4M × $0.000108 = $432/day ≈ $13k/month
  ranking (GBDT, CPU): negligible (~$400/month of vCPU)
  ANN serving: 8M listings × 768 dims × 4 B = 24.6 GB float32 → int8 ~6 GB — small, in-memory
                                            ≈ $600/month
  ⇒ per search ≈ $0.00011  ← well inside the $0.01 ceiling ✅

Valuation:
  GBDT/quantile ensemble on tabular features — NOT an LLM
  200k/day × ~5 ms CPU ⇒ trivial (~$200/month)
  comps retrieval + explanation assembly: ~$0.0002 each ⇒ ~$1.2k/month
  ⇒ per valuation ≈ $0.0003  ← far inside the $0.05 ceiling ✅

Total ≈ $15.4k/month
```

> **Both ceilings are met with two orders of magnitude of headroom, and the LLM is used only for intent parsing.** The valuation model is deliberately a gradient-boosted quantile ensemble, because FR-2/FR-3 demand calibrated intervals and comparable-sale explanations — neither of which an LLM provides. **Spend the headroom on the fairness testing and calibration monitoring that FR-5 and FR-8 require**, which are labour and infrastructure costs rather than inference costs.

## 9.7 Assumptions & open questions

**Assumptions:** 4M searches/day; 200k valuations/day; 8M listings; 6% MdAPE target; token shape for intent parsing.

**Open questions:**
1. **Which attributes count as fair-housing proxies in the target market?** School quality, for instance, correlates strongly with protected characteristics in many geographies — FR-6 and FR-5 are in direct tension and a lawyer, not an engineer, resolves it.
2. Is transaction-price data complete and timely? AVM accuracy is bounded by comp availability, and in thin markets FR-4's refuse path becomes the common case rather than the exception.
3. Does the product make lending decisions downstream? If a lender consumes the AVM, it inherits regulatory obligations the "not an appraisal" non-goal was meant to avoid.
4. What is the actual tolerance for interval width? A calibrated ±20% interval is honest but may be commercially unacceptable — that's a product decision the design must surface, not hide.

---

# 10. Travel — Planning & Booking Assistant

> **Archetype C · Transactional agent.** Same archetype as §1, and the comparison is instructive: this one is harder because **inventory is third-party, volatile, and multi-leg — a plan can be invalid before the user finishes reading it.**

## 10.1 Problem & users

Planning a multi-leg trip means reconciling flights, accommodation, ground transport, and activities across several third-party systems, each with its own live availability and pricing. Users currently do this across a dozen browser tabs. The goal is a conversational assistant that proposes coherent itineraries and books them.

**Primary users:** (a) the traveller planning a trip; (b) customer support handling failed or partial bookings.
**Primary job:** turn a fuzzy trip intent into a **feasible, priced, currently-available** itinerary, then book it atomically.
**"Working" means:** look-to-book conversion up, and the rate of quoted-then-unavailable itineraries near zero.

> **The constraint that makes this design distinct from §1:** a shopping cart holds items whose price and availability are stable for minutes. **A travel itinerary is a set of held-for-seconds inventory across independent suppliers, where leg 3 becoming unavailable invalidates legs 1 and 2.** That makes booking a **distributed transaction with no two-phase commit available** — and how you handle partial failure *is* the design.

## 10.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Natural-language trip intent → structured search | Dates, origin/destination, travellers, budget, preferences extracted; ambiguity asked about, not assumed |
| **FR-2** | P0 | Multi-supplier live search | Flights, hotels, transfers queried in parallel with per-supplier timeouts |
| **FR-3** | P0 | Coherent itinerary assembly | Legs are time-feasible (connection buffers, check-in times, transfer duration) — **no itinerary that can't physically be executed** |
| **FR-4** | P0 | Price/availability freshness at quote time | Re-validated within 60 s of presenting; stale quotes re-priced with an explicit notice |
| **FR-5** | P0 | Explicit confirmation before booking | Full itinerary + total price + cancellation terms shown; single affirmative confirmation required |
| **FR-6** | P0 | Atomic-or-compensated booking | Either all legs book, or booked legs are **automatically released/refunded** with the user informed |
| **FR-7** | P0 | Idempotent booking | A retried booking never double-books or double-charges |
| **FR-8** | P1 | Itinerary modification | Change one leg; re-validate feasibility of the rest |
| **FR-9** | P1 | Policy compliance (corporate travel) | Enforce travel policy caps and preferred suppliers |
| **FR-10** | P2 | Proactive disruption handling | Monitor booked trips; propose rebooking on cancellation |

## 10.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| First itinerary shown | p95 < 6 s | Supplier search dominates; users tolerate more than in §1 because the task is bigger |
| Follow-up turn | p95 < 2.5 s | Refinements should feel conversational |
| Availability | 99.9% | Degraded mode = single-supplier search or hand-off to web flow |
| **Quote accuracy** | ≥ 99% of confirmed quotes bookable at the quoted price | The single most damaging failure — a quoted price that fails at payment |
| **Booking atomicity** | 100% — no orphaned booked legs | An unreleased hotel booking after a failed flight is a direct financial loss and a support case |
| Idempotency | 100% — zero double-charges | Financial correctness |
| Itinerary feasibility | 100% time-feasible | An impossible connection destroys trust instantly |
| Throughput | 400 searches/s peak | *(assumption)* |
| Cost | ≤ $0.25 per completed booking flow | *(assumption)* — against booking commission |
| Supplier timeout | 3 s hard, degrade to partial results | A slow supplier must not hold the whole search |

## 10.4 Non-goals

- **Not** a GDS/supplier connector platform — consumes existing supplier APIs.
- **Not** payment processing (calls an existing PSP).
- **Not** loyalty-programme management.
- **Not** visa/immigration advice (liability).
- **Not** dynamic pricing or inventory ownership.

## 10.5 Latency budget (first itinerary, p95)

| Stage | Budget |
|---|---|
| Intent extraction + clarification check (small model) | 350 ms |
| Fan-out to suppliers (flights, hotels, transfers — parallel) | **3,000 ms** (hard timeout) |
| Normalisation of heterogeneous supplier responses | 250 ms |
| Feasibility filtering (time-window / connection validity) | 180 ms |
| Itinerary combination + optimisation (top-N coherent bundles) | 600 ms |
| Ranking against stated preferences | 220 ms |
| **LLM narration of the top 3 options** (streaming) | **700 ms** TTFT |
| **Total** | **~5,300 ms** — SLO 6,000 ms ✅ **700 ms headroom** |

> **The 3 s supplier fan-out is 57% of the budget and is not under our control** — which is why FR-2 mandates per-supplier timeouts and partial-result degradation. The design consequence: **the itinerary combiner must produce a useful answer from whichever suppliers replied**, not wait for all. Designs that assume complete supplier data have no answer for the slow-supplier case, which is the common case.

## 10.6 Capacity & cost

```
Assumptions: 400 searches/s peak · 8M search sessions/month · 4% book  (ASSUMPTION)
             320k bookings/month · ~10 turns per session

Per session:
  intent + clarification (small tier): 2 calls × (600 in + 120 out)
    = 2 × [(600/1e6 × $0.15)+(120/1e6 × $0.60)] = 2 × $0.000162 = $0.00032
  narration (frontier, 3 options): 3 turns × (2,200 in + 350 out)
    = 3 × [(2200/1e6 × $3.00)+(350/1e6 × $15.00)] = 3 × $0.01185 = $0.0356
  refinement turns (small tier, ~5): 5 × $0.0003 = $0.0015
  supplier API costs (ASSUMPTION: excluded — commercial terms vary)
  ⇒ ≈ $0.0374 per session

Per completed booking: $0.0374 ÷ 0.04 = $0.935  ← 3.7× OVER the $0.25 ceiling ⇒ REDESIGN
```

**Levers, cheapest first:**

| Lever | Mechanism | Est. effect |
|---|---|---|
| **Template the narration** | Itinerary summaries are highly structured — render from data, use the LLM only for the *comparative* sentence | −70% of narration cost |
| **Narrate top 1, not top 3** | Show 3 as structured cards; narrate only the recommended one | −60% narration |
| **Route refinements to small model** | Already assumed, but extend to narration of simple changes | −15% |
| **Cache by (route, date-window, cabin)** | Popular routes repeat heavily; cache *search shape*, not prices | −25% of supplier calls and intent parsing |

```
Combined: $0.0374 → ≈ $0.010 per session ⇒ ≈ $0.25 per booking  ✅ (just at the ceiling)
```

> **The finding worth stating: LLM narration of structured data is the expensive mistake here.** An itinerary is a table. Rendering it as a table costs nothing and reads better; the LLM's genuine value is the one comparative judgement ("the 07:40 saves two hours for ₹1,800 more"). **Using an LLM where a template suffices is the most common cost error in agent designs** — and this arithmetic is how you catch it before shipping.

## 10.7 Assumptions & open questions

**Assumptions:** 8M sessions/month; 4% book rate; 10 turns/session; 3 s supplier timeout; narration token shape; supplier API costs excluded.

**Open questions:**
1. **Do suppliers support inventory holds, and for how long?** FR-6's compensation logic depends entirely on this. Without holds, atomicity is impossible and the design must instead book sequentially with explicit rollback — a materially different and worse UX.
2. What is the real look-to-book rate? Every per-booking cost figure scales inversely with it; 2% doubles the cost per booking.
3. Are supplier commercial terms per-search or per-booking? Per-search pricing would make the cache lever (above) financially essential rather than merely useful.
4. Who bears the cost of a compensated booking (cancellation fees)? FR-6 is a financial-exposure question before it's an engineering one.

---

# 11. HR — Recruitment & Candidate Matching

> **Archetype D · Retrieval & ranking.** Partial overlap with [`27/06_recommendation_system`](../27_ai-platform-system-design/06_recommendation_system/README.md) on the ranking machinery. What's distinctive — and what makes this the most legally constrained design in the folder — is that **anti-discrimination law makes auditable fairness a functional requirement, not a nice-to-have.**

## 11.1 Problem & users

Recruiters receive far more applications than they can read, so screening is shallow and inconsistent, and good candidates are missed. Automating it is attractive and legally hazardous: automated employment-decision tools are increasingly regulated, and a biased ranker is both unlawful and reputationally severe.

**Primary users:** (a) the recruiter triaging a requisition; (b) the hiring manager; (c) the candidate, who has a right not to be unlawfully screened out; (d) legal/compliance, who must be able to audit any decision.
**Primary job:** for a requisition, rank applicants by evidence of job-relevant capability, with an auditable rationale.
**"Working" means:** time-to-shortlist down and shortlist quality up, with **demonstrated absence of disparate impact** — and no candidate rejected solely by an automated system where that's prohibited.

> **The hard constraint that shapes everything:** in several jurisdictions, automated employment-decision tools require **bias audits, candidate notice, and human involvement in adverse decisions.** So this cannot be "a ranker" — it must be a **ranker plus an audit apparatus plus a human decision point**, and the audit apparatus is as much of the system as the model.

## 11.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Parse applications into structured evidence | Skills, experience duration, education, credentials extracted with ≥ 0.95 F1 |
| **FR-2** | P0 | Rank candidates against a requisition | Ordered list with per-candidate evidence citations pointing to CV spans |
| **FR-3** | P0 | **Never auto-reject** | The system ranks and surfaces; **a human makes every rejection decision** |
| **FR-4** | P0 | Exclude protected characteristics and proxies | Name, age, gender, ethnicity, photo, address, university-as-proxy excluded from features; **tested** |
| **FR-5** | P0 | Bias audit reporting | Selection-rate ratios by protected group computed and reportable on demand (e.g. four-fifths-rule style analysis) |
| **FR-6** | P0 | Full decision audit trail | Model version, features, score, rank, and the human's action, retained per statute |
| **FR-7** | P0 | Candidate-facing explanation capability | On request, explain what evidence the ranking was based on |
| **FR-8** | P1 | Requisition-quality feedback | Flag job descriptions with exclusionary language or unrealistic requirement sets |
| **FR-9** | P1 | Recruiter feedback loop | Advance/reject decisions become training signal — **with bias-propagation monitoring** |
| **FR-10** | P2 | Internal-mobility matching | Match existing employees to open roles |

## 11.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| Ranking latency | p95 < 3 s for a 500-applicant requisition | Recruiter-interactive |
| Parse latency | p95 < 20 s per application (async) | Happens at application time, not view time |
| Availability | 99.9% | Degraded mode = chronological/manual review |
| Parse accuracy | ≥ 0.95 field F1 | Below this, ranking rests on bad evidence |
| **Selection-rate ratio** | ≥ 0.8 across protected groups, monitored per requisition family | Four-fifths-rule style threshold; **release-blocking** |
| **Auto-rejections** | **0** | FR-3 is absolute — a compliance boundary, not a tunable |
| Explainability coverage | 100% of ranked candidates | Statutory in some markets |
| Audit retention | Per statute (commonly 1–3 yrs for applicant records) | Regulatory *(verify per market)* |
| Throughput | 50k applications/day | *(assumption)* |
| Cost | ≤ $0.05 per application processed | *(assumption)* |

> **Two rows here are unusual and worth defending in an interview.** "Auto-rejections = 0" is a **hard architectural boundary** — the system has no reject endpoint, which is a stronger guarantee than a policy saying not to use one. And the selection-rate ratio being *release-blocking* means the fairness metric sits in the CI gate alongside accuracy; a model that improves precision while degrading the ratio **does not ship**. That's the difference between fairness as an intention and fairness as an architecture.

## 11.4 Non-goals

- **Not** interviewing, assessment scoring, or video analysis (video-based inference is deliberately excluded — weak validity and heavy regulatory exposure).
- **Not** compensation recommendation.
- **Not** background checks.
- **Not** sourcing/outbound candidate discovery in v1.
- **Not** any automated adverse decision (FR-3).

## 11.5 Latency budget (rank a 500-applicant requisition, p95)

| Stage | Budget |
|---|---|
| Auth + requisition fetch | 30 ms |
| Requisition → structured requirement vector | 250 ms |
| Candidate evidence fetch (pre-parsed, 500 records) | 180 ms |
| Feature construction (skill overlap, tenure, recency) | 320 ms |
| **Ranking model** (GBDT over 500 candidates) | 240 ms |
| Evidence-citation binding (map score drivers → CV spans) | 400 ms |
| **Fairness telemetry emit** (selection-rate counters) | 60 ms |
| Response assembly | 90 ms |
| **Total** | **~1,570 ms** — SLO 3,000 ms ✅ **1,430 ms headroom** |

> Generous headroom is deliberate. Parsing is **async and off-path** (done at application time, per FR-1's separate 20 s budget), which is what makes interactive ranking cheap. Note that fairness telemetry is **on-path** — emitting it lazily would allow a requisition to be ranked without ever being audited, defeating FR-5.

## 11.6 Capacity & cost

```
Assumptions: 50k applications/day · 1.5M/month  (ASSUMPTION)

Application parsing (the dominant cost — async, at application time):
  CV parsing via layout model + small LLM for normalisation
  per application: 3,000 in + 500 out (small tier)
    = (3000/1e6 × $0.15) + (500/1e6 × $0.60) = $0.00045 + $0.00030 = $0.00075
  1.5M × $0.00075 ≈ $1.1k/month
  OCR for scanned CVs (~25%): 375k × 2 pages × 0.8 GPU-s = 167 GPU-h ≈ $167

Ranking: GBDT, negligible CPU (~$300/month)
Evidence citation binding: ~$0.0002/application-view ⇒ ~$600/month
Fairness audit computation (batch, daily): ~$200/month
                                        TOTAL ≈ $2.4k/month ⇒ ≈ $0.0016 per application
                                        ← 30× inside the $0.05 ceiling ✅
```

> **Very comfortably inside budget, and the right conclusion is to spend the surplus on the audit apparatus** — which is labour and tooling, not inference: maintaining the fairness test suite, adversarial proxy-detection testing (does *any* feature combination reconstruct a protected attribute?), and the human-review capacity FR-3 requires. **In this design the expensive part is the governance, not the model** — and a design that budgets only for inference has missed the actual cost.

## 11.7 Assumptions & open questions

**Assumptions:** 50k applications/day; 25% scanned CVs; token shape; $0.05 ceiling; GBDT ranker.

**Open questions:**
1. **Which jurisdictions' automated-employment-decision rules apply?** They differ substantially on audit frequency, notice requirements, and what counts as an "automated decision." This determines whether FR-5's audit is annual, per-requisition, or continuous.
2. Can protected-attribute data be collected *for auditing purposes*? FR-5 is impossible without it, yet collecting it is restricted in some markets — a genuine catch-22 that usually resolves via voluntary self-identification with separated storage.
3. Does recruiter feedback (FR-9) encode historical bias? Training on past advance/reject decisions will reproduce whatever bias those decisions contained. This is the **most dangerous requirement in the system** and may need to be cut.
4. Is university/employer prestige an acceptable feature? It's predictive and a well-documented socioeconomic proxy — a legal question, not a modelling one.

---

# 12. Developer Tools — AI Coding Assistant / SWE Agent

> **Archetype C · Transactional agent**, with a property no other system in this folder has: **correctness is mechanically verifiable.** Complements [`../23_ai-coding-agents-and-code-eval/`](../23_ai-coding-agents-and-code-eval/README.md), which covers the landscape and code-evaluation methodology as a tutorial — this is the system design.

## 12.1 Problem & users

Developers spend substantial time on mechanical changes (adding a field through five layers, writing tests, fixing a failing build, migrating an API). The goal is an agent that takes a task description or an issue and produces a **reviewed-ready pull request** in a large existing repository.

**Primary users:** (a) the developer delegating a task; (b) the reviewer who must trust the diff; (c) platform/security, who own what an agent may touch.
**Primary job:** given an issue and a repo, produce a minimal, correct, tested diff — or **fail honestly and explain why**.
**"Working" means:** a meaningful share of tasks merge with light review, and the agent never silently breaks something.

> **The single most exploitable property of this domain:** unlike every other system here, **the agent can check its own work.** Tests either pass or they don't; the type-checker either accepts the code or it doesn't. That turns the design from "generate plausible output" into a **closed verification loop** — and the quality of the design is almost entirely the quality of that loop, not the model.

## 12.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-1** | P0 | Repo-scale context retrieval | Locate relevant files/symbols in a repo too large for any context window; retrieval quality measured independently |
| **FR-2** | P0 | Agentic edit → run → repair loop | Apply edit, run tests/type-check, read failures, repair — with a **hard step and token budget** |
| **FR-3** | P0 | Verification before proposing | No PR proposed unless the project's build, type-check, and test suite pass |
| **FR-4** | P0 | Minimal diffs | No unrelated reformatting or drive-by changes; diff size reported |
| **FR-5** | P0 | Sandboxed execution | Code runs in an isolated environment with **no production credentials** and egress restrictions |
| **FR-6** | P0 | Honest failure | On budget exhaustion or repeated failure, report what was attempted and why it failed — **never propose an unverified diff** |
| **FR-7** | P0 | No autonomous merge | Agent opens a PR; **a human merges** |
| **FR-8** | P1 | Test authoring | Generate tests for the change, and detect when a test was weakened to pass |
| **FR-9** | P1 | Injection resistance | Repo content, issue text, and dependency code are **untrusted data, never instructions** |
| **FR-10** | P2 | Multi-repo / cross-service changes | Coordinated changes across services with dependency ordering |

## 12.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| Task wall-clock | p50 < 6 min · p95 < 25 min | Slower than this and developers context-switch away and stop using it |
| **Task success rate** | ≥ 35% of scoped tasks produce a mergeable PR | *(assumption)* — below ~25% review overhead exceeds the benefit |
| **False-success rate** | ≤ 1% | A PR that passes CI but is wrong is the **most damaging** failure — it consumes trust irrecoverably |
| Verification coverage | 100% of proposed PRs pass build + tests | FR-3 is absolute |
| Availability | 99.5% | Asynchronous developer tool; queuing is acceptable |
| Throughput | 2,000 tasks/day | *(assumption)* |
| **Cost per task** | ≤ $2.50 | *(assumption)* — must be well below the developer-hour it saves |
| Sandbox isolation | 100% — no credential or network escape | Security boundary |
| Step budget | ≤ 60 tool calls, ≤ 400k tokens per task | Unbounded agent loops are a real, expensive production failure |
| Injection resistance | 0 successful privilege escalations in a red-team suite | See [`21/06`](../21_ai-system-design-deep-dives/06_prompt_injection_defense.md) |

> **The false-success rate at ≤ 1% deserves the most attention.** An agent that fails visibly is merely unhelpful; an agent that produces a confidently wrong, CI-passing diff **transfers its error into the codebase with a human's approval attached**. This is why FR-8's "detect a weakened test" matters — the most common way an agent achieves a passing suite is by making the test agree with the bug.

## 12.4 Non-goals

- **Not** autonomous merging or deployment (FR-7).
- **Not** production incident remediation.
- **Not** architectural design decisions.
- **Not** a code-review replacement (it produces work *for* review).
- **Not** access to production data or secrets (FR-5).
- **Not** dependency upgrades with breaking-change judgement in v1.

## 12.5 The budget that sizes this system (steps and tokens, not latency)

Latency matters, but the binding constraint is **the agent loop's budget** — this is where cost and failure both live.

```
Per task, observed shape (ASSUMPTION — must be measured per repo):
  context retrieval          ~4 tool calls
  read files                ~10 tool calls
  edit                       ~8 tool calls
  run tests                  ~6 invocations
  repair cycles              ~3 iterations × 6 calls = 18
                            ⇒ ~46 tool calls typical, 60 cap

Token accounting (frontier tier, with prompt caching on the repo-context prefix):
  input:  46 calls × ~9,000 tokens avg = 414k  → but ~70% cache-hit on the stable prefix
          effective ≈ 124k fresh + 290k cached
  output: 46 × ~700 = 32k

  fresh input : (124,000/1e6 × $3.00)  = $0.372
  cached input: (290,000/1e6 × $0.30)  = $0.087   (ASSUMPTION: cached reads ~10% of input)
  output      : (32,000/1e6 × $15.00)  = $0.480
                                   ⇒ ≈ $0.94 per task  ✅ inside the $2.50 ceiling

Sandbox compute: ~8 min × 2 vCPU = 0.27 CPU-h × $0.04 ≈ $0.011  (negligible)
Failed tasks still cost: assume 65% fail ⇒ effective cost per MERGED PR
  = $0.94 / 0.35 ≈ $2.69   ← slightly over the per-task ceiling when measured per success
```

> **The distinction between cost-per-task and cost-per-success is the whole point of this arithmetic.** At 35% success, every merged PR carries the cost of ~1.9 failed attempts. Two levers: (a) **fail faster** — abandon at 25 steps when no test has moved from red to green, cutting failed-task cost by ~50%; (b) **triage tasks upfront** with a cheap classifier, declining tasks unlikely to succeed rather than burning budget on them. **Declining work is a design feature here**, and FR-6's honest failure makes it acceptable to users.

**Latency budget** (p50 task, for completeness):

| Stage | Budget |
|---|---|
| Repo index lookup + context retrieval | 20 s |
| Sandbox provision (warm pool) | 15 s |
| Agent loop (~46 calls, LLM + tool execution) | 3.5 min |
| Test suite runs (6 × ~20 s) | 2 min |
| Diff assembly + PR creation | 25 s |
| **Total** | **~6.3 min** — p50 SLO 6 min ⚠️ **marginally over** |

> Fix: **warm sandbox pools** (removing the 15 s provision) and **incremental/affected-test selection** rather than the full suite — running only tests touching changed files typically cuts test time by 60–80% and brings p50 to ~4.5 min. Note this makes FR-3's "test suite passes" mean *affected tests*, with a full suite run before merge — a scope decision the requirement must state explicitly.

## 12.6 Capacity & cost

```
Assumptions: 2,000 tasks/day · 60k/month · 35% success  (ASSUMPTION)

LLM:      60k × $0.94                        ≈ $56.4k/month
Sandbox:  60k × 0.27 CPU-h × $0.04           ≈ $650/month
          + warm-pool idle capacity (~40 vCPU) ≈ $1.2k/month
Repo indexing (incremental, ~500 repos):
  embeddings: 500 repos × 50k chunks × 400 tokens × $0.02/1M ≈ $200 one-off
  re-index on push (incremental)                             ≈ $400/month
Vector storage: 25M chunks × 768 dims × 4 B = 77 GB → int8 ~19 GB ≈ $300/month
                                        TOTAL ≈ $59k/month
⇒ per merged PR ≈ $59k / (60k × 0.35) = $2.81
```

> Against a loaded developer hour, ~$2.81 per merged PR is defensible **if** the PR genuinely saves more than a few minutes of review-adjusted work. **That's the number to argue about in a design review** — not the model choice. And note the LLM is 96% of cost here, which is the opposite of §2 and §6: for agentic loops, token spend genuinely dominates, because the loop multiplies every call.

## 12.7 Assumptions & open questions

**Assumptions:** 2,000 tasks/day; 46 tool calls/task; 70% prompt-cache hit; 35% success rate; token shape; $2.50 ceiling.

**Open questions:**
1. **How long does the test suite actually take?** Every latency number depends on it. A 40-minute suite makes the interactive loop impossible and forces a fundamentally different design (batch/overnight agents).
2. What is the real task success rate on *this* repo? 35% is an assumption; measured rates vary enormously with codebase quality, test coverage, and task scoping. **This single number decides whether the product is viable.**
3. Is there a reliable signal for "test was weakened to pass" (FR-8)? Without it, false-success rate is unenforceable — mutation testing or diff-analysis of test files are candidates.
4. What is the blast radius if the sandbox is escaped? FR-5 assumes isolation; the security review, not the design doc, decides whether that assumption holds.

---

## Cross-system observations

Worth internalising, because they generalise well beyond these twelve.

| Observation | Where it shows |
|---|---|
| **Human review capacity — not model quality — sets the operating threshold** | §2 (1,200 analyst cases/day caps achievable FPR against 259M transactions) · §6 (3% review-queue ceiling) · §7 (SIU capacity caps triage precision) · §11 (human-decision requirement is the throughput limit) |
| **Cost and engineering difficulty are uncorrelated** | §5 is ~$90/month and the hardest design in the set; §8 is ~$132k/month and architecturally conventional |
| **The dominant cost line is rarely the LLM — except in agent loops** | Not the LLM: §2 audit storage · §3 data movement · §6 edge hardware · §8 GPU ranker fleet. **Is** the LLM: §12 at 96% of cost, because an agent loop multiplies every call |
| **Requirements work changes the product, not just the implementation** | §1's cost ceiling forced a change to *when* the agent triggers (all sessions → ~8% high-intent); §12's cost-per-success arithmetic forced upfront task triage |
| **Cost per attempt ≠ cost per success** | §12: at 35% task success, every merged PR carries ~1.9 failed attempts ⇒ $0.94/task becomes $2.81/merged PR. §10: 4% book rate turns $0.037/session into $0.94/booking |
| **Using an LLM where a template suffices is the most common cost error** | §10's itinerary narration (an itinerary is a table); §5's dispatcher explanation; §3's alert text |
| **Two requirements can interact in ways neither reveals alone** | §7's statutory clock × fraud investigation; §9's commute-ranking (FR-6) × fair-housing exclusion (FR-5); §11's recruiter-feedback loop × bias propagation. Also seen while scoping the cut enterprise-RAG system: a semantic cache silently breaks per-user permission isolation unless the cache key includes a permission-set hash — see [`27/01`](../27_ai-platform-system-design/01_production_rag_system/README.md) |
| **Reframing can collapse the hardest-looking constraint** | §4's apparent 4.8-billion-vector ANN problem is really 2M tiny per-patient indexes, because cross-patient retrieval is forbidden |
| **Budget for the bad case, not the median** | §2's 27 ms p99 headroom exists for GC pauses, cache misses, and noisy neighbours |
| **Say it out loud when a budget doesn't sum** | §12's p50 comes out marginally over and names warm pools + affected-test selection as the fix. Seen while scoping the cut voice agent: the turn-latency budget came out 80 ms over and the honest move was naming speculative TTS rather than massaging numbers — see [`27/08`](../27_ai-platform-system-design/08_realtime_voice_assistant/README.md) |
| **Choosing *not* to use an LLM is a design decision worth defending** | §2 (60 ms + mandated explainability ⇒ GBDT) · §5 (solvers are optimal; an LLM adds cost, latency, non-determinism to a solved problem) · §8 (60k RPS at 350 ms) · §9 (calibrated intervals need quantile regression, not tokens) |
| **On-path vs off-path is a domain decision, not a performance one** | §2 writes audit **off-path** (a synchronous write would blow a payment budget); §7 writes **on-path** (a decision communicated but unrecorded is a compliance defect); §11 emits fairness telemetry **on-path** (lazy emission would let a requisition go unaudited). Same mechanism, three different calls |
| **When you have cost headroom, spend it on correctness** | §4 (comfortably under budget ⇒ fund citation verification) · §9 (100× headroom ⇒ fund calibration + fairness monitoring) · §11 (30× headroom ⇒ fund the audit apparatus, which is labour not inference) |
| **Verifiability changes the whole design** | §12 is the only system whose output can be mechanically checked — so the design is a verification loop, and the model is almost incidental |
| **Fairness/harm metrics only work as release gates** | §8's harm guardrails and §11's selection-rate ratio are **release-blocking**, sitting in CI beside accuracy. Merely "monitored" fairness loses to whatever metric has an exec dashboard |

---

## Next

Per-system HLD and LLD sets build on these requirements. Each system's folder carries `01_requirements.md` (its block here, expanded with system-specific depth), `02_hld.md`, `03_lld.md`, and `04_production_and_interview.md`. See the [build status table](README.md#-build-status).

**Do not restate numbers from this file in a per-system requirements file.** Reference them and add only system-specific depth — duplicated numbers drift out of sync, which is exactly the failure mode the shared-register discipline exists to prevent.
