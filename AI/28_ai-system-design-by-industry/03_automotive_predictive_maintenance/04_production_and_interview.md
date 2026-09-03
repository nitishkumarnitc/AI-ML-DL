# 03 · Production & Interview — Automotive Predictive Maintenance

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md)

---

## 4.1 AI-specific concerns

Several rows are "not applicable," and **saying so with a reason is part of the answer** — this is a survival-model system with no LLM in any path.

| Concern | How this design handles it |
|---|---|
| **Token cost** | **Zero.** No LLM anywhere in the serving path. Alert text is templated from SHAP factors, deliberately — see the reasoning in [`03_lld.md`](03_lld.md#32-api-contracts). The real cost story: **storage ~$1.1k/mo, scoring ~$290/mo, training ~$40/mo** ⇒ ~$0.0007/vehicle/month |
| **Latency budget** | **Not the binding constraint.** Daily batch means seconds are irrelevant; the sizing arithmetic is **bandwidth** (5 MB/vehicle/day) and the **batch window** (2 h for 30M predictions). The one latency-sensitive path is DTC hard-fault dispatch, which bypasses batch |
| **Model routing & fallback** | Not model routing — **graceful degradation on data quality**. Coverage < 0.35 ⇒ predict-but-never-alert; staleness > 3 days ⇒ suppress. The fallback is *silence*, which is correct here: a wrong alert costs trust, a missing alert costs one deferred service |
| **Evaluation** | The hardest part of this design. Four signals, none sufficient alone: dealer-disposition precision (biased toward high scores), **warranty-claim recall** (primary, lags 3–12 months), the **non-alerting holdout cohort** (FR-17, non-safety only), and survival calibration. CI gates on: per-component precision at the alerting threshold, median lead time ≥ 14 days, and calibration drift |
| **Hallucination / groundedness** | **N/A** — a survival model cannot hallucinate, and alert text is templated rather than generated. This is a deliberate choice: templated text is deterministic, translatable, and reviewable by the safety/legal organisation |
| **Guardrails** | Not LLM guardrails — the **actionability gate** is the guardrail: per-component precision floors, parts availability, dealer capacity, region trust suppression, cooldown. Plus a hard rule that safety-relevant components are never placed in the holdout |
| **Prompt injection** | **N/A.** Every input is a typed numeric from a signed vehicle certificate. The nearest analogue is **telemetry spoofing** — mitigated by per-vehicle mTLS, CRC, and plausibility bounds on statistics |
| **Prompt / version management** | Not prompts — **two version axes that both matter**: `model_version` and `config_version` (the edge statistic set). Features computed under different `config_version`s are not comparable, so models are trained per config family and both versions are persisted on every prediction |
| **Drift** | Three detectors: **statistic-distribution drift per signal per config** (catches an edge aggregation bug in days rather than months); **cohort drift** (fleet composition changes as new build years enter); and **calibration drift** on the holdout. The first is the important one — it's the only fast signal in a system with 30–180 day labels |
| **Label latency** | Structural, 30–180 days. Handled by: seasoned-labels-only training (≥ 90 days), **intervention flags** so prevented failures are treated as censored rather than false positives, and monthly retrain cadence bounded by label maturity rather than compute |
| **PII / data residency** | VIN is personal data in several jurisdictions when linked to an owner. Telemetry stored keyed by VIN with owner linkage held separately; region-pinned storage; consent basis distinct from any insurance/driver-scoring use (an explicit non-goal) |
| **Observability** | Every prediction persisted with `model_version`, `config_version`, `feature_coverage`, and the gate's `suppress_reason`. **`suppress_reason` is the most-used field in analysis** — it's how you separate "we didn't detect it" from "we detected it and chose not to alert" |
| **Non-determinism** | Survival scoring is deterministic. Real risks: floating-point differences in edge aggregation across ECU hardware revisions (bounded by tolerance checks), and training non-determinism (pin thread counts for audit builds) |
| **Cold start & capacity** | New vehicles have no own-baseline, so **cohort deviation carries the prediction** until ~60 days of history accrues. Batch capacity autoscales on partition count; the 2 h window has slack for late arrivals |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Alert |
|---|---|
| Upload rate vs fleet baseline | drop > 15% for 2 h → suspect carrier/regional outage |
| **Per-vehicle byte budget** — p95 and cap-hit count | cap hits > 0.5% of fleet |
| Ingest queue depth / 429 rate | sustained backpressure > 30 min |
| Late arrivals (> 2 days) | > 10% of windows |
| **Statistic distribution per signal per `config_version`** | PSI > 0.2 vs the config's baseline → **suspect an edge aggregation bug** |
| `degraded_upload` rate | > 1% of vehicles |
| Feature coverage p50/p05 | p05 < 0.4 |
| Batch job wall-clock | > 90 min (window is 2 h) |
| Suppression breakdown by reason | any reason > 30% of would-be alerts |
| **Per-component precision** (dealer dispositions, 90 d) | below the component's floor |
| **Per-dealer / per-region found-rate** (FR-14) | < 0.45 → auto-suppress + investigate |
| Median lead time | < 14 days |
| Alerts aged out unresolved | > 25% |
| Warranty label arrival | no file in 45 days |

### On-call triage order

1. **Is upload rate normal?** A fleet-wide drop is usually a carrier or certificate issue, not ours. Edge buffers absorb 7 days, so this is urgent-but-not-emergency — confirm buffering is working and that predictions are being *suppressed* on staleness rather than issued on stale data.
2. **Is statistic distribution drifting on a specific `config_version`?** This is the highest-value alarm in the system: it's the only detector that catches an edge aggregation bug **before labels would reveal it months later**. Roll back the config; re-derive features from the immutable landing zone.
3. **Is precision below floor for a component?** Suppress that component's alerts in the affected region first (protecting trust), then diagnose. Do not "fix" it by raising the threshold globally — that trades recall everywhere for a local problem.
4. **Is a region's dealer found-rate collapsing?** Could be the model, or could be a parts/process problem at the dealer end. Check the disposition mix: lots of `no_fault_found` implicates the model; lots of `not_serviced` implicates the channel.
5. **Did the batch window overrun?** Check partition skew and late-arrival volume. The window has slack; a persistent overrun means moving to incremental feature materialisation.
6. **Label feed missing?** Block retraining, retain the incumbent. A stale good model beats a model trained on truncated labels.

### Rollback

| Change | Rollback | Time |
|---|---|---|
| Alerting threshold | Config revert | seconds |
| Scoring model | Pointer flip to previous artifact | minutes |
| **Edge config (statistic set)** | Signed rollback to previous `config_version`; features re-derived from landing zone | hours–days (fleet propagation) |
| Feature definition (cloud) | Re-derive from immutable landing zone | hours |
| Firmware | **Not our rollback** — the vehicle programme owns it, which is exactly why FR-12 exists | n/a |

---

## 4.3 Common mistakes

> - **Mistake:** Streaming raw signals to the cloud "so we can do better feature engineering later" → **Why it's wrong:** 1.38 PB/day fleet-wide; unaffordable on cellular and unnecessary, since the model consumes distributional summaries → **Do instead:** aggregate on the edge, and keep a *triggered* raw snapshot around faults for the rare cases that need waveforms.
> - **Mistake:** Compiling the edge statistic set into firmware → **Why it's wrong:** if it's missing the predictive signal you find out 6–12 months later (label latency) with no fix for that vehicle generation → **Do instead:** signed, remotely-updatable config (FR-12) with cohort rollout.
> - **Mistake:** Treating a prevented failure as a false positive → **Why it's wrong:** a correct prediction leads to a replacement, so no failure occurs; scoring that as a miss trains the model to stop predicting successfully → **Do instead:** flag intervention and treat those rows as right-censored.
> - **Mistake:** Using a binary classifier on a fixed 30-day window → **Why it's wrong:** discards right-censoring (≈99% of vehicles haven't failed), forces an arbitrary horizon, and can't answer other horizons without retraining → **Do instead:** survival/time-to-event modelling.
> - **Mistake:** Imputing missing telemetry windows → **Why it's wrong:** a gap means the vehicle was off or out of coverage; interpolating teaches the model that a parked car is degrading → **Do instead:** mark gaps explicitly and expose coverage as a feature.
> - **Mistake:** Dropping low-coverage vehicles from training → **Why it's wrong:** biases the training set toward well-connected regions, producing unexplained regional performance gaps → **Do instead:** keep them, with coverage as a feature so the model learns to be less confident.
> - **Mistake:** Alerting on score alone → **Why it's wrong:** an alert with no available part or no dealer capacity burns the trust that is the scarce resource → **Do instead:** an explicit actionability gate; log suppressed predictions for analysis.
> - **Mistake:** A single global precision threshold → **Why it's wrong:** a 10-minute brake-pad check and a transmission teardown have wildly different investigation costs → **Do instead:** per-component, per-region floors (FR-13).
> - **Mistake:** Unsynchronised upload scheduling → **Why it's wrong:** 2M vehicles waking on a shared trigger produce a thundering herd that takes down ingest → **Do instead:** server-assigned `next_upload_after` jitter.
> - **Mistake:** Transform-on-ingest with no immutable raw landing → **Why it's wrong:** a normalisation bug becomes permanent data loss, discovered months later when labels arrive → **Do instead:** immutable landing zone, re-derivable features.
> - **Mistake:** Putting safety-relevant components in a non-alerting holdout → **Why it's wrong:** withholding a safety alert to improve a metric is not defensible → **Do instead:** restrict the holdout to inconvenience-class components, and be honest that this narrows what it can tell you.

