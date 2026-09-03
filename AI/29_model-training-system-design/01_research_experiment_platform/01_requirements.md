# 01 — Requirements: Research Experiment Platform

> ← [00_concepts.md](00_concepts.md) · [system README](README.md) · → [02_hld.md](02_hld.md)
> · [shared assumptions register](../00_requirements_all_systems.md)

**Three-sentence compression:** The platform's product is not dashboards — it is **readable
conclusions**, and the binding constraint is statistical power, not GPU throughput. The choice that
matters most is **enforced pairing plus mandatory pre-registration**, because pairing turns a
126-run ablation into a 26-run ablation and pre-registration is the only thing that stops a 20-arm
sweep from manufacturing a winner 64% of the time. The failure I would volunteer unprompted: **the
platform can be perfectly correct and still be bypassed** — if the pre-registration flow costs a
researcher more than about two minutes, they will run `python train.py` directly and the whole
guarantee evaporates.

---

## 1.1 Problem statement and users

**What breaks today.** A lab runs ablations with `n=3` seeds, eyeballs the loss curves, and picks a
winner. From [`00_concepts.md §3.3`](00_concepts.md), three seeds can only detect an effect of
**0.046 nats**; real architectural effects are **0.005–0.02 nats**. So the standard protocol is
measuring seed noise and reporting it as a result. Worse, results are not *joinable* — a metric series
in one tool, a config in a YAML file, code in an uncommitted working tree — so a surprising number
cannot be traced back to what produced it, and a regression cannot be bisected.

The consequence is not a wasted $12k of ablation compute. It is a **wrong architectural decision
carried into a $1.11M flagship run** (see [`00_requirements_all_systems.md §E`](../00_requirements_all_systems.md)).

**Primary user:** a research scientist ([role 01](../../00_jobs/01_ai-research-scientist/README.md))
who has a hypothesis and wants a defensible yes/no by end of day.

**Primary job:** *turn a fuzzy research question into a measurable hypothesis, a set of runs, and a
verdict that survives being challenged in a design review.*

**"Working" means:** every conclusion in the lab's research log names its effect size, its confidence
interval, its power, and the exact `(config_hash, code_sha, image_digest, data_manifest_hash, seed)`
that produced each data point — and a colleague can reproduce any of it with one command.

**Secondary users:** the research lead (needs a portfolio view: which ablations are underpowered, what
is queued, what the cluster is being spent on) and the systems team (needs to know which runs are
authorized so [design 03](../03_distributed_training_platform/README.md) can schedule them).

---

## 1.2 Functional requirements

Prioritized P0/P1/P2. Each has an acceptance criterion, because "the system should support
experiments" is untestable.

### P0 — the platform is not viable without these

| ID | Requirement | Acceptance criterion |
|---|---|---|
| **FR-1** | A researcher **pre-registers** an ablation: hypothesis, metric, arms, effect size δ, and a fixed horizon, *before* any run starts | Creating a run against an ablation with no pre-registration record is rejected with `409`. Pre-registration is immutable once the first run starts; edits create a new version and mark the old one superseded |
| **FR-2** | The platform **computes required `n`** from `(σ, δ, ρ, design)` and refuses to accept an under-powered plan without an explicit, recorded override | Submitting `n=3` for δ=0.01 at σ=0.02 returns the required `n=63` (unpaired) / `13` (paired, ρ=0.8) and requires `power_override_reason` to proceed. The override is shown on every result view |
| **FR-3** | The platform **measures σ and ρ** from run history per `(model_family, scale, metric)` and uses the measured values in FR-2, not defaults | A `σ`/`ρ` estimate older than 90 days or based on fewer than 8 runs is flagged `stale` and the power calc surfaces its own confidence interval |
| **FR-4** | The platform **constructs paired arms** — identical seed tuple, data order and eval batches across arms, differing only in the ablated key | For a paired ablation, the diff between any two arms' resolved configs contains exactly the pre-registered ablated keys, verified programmatically. A diff containing anything else is rejected |
| **FR-5** | Every run records full provenance: config hash, code SHA + dirty flag, container image **digest**, data manifest hash, seed tuple | All five columns `NOT NULL`. A run launched from a dirty working tree is accepted but permanently marked `provenance=dirty` and excluded from verdicts by default |
| **FR-6** | Metric time series stream in during the run and are queryable while it runs | Metric visible in the API < 10 s after emission (p95) |
| **FR-7** | A **verdict engine** returns effect size, CI, p-value, achieved power, and one of `supported` / `not_supported` / `inconclusive` — with multiple-comparison correction across the ablation's arms | The verdict names the test used (paired/unpaired), the correction applied (BH at q=0.05), and `inconclusive` is returned when achieved power < 0.80 — **never** `not_supported` |
| **FR-8** | **Duplicate-run detection**: launching a config hash that already has a completed run on the same code+image+data returns the existing result | Second identical submission returns `200` with the prior `run_id` and does **not** consume GPU-hours, unless `force_rerun=true` |

