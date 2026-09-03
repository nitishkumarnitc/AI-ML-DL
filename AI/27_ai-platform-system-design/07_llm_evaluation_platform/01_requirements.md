# 01 · Requirements — LLM Evaluation Platform

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#7-llm-evaluation-platform`](../00_requirements_all_systems.md#7-llm-evaluation-platform)

---

## 1.1 Problem & users

### What breaks today

Twenty product teams ship LLM features with no shared way to answer one question: **"is this change
better?"** Consequences, in the order they hurt:

1. **Prompt changes ship on vibes.** An engineer tweaks a prompt, tries four examples by hand, and merges.
   Regressions reach production and are discovered by users.
2. **Every team rebuilds the same harness.** Twenty half-finished eval scripts, twenty inconsistent metric
   implementations, no comparability across teams.
3. **Quality trends are invisible.** Nobody can say whether a feature got better or worse over a quarter,
   so quality investment can't be justified or defended.

### Users and jobs

| User | Job | What "working" means |
|---|---|---|
| **Engineer (primary)** | Know whether a prompt/model change is safe to merge | A verdict **inside a CI gate** — minutes, not hours |
| PM | Track quality over time | Trend dashboards per feature |
| Compliance reviewer | Evidence a launch was evaluated | Immutable run records tied to versions |
| Platform team | Operate it for 20 teams | Bounded cost, tenant isolation, no manual toil |

### The defining constraint

**This platform sits in the release path.** That makes two ordinarily-nonfunctional properties into
product requirements:

| Property | Why it's a product requirement |
|---|---|
| **CI-gate runtime** | Above ~10 minutes, teams stop waiting and disable the gate |
| **Judge determinism** | If identical inputs score differently, the gate fires on noise and teams learn to ignore it |

> **A bypassed gate is worse than no gate.** No gate is an honest absence of signal; a disabled gate leaves
> behind the *belief* that evaluation is happening. Both failure paths above end in the same place — a
> platform nobody trusts — which is why runtime and determinism outrank feature breadth.

