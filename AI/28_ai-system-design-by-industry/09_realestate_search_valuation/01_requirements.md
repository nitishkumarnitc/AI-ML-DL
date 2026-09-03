# 09 · Requirements — Real Estate: Property Search, Valuation & Recommendation

> **Shared block:** [`../00_requirements_all_systems.md#9-real-estate--property-search-valuation--recommendation`](../00_requirements_all_systems.md#9-real-estate--property-search-valuation--recommendation) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the 470 ms search budget, and the ~$15.4k/month cost arithmetic. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. Two systems, one product surface

The most common way this design goes wrong is being answered as one thing. "An AI property platform" fuses two problems that share a database and nothing else.

| | **Search & ranking** | **Valuation (AVM)** |
|---|---|---|
| Problem class | Ranking / retrieval | Regression with uncertainty |
| Being approximately right | Fine — the user re-filters | **Not fine** — a number is acted on |
| Latency | p95 < 500 ms, interactive | p95 < 2 s, considered |
| Failure cost | A worse result list | A mispriced asset; a fair-lending exposure |
| Correct model | GBDT ranker over behavioural + content features | **Quantile ensemble + conformal calibration** |
| Evaluation | NDCG, enquiry rate, session success | **MdAPE, interval coverage, segment-level bias** |
| Degraded mode | Filter-only search | **Refuse to answer** |
| Legal surface | Fair housing (ranking) | Fair housing **and** appraisal-adjacent exposure |
| Who consumes it | A buyer, browsing | A seller pricing, possibly **a lender deciding** |

They share the property corpus, the geo infrastructure, and the fairness constraint. That is the whole of the overlap.

> **Why the split matters operationally, not just conceptually:** they need separate release gates. A search ranker can ship weekly behind engagement metrics. **An AVM change cannot ship without segment-level error analysis**, because the failure it can introduce is invisible in aggregate metrics and expensive in a legal sense. Fusing them means the AVM inherits the ranker's release cadence, which is the wrong direction for the risk to flow.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | Search and valuation have independent release gates | An AVM model change cannot be deployed through the search release path; verified by pipeline separation |
| **FR-12** | P0 | Valuation outputs are labelled as estimates, not appraisals | Every API response and UI surface carries the label; consumed valuations carry it in the payload, not just the UI |
| **FR-13** | P1 | Downstream consumers of valuations are registered | Known consumers recorded, so an obligation inherited from a lender using the AVM (open question 3) is discoverable rather than a surprise |

---

## B. Hard constraints are filters, never ranking signals

FR-1 says budget, beds, and area are applied as filters. This is the same lesson as [`../01_ecommerce_shopping_agent/`](../01_ecommerce_shopping_agent/) and it is worth restating because the failure is so common and so damaging here.

### The wrong design

```
"3-bed house under ₹90 lakh in Whitefield, quiet street, near a good school"
  → embed the whole query
  → ANN over 8M listings
  → rank by similarity
  → return the top 20
```

This returns a ₹1.4 crore 4-bed. It is *semantically* excellent — quiet street, good school, Whitefield — and completely useless, because "under ₹90 lakh" is not a preference the user is expressing softly. It is a boundary.

### The right design

```
intent parse → { hard: {beds: 3, max_price: 9_000_000, area: "Whitefield"},
                 soft: ["quiet street", "near a good school"],
                 constraints_detected: [...] }
  → HARD FILTER first (PostGIS + SQL) → e.g. 4,200 candidates
  → semantic ANN over THAT SET only for the soft terms
  → rank
```

| Property | Consequence |
|---|---|
| A hard filter cannot be outvoted | No amount of semantic similarity resurrects an over-budget property |
| Filtering first shrinks the ANN problem | 8M → 4,200 candidates: cheaper and faster, not just more correct |
| Empty results are **informative** | "No 3-beds under ₹90 lakh in Whitefield" is a real answer, and better than a list of things the user cannot buy |

> **The empty-result case is where designs cheat.** The temptation is to silently relax the budget so the page is never blank. That is a product decision to waste the user's time, and it destroys trust in every subsequent result. The honest design returns zero and offers *explicit, labelled* relaxations: "0 matches. 14 if you extend to ₹1 crore; 9 if you accept 2 beds; 31 in adjacent areas." The user chooses which constraint to bend.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-14** | P0 | Hard constraints applied as query filters, never as ranking weights | Test: no result exceeds a stated budget or falls short of a stated bed count, for any query phrasing |
| **FR-15** | P0 | Zero results returned as zero, with labelled relaxation options | No silent constraint relaxation; each suggested relaxation states which constraint it bends and the resulting count |
| **FR-16** | P1 | Intent parse failures degrade to keyword + filter search | If structured extraction fails or is low-confidence, fall back rather than guessing constraints. **A hallucinated constraint is worse than no constraint** |

---

## C. The interval is the product, and it forces the architecture

Shared NFR: a 90% prediction interval must contain truth 88–92% of the time. This single row rules out most naive designs.

### C.1 Why a point estimate alone is not an answer

A valuation of ₹1.2 crore means something completely different if the model's honest uncertainty is ±3% (₹1.16–1.24 crore) versus ±25% (₹90 lakh–₹1.5 crore). The second is still useful — it tells a seller the market is thin and they need an agent's judgement — but only if it is *stated*. Delivered as a bare "₹1.2 crore", it is a fabrication with a decimal point.

### C.2 Why an *uncalibrated* interval is worse than none

Users, and especially downstream systems, treat a stated 90% interval as a 90% interval. If it actually covers 70% of the time:

| | Consequence |
|---|---|
| A seller prices at the interval's upper bound | Sits unsold; blames the platform |
| A lender uses the lower bound as collateral floor | Under-collateralised loans, systematically |
| The platform reports "we provide confidence intervals" | Technically true, materially false |

**No interval** at least forces the human to supply their own uncertainty. A wrong interval replaces their judgement with a false one.

### C.3 The architectural consequence

| Requirement | What it forces |
|---|---|
| Interval, not just a point | **Quantile regression** (predict p10/p50/p90 directly) or an ensemble spread |
| Interval that *covers* at its stated rate | **Conformal calibration** on held-out data — quantile models are not automatically calibrated |
| Calibration that holds **per segment** | Conformal calibration computed **per cohort** (geography × price band), not globally |
| Explanation via comparable sales | **Comps are part of the model output**, not a post-hoc rationalisation |

The last row is subtle and important. If comps are retrieved *after* the estimate, to justify it, they are decoration — and sometimes contradictory decoration. If the estimate is *derived from* a comp set, the comps are evidence and the explanation is true.

> **Why this rules out an LLM valuation, stated concretely:** an LLM can produce a plausible number and a plausible interval, and neither will be calibrated, because nothing in its training or inference produces a coverage guarantee. Conformal calibration requires a held-out set, a nonconformity score, and an empirical quantile. That is a statistical procedure, not a generation task. The LLM's role here is intent parsing and prose assembly, both off the numeric path.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-17** | P0 | Intervals produced by quantile regression with conformal calibration | Coverage measured on held-out data: 90% interval covers 88–92% overall |
| **FR-18** | P0 | Calibration computed and validated **per cohort** | Coverage within 85–95% for every cohort with sufficient volume; cohorts below volume threshold route to FR-4's refuse path |
| **FR-19** | P0 | Comps drive the estimate, not the explanation | The comp set is an input to the model; the displayed comps are the ones used. Verified by removing a displayed comp and observing the estimate change |
| **FR-20** | P1 | Interval width is surfaced prominently, never buried | Width shown at the same visual weight as the point estimate; API returns interval without requiring an opt-in parameter |

---

## D. Refusing to answer is a feature with a target rate

FR-4 requires an explicit "insufficient comparable evidence" rather than a wide-interval guess. The shared NFR expects 3–8%.

### D.1 Why a target *rate* rather than just a capability

A refuse path that exists but never fires is decoration. Stating an expected rate makes it testable, and makes the two failure directions visible:

| Refuse rate | Reading |
|---|---|
| **0%** | The model is guessing in thin markets. **This is an alarm, not a success.** |
| 3–8% | Expected: unique properties, thin markets, recent-transaction deserts |
| > 15% | Comp data coverage is the problem, not the model — and no modelling work will fix it |

### D.2 What "insufficient evidence" means operationally

Refusal is triggered by evidence, not by model confidence — because a model can be confidently wrong in exactly the situations where evidence is absent:

| Test | Threshold |
|---|---|
| Comp count within geographic and similarity bounds | fewer than *N* comps |
| Comp recency | no comps within the trailing window |
| Comp dispersion | comp prices too dispersed to support any point estimate |
| Property atypicality | the subject is outside the training distribution on key features |
| Cohort calibration | this cohort has insufficient volume to have validated coverage (FR-18) |

> **The last test is the one that gets missed.** A property in a cohort where we have never validated interval coverage should refuse *even if comps exist*, because we cannot honour the interval's stated meaning. Refusing on calibration grounds, not just data grounds, is what makes FR-17's guarantee real rather than nominal.

### D.3 Refusal must be useful

"We can't value this" is a dead end. A refusal should carry what is available: the comps that do exist with their caveats, a wide-but-labelled range if one is defensible, the reason (thin market vs atypical property — different user actions), and a route to a human valuer.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-21** | P0 | Refusal triggered by evidence sufficiency, not model confidence | Test: an atypical property in a data-rich area with no similar comps refuses, regardless of model output |
| **FR-22** | P0 | Refuse when the cohort's interval calibration is unvalidated | A property in an under-volume cohort refuses even with adequate comps |
| **FR-23** | P0 | Refuse rate is monitored, with alarms in both directions | Alert if the rate falls below 1% (model guessing) or exceeds 15% (data coverage problem) |
| **FR-24** | P1 | Refusal responses are actionable | Reason class, available partial evidence, and a next step; never a bare error |

---

## E. Fair housing: the constraint that shapes both halves

FR-5 forbids protected characteristics and close proxies in ranking and valuation. This is the requirement with the largest gap between "we don't use race" and actually complying.

### E.1 The proxy problem

Nobody sensible feeds demographic composition into a ranker. The exposure comes from features that correlate with protected characteristics:

| Feature | Why it is a proxy risk |
|---|---|
| **School quality ratings** | Correlate strongly with demographic composition in many geographies — and FR-6 explicitly *wants* this feature |
| Postcode / neighbourhood identity | The classic redlining proxy; a fine-grained geo feature can reconstruct historical boundaries |
| "Similar buyers also viewed" | If historical buying patterns are segregated, collaborative filtering **reproduces the segregation** and calls it personalisation |
| Historical price trends by area | Encodes the effects of past discrimination as a prediction about the future |
| Listing-photo CV features (FR-9) | Can pick up neighbourhood cues unrelated to the property's condition |
| Commute-time preferences | Correlate with income and, indirectly, with protected characteristics |

> **FR-5 and FR-6 are in direct tension and engineering cannot resolve it.** School proximity is genuinely what buyers want and genuinely a proxy risk. This needs a documented legal position per market, and the design's job is to make the choice **explicit, configurable per market, and testable** — not to quietly pick one.

### E.2 What testing actually requires

"We don't use protected attributes" is unfalsifiable without measurement. What is testable:

| Test | Method |
|---|---|
| **Proxy detectability** | Can a model predict protected characteristics from our feature vector? If yes, the features carry the information regardless of intent |
| **Segment error parity (AVM)** | MdAPE by neighbourhood cohort; the ≤ 2 pp requirement |
| **Segment coverage parity** | Interval coverage by cohort — an interval that covers 92% in one area and 78% in another is a fairness failure, not just a calibration one |
| **Ranking exposure parity** | Do equivalent properties in different neighbourhoods receive comparable ranking treatment given matched features? |
| **Counterfactual geo tests** | Same property attributes, different neighbourhood: is the valuation difference explainable by market fundamentals, or unexplained? |

The proxy-detectability test is uncomfortable because it usually succeeds — a rich geo feature set does carry demographic information. The honest response is not to claim otherwise but to bound its use, document it, and monitor outcomes.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-25** | P0 | Feature allow-list with documented fairness review per feature | No feature reaches production ranking or valuation without a recorded review; the register is auditable |
| **FR-26** | P0 | Segment error and coverage parity are release gates | An AVM release is blocked by > 2 pp MdAPE spread or out-of-band cohort coverage — **blocking, not monitored** |
| **FR-27** | P0 | Proxy-detectability test in the release pipeline | Adversarial probe reported per release; a material increase requires documented sign-off |
| **FR-28** | P1 | Market-configurable fairness policy | Which features are permitted is configuration per market, reflecting that legal positions differ by jurisdiction |
| **FR-29** | P1 | Collaborative-filtering signals audited for segregation reproduction | "Similar buyers" signals tested for whether they concentrate recommendations along neighbourhood lines |

---

## F. Pre-computation is the hidden design decision in the latency budget

The shared budget allows 60 ms for commute enrichment. A live routing API call per candidate would cost hundreds of milliseconds — for 500 candidates, seconds.

```
Live routing:  500 candidates × ~80 ms (batched, optimistically) → far outside a 470 ms budget
Pre-computed:  isochrone polygons per (origin cell, mode, duration), cached
               → a point-in-polygon test per candidate, ~0.1 ms → 60 ms covers all 500
```

The cost is staleness (traffic patterns change) and storage (many origin cells × modes × durations). Both are acceptable; a 30-minute isochrone does not move much day to day, and the alternative does not fit.

> **This is the kind of dependency that looks free in an architecture diagram.** "Commute-time ranking" is one box. It is either a pre-computation pipeline or a broken latency budget, and which one is not visible in the box.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-30** | P0 | Commute enrichment served from pre-computed isochrones | No live routing calls in the search path; verified by dependency audit |
| **FR-31** | P1 | Isochrone freshness bounded and stated | Refresh cadence documented; typical-traffic assumption surfaced to the user rather than implied as live |

---

## G. Additional non-goals (beyond the shared block)

- **Not** a regulated appraisal — and FR-12/FR-13 exist to keep that boundary from eroding by downstream use.
- **Not** ingesting demographic data at all (the cleanest way to satisfy part of FR-5).
- **Not** an LLM on the numeric path. LLMs parse intent and assemble prose; they do not produce estimates or intervals.
- **Not** rental yield modelling in v1.
- **Not** live traffic routing (FR-30).
- **Not** mortgage underwriting — see [`../../21_ai-system-design-deep-dives/08_credit_risk_scoring_engine.md`](../../21_ai-system-design-deep-dives/08_credit_risk_scoring_engine.md).

---

## H. Open questions carried into the HLD

Beyond the shared block's four:

1. **What is the legal position on school-quality features, per market?** FR-5 versus FR-6, unresolvable by engineering, and the answer changes the feature allow-list.
2. **What cohort definition is used for segment fairness?** Neighbourhood boundaries are themselves contested, and the choice of cohort determines whether bias is detected. A coarse cohort can hide precisely the bias the requirement targets.
3. **Is the comp data complete enough for the target refuse rate?** If refusal would fire on 20% of requests, that is a data-acquisition project, not a modelling one, and the product needs to know before launch.
4. **What interval width is commercially acceptable?** A calibrated ±20% is honest and may be unsellable. Narrowing it while keeping coverage means better features or more comps — never a smaller stated interval.
5. **Does a lender consume the AVM?** If so, the "not an appraisal" boundary is thinner than intended and obligations follow. FR-13 makes this discoverable; it does not make it safe.

---

**Next:** [`02_hld.md`](02_hld.md) →