### P1 — the platform is materially weaker without these

| ID | Requirement | Acceptance criterion |
|---|---|---|
| **FR-9** | **Scaling-law ladder as a first-class object**: declare a ladder, get fitted `L(N,D)` coefficients with CIs and an extrapolation to a target `N` | Ladder fit returns `E, A, α, B, β` with bootstrap CIs and a warning when the target `N` is more than 1.5 orders of magnitude beyond the largest rung |
| **FR-10** | **Two-tier ablation policy**: a cheap screening tier (δ=0.02) that gates entry to a confirmation tier (δ=0.01) | Screening at δ=0.02 requires 4 pairs; promotion to confirmation requires a screening result with p < 0.10. Promotion is one API call, and reuses nothing from the screen (fresh seeds — §1.7 A4) |
| **FR-11** | **Sequential-analysis guard**: if a researcher queries a verdict before the pre-registered horizon, the response uses an alpha-spending boundary, not the naive threshold | Interim verdict includes `boundary=obrien_fleming`, `looks_used=k`, and the adjusted threshold. Naive early stopping is not reachable through the API |
| **FR-12** | **Run lineage**: any run can be re-executed bit-exactly from its provenance tuple with one command | `replay <run_id>` reproduces final loss to within deterministic-kernel tolerance (0 if `deterministic=true` was set, else within the recorded numeric-jitter band) |
| **FR-13** | Cost attribution: GPU-hours per ablation, per researcher, per day | Available within 1 h; an ablation exceeding its declared budget by 20% alerts its owner |

### P2 — nice, and deliberately deferred

| ID | Requirement |
|---|---|
| **FR-14** | Automatic hypothesis suggestion from prior results (an LLM over the research log) |
| **FR-15** | Interactive notebook attach to a live run |
| **FR-16** | Cross-lab result sharing / external publication export |

---

## 1.3 Non-functional requirements

Shared cluster, pricing and reproducibility NFRs are in
[`00_requirements_all_systems.md §A, §D`](../00_requirements_all_systems.md) and are **not repeated
here**. These are the ones specific to this system.