---

## 4.4 Interview follow-ups

**Q: Why not run the model on the vehicle? Edge ML is the obvious move for automotive.**
Because it would buy nothing and cost a lot. The bandwidth problem is already solved by aggregation — 165 KB/day is 33× inside budget, so there's no transfer saving left to capture. Meanwhile edge inference couples model iteration to firmware release cycles, which for a 2M-vehicle fleet means months per change, and it removes the cross-vehicle cohort comparison that's one of my strongest features (a vehicle deviating from *its build cohort* is more informative than deviating from itself). I'd move inference to the edge only if the decision were time-critical — which is exactly the situation in [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/), where the cycle time is 200 ms and inference *must* be local. Same archetype, opposite call, and the discriminator is whether the decision can wait.

**Q: Your labels arrive 30–180 days late and alerting changes the outcome. How do you know the model works at all?**
Honestly: with less certainty than in a system with fast feedback, and I'd say that out loud. Four partial signals. Dealer-disposition precision is measurable within weeks but only for alerts we issued, so it's biased toward high scores. Warranty-claim recall is the primary honest signal — of components that failed, what fraction did we alert ≥ 14 days ahead — but it lags 3–12 months. The non-alerting holdout cohort is the only near-unbiased estimate of what we're missing, and it's ethically bounded to non-safety components, which limits its coverage. And survival calibration on the non-alerted population tests whether predicted 30-day probabilities match observed rates. **No single one is sufficient; the argument is the combination**, and the intervention flag is what stops the naive computation from being actively misleading.

