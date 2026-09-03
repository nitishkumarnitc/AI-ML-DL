# 08 · Requirements — Media: Content Recommendation & Ranking

> **Shared block:** [`../00_requirements_all_systems.md#8-media--content-recommendation--ranking`](../00_requirements_all_systems.md#8-media--content-recommendation--ranking) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the 335 ms latency budget, and the ~$132k/month cost arithmetic. **Those numbers are not repeated here.**
>
> **Overlap note:** [`../../27_ai-platform-system-design/06_recommendation_system/README.md`](../../27_ai-platform-system-design/06_recommendation_system/README.md) owns two-tower training, ANN index construction, and feature-store mechanics. This document assumes them and spends its length on the objective.
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. The objective function *is* the design

Most system-design answers to "build a feed ranker" describe the pipeline: retrieve, rank, re-rank, serve. The pipeline is the easy part and it is largely a solved shape. The hard part is what the ranker is *maximising*, because that single decision determines what the product becomes.

### A.1 Why single-objective engagement optimisation fails predictably

Train a ranker on `P(click)` and it will, correctly and without any bug, learn that:

| Learned behaviour | Why it maximises the objective | What it costs |
|---|---|---|
| Outrage-inducing content | Anger drives clicks and shares more reliably than satisfaction | Measured harm; degraded discourse |
| Cliffhangers and withheld payoff | Non-resolution drives the next click | User-reported regret |
| Extreme positions over moderate ones | Extremes are more clickable than nuance | Polarisation |
| Content similar to what was just clicked | Short-term reward is easy to predict | Narrowing; filter bubbles |
| Autoplay-friendly, compulsive formats | More impressions per session | Session regret; "why did I spend an hour on this" |

**None of these is a modelling error.** They are the objective being satisfied. This is worth stating precisely because the instinct in a review is to reach for a better model, and a better model optimising the same objective gets there faster.

### A.2 The multi-term objective

```
score(user, item) =   w_engage    · P(meaningful_engagement)
                    + w_dwell     · E[dwell | click]         (satiation-capped)
                    + w_share     · P(share)
                    − w_report    · P(report)
                    − w_seeless   · P("see less of this")
                    − w_hide      · P(hide / skip-with-intent)
                    − w_regret    · P(session-end dissatisfaction)
                    + w_diversity · novelty_bonus
                    + w_creator   · distribution_fairness_term
```

Three properties matter more than the exact terms:

| Property | Requirement | Why |
|---|---|---|
| **Negative terms are predicted, not filtered** | The ranker has heads for `P(report)`, `P(see_less)` — it *anticipates* harm rather than reacting to it after the fact | A post-hoc filter cannot stop content the ranker actively wanted to promote |
| **Weights are config, not code** | Versioned, owned by a named product owner, changed through review | A weight quietly set in a loss function is a product decision made by whoever happened to write the training script |
| **Every weight change is an experiment** | Weight changes ship through the same A/B and guardrail machinery as model changes | Otherwise weights become the untracked backdoor around the guardrails |

> **The uncomfortable truth to say out loud:** these weights encode a value judgement about how much engagement a unit of user-reported harm is worth. There is no way to avoid making that judgement — a single-objective ranker just makes it implicitly and sets the harm weight to zero. **Making it explicit, versioned, and owned is the only honest option.**

### A.3 The `dwell` term needs a cap, and the reason is instructive

Raw dwell time rewards content that is slow, confusing, or hard to leave. A video that buries its answer at the end scores better than one that answers immediately. So the dwell term is **satiation-capped**: credit rises to a per-format threshold and then flattens.

This generalises: **every positive signal has a degenerate maximum**, and the design work is finding it before the model does.

| Signal | Degenerate maximum | Mitigation |
|---|---|---|
| Clicks | Clickbait | Weight `meaningful_engagement` (click + dwell + no immediate back-out) |
| Dwell | Slow, withholding content | Cap per format |
| Shares | Outrage (shared *against*, not endorsed) | Separate share-with-comment sentiment; negative shares count negatively |
| Session length | Compulsive use | Regret survey as an explicit negative term |
| Follows | Engagement-bait ("follow for part 2") | Weight *retained* follows at 30 days, not follows |

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | Ranker predicts negative outcomes as first-class heads | Model outputs calibrated `P(report)`, `P(see_less)`, `P(hide)`; calibration measured per head, not just AUC |
| **FR-12** | P0 | Objective weights are versioned config with a named owner | Weight changes are auditable, attributable, and reversible; the serving path records `objective_weights_ver` on every request |
| **FR-13** | P0 | Every positive signal is satiation-capped or composite | No raw-maximisation term in the objective; each term documented with its degenerate maximum and the mitigation |
| **FR-14** | P1 | Weight changes ship as experiments | A weight change cannot reach 100% of traffic without passing the same guardrails as a model change |

---

## B. A guardrail that cannot block a release is not a guardrail

Shared NFR row 6 makes harm metrics release-blocking. This is the single most consequential sentence in the requirements, because it imposes real architecture.

### B.1 What "release-blocking" actually requires

| Requirement | Implication |
|---|---|
| The metric must be measurable **per experiment arm** | Interaction logging must carry the arm assignment, at 3.6B events/day |
| It must be measurable **fast enough to matter** | A guardrail that takes two weeks to compute cannot halt a rollout |
| It must have a **pre-agreed threshold** | "Looks worse" is not a decision procedure; a number agreed *before* the experiment is |
| It must be able to halt **without a human** | Any human in the loop means the halt happens after the harm, during a debate |
| It must be **hard to override** | Overriding must be possible (false alarms exist) but must require a named approver and produce a record |

> **The mechanism that makes this real is auto-halt.** If halting requires a meeting, the design has an intention rather than a constraint. This is why FR-9's experimentation platform is a **P0 in this design specifically** — in most recsys designs it's infrastructure; here it's the enforcement mechanism for the primary NFR.

### B.2 The measurement problem nobody mentions

Harm metrics are **low-rate and slow-moving**. Reported-content rate might be 0.02% of impressions. Detecting a 10% relative regression at that base rate needs a lot of traffic and time.

```
Base rate p = 0.0002 · detect 10% relative lift (p → 0.00022) · 80% power, α = 0.05
Rough per-arm requirement ≈ 16 · p(1−p) / (0.1p)²  ≈ 16 · 0.0002 / (0.00002)²
                          ≈ 8.0M impressions per arm       (order-of-magnitude)
```

At 3.6B impressions/day, 8M per arm is minutes of traffic for a large experiment — but a 1%-traffic experiment takes hours, and **regret survey responses**, which arrive at a tiny sampled rate, take days.

That produces a tiered guardrail design:

| Tier | Signal | Detectable in | Role |
|---|---|---|---|
| **Fast** | Report rate, "see less" rate, hide rate | Minutes to hours | **Auto-halt** authority |
| **Medium** | Retention proxies, session-regret proxies, distribution concentration | 1–3 days | Blocks full ramp |
| **Slow** | Regret surveys, 30-day retention, creator-distribution health | 1–4 weeks | Blocks permanent launch; reviewed retrospectively |

> **The honest caveat:** auto-halt can only ever run on fast signals, which are the *proxies*, not the outcomes we actually care about. The slow signals are the real ones, and they cannot gate a rollout in real time. This is a genuine limitation, not something to design away — the mitigation is a **holdback population** kept off every launched change so slow metrics remain measurable against a stable baseline long after the experiment ends.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-15** | P0 | Automatic rollout halt on fast-guardrail regression | Injected-regression test: an arm with a deliberately degraded harm profile is halted without human action, within the detection window |
| **FR-16** | P0 | Guardrail thresholds pre-registered per experiment | An experiment cannot start without registered thresholds; post-hoc threshold changes are recorded as such |
| **FR-17** | P0 | Long-term holdback population | A persistent small holdback excluded from launched changes, enabling slow-metric measurement against a stable baseline |
| **FR-18** | P1 | Guardrail override requires a named approver and a record | Overrides are possible but never anonymous or invisible |

---

## C. The feedback loop, and why offline metrics lie

This is the failure mode I would raise unprompted, because it is invisible to every standard metric.

### C.1 The loop

```
ranker → what users see → what users interact with → training data → ranker
```

The training set is not a sample of user preferences. It is a sample of **user responses to what this ranker chose to show**. Consequences:

| Effect | Mechanism | Why offline metrics miss it |
|---|---|---|
| **Position bias** | Item at slot 1 gets far more clicks than the same item at slot 15 | The model learns "slot 1 items are good", and offline AUC rewards it for reproducing that |
| **Presentation bias** | Never-shown items have no positive labels, ever | They are absent from evaluation too, so the metric cannot notice |
| **Popularity amplification** | Popular items get shown more, so they accumulate more positives, so they are shown more | Offline metrics improve as concentration worsens |
| **Distribution collapse** | Creator and topic diversity narrows over weeks | No standard metric measures it |
| **Interest narrowing** | Short-term reward is easiest to predict from recent behaviour | Predicting the user's current bubble accurately *is* high offline accuracy |

> **The trap stated plainly:** a model that has collapsed the distribution scores *better* offline, because it has become very good at predicting its own behaviour. Offline AUC going up while creator diversity goes down is not a paradox — it is the expected signature of the loop closing.

### C.2 What has to be built

| Mitigation | Mechanism | Cost |
|---|---|---|
| **Position-bias correction** | Inverse-propensity weighting, or train on randomised-slot data | IPS increases variance; randomisation costs some engagement |
| **Exploration budget** | A slice of impressions to items the ranker is uncertain about | Direct engagement cost, paid deliberately |
| **Randomised-slot logging** | A small fraction of requests with shuffled slots, logged separately | Small, degraded feed for those users |
| **Distribution monitoring** | Gini / entropy over creators and topics, tracked as a first-class metric | Cheap; the highest-value item on this list |
| **Counterfactual evaluation** | Off-policy estimators before online tests | Analytical effort |

Only one of these is cheap, and it is the one most often skipped: **measuring distribution concentration**. Everything else costs engagement; monitoring costs a dashboard.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-19** | P0 | Impressions logged with slot position and propensity | Every impression records slot, the candidate set size it was drawn from, and a propensity estimate — required for unbiased training |
| **FR-20** | P0 | Exploration budget on served impressions | A configurable fraction of slots allocated to exploration; new items receive a guaranteed impression floor (FR-6) |
| **FR-21** | P0 | Distribution-health metrics are release guardrails | Creator-concentration Gini and topic entropy tracked per arm; a regression beyond threshold blocks ramp |
| **FR-22** | P1 | Randomised-slot logging stream | A small fraction of requests served with randomised slots to provide bias-free training and evaluation data |
| **FR-23** | P1 | Counterfactual offline evaluation before online tests | Candidate rankers evaluated with off-policy estimators; online tests reserved for candidates that pass |

---

## D. Integrity filtering happens *before* ranking, and the ordering is the requirement

FR-4 says policy filtering comes before the ranker sees candidates. This looks like an implementation detail and is actually load-bearing.

| Ordering | Consequence |
|---|---|
| **Filter → rank** (chosen) | The ranker never scores, never learns from, and never has the opportunity to promote violating content |
| Rank → filter | The ranker's top item may be removed, leaving a hole; worse, the ranker **trains on** violating content that performed well, and learns the pattern that made it perform |

The second point is the real one. Post-filtering keeps violating content out of the *response* but not out of the *training data*, so the model keeps learning that this kind of content is engaging — and then generalises the pattern to content that is borderline but not removable.

There is a cost to filter-first: it must happen at candidate-set scale (~1,000 items, 25 ms) rather than at result scale (20 items), which means the filter must be a fast lookup against precomputed decisions, not a model invocation.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-24** | P0 | Integrity decisions precomputed and served as a fast lookup | Filter completes for ~1,000 candidates within 25 ms; no synchronous model calls in the filter path |
| **FR-25** | P0 | Filtered items are excluded from training labels | Verified: a removed item's engagement events do not contribute positive training signal |
| **FR-26** | P0 | Demotion is graded, not binary | Integrity supplies a demotion multiplier as well as a removal flag; borderline content is downranked rather than removed or fully promoted |
| **FR-27** | P1 | Filter freshness bounded | A newly-actioned item stops being served within 60 s of the integrity decision |

---

## E. Creators are a second user population with a different objective

The shared block names the creator as a primary user, and their needs conflict with the consumer's in a specific way.

| | Consumer wants | Creator wants |
|---|---|---|
| Objective | The best 20 items for them | A fair chance at distribution |
| Failure | A boring or harmful feed | Inexplicable collapse in reach |
| Timescale | This session | Weeks and months |

A ranker optimised purely for consumers converges on a small set of proven creators, which is locally optimal and globally destructive: the supply side starves, new creators never establish, and the corpus stops renewing. **The consumer objective, maximised, destroys its own input.**

Hence two terms that look like altruism and are actually supply-side investment:

- **Exploration impressions for new items** (FR-6/FR-20) — without them, a new creator's first post has no data, so it is never shown, so it never has data.
- **A distribution-fairness term** in the objective — a small positive weight on under-distributed creators with quality signals above a floor.

And FR-8's transparency: creators experiencing a reach drop currently get silence, which produces conspiracy theories and churn. Aggregate-level explanation ("your recent posts had a higher-than-usual 'see less' rate") is both honest and actionable.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-28** | P0 | New-item impression floor | Every eligible new item receives a minimum exploration allocation within its first N hours, subject to integrity clearance |
| **FR-29** | P1 | Creator-distribution health is a monitored metric with thresholds | Share of impressions to the top 1% of creators, and new-creator establishment rate, tracked and alerted |
| **FR-30** | P1 | Aggregate creator-side explanation | Per-creator distribution summary with the dominant contributing factors, at aggregate not per-item granularity |

---

## F. Additional non-goals (beyond the shared block)

- **Not** integrity classification — consumed as precomputed decisions (FR-24).
- **Not** the ad auction; ads are interleaved downstream and their slots are not part of this objective.
- **Not** a "chronological feed" product — that is the degraded fallback.
- **Not** an LLM in the serving path. At 60k RPS inside 350 ms it is neither affordable nor fast enough; where LLMs help is offline (content understanding, embedding generation, topic taxonomies).
- **Not** deciding platform policy — the design enforces policy decisions, it does not author them.
- **Not** cross-platform identity resolution.

---

## G. Open questions carried into the HLD

Beyond the shared block's four:

1. **What are the agreed guardrail thresholds, numerically?** FR-15's auto-halt is unimplementable without them, and agreeing them under the pressure of a launch is exactly when they get set permissively.
2. **How large can the exploration budget be before engagement loss is unacceptable?** This single number determines both cold-start quality and how badly the feedback loop bites.
3. **Is a randomised-slot stream acceptable to the business?** It means deliberately serving a worse feed to a small population. The unbiased data is worth a great deal; the decision is not engineering's to make.
4. **What is the holdback population's size and permanence?** FR-17 requires users who never receive launched changes — valuable for measurement, and a real cost to those users' experience.
5. **Does "meaningful engagement" have an agreed definition?** Every term in the objective depends on it, and it is the definition most likely to be quietly redefined toward whatever is currently improving.

---

**Next:** [`02_hld.md`](02_hld.md) →
