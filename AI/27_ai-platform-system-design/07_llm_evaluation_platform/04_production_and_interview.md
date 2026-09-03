# 04 · Production & Interview — LLM Evaluation Platform

> **Phase 4 of 4** · [← LLD](03_lld.md) · [README](README.md)

---

## 4.1 AI-specific concerns

### Cost

| Cost centre | Per full run | Per smoke run |
|---|---:|---:|
| Judge calls (tiered small/frontier) | $1.80 | $0.45 |
| **Target app invocations** | $2.28 | $0.57 |
| Cache savings (~50% on reruns) | −$1.78 | −$0.12 |
| **Net** | **≈ $2.30** | **≈ $0.90** |

**Counting the target app's own calls is not optional** — an eval run *executes the system under test*, so
the platform's bill includes 200 executions of the tenant's feature. That's ~35% of run cost, and designs
that budget only judge calls understate it materially.

**The three levers, in order of structural significance:**

| Lever | Kind | Effect |
|---|---|---|
| **Tiered suites** (50 PR / 200 nightly) | **Architectural** — resolves a requirement conflict | −75% of PR-path volume |
| Judge cache keyed on all versions | Infrastructural | −~50% on iterative reruns |
| Tiered judge models | Configuration | −60% judge cost |

### Runtime — a product requirement, not an SLO

Above ~10 minutes teams disable the gate, and **a bypassed gate is worse than no gate** because it leaves
behind the belief that evaluation is happening. Two properties carry the budget:

- **32-way concurrency** — 600 judge calls serially at ~2 s each is 20 minutes; concurrency is what makes
  10 minutes reachable at all, not an optimization on top.
- **Target-output caching** — re-running after changing only a *metric* shouldn't re-invoke the tenant's app
  200 times.

### Judge determinism — the platform's foundation

**If the judge is noisy, every gate on the platform is noise.** A naive "score 0–10" judge swings several
points on identical inputs, so a 3-point regression threshold fires at random. Four independent controls,
all required:

| Control | Closes |
|---|---|
| **Frozen `eval_steps`** (generated once per metric, then versioned) | The judge re-deriving what the metric *means* on each call — the dominant drift source |
| **Probability-weighted scoring** over score tokens | The argmax tie-break between near-equal candidates |
| `temperature=0` | Sampling randomness — **necessary but nowhere near sufficient** |
| Pinned `judge_version` + versioned cache keys | Silent provider-side model changes |

**Why `temperature=0` alone doesn't work**, since it's the intuitive answer: it makes sampling deterministic
but not the *score*. Provider-side batching, hardware non-determinism, and floating-point ordering all shift
which token wins when two are nearly tied — and near-ties are exactly the ambiguous cases that matter.
Probability weighting sidesteps the tie-break entirely by using the distribution rather than the winner.
Mechanism detail in [`16_evals/15`](../../16_evals/15-mastering-g-eval-deterministic-judge.md).

### Judge accuracy — separate from determinism, and both required

| | σ (determinism) | MAE (accuracy) | Consequence |
|---|:---:|:---:|---|
| Healthy | < 0.05 | ≤ 1.0 | Gate is trustworthy |
| Reproducibly wrong | 0.01 | 4.0 | **Passes gates it shouldn't** — worst case |
| Accurate but noisy | 0.5 | 2.0 | Blocks deploys at random; teams disable the gate |

**Cohen's κ is checked *before* MAE**, and the order is load-bearing: if humans can't agree with each other
(κ < 0.6), a high MAE isn't the judge's fault — it's measuring an ambiguous rubric. Recalibrating against
inconsistent labels makes the judge worse.

### Evaluating the evaluator

The platform must test itself, and this is the part that's easy to omit:

| Self-test | What it catches | Gate |
|---|---|---|
| **Determinism canary** — 20 fixed cases × 5 reruns, σ per metric | Judge variance regression | **Blocks judge upgrades** |
| **Cache-bypass assertion** on the canary | A canary that measures cache consistency and trivially passes | Test-level |
| Metric reference tests | Drift from published metric definitions | Blocks metric changes |
| Calibration freshness | Stale MAE presented as current | Alerts |
| Estimate-vs-actual cost | Systematic underestimation teams budget on | Alerts |

