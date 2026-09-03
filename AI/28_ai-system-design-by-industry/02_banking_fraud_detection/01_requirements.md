# 02 · Requirements — Banking Fraud Detection & Transaction Monitoring

> **Shared block:** [`../00_requirements_all_systems.md#2-banking--fraud-detection--transaction-monitoring`](../00_requirements_all_systems.md#2-banking--fraud-detection--transaction-monitoring) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the latency budget, and the capacity arithmetic. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. The two-system split, made explicit

The shared block states this is two systems. Here is the separation as a contract, because conflating them is the single most common failure in fraud-system design.

| | **Real-time authorisation** | **AML transaction monitoring** |
|---|---|---|
| **Question answered** | "Approve this transaction, now?" | "Is this pattern of activity suspicious?" |
| **Unit of analysis** | One transaction | An account/entity over days–months |
| **Latency** | p99 < 60 ms, in the payment path | < 24 h |
| **Bound by** | **Latency** | **Throughput and analyst capacity** |
| **Consequence of failure** | Payment declined or fraud approved | Missed regulatory report |
| **Regulatory driver** | Card-scheme rules, consumer protection | AML statute (SAR filing) |
| **Model shape** | GBDT on ~200 streaming features | Pattern rules + graph algorithms + GBDT on aggregates |
| **Fail mode** | **Fail open to rules** | Fail behind (queue and catch up) |
| **Can it be down for 10 min?** | No — blocks payments | Yes — 24 h budget absorbs it |

> **Why they must not share a service.** A single service would have to satisfy the stricter of every constraint: 60 ms latency *and* multi-day windowing *and* 99.99% availability *and* graph traversal. That service is impossible to build. Splitting them means each half gets requirements it can actually meet, and the only coupling is a shared feature store plus a shared audit trail.

**What they legitimately share:**

| Shared | Why |
|---|---|
| Feature store (read by both) | Velocity aggregates are useful to both; computing them twice invites divergence |
| Audit store | One replayable record per decision, whichever system made it |
| Label store | Chargeback and analyst dispositions train both |
| Entity resolution | "Same customer/device/beneficiary" must mean one thing |

---

## B. The capacity arithmetic that sets the threshold

This is the most important reasoning in the design, and it belongs in requirements because it constrains the model's objective.

```
Transaction volume:      3,000 TPS × 86,400 s      = 259,200,000 /day
Analyst review capacity: 40 analysts × 30 cases    =       1,200 /day   (ASSUMPTION)

Reviewable fraction = 1,200 / 259,200,000 = 0.00046%  ≈ 4.6 per million
```

Now put the NFR next to it:

```
NFR says: ≤ 0.5% false-positive rate
0.5% of 259.2M = 1,296,000 false positives/day
Against a queue that absorbs 1,200.

⇒ The 0.5% FPR figure is NOT a review-queue target. It cannot be.
```

**Resolving the apparent contradiction — the two thresholds:**

| Threshold | Applies to | Operating point | Volume/day |
|---|---|---|---|
| **T_decline** | Automated decline / step-up in the authorisation path | High score | ~0.5% of transactions get *stepped up* (friction, not review) |
| **T_review** | Human analyst case creation | Much higher score | **≤ 1,200 cases** — sized to capacity |

So the model produces one score consumed by **two thresholds with different economics**:

- Crossing `T_decline` costs a customer some friction (step-up authentication). That can happen 1.3M times a day; the constraint is customer experience, not headcount.
- Crossing `T_review` consumes a scarce human. That must be ≤ 1,200/day, ranked by **score × exposure** so the queue holds the highest-expected-loss cases, not merely the highest-probability ones.

> **The design consequence:** the model's objective is not "maximise recall." It's **maximise recall at `T_decline` subject to a customer-friction ceiling, and maximise recovered exposure in the top 1,200 cases at `T_review`.** Those are different optimisations, and the second is a *ranking* problem over expected loss rather than a classification problem.

**Requirement added here (not in the shared block):**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | Two independently-configurable thresholds | `T_decline` and `T_review` set separately per segment, changeable via audited config without redeploy |
| **FR-12** | P0 | Queue ranked by expected loss | Case priority = `P(fraud) × exposure`, not `P(fraud)` alone; validated against recovered-loss-per-case-reviewed |
| **FR-13** | P1 | Queue-depth feedback | If the queue exceeds capacity for N days, `T_review` auto-tightens and an alert fires — the queue must never silently grow unbounded |

---

## C. Label latency, and what it does to everything

Fraud labels do not arrive when the prediction is made.

| Label source | Typical lag | Reliability |
|---|---|---|
| Customer-reported fraud | 1–30 days | High |
| **Chargeback confirmation** | **30–90 days** | Highest — the ground truth |
| Analyst disposition (queue) | Hours–days | Good, but **only for cases we chose to review** |
| No signal (approved, never disputed) | — | Assumed legitimate — an assumption, not a fact |

### The three consequences

**1. Retraining cadence is bounded by label maturity, not by compute.** A model retrained weekly on 7-day-old data is training largely on unlabelled rows. Sensible cadence: **monthly full retrain on data seasoned ≥ 90 days**, with a lighter weekly refresh of only the fast-moving velocity features.

**2. Evaluation must be out-of-time, not just out-of-sample.** A random split leaks future fraud patterns into training. Required: train on months 1–9, validate on 10, test on 11–12, and report the degradation from validation to test as the honest estimate of live decay.

**3. Selection bias in analyst labels.** We only learn the outcome of cases we *reviewed*. Cases below `T_review` are never investigated, so the label set is biased toward what the current model already suspects — a feedback loop that narrows the model's view over time.

**Mitigation (requirement, not an afterthought):**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-14** | P1 | Random-holdout exploration | A small random sample (**~0.2% of transactions above a floor score**) is reviewed regardless of ranking, to produce unbiased labels |
| **FR-15** | P1 | Label-maturity tracking | Every training row carries a maturity flag; models report what fraction of their training labels were seasoned ≥ 90 days |

> FR-14 costs real analyst time (~2–3 of the 1,200 daily cases). It is worth it: without an unbiased sample there is no way to detect that the model has stopped seeing a whole fraud typology. This is the same argument as exploration in a recommender, and it is routinely cut first and regretted later.

---

## D. Explainability: what "reason codes" actually means

The shared NFR says 100% of declines carry reason codes. Precisely:

| Layer | What it produces | Consumer |
|---|---|---|
| **Reason code** | A fixed enum from a governed list (e.g. `VELOCITY_1H_ANOMALY`, `GEO_IMPOSSIBLE`, `MERCHANT_RISK_HIGH`) | Customer-facing messaging, regulator, dispute handling |
| **Top-5 feature contributions** | SHAP values on the actual scored feature vector | Analyst desktop, model-risk review |
| **Rule hits** | Which deterministic rules fired | Analyst, audit |

**Two rules that constrain the model choice:**

1. **Reason codes must be derivable at scoring time**, inside the 60 ms budget — so SHAP must be computed with the fast tree-path method, and the code mapping must be a lookup, not a second model call.
2. **The mapping from features to reason codes is governed** — a fixed, versioned table reviewed by compliance. The model cannot invent a new reason code, because a customer-facing explanation the bank hasn't approved is a regulatory problem.

> This is what makes a GBDT the right choice and effectively rules out a deep model: exact per-prediction attributions in single-digit milliseconds, from the tree structure itself.

---

## E. Additional non-goals (beyond the shared block)

- **Not** deciding customer remediation or refunds.
- **Not** autonomous account closure or freezing — that requires human authorisation.
- **Not** blocking on sanctions screening (separate regulated system, runs in parallel).
- **Not** merchant-side risk scoring.
- **Not** authoring the SAR (FR-10 drafts; a human reviews, edits, and files).

---

## F. Open questions carried into the HLD

Beyond the shared block's list:

1. **What is the real authorisation timeout allocation?** The 60 ms target derives from a typical ~500 ms end-to-end network budget. If fraud scoring is actually allocated 30 ms, the feature-fetch strategy must change (fewer features, more pre-computation) — this is the single highest-leverage unknown.
2. **Is `T_review` owned by risk or by operations?** FR-11 makes it a config change; someone must own the trade-off between recovered loss and analyst overtime.
3. **Can we get chargeback outcomes as a stream, or only monthly files?** Determines whether label ingestion is continuous or batch, and therefore how quickly a new fraud typology becomes trainable.
4. **Does the bank operate in jurisdictions with differing SAR clocks?** FR-6's 24 h detection target assumes the tightest; if one market requires faster, the AML path needs a priority lane.

---

**Next:** [`02_hld.md`](02_hld.md) →
