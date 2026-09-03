# 09 · Production & Interview — Real Estate: Property Search, Valuation & Recommendation

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md)

---

## 4.1 AI-specific concerns

| Concern | How this design handles it |
|---|---|
| **Token cost** | **~$15.4k/month total**, of which intent parsing is ~$13k — the LLM is used for *one thing*, and it is not the numbers. $0.00011/search and $0.0003/valuation are both ~100× inside their ceilings |
| **Where the headroom goes** | Deliberately: **fairness testing and calibration monitoring**. Those are labour and infrastructure costs, not inference costs, and they are the ones that actually protect the product |
| **Latency budget** | Search ~470 ms against 500 ms. Intent parse (140 ms) is the largest single leg and an external dependency — its p99 is the likeliest breach. Valuation's 2 s budget is dominated by data fetch, not compute |
| **Model routing & fallback** | Search: intent parse → keyword + filter fallback. Valuation: quantile ensemble → **comps-only** (the industry's own method) → queue. Each rung is worse and honest |
| **Evaluation** | Two entirely separate regimes. Search: NDCG, enquiry rate, session success. Valuation: **MdAPE, interval coverage, and per-cohort versions of both** — plus refuse-rate monitoring in both directions |
| **Hallucination / groundedness** | Confined to intent parsing, and handled by validating parsed constraints against market reality rather than only against a schema. **The numeric path has no generative component**, which is the single biggest reason to prefer a quantile GBDT here |
| **Uncertainty quantification** | The centre of the design: quantile regression + **per-cohort conformal calibration** with an expiry. An uncalibrated interval is worse than no interval, because users treat a stated 90% as 90% |
| **Guardrails** | Hard constraints as filters (FR-14); zero results returned as zero (FR-15); evidence-based refusal (FR-21); refusal on uncalibrated cohorts (FR-22); **blocking fairness gate** (FR-26); feature allow-list with recorded review (FR-25) |
| **Prompt injection** | Listing descriptions are seller-supplied text, and they reach the embedding pipeline. They must never reach a decision prompt. Descriptions influence *semantic similarity only*; no listing text participates in valuation or in constraint parsing |
| **Version management** | Every valuation pins `model_ver`, `calibration_ver`, `feature_allowlist_ver`, and `cohort_id`. The allow-list version is the unusual one, and it is what makes "which fairness policy applied to this estimate" answerable |
| **Drift** | Three distinct kinds: market drift (invalidates calibration — the insidious one), listing-mix drift (affects search relevance), and comp-availability drift (moves the refuse rate). Only the first has a silent failure mode |
| **Label latency** | For valuation, ground truth is **a completed sale** — months later, and only for properties that actually sell. This is a selection problem: properties that sell are not a random sample of properties valued, so production coverage is measured on a biased subset and that limitation is stated rather than ignored |
| **Fairness / legal exposure** | The dominant non-functional concern. Segment MdAPE spread ≤ 2 pp and per-cohort coverage parity are **release gates**; a proxy-detectability probe reports per release; the allow-list is per market because legal positions differ |
| **PII / residency** | Property addresses are personal data when tied to owners. Address hashing for dedupe, market-scoped storage, and — notably — **no demographic data ingested at all**, which is the cleanest partial answer to FR-5 |
| **Cold start** | New market: no comps, no calibration ⇒ **every valuation refuses** until volume arrives. That is the correct behaviour and it must be planned for commercially, not discovered at launch |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Alert |
|---|---|
| Search p50/p95/p99 | p95 > 480 ms |
| Intent parse latency + failure rate | p99 > 250 ms · failure > 2% |
| **Intent parse anomaly rate** (implausible parsed constraints) | > 0.5% |
| Fallback-to-keyword rate | > 5% |
| Zero-result rate + relaxation acceptance | (informational; a rising zero-rate is a supply signal, not a bug) |
| Isochrone cache hit rate | < 95% |
| **AVM MdAPE — overall and per cohort** | overall > 6% · **spread > 2 pp** |
| **Interval coverage per cohort** (rolling, from resolved sales) | outside 85–95% for any cohort |
| Cohorts marked `insufficient` | trend up |
| **Calibration expiry countdown** per cohort | any cohort within 14 days of `valid_until` |
| **Refuse rate** | **< 1% (guessing) or > 15% (data coverage)** |
| Refuse reason-class mix | a shift toward `uncalibrated_cohort` |
| Comp count distribution + radius-expansion rate | expansion rate rising |
| Unverified-comp share | > 40% |
| Proxy-probe AUC per release | delta above threshold |
| Fairness gate pass/block history | any block (informational but reviewed) |
| Cost per search / per valuation | vs ceilings |

### On-call triage order

1. **Is search serving?** Degrade to keyword + filter. Results stay correct; the UX gets worse. Do not let a failed intent parse filter on a guessed constraint set — that is silently wrong, which is worse than visibly limited.
2. **Is a cohort's interval coverage out of band?** This is the highest-consequence quality alarm, because the interval is a promise. Recalibrate; if recent volume cannot support recalibration, mark the cohort uncalibrated and let it refuse. Refusing a segment is uncomfortable and correct.
3. **Has the refuse rate moved sharply?** Both directions are alarms. A drop toward zero after a model change almost always means the sufficiency test got weakened during model work — check whether a threshold moved. A spike toward 20% is a data-coverage problem, and **the wrong fix is loosening sufficiency**, which converts a visible data gap into invisible bad estimates.
4. **Did the fairness gate block a release?** Working as designed. Read `mdape_by_cohort` before arguing with it; a model that is better overall and worse in spread is not an improvement.
5. **Is MdAPE degrading in one cohort only?** Usually comp-data lag or a genuine market move in that area. Check ingestion lag before touching the model.
6. **Is the isochrone cache cold for a popular origin?** Radius fallback is labelled, so results stay honest, but commute-constrained searches degrade. Backfill the origin cell.
7. **Has a new consumer appeared in the valuation register?** If a lender is calling the API, that is not an engineering incident — it is a legal one, and it needs to be escalated the same day.

### Rollback

| Change | Rollback | Time |
|---|---|---|
| Intent parse prompt/schema | Versioned config revert | seconds |
| Ranking model | Pointer flip to previous GBDT | < 1 min |
| **AVM model** | Pointer flip — **and calibration must roll back with it**; a model paired with another model's conformal deltas has undefined coverage | < 1 min |
| Calibration version | Previous per-cohort calibration retained; revert independently only if the model is unchanged | seconds |
| Feature allow-list | Versioned; reverting narrows features, never widens them silently | seconds |
| Sufficiency thresholds | Versioned config, and **changes are reviewed like model changes** because they move the refuse rate | seconds |
| Isochrone generation | Previous generation retained; pointer swap | minutes |

> The AVM row carries a real trap. `model_ver` and `calibration_ver` must move together, because conformal deltas are computed *for a specific model's* residuals. Rolling back one without the other produces intervals with no coverage guarantee at all — and nothing in the system would complain.

---

## 4.3 Common mistakes

> - **Mistake:** Designing this as one system → **Why it's wrong:** search tolerates being approximately right; valuation does not, and it carries legal exposure. Fusing them makes the AVM inherit the ranker's release cadence → **Do instead:** two pipelines, two evaluation regimes, two release gates.
> - **Mistake:** Embedding the whole query and ranking by similarity → **Why it's wrong:** turns "under ₹90 lakh" into a soft preference and returns a ₹1.4 crore house that is semantically perfect and useless → **Do instead:** hard constraints as filters, applied first.
> - **Mistake:** Silently relaxing constraints to avoid an empty page → **Why it's wrong:** the user browses homes they cannot buy and stops trusting every subsequent result → **Do instead:** return zero with labelled relaxations and let the user choose which constraint to bend.
> - **Mistake:** Filtering on a low-confidence or implausible parse → **Why it's wrong:** a hallucinated constraint is worse than no constraint, because the failure is invisible → **Do instead:** validate against market reality, and fall back to keyword + filter.
> - **Mistake:** A point estimate with no interval → **Why it's wrong:** ₹1.2 crore means something entirely different at ±3% than at ±25%, and the user cannot tell which → **Do instead:** quantile regression with the interval surfaced at equal visual weight.
> - **Mistake:** An interval that isn't calibrated → **Why it's wrong:** worse than none — users and downstream systems treat a stated 90% as 90%, so a 70%-covering interval replaces their judgement with a false one → **Do instead:** conformal calibration with measured coverage.
> - **Mistake:** Calibrating globally → **Why it's wrong:** global 90% coverage can be 96% in dense urban cohorts and 74% in thin ones, and the thin cohorts are exactly the fairness-sensitive ones → **Do instead:** per-cohort calibration, with under-volume cohorts refusing.
> - **Mistake:** Calibration without an expiry → **Why it's wrong:** a moving market silently invalidates last quarter's quantiles and nothing complains → **Do instead:** `valid_until`, forcing recalibration or refusal.
> - **Mistake:** An LLM producing the valuation → **Why it's wrong:** coverage guarantees come from a held-out set, a nonconformity score, and an empirical quantile. That is a statistical procedure, not a generation task; an LLM yields a plausible interval that means nothing → **Do instead:** quantile GBDT; keep the LLM on intent parsing and prose.
> - **Mistake:** No refuse path → **Why it's wrong:** the model produces confident numbers exactly where evidence is absent → **Do instead:** evidence-based sufficiency with a monitored target rate.
> - **Mistake:** Triggering refusal on model confidence → **Why it's wrong:** a model can be confidently wrong where there is no evidence; confidence is not evidence about evidence → **Do instead:** comp count, recency, dispersion, atypicality, and cohort calibration.
> - **Mistake:** Retrieving comps to justify an estimate → **Why it's wrong:** they become decoration, occasionally contradictory decoration → **Do instead:** comps as model input; removing a displayed comp must change the number.
> - **Mistake:** Comparing comps on current attributes → **Why it's wrong:** backdates today's renovation onto a three-year-old sale → **Do instead:** `attrs_at_sale`.
> - **Mistake:** Reporting only aggregate MdAPE → **Why it's wrong:** 5.8% overall can hide 4.1% in one cohort and 9.4% in another, and systematic under-valuation by area is a legal problem → **Do instead:** per-cohort error and coverage as blocking release gates.
> - **Mistake:** "We don't use protected attributes, so we're fine" → **Why it's wrong:** unfalsifiable, and rich geo features carry the information regardless of intent → **Do instead:** a proxy-detectability probe, a reviewed feature allow-list, and outcome parity tests.
> - **Mistake:** Live routing calls for commute ranking → **Why it's wrong:** 500 candidates × 80 ms against a 470 ms total budget → **Do instead:** pre-computed isochrones, and *say* they are typical-traffic rather than live.
> - **Mistake:** Rolling back the AVM without its calibration → **Why it's wrong:** conformal deltas are fitted to a specific model's residuals; mismatched, the interval has no guarantee → **Do instead:** model and calibration version move together.

---

## 4.4 Interview follow-ups

**Q: Why are search and valuation separate systems? They share a database.**
They share the corpus, the geo layer, and the fairness constraint — that's the whole overlap. Everything else differs: problem class (ranking versus regression with uncertainty), tolerance for being wrong (a bad result list versus a mispriced asset), evaluation (NDCG versus MdAPE and interval coverage), and degraded mode (filter-only search versus refusing to answer). The operational consequence is the one I'd emphasise: they need **separate release gates**. A search ranker can ship weekly behind engagement metrics. An AVM change cannot ship without per-cohort error analysis, because the failure it can introduce is invisible in aggregate metrics and expensive in a legal sense. Fusing them makes the risk flow the wrong direction — the AVM inherits the ranker's cadence.

**Q: Why not just add a ± band to a point estimate?**
Because the band wouldn't cover at its stated rate, and that's worse than having no band. Users — and especially downstream systems — treat a stated 90% interval as a 90% interval. A seller who prices at the upper bound of a 70%-covering interval sits unsold; a lender using the lower bound as a collateral floor is systematically under-collateralised. No interval at least forces the human to bring their own uncertainty. A wrong interval replaces their judgement with a false one. Getting coverage right needs quantile regression plus conformal calibration on held-out data, and that's a statistical procedure with a measurable guarantee, not a heuristic width.

**Q: Why per-cohort calibration rather than global?**
Because global coverage is an average, and an average can be honest while every individual answer is wrong. A global 90% can decompose into 96% in dense urban cohorts and 74% in thin rural ones — and the thin cohorts are precisely the ones that overlap with fairness-sensitive segments, so the failure lands where it does the most legal damage. Per-cohort calibration means some cohorts have too little holdout volume to support a coverage claim at all, and my answer there is that those cohorts **refuse**. That's uncomfortable — it means a growing platform refuses in every new market until volume arrives — but the alternative is offering an interval whose stated meaning we've never verified.

**Q: A 0% refuse rate sounds like a better product. Why is it an alarm?**
Because the properties that would have refused didn't become valuable-able; the model just stopped admitting it. A heritage bungalow on a 0.8-acre mixed-use plot with three loosely-similar comps spanning ₹4.2 to ₹11.8 crore has no defensible point estimate. A p50 of ₹7.1 crore there is arithmetic dressed as knowledge, and any seller who prices on it learns that the hard way. So the refuse rate has alarms in both directions: below 1% means the sufficiency test isn't firing, above 15% means comp-data coverage is the problem and no modelling work will fix it. And the refusal itself has to be useful — reason class, the comps that do exist with their dissimilarity flagged, and a route to a human valuer.

**Q: You refuse on "uncalibrated cohort" even when comps exist. Isn't that over-cautious?**
It's the test that makes the interval guarantee real rather than nominal. We might have comps, a trained model, and a plausible-looking p50 — and no validated coverage for that cohort, because there was never enough holdout volume or the calibration expired when the market moved. Offering a 90% interval there means asserting something we haven't checked. I'd rather refuse and say why. And it composes with the expiry mechanism: if a cohort's rolling coverage drifts to 79% and the recent sales volume is too thin to recalibrate, there genuinely is no honest interval available for that cohort right now, and pretending otherwise is the failure this design exists to avoid.

**Q: How do you actually comply with fair housing? "We don't use race" isn't much.**
It isn't, and it's unfalsifiable. What's testable is four things. First, a **feature allow-list** where every feature carries a recorded fairness review, and material-risk features need legal sign-off, not engineering sign-off. Second, **segment error parity** — MdAPE spread across cohorts ≤ 2 pp, as a blocking release gate. Third, **segment coverage parity**, because an interval covering 92% in one area and 78% in another is a fairness failure and not merely a calibration one. Fourth, a **proxy-detectability probe**: can a model recover protected characteristics from our feature vector? That test usually succeeds to some degree with rich geo features, so the gate is on the *delta* versus the incumbent — an absolute zero isn't achievable, and pretending it is turns the test into theatre. I'd also be direct that FR-5 and FR-6 are in genuine tension: school-quality features are what buyers want and a proxy risk in many geographies. Engineering can make that choice explicit, market-configurable, and testable. It cannot resolve it — that's a legal position.

**Q: The fairness gate blocks a model that's more accurate overall. What do you do?**
Accept the block. A model at 5.1% overall MdAPE with a 3.4 pp cohort spread is worse than one at 5.8% with a 1.2 pp spread, because the spread is the legal exposure and the 0.7 pp of aggregate accuracy is a product nicety. I'd want that trade decided in advance and encoded in the gate, precisely so it isn't relitigated on a day when someone has a launch date. If the accuracy gain is genuinely large and concentrated in a cohort that was previously underserved, that's a case worth making — through the documented sign-off path, with the cohort table in front of everyone, not by lowering the threshold.

**Q: Commute-time ranking in 60 ms. How?**
Pre-computed isochrones. Live routing would be 500 candidates against a 470 ms total budget — even optimistically batched at 80 ms it's out by an order of magnitude. So isochrone polygons are computed per (origin cell, mode, duration band) and cached, and enrichment becomes a point-in-polygon test at roughly 0.1 ms per candidate. The costs are staleness and storage, both acceptable: a 30-minute drive isochrone doesn't move much day to day. The part I'd insist on is **telling the user** it's typical traffic rather than live, because a stated constraint satisfied by a weaker metric is a quiet lie. This is the kind of dependency that looks free in an architecture diagram — "commute-aware ranking" is one box, and it's either a pre-computation pipeline or a broken budget.

**Q: What's your ground truth for valuation accuracy?**
A completed sale, which arrives months later and only for properties that actually sell. That's a real limitation and I'd state it rather than gloss it: properties that sell are not a random sample of properties valued — a seller who got an estimate they disliked may not list at all — so production coverage is measured on a biased subset. The mitigations are partial: holdout coverage from historical transactions (unbiased by construction, but stale), rolling production coverage from resolved sales (fresh, biased), and monitoring both. I'd rather report two imperfect measurements and name their biases than report one number as though it were clean.

**Q: What would you build first?**
The comp retrieval and the sufficiency test, with **comps-only valuation** — the industry's own method — as the initial product. It's transparent, defensible, immediately shippable, and it makes the refuse path exist from day one rather than being retrofitted around a model that never says no. Crucially, it also generates the holdout data and cohort structure the eventual quantile model needs. Then the quantile GBDT with per-cohort conformal calibration, which is where the real value is. On the search side, intent parsing with hard filters first — that's most of the product benefit for very little machinery. I'd build the fairness gate before the AVM model ships, not after, because retrofitting a blocking gate onto a shipped model means the first thing it does is block a model people are already relying on.

**Q: What breaks at 100×?**
Intent parsing becomes the entire cost structure — 400M searches a day through an external model is untenable, so the endgame is a distilled in-house parser plus an aggressive semantic cache keyed on normalised query shape, and the interesting engineering moves to cache-key design. But the more counter-intuitive break is that **scale makes uncertainty quantification worse, not better**. More markets means more cohorts means thinner volume *per cohort*, which is the opposite of what conformal calibration needs. The answer is hierarchical shrinkage toward parent cohorts — and it has to be **disclosed**, because a shrunk interval borrows strength from a market the property isn't in. That's defensible only if it's stated. It's worth flagging because the throughput numbers make it look like everything gets easier at scale, and the statistical machinery gets harder.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **AVM** | Automated Valuation Model | Deliberately *not* an appraisal; FR-12/13 keep that boundary from eroding by use |
| **Comp** | Comparable sale used as valuation evidence | Must drive the estimate, not decorate it (FR-19) |
| **`attrs_at_sale`** | A comp's attributes at the time it sold | Prevents backdating today's renovation onto an old sale |
| **MdAPE** | Median absolute percentage error | The accuracy target (≤ 6%) — and useless in aggregate alone |
| **Prediction interval** | The p10–p90 range around the estimate | The product; a point estimate without it is unusable |
| **Interval coverage** | How often the interval actually contains truth | 88–92% for a stated 90%; an uncalibrated interval is worse than none |
| **Quantile regression** | Predicting p10/p50/p90 directly | The structure that makes an interval possible |
| **Conformal calibration** | Widening the interval by an empirical quantile of held-out nonconformity | What turns a nominal band into a covering one |
| **Nonconformity score** | How far outside the band the truth fell, scaled by width | Comparable across price levels, which raw error is not |
| **Cohort** | (Geography × price band) grouping | The unit of calibration, of fairness analysis, and of refusal |
| **`valid_until`** | Calibration expiry | A moving market silently invalidates old quantiles; expiry forces the issue |
| **Sufficiency test** | Evidence check gating whether to value at all | Uses evidence, never model confidence |
| **Refuse rate** | Share of requests declined | 3–8% expected; **0% is an alarm** |
| **Atypicality** | Distance from the training distribution | Refusal trigger even in data-rich areas |
| **Comp dispersion** | Spread of adjusted comp prices | Too dispersed ⇒ no point estimate is supportable |
| **Hard constraint** | Budget, beds, area — a boundary, not a preference | Applied as a filter; never outvoted by similarity |
| **Labelled relaxation** | An explicit offer to bend one stated constraint | The honest alternative to silently widening the budget |
| **Isochrone** | Polygon reachable within a travel time | Pre-computed; the reason commute ranking fits the budget |
| **Feature allow-list** | Reviewed register of permitted features per market | Makes "we don't use protected attributes" testable |
| **Proxy risk** | A feature correlating with protected characteristics | School quality is the canonical case, and FR-5/FR-6 collide there |
| **Proxy-detectability probe** | Adversarial test recovering protected traits from features | Gated on delta versus incumbent, because zero isn't achievable |
| **Segment parity** | Comparable error *and* coverage across cohorts | Aggregate accuracy hides the legally dangerous failure |

---

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md) · **Next system:** [`../10_travel_planning_assistant/`](../10_travel_planning_assistant/)