**The cache-bypass assertion is a real trap worth naming.** The obvious canary implementation routes through
the judge cache, gets identical cached verdicts, reports σ = 0, and passes forever — while measuring
nothing.

### Dataset rot — the failure with no technical detection

**Datasets drift from what the product actually does.** The infrastructure keeps working perfectly, gates
keep passing, teams keep trusting them, and quality drifts unmeasured.

| Mitigation | Nature |
|---|---|
| `owner_email` required on every dataset | Schema-level: makes ownership an input, not an afterthought |
| Flag cases unchanged > N months for review | Heuristic prompt, not detection |
| Promote production failures into datasets ([FR-12](01_requirements.md#datasets)) | Keeps cases current |
| Human review of `expected` values on a cadence | The only real fix |

**This is a staffing question wearing technical clothes** ([Q1](01_requirements.md#open-questions)), and it's
the most common way eval platforms decay while appearing healthy.

### Prompt injection

**Mostly not this platform's concern** — it evaluates offline, holds no tools, and takes no actions. Two
things that *are* in scope:

| Concern | Control |
|---|---|
| A malicious **dataset case** crafted to manipulate the judge into a high score | Judge prompts fence case content as data; a suspiciously perfect score on an anomalous case is worth flagging |
| **Cross-tenant dataset access** | `tenant_id` from the token as a mandatory predicate; 403s logged as security events |

**The gaming vector is real if evaluation ever becomes a performance metric.** A team whose bonus depends on
a green gate has an incentive to craft cases that pass, which is an argument for platform-owned shared
metrics and minimum thresholds ([F10](02_hld.md#25-failure-modes--blast-radius)) rather than
fully tenant-defined evaluation.

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Metrics | Alert |
|---|---|---|
| **Determinism** | σ per metric, current judge version | **σ > 0.05** ⚠️ |
| **Calibration** | MAE vs human; Cohen's κ; label sample size | MAE > 1.0 · κ < 0.6 · labels > 30 days stale |
| Runtime | Suite duration p50/p95 by suite type | Full p95 > 10 min · smoke p95 > 3 min |
| **Verdict mix** | pass / fail / **inconclusive** / target_unhealthy | Inconclusive > 20% (suite too small) · target_unhealthy spike |
| Cost | $/run by suite; estimate vs actual; per-tenant | Per-tenant burn > 1.5× 7-day average |
| Cache | Judge-cache hit rate; target-output hit rate | Judge hit rate < 30% |
| **Dataset health** | Age of last edit; case count; owner set | Any dataset unedited > 6 months |
| **Baseline health** | Age of pinned baseline per app | **Baseline age > 90 days** |
| Adoption | Runs/team/day; teams with zero runs this week | A team going quiet — likely bypassing the gate |

**"Teams with zero runs this week" is the adoption canary.** The platform's real failure mode isn't an
outage — it's teams quietly routing around it. A team that stops submitting runs has usually disabled the
gate, and that's worth a conversation rather than a dashboard nobody reads.

**Inconclusive rate above ~20%** means the smoke suite is too small to resolve the thresholds being used —
either grow the suite or loosen the threshold, but don't leave engineers with a gate that mostly shrugs.

### Triage order

1. **Determinism canary σ.** If the judge is noisy, nothing else is interpretable. Check first, always.
2. **Verdict type.** `target_unhealthy` ⇒ the tenant's app, not us. `inconclusive` ⇒ sample size vs
   threshold.
3. **Baseline comparability.** A `422` means judge/metric versions moved — expected after an upgrade, and
   the fix is re-baselining, not investigating quality.
4. **Calibration freshness.** A stale MAE presented as current is worse than none.
5. **Cache hit rate.** A collapse usually means a version bumped somewhere and cost is about to spike.
6. **Per-tenant concurrency and target latency.** One slow tenant explains platform-wide slowness.
7. **Dataset age.** Rules in rot.
8. **Only then** the metric definition or judge model itself.

### Rollback

| Change | Rollback | Notes |
|---|---|---|
| **Judge version** | Repin; **cache auto-invalidates** (version is in the key) | Runs judged by the old version stay comparable to their baselines |
| Metric definition | Revert `metric.version` | Invalidates cache correctly; **re-baseline required** |
| `eval_steps` regenerated | Revert to the frozen prior version | This is why they're stored rather than regenerated |
| Threshold | Config push | Instant |
| Dataset version | Repin the run to the prior version | Immutability makes this trivially safe |
| Suite tiering | Config | Instant |

**Judge and metric rollbacks require re-baselining, and that's correct rather than annoying.** A baseline
judged under the old version isn't comparable to runs under the new one, so the platform refuses the
comparison ([E1](03_lld.md#36-edge-cases--correctness)) instead of producing a delta that measures the judge
change rather than the app change.

---

## 4.3 Common mistakes

> **Mistake:** One comprehensive suite on every PR.
> **Why it's wrong:** ~$102k/month and 10+ minute gates ⇒ teams disable it, and a bypassed gate creates
> false confidence.
> **Do instead:** tiered suites — 50-case smoke on PR, 200-case full nightly ([§1.6](01_requirements.md#the-three-levers)).

> **Mistake:** A naive "score this 0–10" judge.
> **Why it's wrong:** multi-point swings on identical inputs make a 3-point regression threshold fire on
> noise. Every gate becomes a coin flip.
> **Do instead:** frozen CoT steps + probability-weighted scoring ([§3.3](03_lld.md#g-eval-scoring--the-stabilization)).

> **Mistake:** Assuming `temperature=0` gives determinism.
> **Why it's wrong:** it fixes sampling, not scoring. Batching, hardware, and float ordering still flip
> near-ties — which are the ambiguous cases that matter.
> **Do instead:** probability-weight over the score-token distribution.

> **Mistake:** Regenerating judge evaluation steps on every call.
> **Why it's wrong:** the judge re-derives what the metric means each time — the dominant source of drift.
> **Do instead:** generate once, freeze, version ([§3.1](03_lld.md#metrics--versioned-with-the-cot-steps-that-stabilize-them)).

> **Mistake:** Mutable datasets.
> **Why it's wrong:** a metric change between runs might be the code or the *test*, and you can't tell which.
> **Do instead:** immutable content-addressed versions, recorded on every run.

> **Mistake:** Comparing against the previous run.
> **Why it's wrong:** permits a ratchet — twenty consecutive 2-point drops each pass a 3-point threshold and
> the feature loses 40 points invisibly.
> **Do instead:** a pinned baseline promoted deliberately ([§2.2](02_hld.md#regression-detection)).

> **Mistake:** Binary pass/fail on a 50-case suite.
> **Why it's wrong:** forces a decision the sample can't support; blocking on noise is what gets gates
> disabled.
> **Do instead:** three verdicts with a confidence interval — `inconclusive` defers to the nightly run.

> **Mistake:** Judging partial results when the target app is down.
> **Why it's wrong:** an outage reads as a catastrophic quality regression, and an engineer hunts a prompt
> bug that doesn't exist.
> **Do instead:** `424 target_unhealthy` as a distinct terminal state ([E2](03_lld.md#36-edge-cases--correctness)).

> **Mistake:** Treating an unparseable judge response as a score of 0.
> **Why it's wrong:** manufactures a regression out of a parsing bug.
> **Do instead:** mark the case errored, exclude from the mean, surface the error count.

> **Mistake:** Omitting the version from cache keys.
> **Why it's wrong:** stale verdicts from an older judge or edited metric silently corrupt comparisons.
> **Do instead:** every version that could change the verdict goes *in* the key.

> **Mistake:** Recalibrating the judge when humans disagree with each other.
> **Why it's wrong:** calibrating against inconsistent labels makes it worse. Low κ means the **rubric** is
> ambiguous.
> **Do instead:** check κ before MAE and fix the rubric first ([§3.3](03_lld.md#calibration)).

> **Mistake:** Running the determinism canary through the judge cache.
> **Why it's wrong:** it measures cache consistency, reports σ = 0, and passes forever while testing nothing.
> **Do instead:** the canary bypasses the cache, asserted in the test.

> **Mistake:** Letting teams set their own thresholds without minimums.
> **Why it's wrong:** a gate that can't fail is theatre — especially if evaluation becomes a performance
> metric.
> **Do instead:** platform minimums; make loosening a reviewed, visible change.

---

## 4.4 Interview follow-ups

### "The requirements say $2 per run and a 10-minute CI gate. Can you hit both?"

Not as stated — a 200-case suite is about $6.78 once you count the target app's own 200 invocations, which is
roughly 35% of the cost and the part people forget. Three levers get most of the way: small-tier judges for
cheap metrics, a judge verdict cache keyed on all versions, and tiered suites. Tiering is the one that's
structural rather than a tune: a 50-case smoke suite on every PR at ~$0.90 and a 200-case full suite nightly
at ~$2.30. That resolves what was actually a requirement conflict — "fast and cheap enough for every PR" and
"thorough enough to trust before release" were being forced onto one artifact. The honest trade is that a
smoke suite can miss a regression the full suite would catch, so a bad change can merge and be caught up to
24 hours later. Fine for internal features with fast rollback; not fine for something shipping to customers
without a canary.

### "Why isn't `temperature=0` enough for judge determinism?"

Because it makes *sampling* deterministic, not *scoring*. When the judge is genuinely torn between 7 and 8,
which token wins the argmax depends on provider-side batching, hardware non-determinism, and
floating-point ordering — and those near-ties are exactly the ambiguous cases that matter. So you get
multi-point swings on identical inputs, and a 3-point regression threshold fires at random. The fix is to
stop looking at which token won and use the distribution instead: probability-weight over the candidate
score tokens, so a judge torn between 7 and 8 returns ~7.5 every time. Combined with freezing the
chain-of-thought evaluation steps so the judge isn't re-deriving what the metric means on each call, that
brings σ under 0.05.

### "How do you know the judge is any good?"

Two independent measurements, and both are necessary. **MAE against human labels** — is it accurate? I'd
gate at MAE ≤ 1.0 on a 0–10 scale. And **Cohen's κ among human raters** — is the rubric even unambiguous?
The order matters: if humans can't agree with each other, a high MAE isn't the judge's fault, and
recalibrating against inconsistent labels makes it worse. The failure combination people miss is
*reproducibly wrong* — σ near zero, MAE of 4 — which passes gates it shouldn't and looks perfectly healthy
on a determinism dashboard.

### "A team says the gate keeps failing but they changed nothing. What's happening?"

Check the determinism canary first — σ per metric on a fixed case set, five reruns, cache bypassed. If σ
exceeds the threshold, the judge is noisy and every gate on the platform is a coin flip. Second possibility
is that the verdict is `inconclusive` rather than `fail` and their CI is treating it as failure — a 50-case
suite has real sampling error and the honest answer when the confidence interval straddles the threshold is
"I don't know." Third is a baseline comparability issue: if the judge or metric version moved, the platform
should be returning a 422 rather than comparing numbers that measure the judge change instead of their app.

### "Why immutable datasets? That seems inconvenient."

Because without it you can't attribute a metric change to a cause. If a dataset can be edited in place, a
5-point drop between two runs might be the model, the prompt, or someone quietly rewording an expected
answer — and there's no way to tell. Immutability plus recording the resolved version on every run means a
six-month-old run's numbers still mean something, and replaying it uses exactly the cases it used. It also
makes rollback trivial: repin the version. The inconvenience is real but small — a "change" is just a new
version with a change note.

### "What's the failure mode you'd worry about most in a year?"

Dataset rot, because there's no technical detection and every signal looks healthy. The infrastructure works
perfectly, gates keep passing, teams keep trusting them — while the test cases slowly stop representing what
the product actually does. Expected answers reflect a policy from eighteen months ago; the product changed;
the gate doesn't notice. The mitigations are heuristic at best: require an owner on every dataset, flag cases
unchanged past some threshold, promote production failures into the golden set. Fundamentally it's a staffing
question dressed as a technical one, and worth raising before launch rather than a year in.

### "You compare against a pinned baseline. Why not just the previous run?"

Because rolling comparison permits a ratchet. Twenty consecutive 2-point drops each pass a 3-point
threshold, and the feature quietly loses 40 points with every individual comparison looking fine. A pinned
baseline makes cumulative drift visible and turns promoting a new baseline into a deliberate act with an
owner and a timestamp. The cost is that baselines go stale, so I'd alert when one is older than 90 days —
comparing against something ancient makes the gate meaningless in the other direction.

### "The target app returns 503 for most cases. What does the run report?"

`424 target_unhealthy`, as a distinct terminal state — not a quality failure. The naive implementation judges
whatever succeeded, computes a mean over nine cases, finds a massive regression, and blocks the PR with a
quality verdict. The engineer then spends an hour hunting a prompt bug that doesn't exist. Detecting
majority-error and failing with an infrastructure reason saves that hour every time it happens, and it keeps
the quality dashboards honest.

### "What breaks at 10× — 200 teams?"

Dataset ownership, not infrastructure. Judge rate limits and store partitioning are ordinary scaling
problems. But 200 teams' datasets rotting in parallel is the [F3](02_hld.md#25-failure-modes--blast-radius)
problem multiplied, and infrastructure doesn't fix it. At that scale the platform has to make rot *visible* —
a dataset health score surfaced to owners, staleness alerts, prompts to review — otherwise you have 200
teams' worth of green gates measuring nothing. The interesting secondary move is self-hosting the judge on
[04](../04_llm_inference_platform/README.md): at continuous high volume the utilization conditions that made
self-hosting lose there no longer hold, and it permanently resolves the log-probability dependency.

### "What if the provider stops exposing log-probabilities?"

That's assumption [A1](01_requirements.md#assumptions) and it's the technical dependency that could force a
redesign, since probability-weighted scoring needs them. The fallback is an ensemble of three judge calls
with the median — comparable variance reduction at roughly triple the cost and latency, which would push
back on the tiering economics. I'd also mark those runs non-comparable to prior baselines, because the
scoring mechanism changed. Longer term it's an argument for self-hosting the judge, where log-prob access is
guaranteed by construction.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Golden dataset** | Curated (input, expected) cases used as ground truth | Immutable and versioned, or comparison is meaningless |
| **Dataset rot** | Cases drifting from what the product now does | Gates keep passing while quality drifts — **no technical detection** |
| **LLM-as-a-judge** | Using an LLM to score another LLM's output | Scalable evaluation; **worthless if not stabilized** |
| **G-Eval** | Frozen CoT eval steps + probability-weighted scoring | The mechanism delivering σ < 0.05 |
| **`eval_steps`** | Chain-of-thought criteria generated once, then frozen | Regenerating per call is the dominant drift source |
| **Probability-weighted score** | Expectation over candidate score tokens | Removes the argmax tie-break that causes multi-point swings |
| **Determinism (σ)** | Score standard deviation across identical reruns | Must sit well below the regression threshold or gates fire on noise |
| **Determinism canary** | Fixed cases re-scored per judge version, cache bypassed | The most important test the platform runs on itself |
| **MAE vs human** | Mean absolute judge–human score difference | Judge *accuracy*; independent of determinism |
| **Cohen's κ** | Inter-rater agreement among humans | Low κ ⇒ the **rubric** is ambiguous, not the judge |
| **Reference-based / reference-free** | Metric needs an expected answer, or doesn't | Determines whether `expected` is required on a case |
| **Pinned baseline** | An explicitly promoted run used for comparison | Prevents the slow-drift ratchet |
| **Tiered suites** | Small smoke on PR, full suite nightly | The structural fix to the cost/runtime conflict |
| **`inconclusive` verdict** | CI straddles the threshold | Makes tiering safe — the fast suite may say "I don't know" |
| **`target_unhealthy`** | Majority of cases errored | Distinguishes an outage from a quality regression |
| **Judge cache** | Verdicts keyed on prompt, output, metric, and versions | ~50% saving on iterative PRs; **versions must be in the key** |
| **Regression gate** | CI blocking on a metric drop past a threshold | The platform's product; only trustworthy if the judge is stable |
| **Comparability** | Two runs sharing dataset, judge, and metric versions | A different judge means non-comparable, never a silent substitution |
| **Experiment tracking** | Config + metrics recorded per run | Turns evaluation into a trend rather than an event |
| **Online eval** | Scoring sampled production traffic | Catches what offline datasets miss |
| **Bypassed gate** | A gate teams disabled or ignore | **Worse than no gate** — leaves false confidence behind |

---

**Files:** [README](README.md) · [Requirements](01_requirements.md) · [HLD](02_hld.md) · [LLD](03_lld.md) · **Production & interview** (this file)