| NFR | Target | Why this number |
|---|---|---|
| **Turnaround: hypothesis → verdict** | **p95 < 2.5 h** | The platform's real product is iteration rate. Same-day turnaround supports ~5 hypotheses/researcher/week; a 2-day loop supports ~2. The 2.5 h figure is derived, not chosen — see §1.5 |
| Pre-registration cost to the researcher | **< 2 min**, ≤ 6 required fields | This is the **adoption constraint and the top risk.** Above ~2 min, researchers bypass the platform and every guarantee above becomes optional |
| Metric ingest freshness | p95 < 10 s from emit to queryable | A researcher watching a live run needs to kill a diverging job quickly; > 30 s and they open a terminal instead |
| Metric ingest throughput | 1,200 points/s sustained, **6,000 points/s peak** | 200 concurrent runs × 60 metrics / 10 s emit interval; peak = 5× from synchronized wave starts (§1.6) |
| Verdict computation | < 5 s for ≤ 64 arms × ≤ 256 runs | It is called interactively; anything slower gets cached-and-stale, which is worse than slow |
| **Verdict calibration** | **FDR ≤ 0.05** across all `supported` verdicts in a quarter, audited retrospectively | The one correctness metric that matters. If 20% of "supported" verdicts fail confirmation, the platform is actively harmful — it is laundering noise as rigor |
| Query latency (compare N runs) | p95 < 800 ms for 64 runs × 20k steps × 4 metrics | Interactive comparison UI |
| Durability of results | 11 nines for run records and verdicts; metrics recoverable | A lost verdict is a lost decision audit trail |
| Availability (control plane) | 99.5% | **A control-plane outage must not kill in-flight runs** — the agent buffers metrics locally and replays. See [02_hld §2.5](02_hld.md) |
| Retention | Run records + verdicts **forever**; full metric series 2 years then downsample to 1/100; artifacts per policy (§1.6) | Run records are the lab's research memory and are tiny. Metrics and checkpoints are not |
| **Cost ceiling** | ≤ **$60k/quarter** all-in (platform infra + the GPU-hours it authorizes) | Set against the ~$1.11M flagship run this de-risks: ≤5.4% insurance premium. Arithmetic in §1.6 |
| Scale | 5,000 runs/quarter · 200 concurrent · 6×10⁹ metric points/quarter · 500 ablations/quarter | Assumed lab of ~25 researchers |

---

## 1.4 Explicit non-goals

| Not building | Why |
|---|---|
| **The training loop / trainer itself** | Owned by [design 03](../03_distributed_training_platform/README.md). This platform *authorizes and records*; it does not execute. Conflating them is how experiment trackers become unmaintainable training frameworks |
| **The GPU scheduler** | Also design 03. This platform submits an authorized job spec and gets back a handle |
| **Post-training algorithms** (SFT/DPO/RLVR) | Owned by [design 02](../02_post_training_pipeline/README.md). This platform is *metric-agnostic* — it works on any scalar with a measurable σ, including a win-rate |
| **Model serving / inference** | Covered in [`27/04`](../../27_ai-platform-system-design/04_llm_inference_platform/README.md) |
| **A general-purpose BI tool** | Deliberately narrow: pre-register → run → verdict. Adding arbitrary dashboarding is what turns a rigor tool into a place where rigor is optional |
| **Automated hypothesis generation** (FR-14) | v2. The bottleneck today is *reading results correctly*, not producing more hypotheses |
| **Human-subject / preference-annotation workflows** | Different problem (inter-annotator agreement, not seed variance) |

---

## 1.5 Turnaround budget

This is not a serving system, so there is no request-latency SLO. The equivalent discipline is a
**turnaround budget** — and it must sum to the SLO the same way.

| Stage | Budget (p95) | Notes |
|---|---|---|
| Pre-register + power calc (interactive) | **2 min** | Human time. The adoption constraint, not a compute cost |
| Config resolution, validation, pair-diff check, dedup lookup | 10 s | Pure control-plane work; §3.3 algorithm |
| Queue admission for 26 runs | **30 min** | Assumption: shared cluster at 70% utilization, ablation-priority class. The largest single term and the one *not* owned by this platform |
| Run execution — 26 runs × 3.37 GPU-hr, 8 GPUs each, 13 concurrent slots (104 GPUs) | **50.6 min** | 2 waves × 25.3 min. A 200M model on 4B tokens; see §1.6 |
| Metric flush + ingest lag on final point | 10 s | |
| Verdict computation (paired t-test + BH + power) | 5 s | |
| **Total hypothesis → verdict** | **≈ 83 min (1.4 h)** | **SLO 2.5 h ✅ — 67 min headroom** |

**Where the headroom goes, honestly:** queue wait is the volatile term. At 95% cluster utilization it
can reach 2 h on its own and the SLO breaks. The budget therefore carries a **reserved ablation
partition** (§[02_hld 2.2](02_hld.md)) rather than pretending queueing is free — that reservation is a
real cost paid to protect a real SLO.

