# 02 · Production & Interview — Banking Fraud Detection

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md)

---

## 4.1 AI-specific concerns

Several rows here read "not applicable" — and **saying so with a reason is part of the answer.** A design that invents LLM concerns for a GBDT system is padding.

| Concern | How this design handles it |
|---|---|
| **Token cost** | **Almost none.** The authorisation path has no LLM. The only LLM use is SAR drafting: ~200/month × (6,000 in + 1,500 out) frontier ≈ **$8/month**. The real cost story is **audit storage (~$4k/mo compressed from ~$31k raw)** and the feature store (~$4–6k) |
| **Latency budget** | Sums to **~33 ms against a 60 ms p99 SLO** — 27 ms headroom held deliberately for GC pauses, slow Redis keys, and noisy neighbours. Rules run **concurrently** with inference; the audit write is **off-path** |
| **Model routing & fallback** | Not model routing — **capability fallback**: model → rules → switch's own policy. Every step **fails open** (approve-with-rules), because declining everything during our outage is worse than the fraud missed |
| **Evaluation** | **Out-of-time, not just out-of-sample**: train months 1–9, validate 10, test 11–12; the validation→test degradation *is* the honest live-decay estimate. CI gates on recall@fixed-FPR, calibration, and **per-segment** performance (a model can improve overall while degrading on one card product). Champion/challenger before promotion |
| **Hallucination / groundedness** | **N/A for scoring** — a GBDT cannot hallucinate. **Applies to SAR drafting**: the LLM writes only from structured case evidence, every factual claim must trace to a `txn_id` or case field, and a human attests before filing |
| **Guardrails** | Not LLM guardrails — **decision guardrails**: reason codes constrained to a governed enum (an ungoverned code fails CI); threshold changes require two-person approval + canary + auto-revert; a decline-rate anomaly detector fires independently of the model |
| **Prompt injection** | **Narrow but real surface.** SAR drafting ingests free-text fields (merchant names, analyst notes, customer descriptions) that could contain injected instructions. Treated as untrusted data; the drafter has **no tools and no write access**; output is reviewed by a human before filing. Everything else in the system consumes typed numerics |
| **Prompt / version management** | `model_version` **and** `threshold_version` persisted on every decision. Both are needed: the same score decides differently under different thresholds, and audits ask about *decisions* |
| **Drift** | Three detectors: **score-distribution shift** (PSI on the score histogram, daily); **feature drift** (per-feature PSI vs the training window); and — the one that actually matters — **recall on the random holdout (FR-14)**, the only signal that catches a fraud typology the ranked queue never surfaces |
| **Label latency** | Structural: chargebacks lag 30–90 days. Retrain **monthly on labels seasoned ≥ 90 days**; `is_biased_sample` separates ranked-queue labels from holdout labels so metrics aren't quietly optimistic |
| **PII / data residency** | Card tokens, never PANs. The SAR drafter is the only component sending data to a third-party model — requires zero-retention terms and region pinning, and a self-hosted model is the fallback if those aren't obtainable |
| **Observability** | Every decision traced: score, features, SHAP, rule hits, both versions, latency, degraded flag. Cost attributable per plane. **Per-segment decline rates** dashboarded, because an aggregate decline rate hides a segment-level catastrophe |
| **Non-determinism** | Tree inference is deterministic. Reproducibility risks are elsewhere: multithreaded training float accumulation (pin `n_jobs` for audit builds) and feature-store race conditions. `feature_vector` is persisted precisely so any decision is replayable |
| **Cold start & capacity** | New cards/devices have absent velocity features → NaN, which the tree handles natively (see [`../../24_xgboost/`](../../24_xgboost/README.md)); the model learns the cold-start regime. Capacity autoscales on **request queue depth**, not CPU |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Alert |
|---|---|
| Scoring p50/p95/**p99** | p99 > 50 ms for 5 min (early, before the 60 ms SLO) |
| **Availability of the score endpoint** | any 30 s window < 99.9% → page |
| **Degraded-decision rate** | > 0.5% of transactions |
| Decline rate, **per segment** | ±20% vs 7-day baseline per segment |
| Step-up rate | > 1% (customer-friction ceiling) |
| **Queue depth vs 1,200 capacity** | > 90% → warn (auto-tighten per FR-13); > 100% → page |
| Case SLA breaches | any |
| Feature age p99 | > 5 s |
| Stream processor consumer lag | > 10 s |
| Audit queue depth / reconciliation gap | any sustained gap → **compliance incident** |
| **Holdout recall** (FR-14) | drop > 10% vs trailing 30 days → suspected new typology |
| Score PSI vs training distribution | > 0.2 |
| Chargeback label arrival | no file in 48 h |

### On-call triage order

1. **Is the score endpoint up and inside p99?** Payments come first. If we're timing out, the switch is running on its own policy and fraud control is effectively off — fail open is safe, but blind.
2. **Is the degraded rate elevated?** Almost always the feature store or stream lag. Confirm fail-open is working (approve-with-rules, not decline-storm) and fix the store — do not "fix" it by tightening thresholds.
3. **Is the decline rate anomalous *per segment*?** An aggregate that looks normal can hide one card product declining 40% of traffic. If a threshold change is in canary, revert first and diagnose after.
4. **Is the queue over capacity?** Confirm displace-or-defer is engaging (nothing dropped), then tighten `T_review`. Escalate to risk ops if it persists — that's a staffing conversation, not an engineering one.
5. **Is holdout recall falling?** Suspect a new fraud typology. Fast mitigation is a **rules patch** (deployable in hours); the model retrain follows in weeks once labels season.
6. **Audit gap?** Backfill from the transaction lake by re-scoring with the recorded model version. Treat as a compliance incident with a written timeline.

### Rollback

| Change | Rollback | Time |
|---|---|---|
| Threshold | Config revert (auto-reverts on canary anomaly) | seconds |
| Model version | Pointer flip; previous artifact stays warm | < 1 min |
| Rules | Config revert; rules are data, not code | seconds |
| Feature definition | **Hard** — requires stream reprocessing. Hence additive-only feature changes, never in-place redefinition | hours |

> That last row is the operational reason feature definitions are versioned and additive: you cannot roll back a feature whose historical values were computed by code that no longer exists.

---

## 4.3 Common mistakes

> - **Mistake:** Failing *closed* when the model or features are unavailable → **Why it's wrong:** a 10-minute outage declines ~1.8M legitimate transactions; the self-inflicted damage vastly exceeds the fraud avoided → **Do instead:** fail open to rules, mark `degraded`, and let the switch apply its own caution.
> - **Mistake:** Quoting an FPR target without checking review capacity → **Why it's wrong:** 0.5% of 259M is 1.3M alerts against a 1,200-case queue; the number is unstaffable and therefore meaningless → **Do instead:** two thresholds — friction (`T_decline`) and headcount (`T_review`) — with the second sized to capacity.
> - **Mistake:** Ranking the analyst queue by probability → **Why it's wrong:** it fills the queue with high-confidence low-value cases and misses the large-exposure moderate-confidence ones → **Do instead:** rank by `P × exposure`, and validate against recovered-loss-per-case-reviewed.
> - **Mistake:** Random train/test split → **Why it's wrong:** leaks future fraud patterns backwards; offline metrics look excellent and collapse in production → **Do instead:** out-of-time splits, and report validation→test degradation as the expected live decay.
> - **Mistake:** Training only on reviewed cases → **Why it's wrong:** selection bias — you only learn outcomes for what the current model already suspected, so the model's blind spots become permanent → **Do instead:** an unbiased random holdout (FR-14), even at the cost of a few analyst-hours.
> - **Mistake:** Synchronous audit write on the payment path → **Why it's wrong:** puts the audit store's availability inside the payment path for 10–20 ms of budget → **Do instead:** durable queue off-path plus reconciliation. *(Note this is the opposite call from [`../07_insurance_claims_automation/`](../07_insurance_claims_automation/) — same mechanism, different domain constraint.)*
> - **Mistake:** Storing the score without the feature vector → **Why it's wrong:** you cannot answer "why was this declined" three years later, which is exactly what a regulator asks → **Do instead:** persist the exact input, model version, **and** threshold version.
> - **Mistake:** Retraining weekly because compute is cheap → **Why it's wrong:** labels lag 30–90 days, so a weekly retrain trains largely on unlabelled rows → **Do instead:** monthly on seasoned labels; refresh only fast-moving features more often.
> - **Mistake:** Unbounded graph traversal → **Why it's wrong:** one hub entity (a shared processor) connects millions of accounts and the walk never terminates — it takes down the graph store → **Do instead:** degree cap, hop limit, node budget.
> - **Mistake:** Monitoring only the aggregate decline rate → **Why it's wrong:** one segment can be catastrophically wrong while the total looks fine → **Do instead:** per-segment dashboards and alerts.
> - **Mistake:** Reaching for an LLM because it's a fraud "AI" system → **Why it's wrong:** 60 ms, tabular features, 259M/day, mandated exact attribution — every constraint points away from it → **Do instead:** GBDT, and be able to say why.

---

## 4.4 Interview follow-ups

**Q: Why not a deep sequence model? Transaction histories are sequences.**
They are, and a sequence model would likely capture longer behavioural patterns better. Two things stop me. First, **explainability**: FR-2 requires a per-decision reason for every decline, derivable inside 60 ms — trees give exact attribution from their structure, while attribution for a sequence model is approximate and slower. Second, **budget**: 6 ms of the 33 ms is the tree; a sequence model over even a modest history doesn't fit alongside a 20 ms feature fetch. Where I *would* use one is offline, in the AML plane, where the budget is 24 hours — and I'd feed its output back as a *feature* to the real-time model rather than replacing it.

**Q: You said fail open. Doesn't that mean fraudsters just need to DDoS your feature store?**
It's a real attack and the reason fail-open isn't the whole answer. Three defences. The rules engine still runs, so known-fraud patterns, sanctions, and hard policy are unaffected — fail-open means "approve-with-rules," not "approve everything." The `degraded` flag is returned in-band, so the switch can apply its own elevated caution during degradation. And the degraded-rate alert pages immediately, so the window is minutes, not hours. What I would *not* do is flip to fail-closed under load, because that converts an availability attack into a guaranteed mass-decline event — which is the outcome the attacker wants anyway.

**Q: Analyst capacity caps you at 1,200 cases. Isn't the obvious answer to hire more analysts?**
It's *an* answer, and it's a business decision with a computable break-even: the marginal analyst is worth hiring while the recovered loss from their 30 daily cases exceeds their loaded cost. Because the queue is ranked by expected loss, marginal value **declines** as you add analysts — case 1,201 is worth less than case 1. So the honest framing is a curve, not a yes/no. Meanwhile the engineering answer is to make each case more valuable: better ranking, richer evidence to shorten review time, and automated disposition for the highest-confidence cases so humans see only genuinely ambiguous ones.

**Q: How do you know the model hasn't gone blind to a new fraud typology?**
This is what the random holdout is for, and it's the requirement most likely to be cut. The ranked queue only shows analysts what the model already suspects, so if a typology emerges that the model scores low, it never enters the queue, never gets labelled, and never gets learned — a silent blind spot that all your accuracy metrics look fine through. FR-14 reviews ~0.2% of above-floor transactions **regardless of rank**, which costs 2–3 of the 1,200 daily cases and is the only unbiased recall estimate available. If holdout recall drops while queue-based recall holds, that's the signature of a new typology.

**Q: Walk me through a regulator asking why a specific transaction was declined 18 months ago.**
Query `decisions` by `txn_id`: it returns the score, decision, governed reason codes, the top-5 SHAP contributions, which rules fired, the **exact feature vector**, the model version, and the threshold version. From the model registry I can retrieve that artifact and re-score the stored vector to reproduce the score bit-for-bit. Because thresholds are versioned separately, I can also show that under the *then-current* threshold this score produced a decline. The feature vector is why the whole thing works — and it's also why audit storage is the dominant cost line, which is a trade-off I'd defend as obviously correct.

**Q: 27 ms of headroom on a 60 ms budget looks wasteful. Why not use it?**
Because p99 in a payment path is dominated by tail events, not average work: a JVM/GC pause, a Redis key that happens to be on a rebalancing shard, a co-tenant saturating the NIC. Budgeting to 55 ms would satisfy the arithmetic and page weekly. If I needed the headroom I'd spend it on more features rather than a bigger model, since feature fetch is the larger and more variable leg — but I'd want a month of p99.9 data first.

**Q: The two thresholds seem like complexity. Why not one?**
Because they gate resources with completely different economics. Crossing `T_decline` spends *customer patience* — it can happen 1.3M times a day and the ceiling is a UX judgement. Crossing `T_review` spends *a scarce human* — it can happen 1,200 times a day and the ceiling is headcount. A single threshold forces one number to serve both, which either floods the queue or under-uses the friction budget. Splitting them also lets risk ops tune friction without touching staffing, which is how the organisation actually works.

**Q: What would you build first?**
The feature store and the streaming aggregation, with the rules engine in front. That combination is independently useful — it improves fraud control on day one without any model — and it's the hard part of the infrastructure. The GBDT is comparatively easy once features exist and labels are flowing. I'd defer the graph/ring detection and SAR drafting entirely; they're valuable but they don't block the authorisation path, which is where the money is.

**Q: What's the biggest risk in this design?**
The label pipeline, not the model. Everything downstream — retraining cadence, drift detection, threshold tuning, even the business case — depends on chargebacks and dispositions arriving reliably with correct timestamps. If that feed is late, partial, or mis-dated, the model silently degrades and every metric that would tell you is computed from the same broken data. I'd invest in label-arrival monitoring and reconciliation earlier than most teams do.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Authorisation path** | The synchronous payment-approval flow the scorer sits inside | Imposes the 60 ms budget and the fail-open requirement |
| **`T_decline` / `T_review`** | Separate thresholds for automated action vs human case creation | Spend customer friction vs spend a scarce analyst — different economics |
| **Fail open** | On internal failure, approve-with-rules rather than decline | Declining everything during our outage is the worse failure |
| **`degraded` flag** | In-band signal that a decision was made without full features | Lets the switch apply caution and excludes the row from evaluation |
| **Velocity features** | Counts/amounts over rolling windows (1 m, 1 h, 24 h, 7 d) | The signal that catches rapid-fire card testing; needs < 2 s freshness |
| **Feature age** | How stale a fetched feature is, exposed as a model input | Lets the model discount stale inputs instead of trusting them |
| **Reason code** | Governed enum explaining a decline, customer- and regulator-facing | Must be derivable in-budget and pre-approved by compliance |
| **SHAP (tree-path)** | Exact per-prediction feature attribution computed from tree structure | Gives explainability in single-digit ms — a key reason for GBDT |
| **SAR** | Suspicious Activity Report filed with the regulator | The only LLM use; drafted by model, **filed by a human** |
| **Structuring** | Splitting deposits to stay under a reporting threshold | Deterministic legal definition ⇒ correctly a rule, not a model |
| **Ring / community detection** | Graph clustering over shared devices/IPs/beneficiaries | Finds coordinated fraud no per-transaction model can see |
| **Degree cap** | Refusing to traverse very-high-degree graph nodes | Hub entities otherwise make traversal unbounded |
| **Expected loss ranking** | Queue priority = `P(fraud) × exposure` | Fills a capacity-capped queue with the most recoverable value |
| **Displace-or-defer** | Queue-full policy that never discards a detection | "Detected and dropped" is indefensible at audit |
| **Label maturity** | Days between transaction and confirmed outcome | Chargebacks lag 30–90 days; training on unseasoned labels is training on noise |
| **Selection bias (labels)** | Only reviewed cases get labelled, so labels reflect current model beliefs | Creates permanent blind spots; countered by the random holdout |
| **Random holdout (FR-14)** | Unbiased sample reviewed regardless of rank | The only detector for a typology the queue never surfaces |
| **Out-of-time validation** | Evaluating on a later period than training | Random splits leak future patterns and flatter the model |
| **Champion / challenger** | Comparing a candidate against the deployed model before promotion | Recency isn't quality; a newer model can be worse |
| **`threshold_version`** | Version stamp on the threshold config applied to a decision | The same score decides differently under different thresholds |
| **Replayability** | Re-scoring a stored feature vector with a stored model version | What makes "why was this declined 18 months ago" answerable |

---

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md) · **Next system:** [`../03_automotive_predictive_maintenance/`](../03_automotive_predictive_maintenance/)