> **Mental model:** the platform is a **unit-test runner for non-deterministic code.**
>
> *Where the analogy breaks:* a unit test is deterministic and free. Here, every assertion costs money and
> is *itself* produced by a probabilistic model — so the runner has to guarantee its own reproducibility
> before its results mean anything. That inversion is what makes judge stabilization
> ([FR-4](#judging--where-the-platforms-credibility-lives)) infrastructure rather than a feature.

---

## 1.2 Functional requirements

### Datasets

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | **Versioned, immutable** datasets with lineage | Every run pinned to a dataset version; a version can never be mutated |
| FR-12 | P2 | Synthesize new cases from production failures | Failed production traces promotable to test cases |

**Immutability is what makes historical comparison meaningful.** If a dataset can be edited in place, a
metric moving between two runs might mean the model changed or the *test* changed — and you can't tell
which. Versioning converts that ambiguity into a fact recorded on the run.

### Running evaluations

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-2** | P0 | Run a suite against a target app/prompt/model version | Target invoked via an adapter; versions recorded |
| **FR-3** | P0 | Built-in metrics: groundedness, answer relevance, correctness, contextual precision/recall | Match published reference implementations within tolerance |
| FR-5 | P0 | Custom metrics from a user-supplied criteria/rubric | Same stabilization as built-ins |
| FR-13 | P2 | Capture cost and latency alongside quality | Operational evals in the same run |

**Metrics must match reference implementations within tolerance**, because a "groundedness" score that
means something different here than in the published literature is a number teams can't reason about or
compare against anything external.

### Judging — where the platform's credibility lives

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-4** | P0 | **LLM-as-a-judge with G-Eval-style stabilization** | **Same input → score σ < 0.05 across reruns** |
| FR-8 | P1 | Human evaluation workflow with inter-rater agreement | Reports Cohen's κ; flags ambiguous rubrics |
| FR-10 | P1 | Judge calibration against human labels | MAE reported per metric |

**Two mechanisms deliver FR-4**, both from [`16_evals/15`](../../16_evals/15-mastering-g-eval-deterministic-judge.md):

1. **Chain-of-thought evaluation steps generated once and reused** — rather than letting the judge
   re-derive what "correctness" means on every call, which is the main source of drift.
2. **Probability-weighted scoring** over candidate score tokens, instead of taking the single sampled
   token — which converts a noisy integer pick into a stable decimal.

**Cohen's κ in FR-8 is doing real work.** Low inter-rater agreement among *humans* means the rubric is
ambiguous — and no judge can be more consistent than the definition it's given. Measuring κ tells you
whether to fix the judge or fix the rubric.

### Gating and tracking

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-6** | P0 | **Regression detection vs a pinned baseline** | Blocks CI on > threshold drop; threshold per metric |
| **FR-7** | P0 | Experiment tracking: config + metric history | Runs comparable across time and teams |
| FR-11 | P1 | CI integration with a pass/fail gate | GitHub Actions and equivalents |
| FR-9 | P1 | Online eval on sampled production traffic | Configurable sample rate |

---

## 1.3 Non-functional requirements

### Runtime — a product requirement

| NFR | Target | Why this number |
|---|---|---|
| **Suite runtime (200 cases)** | **p95 < 10 min** | **Must fit a CI gate.** Above this, teams disable it |
| Suite runtime (50-case smoke) | p95 < 3 min | The PR-path target after tiering ([§1.6](#16-capacity--cost-estimation)) |
| Parallelism | ≥ 32 concurrent judge calls | How the 10-minute target is met at all |
| Availability | 99.5% | Internal; a CI retry is acceptable |

**10 minutes is not a comfort target.** A 200-case suite with 3 metrics is 600 judge calls; serially at
~2 s each that's 20 minutes. Parallelism at 32 brings it to ~40 s of judge time plus target-app calls —
so the concurrency figure is what makes the runtime achievable, not an optimization on top of it.

### Judge quality

| NFR | Target | Why this number |
|---|---|---|
| **Determinism** | score **σ < 0.05** across reruns | Below the 3-point regression threshold by a wide margin, so the gate fires on signal not noise |
| **Judge–human agreement** | **MAE ≤ 1.0** on a 0–10 scale | Above this the judge isn't trustworthy as a gate — it's measuring something other than what humans mean |
| Inter-rater agreement (human) | κ ≥ 0.6 | Below this the *rubric* is the problem, not the judge |

**Determinism and agreement are independent, and both are required.** A judge can be perfectly
reproducible and consistently wrong (σ = 0, MAE = 4), or accurate on average and unusably noisy (MAE = 0.5,
σ = 2). The first passes gates it shouldn't; the second blocks deploys at random.

### Scale, cost, isolation

| NFR | Target | Why |
|---|---|---|
| Throughput | 500 suite runs/day across 20 teams | ~25 runs/team/day |
| Cost | ≤ $2.00 per 200-case run | Cheap enough to run on every PR — ⚠️ **unachievable as stated; see [§1.6](#16-capacity--cost-estimation)** |
| **Isolation** | Team A cannot read team B's datasets or runs | Multi-tenant; datasets often contain product-sensitive content |
| Retention | Runs + traces 1 year | Trend analysis and audit |

---

## 1.4 Non-goals

| Out of scope | Why | What would bring it in |
|---|---|---|
| **Runtime guardrails / blocking production requests** | This is an *offline* gate. Runtime blocking is a serving concern with millisecond budgets | Never here — see [10](../00_requirements_all_systems.md#10-enterprise-ai-agent-platform) |
| Training reward models | Different problem, different infrastructure | — |
| **Replacing human review for high-stakes launches** | The platform *gates*; it does not decide. A passing suite is evidence, not authorization | — |
| Evaluating non-LLM models | Classical ML metrics (AUC, calibration) belong with the model owners — see [06](../06_recommendation_system/04_production_and_interview.md#41-ml-specific-concerns) |
| Being a prompt IDE | Prompts live in the teams' repos; this evaluates them | — |
| Fully automated dataset curation | [FR-12](#datasets) suggests candidates; **humans approve** | Judge quality reaches human parity |

**"Gates but does not decide" is worth stating explicitly**, because the natural drift is toward treating a
green suite as a launch approval. A 200-case suite cannot cover the space of things that can go wrong with
a customer-facing LLM feature; it can only establish that known failure modes haven't regressed.

---

## 1.5 Runtime budget

Target: p95 < 10 min for a 200-case suite with 3 metrics.

| # | Stage | Budget (p95) | Notes |
|---|---|---:|---|
| 1 | Submit + validate + resolve dataset version | 5 s | |
| 2 | Queue wait | 20 s | Per-tenant fairness; absorbs bursts |
| 3 | **Target app invocation — 200 cases, 32 concurrent** | **150 s** | The team's app; **we don't control its latency** |
| 4 | **Judge calls — 600, 32 concurrent, ~50% cache hit** | **190 s** | ~300 uncached × ~2 s ÷ 32 ≈ 19 s of wall-clock per wave |
| 5 | Aggregate + regression check | 10 s | Deterministic |
| 6 | Persist run + traces | 15 s | Async where possible |
| | **Total** | **≈ 6 min 30 s** | vs 10 min SLO → **~3.5 min headroom** ✅ |

**Stage 3 is the risk, and it isn't ours.** The target app's latency is a property of the *team's* system —
a slow RAG pipeline with a 6-second p95 makes 200 cases take 37 s of wall-clock at 32 concurrency, but a
tenant whose app takes 30 s per call blows the budget entirely. Mitigation: **per-tenant concurrency limits
and a hard per-case timeout**, so one slow tenant can't monopolize the runner
([F5](02_hld.md#25-failure-modes--blast-radius)).

**The 50-case smoke suite lands at ≈ 2 min**, comfortably inside a PR flow.

---

## 1.6 Capacity & cost estimation

Rates per [`../00_requirements_all_systems.md#shared-conventions`](../00_requirements_all_systems.md#shared-conventions).

### The naive design

```
Suite: 200 cases × 3 metrics = 600 judge calls

Judge on frontier tier (quality matters for gating), 1,500 in / 200 out:
  (1500/1e6 × $3.00) + (200/1e6 × $15.00) = $0.0045 + $0.0030 = $0.0075/judge call
  600 × $0.0075                                                = $4.50

Plus the TARGET APP's own calls — the cost people forget:
  200 cases × $0.0114 (a RAG query, per 01)                    = $2.28
                                                                 ──────
Total per run                                                  ≈ $6.78     vs a $2.00 ceiling

500 runs/day × $6.78 ≈ $3,390/day ≈ $102,000/month              ⇒ UNTENABLE
```

**Counting the target app's calls is not optional.** An eval run *invokes the system under test*, so the
platform's bill includes 200 executions of the tenant's feature. Designs that budget only judge calls
understate cost by ~35% here.

### The three levers

| # | Lever | Mechanism | Effect | Cost/run |
|---|---|---|---|---:|
| 0 | *(naive)* | — | — | $6.78 |
| 1 | **Tiered judge models** | Small tier for cheap metrics (relevance, format); frontier only for correctness and groundedness | judge −60% | ≈ $4.00 |
| 2 | **Judge verdict cache** | Key on `(prompt_hash, output_hash, metric, judge_version)` — unchanged cases on iterative PRs are free | −~50% on PR reruns | ≈ $2.30 |
| 3 | **Tiered suites** | **50-case smoke on every PR; 200-case full nightly** | −75% of PR-path volume | **≈ $0.90 PR** |

### The resulting cost model

```
Per-tenant per day: assume 25 runs = 23 PR smoke runs + 2 full runs
  PR smoke:  23 × $0.90 = $20.70
  Full:       2 × $2.30 =  $4.60
                          ──────
  Per team/day          ≈ $25.30
  20 teams              ≈ $506/day  ≈  $15,200/month     ✅ ~85% below the naive figure
```

> **Tiering is a structural decision, not a micro-optimization**, and it's the answer to a requirement
> conflict rather than a cost tweak. "Fast and cheap enough to run on every PR" and "thorough enough to
> trust before release" are different requirements that were being forced onto one artifact. Separating
> them satisfies both — and it's also what makes the runtime budget
> ([§1.5](#15-runtime-budget)) comfortable rather than marginal.
>
> **The trade-off to state honestly:** a smoke suite can miss a regression that the full suite would catch,
> so a bad change can merge and be caught up to 24 hours later by the nightly run. That's acceptable for
> internal features with fast rollback; it would not be for anything shipping directly to customers
> without a canary.

### Judge cache economics

```
Cache key: (prompt_hash, output_hash, metric_name, judge_version)

Why the hit rate is high on PRs: an engineer iterating on ONE prompt changes
the output for a subset of cases; the rest produce byte-identical outputs and
their verdicts are already known.

Assume 50% hit rate on iterative reruns (assumption A2):
  600 judge calls → ~300 actual  ⇒ ~50% judge cost AND ~50% judge latency

⚠️ Any change to judge_version or the metric definition invalidates the whole
   cache — correctly. A stale verdict from an older judge would silently
   corrupt the comparison.
```

### Storage

```
Runs:   500/day × 365 = 182,500 runs/year — trivial
Traces: 500 runs × 200 cases × ~8 KB = 800 MB/day ≈ 292 GB/year
  ⇒ ~$7/month. Keep full traces; they're the debugging value.
```

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | **Log-probabilities available from the judge provider** | Medium | **Determinism (σ < 0.05) is unachievable** without them — probability-weighted scoring needs token logprobs. Would force a different judge provider or an accepted higher variance, which weakens every gate |
| **A2** | ~50% judge-cache hit rate on iterative PRs | Medium | Cost rises toward $4/run; tiering still holds the line |
| **A3** | **Teams will adopt a shared platform** | **Low** | **The multi-tenant complexity is wasted.** Validate with 2–3 teams before building for 20 |
| A4 | Target apps respond < 6 s p95 | Low | Runtime budget breaks for slow tenants; per-tenant limits contain it |
| A5 | 3 metrics per case average | Medium | Cost and runtime scale linearly |
| A6 | 500 runs/day across 20 teams | Low | Linear; burst behaviour matters more than average |

**A1 is the technical dependency that could force a redesign**, and A3 is the organizational one that could
make the whole thing unnecessary. Both are cheap to check early and expensive to discover late.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | **Who owns golden-dataset quality?** | **Datasets rot** — they drift from what the product does, and stale cases produce meaningless gates. Unowned datasets are the most common way eval platforms decay | Per-team, needs naming |
| **Q2** | Is a judge permitted to see production data (PII)? | May force a self-hosted judge, changing cost and the log-prob dependency ([A1](#assumptions)) | Legal / Security |
| **Q3** | Who sets regression thresholds — platform or teams? | Platform default with per-team override is likely right, but it needs deciding before teams tune them to always pass | Platform + teams |
| Q4 | Should a failed gate block merge or warn? | Blocking builds trust in the signal but creates pressure to disable it | Engineering leadership |
| Q5 | Is a shared metric library mandatory or advisory? | Mandatory gives comparability across teams; advisory gives adoption | Platform |

**Q1 is the sleeper that kills eval platforms.** The infrastructure keeps working perfectly while the
datasets slowly stop representing the product — so gates keep passing, teams keep trusting them, and
quality drifts unmeasured. **Dataset ownership is a staffing question disguised as a technical one**, and
worth raising before launch rather than a year in.

---

**Next:** [02_hld.md →](02_hld.md) — architecture, judge stabilization, dataset versioning, caching, regression detection, failure modes, and the scale plan.
