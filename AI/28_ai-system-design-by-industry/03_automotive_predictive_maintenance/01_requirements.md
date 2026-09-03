# 03 · Requirements — Automotive Predictive Maintenance

> **Shared block:** [`../00_requirements_all_systems.md#3-automotive--predictive-maintenance`](../00_requirements_all_systems.md#3-automotive--predictive-maintenance) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the bandwidth arithmetic, and the cost summary. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. The edge/cloud split as a contract

The shared block establishes the 4,000× reduction. What it does not spell out is the **contract** — and getting this contract wrong is unrecoverable for the lifetime of a vehicle, because edge code may be frozen at build time.

### What the edge computes

Per signal, per hourly window:

| Statistic | Why it's in the set |
|---|---|
| `mean`, `std` | Central tendency and dispersion — the baseline for drift |
| `min`, `max` | Excursions matter; a mean hides a spike |
| `p95` | Tail behaviour without keeping the distribution |
| `drift_slope` | Linear trend within the window — the single most predictive statistic for gradual degradation |
| `threshold_crossings` | Count of excursions past a calibrated bound |

Plus, per window: DTC (Diagnostic Trouble Code) events, and per trip: duration, distance, ambient conditions.

```
200 signals × 7 statistics × 4 bytes × 24 hourly windows = 134 KB
+ DTC events (~2 KB) + trip summaries (~10 KB) + headers/framing (~19 KB)
⇒ ~165 KB/vehicle/day    (budget 5 MB — 33× headroom)
```

### What the edge deliberately does *not* do

| Not on the edge | Why |
|---|---|
| **Model inference** | A component-failure model needs fleet-wide context and monthly retraining. Scoring on-vehicle would freeze the model to firmware cadence |
| Cross-signal correlation | Combinatorial explosion; cheap in the cloud, expensive in a constrained ECU |
| Anything requiring history > 24 h | Buffer is sized for connectivity gaps, not analysis |

> **The asymmetry to defend:** the edge does **compression**, the cloud does **inference**. Pushing inference to the edge is tempting (it saves nothing here, since aggregates are already tiny) and costs enormously — it couples model iteration to firmware release cycles. Contrast [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/), where inference *must* be on the edge because the cycle time is 200 ms and the network is unreliable. **Same archetype, opposite call, driven by whether the decision is time-critical.**

### The 33× headroom is deliberate

The budget is 5 MB and we use 165 KB. That is not over-engineering — it is the reserve for:

| Consumer of headroom | Estimate |
|---|---|
| Reconnect burst after a multi-day gap (up to 7 days buffered) | ~1.2 MB |
| Diagnostic snapshot on a DTC event (raw window around the fault) | ~500 KB |
| Future signals added by later vehicle programmes | unknown — the real reason |
| Retransmission on unreliable links | ~20% overhead |

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | Edge upload must respect a hard monthly byte budget | Per-vehicle cumulative counter; on approaching the cap, downgrade to essential statistics only and log the downgrade |
| **FR-12** | P1 | Edge aggregation config is remotely updatable | The statistic set and window size can be changed by signed config **without a firmware release** |

> FR-12 is the mitigation for the worst risk in this design. If the statistic set is frozen at build time and turns out to be missing the predictive signal, you discover it 6–12 months later (label latency) with no way to fix it for that vehicle generation.

---

## B. The precision floor is trust economics, not statistics

The shared NFR sets alert precision ≥ 0.70 and calls it socio-technical. Making that concrete:

```
Assume a dealer receives N alerts and investigates each.
Investigation cost: ~45 min of a technician's time  (ASSUMPTION)
At precision p, the dealer finds a genuine fault in p·N cases.

Observed behaviour (ASSUMPTION — must be validated with the dealer network):
  p ≥ 0.7  → dealers continue investigating; alerts are treated as credible
  p ≈ 0.5  → dealers begin triaging alerts by their own judgement, ignoring some
  p ≤ 0.3  → alerts are ignored wholesale; the system is dead regardless of its recall
```

**The consequence for the model's objective:** this is **not** "maximise recall subject to precision ≥ 0.70." Precision below the floor destroys the channel, so the floor is a *hard constraint*, and within it recall is maximised. And because the floor is behavioural, it is **per-component and per-region tunable** — a brake-pad alert that costs 10 minutes to check tolerates lower precision than a transmission alert requiring a teardown.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-13** | P0 | Per-component, per-region precision thresholds | Configurable; each component's alerting threshold set from its investigation cost, not a global number |
| **FR-14** | P1 | Dealer-level trust telemetry | Track per-dealer alert→investigation→found rates; a dealer whose found-rate collapses is a signal to suppress alerts in that region and investigate why |

> FR-14 is unusual and worth including: it monitors **the humans' response to the model**, not the model. If dealers in one region stop acting on alerts, recall is irrelevant there and the system is failing invisibly.

---

## C. The label problem, and how evaluation survives it

This is the hardest requirement in the design and the one most likely to be under-specified.

### What we can and cannot observe

| Event | Observable? | Lag |
|---|---|---|
| Alert issued | ✅ Always | 0 |
| Owner books service | ✅ If through the dealer network | Days–weeks |
| **Dealer disposition** (fault found / not found) | ⚠️ **Only if the vehicle is serviced *and* the dealer records it** | 1–8 weeks |
| Component actually failed (no alert) | ⚠️ Only via warranty claim or roadside event | 1–12 months |
| Component fine, never alerted | ❌ **Never directly observable** | — |

### The three consequences

**1. The negative class is unobservable.** We never learn "this component was fine for 30 more days." We infer it from absence of a claim, which is an assumption, not a label.

**2. Alerts change the outcome they predict.** If we alert and the part is replaced, the failure we predicted **does not happen** — so a correct prediction produces no failure to validate against. This is **intervention censoring**, and it is the deepest evaluation problem here.

**3. Coverage is biased.** Only vehicles serviced *at network dealers* produce dispositions. Independent-garage repairs are invisible.

### How evaluation actually works

| Method | What it measures | Limitation |
|---|---|---|
| **Dealer disposition precision** | Of alerts investigated, fraction with a confirmed fault | Only covers investigated alerts; biased toward high-scoring ones |
| **Warranty-claim recall (retrospective)** | Of components that failed under warranty, fraction alerted ≥ 14 days prior | The primary recall signal; lags 3–12 months |
| **Holdout non-alerting cohort** | A small randomised cohort where sub-threshold predictions are **not** alerted, tracked for failures | The only way to estimate what we're missing — ethically bounded to non-safety components |
| **Survival-model calibration** | Do predicted 30-day failure probabilities match observed rates in the non-alerted population? | Requires the holdout to be meaningful |

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-15** | P0 | Every alert records its own outcome lifecycle | Alert → viewed → booked → serviced → disposition, each timestamped; unresolved alerts explicitly aged out with a reason |
| **FR-16** | P1 | Intervention flag on every label | Labels record whether an alert preceded the service, so intervention-censored rows are excluded from naive recall computation |
| **FR-17** | P1 | Non-alerting holdout cohort | ~0.5% of vehicles, **non-safety components only**, where predictions are logged but not alerted — reviewed retrospectively against warranty claims |

> **FR-17 has an ethical boundary and it must be stated.** Withholding a safety-relevant alert to improve a metric is not acceptable. The holdout is restricted to components whose failure is an inconvenience (cabin filter, battery degradation, minor sensors) rather than a hazard — and that restriction narrows what it can tell us. This is a genuine limitation, not a solved problem.

---

## D. Why daily batch is correct

The shared NFR says daily. Defending it, since "real-time" is the reflex answer:

| Consideration | Implication |
|---|---|
| Degradation timescale | Weeks to months. A 6-hour-fresher prediction changes nothing |
| Alert actionability | Owner must book, dealer must have parts and a bay — lead time is days regardless |
| Upload cadence | Vehicles are off, parked underground, or out of coverage; opportunistic upload is inherently irregular |
| Cost | Batch scoring on 10 vCPU for 2 h/day ≈ $290/month. Continuous streaming inference would cost far more for zero benefit |
| Exception | **DTC hard-fault events** bypass batch — an active fault code is dispatched immediately, because that's a *current* condition, not a prediction |

> The nuance worth stating: **prediction is batch, but faults are streaming.** Conflating them would either make faults slow or predictions expensive.

---

## E. Additional non-goals (beyond the shared block)

- **Not** any safety-critical intervention — no braking, steering, or power limiting. This keeps the system outside functional-safety (ISO 26262-style) certification scope, which is a deliberate and load-bearing scope decision.
- **Not** raw-signal cloud storage (FR-3 exists to prevent it).
- **Not** dealer scheduling or DMS integration beyond emitting an alert.
- **Not** autonomous parts ordering in v1 (FR-5's actionability gate *reads* parts availability, it doesn't order).
- **Not** driver-behaviour scoring for insurance purposes — different consent basis entirely.

---

## F. Open questions carried into the HLD

Beyond the shared block's list:

1. **Can edge aggregation config be updated without a firmware release (FR-12)?** If not, the statistic set is frozen for that vehicle generation's life, and the design must compensate by uploading a broader (larger) statistic set defensively — consuming the bandwidth headroom.
2. **What fraction of servicing happens at network dealers?** This bounds label coverage. If it's 40%, most outcomes are invisible and the evaluation strategy leans much harder on warranty claims.
3. **Is a non-alerting holdout (FR-17) acceptable to legal and to the safety organisation?** If not, there is no unbiased recall estimate and we must be honest that recall is an inference, not a measurement.
4. **Who owns the false-alarm cost?** Without a named owner, the FR-13 precision floors will erode under pressure to increase recall.
5. **What is the actual per-MB cellular cost?** The 5 MB budget was given, not derived. If data is effectively free on the chosen carrier plan, the edge/cloud split could be rebalanced toward richer uploads.

---

**Next:** [`02_hld.md`](02_hld.md) →