**Q: What's the single biggest risk?**
The edge statistic set being wrong and frozen. If `drift_slope` turns out to be the wrong summary for, say, a bearing failure that shows up as a change in *spectral* content, no amount of cloud modelling recovers it — the information was discarded on the vehicle. And the feedback loop is so slow you'd learn this a year in. That's why FR-12 (remotely updatable config) is the highest-leverage requirement in the design, and why the statistic set defensively includes both a trend measure and a threshold-crossing count. If config *can't* be updated remotely, I'd upload a deliberately broader statistic set and spend the bandwidth headroom on insurance.

**Q: 33× bandwidth headroom seems like a lot left on the table.**
It's held for four things: reconnect bursts after multi-day outages (~1.2 MB), raw diagnostic snapshots around fault events (~500 KB), retransmission overhead on poor links, and — the real reason — future signals from later vehicle programmes. The alternative is spending it now on statistics we can't yet justify, then discovering we have no room for the one we need. I'd rather hold reserve on a resource I can't expand mid-generation.

**Q: Precision 0.70 is low for a production ML system. Defend it.**
It isn't a statistical target, it's a behavioural threshold. A technician who investigates three alerts and finds nothing twice stops treating alerts as credible, and once that happens recall is irrelevant — the channel is dead. So the floor is set by investigation cost and human tolerance, not by an ROC curve. It's also per-component: a brake-pad check costing 10 minutes tolerates lower precision than a transmission teardown. And FR-14 monitors the humans' actual behaviour, because the floor is an assumption about them that needs validating. **This is a case where the socio-technical constraint dominates the statistical one, and designing to the statistics alone would produce a system nobody uses.**

**Q: Walk me through a fleet-wide connectivity outage.**
Edge buffers absorb it — 7 days of windows, so a 2-day carrier incident is invisible to the model once vehicles reconnect. The nightly batch still runs, but features age: `coverage_30d` falls and `max_gap_days` rises, both of which are model inputs, so predictions widen their intervals automatically. Past 3 days of staleness the gate suppresses alerts entirely rather than issuing them on stale signal. On recovery, ingest applies rate limiting with 429-and-retry-after, and vehicles upload on server-assigned jittered schedules so the recovery spreads over hours instead of arriving as a single spike. The thing I'd watch is whether suppression is engaging correctly — the dangerous failure is alerting confidently on week-old data.

