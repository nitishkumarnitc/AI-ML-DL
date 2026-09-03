# 05 · Production & Interview — Logistics: Forecast + Optimisation

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md)

---

## 4.1 AI-specific concerns

Most rows here read "not applicable," and **that is the answer** — inventing LLM concerns for a solver system would be padding. The interesting content is why an LLM is the wrong tool.

| Concern | How this design handles it |
|---|---|
| **Token cost** | **Zero in the critical path.** Total system cost is **~$90/month**: forecast inference ~$19, training ~$7, routing ~$14, intraday re-plans ~$3, storage ~$46. The cheapest system in this folder and the hardest design — **cost and difficulty are uncorrelated** |
| **Latency budget** | **Not the binding constraint.** The binding constraint is the **dispatch deadline**: a 90-minute window that the pipeline fills to ~56 minutes, holding 34 minutes specifically to absorb a non-converging solve. The one latency-shaped requirement is the 3-minute intraday re-plan |
| **Model routing & fallback** | Not model routing — **staged degradation**: converged solve → anytime incumbent → previous feasible plan → yesterday's plan with manual dispatch. Each step is worse and *valid*; none is invalid |
| **Evaluation** | Two independent regimes. **Forecast:** WAPE and pinball loss by SKU class / location / horizon, plus **calibration coverage** (FR-13) — a p90 covering 70% of outcomes is worse than a point estimate because it carries false precision. **Routing:** gap-to-bound, feasibility rate (must be 100%), and plan-vs-actual arrival deviation, which is the only metric that tests the travel-time matrix |
| **Hallucination / groundedness** | **N/A.** No generative component. The nearest analogue is a **miscalibrated quantile**, which is the same category of harm — false confidence in a number — and is why calibration is monitored rather than assumed |
| **Guardrails** | The **independent validator** (FR-18) is the guardrail: separate code from the solver, re-checking every hard constraint from scratch. Duplicated logic is normally a smell; here it's deliberate, because a solver bug relaxing driver-hours is a legal exposure |
| **Prompt injection** | **N/A.** Every input is a typed numeric from internal systems |
| **Prompt / version management** | Not prompts — **`model_version`, `solver_version`, and `forecast_run_id`** persisted on every plan, giving full lineage from a delivered route back to the demand data that justified it |
| **Drift** | Three detectors: forecast **residual drift** by class; **calibration drift** (empirical coverage vs nominal); and **plan-vs-actual arrival deviation**, which catches travel-time matrix staleness — a drift the models themselves cannot see |
| **Non-determinism** | Metaheuristics are stochastic. Seeds are logged per region so a plan is reproducible; and because the validator is independent and deterministic, an irreproducible solve still cannot produce an invalid plan |
| **Cold start & capacity** | New SKUs forecast from cohort; new locations from tier peers. Routing capacity is 60 workers for ~90 s once daily — trivially provisioned, and the window headroom absorbs contention |
| **Why not an LLM** | Three reasons, worth saying plainly: (1) **solvers are optimal here** and an LLM is strictly worse at combinatorial assignment; (2) it would add cost, latency, and **non-determinism** to a deterministic problem; (3) FR-5's dispatcher explanation is *better* templated from solver output — deterministic, auditable, translatable. **Recognising a solved problem and not reaching for a model is the signal** |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Alert |
|---|---|
| **Run wall-clock vs window** | > 75% of window consumed → warn; projection says miss → page |
| `will_meet_deadline` projection | flips to false → page immediately |
| Per-stage duration vs budget | any stage > 130% of budget |
| **Regions interrupted** (of 60) | > 10 → warn; > 25 → investigate region sizing |
| Gap-to-bound (plan level) | > 12% |
| **Feasibility rate** | **< 100%** → page; this is an invariant |
| Validator rejection count | **any** → page (implies a solver or repair bug) |
| **Calibration coverage** (p90 empirical) | outside 0.85–0.94 |
| Censoring rate by SKU class | > 25% class-wide (supply problem, not a model problem) |
| Forecast WAPE by class | > 30% |
| **Plan-vs-actual arrival deviation** | p90 > 20 min → suspect stale travel-time matrix |
| Stale-forecast fallback used | any |
| Intraday re-plan latency | p95 > 3 min |
| Frozen-stop assertion trips | **any** → page |

