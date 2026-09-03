# 05 · Requirements — Logistics: Demand Forecasting + Route Optimisation

> **Shared block:** [`../00_requirements_all_systems.md#5-logistics--demand-forecasting--route-optimisation`](../00_requirements_all_systems.md#5-logistics--demand-forecasting--route-optimisation) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the two-stage arithmetic, and the cost summary. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. The quantile contract between the two stages

The shared block establishes that the forecast passes quantiles rather than a point estimate. This is the single most important interface in the design, so here it is as a contract.

### What crosses the boundary

```
FORECAST OUTPUT (per SKU × location × day):
  p10  — pessimistic demand   (10% chance actual falls below this)
  p50  — median demand
  p90  — optimistic demand    (90% chance actual falls below this)
  + distribution family/parameters where available
  + a coverage flag (was this series' history sufficient to trust the spread?)
```

### Why a point estimate breaks the downstream optimiser

| With a point forecast | With quantiles |
|---|---|
| Router loads exactly `p50` per stop | Router chooses a quantile per stop from the service-level target |
| Half of all stops are under-supplied by construction | Under-supply frequency is a **chosen** parameter |
| Forecast error becomes silent stock-out | Forecast uncertainty becomes an explicit cost/service trade-off |
| Both components look correct in isolation | The combined system is tunable |

> **The failure this prevents is invisible in both components' own metrics.** The forecast reports good WAPE; the router reports a near-optimal solution against the demand it was given. Neither is wrong. But the *system* systematically under-serves, because the router was optimising against the median of a distribution it never saw. **A design that flattens uncertainty at a system boundary has moved the error somewhere nobody is measuring.**

### The service-level mapping (FR-7)

| Planner sets fill-rate target | Router loads to | Effect |
|---|---|---|
| 85% | ≈ p85 | Lower inventory cost, more stock-outs |
| 95% | ≈ p95 | Standard grocery/pharma expectation |
| 99% | ≈ p99 | High-value or critical items; heavy inventory cost |

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | The forecast→optimiser interface carries a distribution, never a scalar | Schema enforcement: a payload with only a point estimate is rejected at the boundary |
| **FR-12** | P0 | Service level is configurable per SKU class and per location tier | Planner-settable without redeploy; the chosen quantile recorded with every plan |
| **FR-13** | P1 | Quantile calibration is monitored | Empirical coverage of the p90 band reported weekly; if actual falls below p90 more than ~10% of the time, the spread is mis-calibrated and the router is being misled |

> FR-13 matters because a *miscalibrated* quantile is worse than a point estimate — it carries false precision. If p90 is really p70, the planner believes they've bought 90% service and haven't.

---

## B. Demand censoring — the silent error

**This is the failure mode I'd volunteer unprompted**, because it is nearly universal and it looks like success.

### The problem

We observe **sales**, not **demand**. When a location stocks out at 14:00, the afternoon's unmet demand is invisible. Train on sales and the model learns:

```
"Demand at location L for SKU S on stock-out days ≈ 40 units"
...when actual demand was 90 and 40 was simply all that existed to sell.
```

The model then forecasts 40, the router supplies 40, the location stocks out again, and the observation confirms the forecast. **A self-fulfilling under-forecast, with excellent measured accuracy.**

### Detection

| Signal | Interpretation |
|---|---|
| Sales flat-lining at exactly available stock | Almost certainly censored |
| Zero sales with zero stock | Censored, not zero demand |
| Sales trailing off mid-day (from intraday data) | Partial censoring |
| Sales at a nearby location spiking simultaneously | Demand shifted, not absent |

### Correction (three options, in order of preference)

| Approach | Method | Trade-off |
|---|---|---|
| **1. Exclude censored observations** | Drop days where stock hit zero from the training target | Simple, unbiased, but discards data — and censoring is most common on high-demand days, so you lose the observations that matter most |
| **2. Treat as right-censored** | Model demand as ≥ observed sales using survival-style likelihood | Statistically correct; uses all data; more complex fit |
| **3. Impute from comparable locations** | Estimate what demand would have been from uncensored peers | Uses all data but introduces model-on-model error |

**Design stance:** option 2 for the primary model, with option 1 as a validation cross-check. If the two disagree materially, the censoring correction itself is suspect.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-14** | P0 | Every training observation carries a censoring flag | Derived from stock-position history, not inferred from sales shape alone |
| **FR-15** | P0 | The model handles censored observations explicitly | Held-out test on artificially censored data recovers the uncensored demand within a stated tolerance |
| **FR-16** | P1 | Censoring rate reported per SKU × location | A series with > 30% censored history is flagged as low-confidence, and its quantile spread widened |

---

## C. "Anytime interruptible" is a functional requirement

FR-4 says a good-enough plan on time beats an optimal plan late. That has a concrete architectural consequence most designs miss.

### What it means

The optimiser must, **at any moment**, be able to return the best feasible solution found so far. Not "usually finishes in 4 minutes" — **provably interruptible at the deadline with a valid plan in hand.**

```
t=0     construct an initial feasible solution (greedy insertion)  ← MUST be feasible
t=0..N  improve via local search / LNS, always keeping the best-feasible
t=cut   return best-feasible, whatever it is
```

### Why the initial solution must be feasible, not just fast

If the first construction produces an *infeasible* plan (capacity violated, time window missed) and the deadline arrives during improvement, there is nothing valid to return. So the construction heuristic is not an optimisation detail — it is the **availability mechanism**.

| Phase | Guarantee |
|---|---|
| Construction (~10 s) | A feasible plan exists, possibly poor |
| Improvement (~80 s) | Monotonically non-worsening; best-feasible always retained |
| Interrupt | Return best-feasible immediately |

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-17** | P0 | The solver is anytime-interruptible with a feasible incumbent | Injected interrupt at any point during solving returns a plan passing 100% hard-constraint validation |
| **FR-18** | P0 | Hard-constraint validation is a separate stage from the solver | The validator is independent code; a solver bug cannot produce a plan the validator accepts |

> FR-18 is a defence-in-depth decision. The solver enforces constraints internally, and the validator re-checks them from scratch. Duplicated logic is normally a smell; here it is deliberate, because a solver bug that silently relaxes a driver-hours constraint is a legal problem, not just a bad plan.

---

## D. Clustering must respect operational reality

The shared block's arithmetic assumes ~60 geographic regions solved in parallel. Naive k-means on coordinates produces clusters dispatchers reject, and it is worth being explicit about why.

| Naive clustering ignores | Consequence |
|---|---|
| Depot assignment | A cluster spanning two depots has no valid vehicle assignment |
| Driver domicile | Drivers start and end at specific locations |
| Physical barriers | A river or motorway makes two nearby points 40 minutes apart |
| Existing territory agreements | Union or contractual territory boundaries |
| Vehicle-type compatibility | Some areas require smaller vehicles (access restrictions) |

**The approach:** cluster on **travel time**, not Euclidean distance, seeded by depot, with territory constraints as hard cluster boundaries. Cross-region stops (genuinely ambiguous assignments) are handled by the repair pass rather than forced into one cluster.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-19** | P0 | Clustering respects depot, territory, and vehicle-access constraints | Zero clusters spanning a territory boundary; every cluster has ≥ 1 compatible depot |
| **FR-20** | P1 | Cross-region repair pass | Boundary stops reassigned if it improves total cost, without violating any cluster's feasibility |

---

## E. Additional non-goals (beyond the shared block)

- **Not** real-time traffic-aware re-routing during execution (the plan is produced pre-dispatch; in-cab navigation is a separate system).
- **Not** driver telematics or behaviour scoring.
- **Not** carrier selection or freight procurement.
- **Not** an LLM anywhere in the forecast or routing path — see [`04_production_and_interview.md`](04_production_and_interview.md#41-ai-specific-concerns) for the reasoning.
- **Not** strategic network design (facility location, depot placement) — that's a quarterly exercise, not a daily one.

---

## F. Open questions carried into the HLD

Beyond the shared block's list:

1. **What is the actual dispatch cut-off, and is it negotiable?** Every number derives from a 90-minute window. A 30-minute window forces a coarser decomposition and a worse quality target — and that trade should be a business decision, not an engineering surprise.
2. **Is intraday stock-position history available?** FR-14's censoring flags require knowing *when* stock hit zero, not just end-of-day position. Without intraday data, censoring detection degrades to inference from sales shape, which is materially weaker.
3. **What is the true asymmetry between under- and over-forecasting?** FR-12's quantile selection is meaningless without it, and the answer differs sharply between perishable and durable goods.
4. **Who owns the service-level targets?** They trade inventory cost against fill rate — a commercial decision that needs a named owner, or it will default to whatever the last incident suggested.
5. **Are travel-time matrices available and current?** Clustering and routing both depend on them; stale matrices produce plans that are feasible on paper and late in reality.

---

**Next:** [`02_hld.md`](02_hld.md) →