**Q: Why daily batch rather than continuous scoring?**
Because degradation takes weeks and action takes days. A prediction 6 hours fresher changes no decision: the owner still has to book, the dealer still needs a part and a bay. Batch costs ~$290/month; continuous inference would cost meaningfully more for zero decision benefit. The nuance is that **faults are streaming even though predictions are batch** — an active DTC hard fault is a current condition, not a forecast, and it bypasses the batch entirely. Conflating the two would make either faults slow or predictions expensive.

**Q: What would you build first?**
The edge aggregator and the ingest/landing pipeline, with no model at all. That gets telemetry flowing, starts accruing the history the model will need, and immediately enables fleet analytics (cohort failure rates) which has standalone value for engineering. Crucially it also starts the clock on labels — I can't train anything useful until I have seasoned outcomes, so the data pipeline is on the critical path in a way the model isn't. I'd defer the holdout cohort and per-region thresholds to v2.

**Q: What breaks at 100×?**
Storage cost and the batch window, not compute. 200M vehicles is 33 TB/day and ~24 PB at 24-month retention. I'd tier: full hourly resolution for 90 days, downsample to daily statistics beyond. For the window, I'd stop scoring every vehicle every day — most vehicles are unremarkable on most days, so a change-triggered policy (score only where features moved materially) cuts volume by roughly an order of magnitude. The thing that *doesn't* scale is label coverage: dealer capacity and warranty volume don't grow with fleet size, so recall estimation leans harder on the holdout and on pooled hierarchical models for rare failures.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Edge aggregation** | Computing windowed statistics on-vehicle instead of uploading raw signals | The ~4,000× reduction that makes the system affordable — *the* design decision |
| **Welford's algorithm** | Numerically stable online mean/variance in constant memory | An ECU cannot buffer 36,000 samples × 200 signals; naive sum-of-squares loses precision |
| **`config_version`** | Version of the edge statistic set that produced a window | Features under different versions aren't comparable; it's part of the dedupe key |
| **Store-and-forward** | On-vehicle buffer (7 days) replayed on reconnect | Makes intermittent connectivity a non-event; *the* availability mechanism |
| **Byte budget** | Per-vehicle cumulative monthly upload cap with graceful downgrade | Bandwidth is the binding constraint, so it needs enforcement, not hope |
| **Survival / time-to-event model** | Models time until an event, handling right-censoring natively | ~99% of vehicles haven't failed; a binary classifier discards that information |
| **Right-censoring** | An observation where the event hasn't happened yet by the observation time | The normal case here, and why survival modelling is correct |
| **Intervention censoring** | A correct prediction causes a repair, so the predicted failure never occurs | Counting it as a false positive would train the model to stop working |
| **Coverage** | Fraction of expected telemetry windows actually received | A **model input**, so low-coverage vehicles get wider intervals rather than confident guesses |
| **Actionability gate** | Stage between score and alert: threshold, parts, capacity, trust, cooldown | An alert nobody can act on is worse than silence |
| **Precision floor (trust economics)** | ≥ 0.70, set by investigation cost and human tolerance | A behavioural constraint, not a statistical target |
| **Dealer found-rate** | Fraction of investigated alerts where a fault was confirmed, per dealer/region | Monitors *the humans' response to the model* — a failure invisible to model metrics |
| **Non-alerting holdout** | Cohort where sub-threshold predictions are logged but not alerted | The only near-unbiased recall estimate; ethically limited to non-safety components |
| **`suppress_reason`** | Why a prediction didn't become an alert | Separates "didn't detect" from "detected and chose not to alert" |
| **DTC** | Diagnostic Trouble Code — an ECU-reported fault | A *current* condition, so it bypasses batch onto the streaming fault path |
| **Own-baseline vs cohort deviation** | Deviation from a vehicle's own history vs from its build/climate peers | Cohort comparison is only possible in the cloud — a key reason inference isn't on the edge |
| **Lead time** | Days between alert and confirmed fault | ≥ 14 days median, or there's no time to schedule service |
| **Immutable landing zone** | Raw uploads stored unmodified before normalisation | The only recovery path when a feature bug surfaces months later |

---

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md) · **Next system:** [`../04_healthcare_clinical_ai/`](../04_healthcare_clinical_ai/)