### On-call triage order

1. **Will the run meet the deadline?** This is the only true emergency. Check the live projection, not elapsed time. If it will miss: lower the routing quality target (accept a bigger gap), or accept a stale forecast — **both are pre-authorised degradations**, and a planner should be told which one you took.
2. **Did the validator reject a plan?** The incumbent was published, so dispatch is safe. But a rejection means the solver or repair pass produced an illegal plan, which is a correctness bug that must be found before it recurs. Capture the violating route and the seed.
3. **Feasibility below 100%?** Should be impossible — the validator gates publication. If a published plan is infeasible, the validator itself is wrong. Stop publishing and escalate.
4. **Many regions interrupted?** Usually region sizing or a demand spike making instances harder. Not urgent (plans are valid, just costlier); retune region count offline.
5. **Calibration drifting?** Recalibrate rather than retrain mid-cycle, and widen spreads as an interim measure. Understand that until it's fixed, planners are getting less service than they think they bought.
6. **Arrival deviation rising?** Check travel-time matrix age first. This failure looks like a routing problem and is usually a data problem.

### Rollback

| Change | Rollback | Time |
|---|---|---|
| Service levels | Config revert | seconds |
| Solver parameters (region count, time budget) | Config revert | seconds |
| Forecast model | Pointer flip; previous artifact retained | minutes |
| Censoring logic | **Requires feature rebuild** — hence versioned and additive | hours |
| Clustering constraints | Config revert; re-cluster | minutes |

---

## 4.3 Common mistakes

> - **Mistake:** Passing a point forecast to the optimiser → **Why it's wrong:** the router optimises confidently against the median, so half of all stops are under-supplied by construction, and the error is invisible in both components' own metrics → **Do instead:** pass quantiles and make the service level an explicit choice.
> - **Mistake:** Training on raw sales → **Why it's wrong:** stock-outs censor demand, so the model learns to forecast the stock-out; supply matches, it stocks out again, and the observation confirms the forecast — a self-fulfilling under-forecast with excellent measured accuracy → **Do instead:** derive censoring from stock positions and model censored observations explicitly.
> - **Mistake:** Inferring censoring from the shape of sales → **Why it's wrong:** false positives on genuinely flat demand, false negatives when a stock-out coincides with low demand → **Do instead:** join stock-position history; treat closing-zero as a weaker signal when intraday data is missing.
> - **Mistake:** One model per series → **Why it's wrong:** 4.2M fits is operationally absurd *and* worse, because each model sees only its own thin history and cannot borrow seasonality from peers → **Do instead:** one global model with series identifiers as features.
> - **Mistake:** Trying to solve the VRP exactly → **Why it's wrong:** NP-hard at 25k stops; you will miss the deadline and have nothing → **Do instead:** decompose geographically, solve in parallel, accept an 8% gap.
> - **Mistake:** A solver whose first solution is infeasible → **Why it's wrong:** if the deadline arrives during improvement there is nothing valid to return → **Do instead:** feasible-first construction; the construction heuristic *is* the availability mechanism.
> - **Mistake:** Trusting the solver's internal feasibility check → **Why it's wrong:** a bug that silently relaxes driver-hours is a legal exposure, and the same code that created the plan cannot independently verify it → **Do instead:** an independent validator in separate code.
> - **Mistake:** k-means on latitude/longitude for clustering → **Why it's wrong:** produces clusters spanning depots and territory boundaries, and treats a river as a short distance; dispatchers reject the plans → **Do instead:** cluster on travel time with depot and territory as hard constraints.
> - **Mistake:** Full re-solve on an intraday disruption → **Why it's wrong:** takes longer than the 3-minute budget and reshuffles already-delivered stops → **Do instead:** partial re-solve of affected regions with executed stops frozen and asserted.
> - **Mistake:** Reporting calibration globally → **Why it's wrong:** coverage typically degrades at long horizons and on low-volume series, and a global average hides both → **Do instead:** report by class, tier, and horizon.
> - **Mistake:** Reaching for an LLM because it's an "AI system design" → **Why it's wrong:** adds cost, latency, and non-determinism to a problem solvers handle optimally → **Do instead:** use a solver, and be able to explain why.