**A second budget, for the screening tier:** 4 pairs = 8 runs, one wave → 2 min + 25.3 min + 30 min
queue ≈ **58 min**. Screening is designed to fit inside a coffee break, because that is what makes
researchers use it instead of skipping to a full run.

---

## 1.6 Capacity and cost estimation

### 1.6.1 The unit run

```
Assume (A1): ablation-scale model 200M params, 4B tokens  [Chinchilla-optimal 20×N]
C = 6ND = 6 × 0.2e9 × 4e9 = 4.80e18 FLOPs
On 8 × H100 at 40% MFU: 8 × 989e12 × 0.40 = 3.166e15 FLOP/s
  T = 4.80e18 / 3.166e15 = 1,516 s = 25.3 min
  ⇒ 8 GPUs × 0.42 h = 3.37 GPU-hr = $10.11 per run   (at $3.00/GPU-hr, assumption A1)
```

### 1.6.2 The cost of rigor — and why it forces a two-tier design

```
Lab volume assumption: 200 substantive ablations per quarter.

(a) Status quo, underpowered:   200 × 2 arms × 3 seeds = 1,200 runs
    1,200 × 3.37 = 4,044 GPU-hr = $12,133/quarter
    → and from §00_concepts §3.3, δ_min = 0.046 nats. Most of this buys nothing.

(b) Naive fix — confirm everything at δ=0.01 (13 pairs = 26 runs):
    200 × 26 = 5,200 runs = 17,524 GPU-hr = $52,572/quarter
    + platform infra ~$7,500/quarter  ⇒  $60,072  ← EXCEEDS the $60k ceiling

(c) Two-tier (FR-10) — screen at δ=0.02, confirm only what passes:
    δ=0.02 paired, ρ=0.8:  n = 7.85 × (0.01265/0.02)² = 3.14 → 4 pairs = 8 runs
    Screen:   200 ablations × 8 runs  = 1,600 runs
    Promote:  assume 25% pass         =  50 ablations
    Confirm:   50 ablations × 26 runs = 1,300 runs
    Total 2,900 runs × 3.37 = 9,773 GPU-hr = $29,319/quarter
    + platform infra $7,500            ⇒  $36,819/quarter   ✅ 39% under ceiling
```

> **The structural finding:** full power on every ablation does not fit the budget, and the fix is not
> a micro-optimization — it is **tiering the effect size you are willing to detect**, exactly as
> [`27/07`](../../27_ai-platform-system-design/07_llm_evaluation_platform/README.md) tiers eval suites
> to fit a CI gate. Tier 1 answers "is there plausibly anything here?" for $81/ablation; tier 2 answers
> "is it real?" for $263, and only 25% of ablations earn it.

**Note what (c) also proves:** the *platform's own infrastructure* is $7.5k of a $36.8k bill — **20%.**
Any argument about this platform is an argument about how many runs it authorizes, not about its
servers. Optimizing the control plane is the wrong conversation.

### 1.6.3 The scaling-law ladder

```
Ladder N ∈ {20M, 40M, 80M, 160M, 320M, 640M, 1.3B}, each Chinchilla-optimal (C = 120N²)
Σ C = 2.68e20 FLOPs  — 76% of it is the top rung alone (N² dominates)
On 64 × H100 @ 40% MFU: 2.9 h wall-clock = 188 GPU-hr = $565
× 6 (3 seeds × 2 learning rates per rung) = $3,391

vs. the $1.11M flagship it extrapolates to:  0.31%
```

**This is the cheapest insurance in the lab** and it is the number to lead with when someone asks why
the platform needs a ladder abstraction rather than ad-hoc scripts.

### 1.6.4 Storage and ingest sizing