---

## 4.4 Interview follow-ups

**Q: Why quantiles rather than a point forecast plus a safety-stock multiplier?**
Because a single multiplier applies one uncertainty assumption to series with wildly different variances. A high-volume staple with stable demand and a low-volume seasonal item need very different buffers, and a global multiplier over-stocks one while under-stocking the other. Quantiles carry each series' own uncertainty, so the service-level decision is made per series with the right spread. There's a second benefit: it makes the trade-off **visible**. A planner asking for 99% fill sees the inventory cost of that choice rather than discovering it in the next stock-take.

**Q: How do you know your censoring correction is right? You're correcting toward unobserved data.**
I can't verify it directly, and I'd say that plainly. Three things give me confidence. First, **synthetic censoring**: take uncensored series, artificially censor them at known points, and check the corrected model recovers the true demand within tolerance — that's FR-15's acceptance criterion. Second, **method agreement**: fit with right-censored likelihood and separately by excluding censored days; if they disagree materially, the correction is suspect and I'd rather know. Third, **the downstream signal** — if the correction is working, supplying to the corrected forecast should reduce stock-out frequency at the same inventory level, which is measurable in production. If none of those hold, the honest position is that this series' forecast is low-confidence, which is what the flag exists for.

**Q: Your routing is 8% from optimal. That's real money — why not solve it properly?**
Because "properly" doesn't fit in the window, and a late plan has infinite cost. Exact VRPTW at 25,000 stops with 800 vehicles is not solvable in 25 minutes with any technology I'd bet a dispatch on. The 8% figure is also worth interrogating: it's the gap to a *bound*, not to a known optimum, so true optimality is somewhere between. Where I would push is region sizing — larger regions capture more cross-region savings but take longer, so there's a tunable trade-off, and `regions_interrupted` tells me whether I've pushed too far. If the business valued that 8%, the honest answer is to negotiate a longer window rather than to pretend a better solver exists.

**Q: What actually happens if the deadline is missed?**
Manual dispatch, using yesterday's plan as a base. That's genuinely bad — costlier routes, likely some missed time windows — which is why 34 minutes of the window are held in reserve and why `will_meet_deadline` is a live projection rather than a post-hoc observation. The projection is the important part: it lets a planner choose a degradation (bigger routing gap, or a stale forecast) *before* the deadline passes. A system that only tells you it missed is much worse than one that tells you it's going to.

**Q: Why is the validator separate code? That's duplicated logic.**
It is, deliberately. The solver enforces constraints while searching; the validator re-derives them from scratch afterwards. If they shared code, a bug in the shared constraint model would be invisible — the solver would produce a plan violating driver-hours and the check would agree it's fine. And the consequence isn't a suboptimal route, it's a driver exceeding legally mandated hours, which is a regulatory matter. The scenario in the failure sequence diagram is exactly this: the repair pass introduced a violation the solver's internal check missed, the independent validator caught it, and the pre-repair incumbent shipped instead. **Duplication as defence-in-depth is justified when the failure is legal rather than economic.**

**Q: This is a $90/month system. Isn't that suspiciously cheap for something you're calling the hardest design?**
The two facts are unrelated, which is the point. The cost is low because it's CPU work — trees and metaheuristics — running once a day on modest hardware, with no per-token pricing and no GPU. The difficulty is that it chains two hard problems under a hard deadline, with an interface (uncertainty) that's easy to get wrong in a way neither component's metrics reveal. If anything the low cost is a design achievement: it would have been easy to build something ten times more expensive and worse by putting a model where a solver belongs.