```
Metric points:  5,000 runs × 20,000 steps × 60 metrics = 6.0e9 points/quarter
  Columnar TSDB with delta-of-delta + gorilla-style float compression ≈ 3 bytes/point
  ⇒ 18 GB/quarter, 72 GB/year  → trivial. This is NOT a big-data problem.

Ingest:  200 concurrent runs × 60 metrics / 10 s = 1,200 points/s sustained
         peak 5× (synchronized wave starts of a 26-run ablation) = 6,000 points/s
  ⇒ a single Postgres/Timescale node handles this. Kafka is not required at this scale.

Artifacts (checkpoints from ablation runs):
  5,000 runs × 200M params × 16 bytes = 16.0 TB/quarter
  Retention: final checkpoint only, and only for runs referenced by a verdict (~20%)
  ⇒ 3.2 TB/quarter live = $74/month.  Keep-everything would be $368/month — still
    cheap, so the retention policy here is about findability, not cost.
```

> **Called out deliberately:** at this scale the metric store is *small*. A design that reaches for
> Kafka + Spark + a data lake for 6,000 points/s has mistaken the domain for the tooling. The hard
> part of this system is the **join key and the statistics**, not the volume — and saying so is a
> stronger answer than over-building.

---

## 1.7 Assumptions and open questions

| # | Assumption | If wrong, what changes |
|---|---|---|
| **A1** | **σ = 0.02 nats** for final val loss at 200M scale | Everything. `n` scales as σ². At σ=0.04, the δ=0.01 paired design needs 51 pairs, not 13, and the two-tier budget in §1.6.2 breaks. **This is measurable in one afternoon (8 identical runs = 27 GPU-hr = $81) and FR-3 makes measuring it a P0 requirement rather than an assumption.** |
| **A2** | **ρ = 0.8** paired correlation | At ρ=0.5 pairing buys 2× not 4.8×; confirmation needs 32 pairs and (c) costs $52k. Also measurable from history — and if ρ < 0.5 for a given ablation type, pairing should be *refused* for it, not silently applied |
| **A3** | 25% of screened ablations promote to confirmation | If 60% promote, (c) costs $61k and exceeds the ceiling. Mitigation: promotion threshold `p < 0.10` is a **tunable budget knob**, and §1.6.2 should be re-run quarterly against actual promotion rate |
| **A4** | Screening and confirmation use **independent seeds** | If confirmation reuses the screening runs, the confirmation is conditioned on the screen and its p-value is invalid (this is selection bias, and it is subtle enough that FR-10's acceptance criterion states it explicitly) |
| A5 | 200M / 4B tokens is a representative ablation scale | Larger ablation scale raises cost linearly and *lowers* σ (bigger models are less seed-sensitive), which partly self-corrects. The scale at which an ablation is *informative* is itself a research question — see Q2 |
| A6 | Shared cluster at 70% utilization, ablation priority class available | The 30-min queue term in §1.5 is the SLO's weakest link and it is owned by design 03, not this platform |
| A7 | Final validation loss is the metric | For a win-rate or pass-rate metric, σ is binomial and the power formula changes (§[03_lld 3.3](03_lld.md) handles both) |

### Open questions

1. **Does the lab have σ and ρ measured today?** Almost certainly not. The platform's first
   deliverable should be a **variance census** — 8 identical runs per (family, scale) — before any
   power calculation is trusted. Cost: ~$81 per cell. This is the single highest-leverage $500 in the
   whole design.
2. **At what scale does an ablation stop transferring?** The platform can *record* that a result held
   or failed to hold at the next rung (FR-9), which over a year produces the lab's own transfer prior.
   Nobody can answer it up front, and pretending otherwise would be the wrong kind of confidence.
3. **What is the enforcement boundary?** If researchers can submit jobs to the cluster directly,
   pre-registration is advisory and FDR is unenforceable. This is an **organizational** decision that
   determines whether the technical design matters at all — see [02_hld §2.2](02_hld.md), where it is
   the first row of the component table.
4. **Who is allowed to override a power check (FR-2)?** If everyone can, nobody does the work. If only
   the lead can, the lead becomes a bottleneck. Proposed: self-serve override with the reason recorded
   and surfaced on every result — social cost, not a gate.

---

← [00_concepts.md](00_concepts.md) · [system README](README.md) · → [02_hld.md](02_hld.md)