**Q: Where would you use an LLM in this system, if anywhere?**
Nowhere in the critical path, and I'd resist it in the explanation too. The dispatcher explanation (FR-5) looks like a natural fit, but a plan is structured data — route, cost, load, slack, which stops were deferred and why — and a template renders that better than a model: deterministic, translatable, auditable, and free. The only place I'd genuinely consider one is a conversational *interface* for planners ("what if I raise service level on perishables?"), and even then the LLM would translate the question into parameters and hand off to the solver, sitting strictly outside the solve.

**Q: What would you build first?**
The censoring detector and the forecast, with no routing at all. Better demand forecasts have standalone value — they improve ordering immediately, even with existing manual routing — and the censoring work is the thing that makes every downstream number trustworthy. Building routing first would produce beautifully optimised delivery of the wrong quantities. I'd also build the independent validator early, before the solver, so the solver is developed against a check it can't influence.

**Q: What breaks at 100×?**
The window itself, and it's a redesign rather than a scaling knob. At 2.5M stops even perfect parallelism runs into data movement and the coordination cost of thousands of workers, and 90 minutes stops being enough. The answer is to stop planning in nightly batches and move to **continuous planning** — maintain a rolling plan updated incrementally as orders arrive, so there's never a single deadline to miss. That changes the failure model entirely (from "missed the window" to "plan quality degrades under load"), and naming the trigger for that transition is more useful than claiming the batch design scales.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Quantile forecast** | Predicting p10/p50/p90 rather than a single expected value | Lets the optimiser make an explicit service-level trade-off instead of silently under-supplying |
| **Pinball loss** | The loss function for quantile regression | Point-accuracy metrics say nothing about whether the *spread* is right |
| **Calibration coverage** | How often actuals fall below a nominal quantile | A p90 covering 70% is worse than a point estimate — it carries false precision |
| **Quantile crossing** | p10 > p50, from independently-fitted quantile models | Common, and produces nonsense downstream; repaired and constraint-checked |
| **Demand censoring** | Observed sales understate demand because stock ran out | Training on sales creates a self-fulfilling under-forecast with excellent measured accuracy |
| **Right-censored observation** | A record known only as "demand ≥ observed" | The statistically correct way to use stock-out days rather than discarding them |
| **Service level / fill rate** | Target fraction of demand met from stock | The planner's dial; maps to which quantile the router loads to |
| **Global model** | One model across all series, with series identifiers as features | Enables cross-series learning; the alternative is 4.2M thin-history fits |
| **VRPTW** | Vehicle Routing Problem with Time Windows (plus capacity, driver hours) | The actual formulation; NP-hard, hence decomposition |
| **Geographic decomposition** | Splitting stops into ~60 regions solved in parallel | Takes ~90 min sequential to ~4 min — *this* is what makes the deadline |
| **Anytime algorithm** | One that can return its best feasible solution at any moment | FR-17; the interrupt guarantee that makes a hard deadline survivable |
| **Feasible-first construction** | Producing a valid (if poor) plan within seconds before improving | The availability mechanism — without it, an interrupt yields nothing |
| **Gap to bound** | Distance from the best-known lower bound on cost | Reports solution quality honestly; not the same as distance from optimal |
| **Independent validator** | Separate code re-checking all hard constraints post-solve | Defence in depth, because a driver-hours violation is a legal matter |
| **Cross-region repair** | Reassigning boundary stops between adjacent regions | Recovers savings lost to decomposition; bounded because it's on the critical path |
| **Frozen stop** | An already-executed stop, immutable in an intraday re-plan | Sending a driver to a delivered stop is worse than no re-plan |
| **Travel-time matrix** | Pairwise travel durations underpinning clustering and routing | Staleness produces plans feasible on paper and late in reality |
| **Dispatch deadline** | The hard cut-off by which routes must be released | The binding constraint of the whole system — not latency |
| **`regions_interrupted`** | Count of regions that returned an anytime incumbent | Tells a dispatcher how rough today's plan is; a rising trend means retune |

---

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md) · **Next system:** [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/)
