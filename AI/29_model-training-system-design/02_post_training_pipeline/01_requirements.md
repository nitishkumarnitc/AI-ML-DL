# 01 — Requirements: Post-Training Pipeline

> ← [00_concepts.md](00_concepts.md) · [system README](README.md) · → [02_hld.md](02_hld.md)
> · [shared assumptions register](../00_requirements_all_systems.md)

**Three-sentence compression:** The system's shape is set by **generation, not gradients** — the
rollout phase is 29% of a GRPO step, wants the opposite memory layout from training, and forces two
engines over one set of weights. The choice that matters most is **in-memory weight broadcast between
trainer and generator**, because the obvious alternative (checkpoint to object store, reload the
inference engine) costs ~56 s against an ~89 s step — a 63% tax. The failure I would volunteer:
**reward hacking is invisible at the sample sizes people actually hold out** — 100 held-out prompts can
only detect a 14-point divergence, and hacking announces itself at 2–5 points.

---

## 1.1 Problem statement and users

**What breaks today.** A research engineer wants to run SFT → DPO → RLVR on an open base model and see
whether behaviour moved in the intended direction. In practice: the SFT corpus was never checked
against the eval suites, so every subsequent number is unfalsifiable; the DPO loss collapsed to 0.03 in
40 steps and nobody noticed the remaining 460 steps did nothing; the RLVR pass rate climbed beautifully
because the model learned to make the unit tests pass without solving the problem. **All three failures
look like progress on a dashboard.**

The systems half is just as broken: the first implementation writes a checkpoint after every update and
restarts the inference engine, so 63% of the GPU budget goes to weight movement, and the sandboxed
verifier fleet leaves every GPU idle for 18% of every step.

**Primary user:** a research engineer
([role 02](../../00_jobs/02_research-engineer-model-training/README.md)) running ~20 post-training
experiments a week on an 8B policy, promoting a few to 70B.

**Primary job:** *take a base model and a behavioural target, and produce a checkpoint plus honest
evidence that the target was met and not gamed.*

**"Working" means:** every experiment ends with a signed report containing the eval delta on a
**held-out** suite, the length-normalized win rate, the KL to reference, the train-vs-held-out verifier
gap, and an explicit reward-hacking verdict — and the checkpoint cannot be promoted without it.

**Secondary users:** the research scientist who wants the experiment's *verdict* to be statistically
readable (that is [design 01](../01_research_experiment_platform/README.md)'s job, and this system
emits its metrics in a form design 01 can consume), and the systems team who owns the cluster
([design 03](../03_distributed_training_platform/README.md)).

---

## 1.2 Functional requirements

### P0 — the pipeline is not trustworthy without these

| ID | Requirement | Acceptance criterion |
|---|---|---|
| **FR-1** | **Data curation**: ingest a corpus, near-dedup it, decontaminate against **all** registered eval suites, and emit an immutable versioned manifest | A manifest is `usable=false` until decontamination has run against every registered suite. Dedup at Jaccard ≥ 0.8 (MinHash, 128 perms, b=16/r=8). Report lists removed counts and reasons |
| **FR-2** | **SFT stage** with loss masked to response tokens only | Unit test asserts prompt-token loss contribution is exactly 0. A run whose prompt mask is absent fails at startup, not silently |
| **FR-3** | **Preference stage (DPO)** with the reference model frozen and the implicit-reward margin logged per step | Logs `dpo_loss`, `implicit_reward_margin`, `reward_accuracy`, `mean_chosen_len`, `mean_rejected_len` every step |
| **FR-4** | **DPO collapse detection**: abort when the loss saturates before the run is meaningfully done | Run halts with `dpo_collapse` if **EMA(`dpo_loss`) < 0.10** (i.e. `β·Δ > 2.2`) or **`reward_accuracy > 0.99` measured over a rolling window of ≥256 pairs** before 20% of planned steps. Both are windowed deliberately: a batch-of-8 loss is noisy, and raw 8/8 accuracy occurs ~27% of the time at 85% true accuracy, so an un-windowed check aborts healthy runs. Halting is the default; continuing requires an explicit flag |
| **FR-5** | **RLVR stage (GRPO)** with group size `k`, verifier-based rewards, and per-step KL to reference | Logs per step: reward mean/std, `frac_zero_std_groups`, KL, mean rollout length, verifier timeout rate |
| **FR-6** | **Verifier sandbox**: execute model-generated code with **no network**, a read-only filesystem except a scratch dir, a CPU/memory/wall-clock cap, and no host credentials | An escape-attempt test suite (network call, write outside scratch, fork bomb, read `/proc/self/environ`, mount) fails closed. This is arbitrary code execution **by design** — see [§4.1](04_production_and_interview.md) |
| **FR-7** | **Held-out verifier**: ≥ 1,500 prompts scored by an **independently implemented** verifier, never used for training | Report includes `train_pass_rate`, `heldout_pass_rate`, `gap`, and the gap's 95% CI (2 SE = 3.7 points at n=1,500). The gap is computed over a **rolling window of 8 steps** so the training side is not the noisier half (§1.7 A8). The two verifier implementations must not share a module (enforced by import-graph check in CI) |
| **FR-8** | **Reward-hacking verdict** combining verifier gap, length drift, KL, and refusal rate | Every experiment report ends in `clean` / `suspected` / `confirmed`, with the triggering signal named. `suspected` blocks promotion; it does not block the experiment |
| **FR-9** | **In-memory weight sync** from trainer to generation engine each step | Weight sync p95 < 2 s for an 8B policy. A checkpoint-round-trip fallback exists but emits a loud warning with its measured cost |
| **FR-10** | **Length-normalized win rate** reported alongside the raw win rate | Both reported always. A win-rate improvement that disappears under length normalization is flagged `length_confounded` |

### P1 — materially better with these

| ID | Requirement | Acceptance criterion |
|---|---|---|
| **FR-11** | **Pipelined verify**: overlap batch *t*'s verification with batch *t+1*'s generation, with bounded staleness | GPU-idle time during verify < 3% of step (from 18%). `max_staleness` is a declared config value, and every rollout records the weight version that produced it |
| **FR-12** | **Zero-gradient cold-start guard** | If `frac_zero_std_groups > 0.9` for 10 consecutive steps, halt with `cold_start_no_signal` and suggest an easier prompt mix or an SFT warm-up |
| **FR-13** | **Checkpoint promotion gate**: a checkpoint is promotable only with a passing eval report and a `clean` hacking verdict | Promotion API returns `409` with the failing gate named. No manual override without a recorded reason |
| **FR-14** | **70B tier** with the same interface as 8B | Same API; parallelism plan delegated to [design 03](../03_distributed_training_platform/README.md) |
| **FR-15** | **Experiment lineage**: every checkpoint names its base, its data manifests, and every stage config | `lineage <ckpt>` prints the full chain to the base model |

### P2 — deliberately deferred

| ID | Requirement |
|---|---|
| **FR-16** | Learned reward model training (RLHF proper). RLVR first: a program is harder to fool than a network |
| **FR-17** | Human preference annotation workflows (different problem: inter-annotator agreement) |
| **FR-18** | Multi-objective reward blending / Pareto-front search |
| **FR-19** | Online/continual post-training from production traffic |

---

## 1.3 Non-functional requirements

Cluster, price and reproducibility NFRs live in
[`00_requirements_all_systems.md §A, §D`](../00_requirements_all_systems.md).

| NFR | Target | Why this number |
|---|---|---|
| **8B experiment wall-clock** | **< 14 h** (500 GRPO steps) | An experiment started at end of day must have a verdict by morning, or the iteration rate halves |
| GRPO step time (8B, 256 prompts × k=8) | **p95 < 100 s** | Derived, not chosen — §1.5 budgets to 89.5 s |
| **Weight-sync latency** | **p95 < 2 s** | Anything larger is a visible fraction of an 89 s step. The measured in-memory figure is 0.04–0.32 s, so this is a 6× safety margin |
| GPU idle per step | **< 3%** (P1); ≤ 18% accepted in v1 | The serialized verify phase is 16 s of every 89 s step with all GPUs idle |
| Generation throughput (8B) | ≥ 8,000 output tok/s/GPU at batch ≥ 256 | Assumption A6 in the shared register — **15% of the 53,600 tok/s weight-bound roofline**, flagged as the largest known efficiency gap |
| Max concurrent rollouts | **≥ 2,048** on one 8×H100 node | Sizing driver for the whole memory budget (§1.6.2), and the constraint that decides GRPO-vs-PPO |
| **Reward-hack detectability** | **gap ≥ 3.7 points detectable** at n=1,500 held-out; ≥ 1,500 is the floor | 2 SE at n=1,500 is 3.7 points (§00_concepts 6). Resolving exactly 3.0 points needs n≈2,223. Below 1,500 the detector is decorative — at n=100 it can only see 14.1 points. **And see §1.7 A8: past ~1,500 the *training* side dominates the SE, so the gap must be computed over a rolling window of steps** |
| Verifier sandbox | Zero network egress · ≤ 2 s CPU · ≤ 512 MB · read-only FS except scratch · no host creds | Model-generated code is untrusted input. The sandbox is the security boundary of the entire system |
| Verifier throughput | 256 concurrent sandboxes, ≥ 128 completions/s | 2,048 rollouts must verify in ≤ 16 s |
| Data freshness | New corpus → decontaminated manifest < 2 h for 600M tokens | Decontamination is ~10 CPU-min; the rest is ingest and dedup |
| Decontamination coverage | **100% of registered eval suites, no sampling** | Partial coverage gives false confidence. Cost is ~10 CPU-minutes (§1.6.4) — there is no argument for sampling |
| **Cost ceiling** | ≤ **$60k/month** | Business ceiling. §1.6.3 lands at $52.7k |
| Reproducibility | Bit-exact SFT/DPO replay; RLVR replay to within recorded rollout seeds | RLVR involves sampling; exact replay requires storing the rollout RNG state, which the design does |
| Retention | Rollouts sampled at 5% + **all** rollouts from flagged steps; all reports and manifests forever | 2.36M tokens/step × 500 steps is ~1.2B tokens/experiment — cannot keep it all, but must keep the evidence |
| Scale | 20 × 8B experiments/week · 10 × 70B/month · 2,900 GPU-hr/week | Assumed team of ~8 research engineers |

---

## 1.4 Explicit non-goals

| Not building | Why |
|---|---|
| **Pre-training a base model from scratch** | [Design 03](../03_distributed_training_platform/README.md). This pipeline consumes a base checkpoint |
| **The GPU scheduler and parallelism plan** | Also design 03. This pipeline declares a topology requirement and gets placement |
| **Statistical verdicts across experiments** | [Design 01](../01_research_experiment_platform/README.md). This pipeline *emits* metrics with the seed/provenance metadata design 01 needs; it does not compute p-values |
| **Learned reward-model training** (FR-16) | v2, deliberately. RLVR's verifier is a program — a much narrower attack surface than a neural reward model, and the right thing to build first |
| **Human annotation tooling** | Different problem entirely |
| **Serving the resulting model** | [`27/04`](../../27_ai-platform-system-design/04_llm_inference_platform/README.md) |
| **Authoring the RL environments/tasks themselves** | [`AI/10_rl-environments-and-infra`](../../10_rl-environments-and-infra/README.md). This pipeline *runs against* environments; it does not design them |
| **Multi-modal post-training** | Text only in v1 |

---

## 1.5 Step budget

The latency analogue for this system. A GRPO step must sum to the p95 target, and the interesting part
is **which stages can overlap**.

**Assumptions:** 8B policy, 8×H100, 256 prompts/step, `k`=8 → 2,048 rollouts, 512-token prompts,
640-token mean response (A6: 8,000 decode tok/s/GPU; 40% MFU on training compute).

| Stage | Budget (p95) | Share | GPU busy? | Overlappable? |
|---|---|---|---|---|
| Weight sync (in-memory broadcast, 16 GB) | **0.3 s** | 0.3% | briefly | no — a barrier by definition |
| Generation: prefill (1.05M tokens) | 5.3 s | 5.9% | **yes** (compute-bound) | with nothing |
| Generation: decode (1.31M tokens) | **20.5 s** | 22.9% | **yes** (bandwidth-bound) | with the *previous* batch's verify (FR-11) |
| Verify: 2,048 sandboxed test runs, 256 parallel | **16.0 s** | 17.9% | **NO — all GPUs idle** | with the *next* batch's generation (FR-11) |
| Reference logprobs (forward only, 2.36M tokens) | 11.9 s | 13.3% | yes | fusable into the training forward |
| Policy update (fwd+bwd, 2.36M tokens) | **35.8 s** | 40.0% | yes | with nothing |
| **Total, serialized** | **≈ 89.8 s** | | | **p95 SLO 100 s ✅ 10 s headroom** |
| *Total with FR-11 pipelining* | *≈ 73.8 s* | | | *GPU idle 18% → <3%* |

**Two things this budget makes visible that a single number would hide:**

1. **The policy update is only 40% of the step.** A design that optimizes the training loop and ignores generation is optimizing the minority of the cost. Generation + verify is 47%.
2. **16 seconds of every step has zero GPU work**, because verification is CPU-bound sandboxed execution. Recovering it requires accepting **one-step-off-policy rollouts** — a genuine algorithmic concession (staleness) traded for a systems win. That trade, made explicitly and bounded by a declared `max_staleness`, is the design decision this budget exists to surface.

**Full-experiment wall clock:** 500 steps × 89.8 s = **12.5 h** (SLO < 14 h ✅). With pipelining: 10.3 h.

---

## 1.6 Capacity and cost estimation

### 1.6.1 Tokens per step

```
256 prompts × k=8 = 2,048 rollouts
Prefill:  2,048 × 512 =  1.05 M tokens
Decode:   2,048 × 640 =  1.31 M tokens
Total context touched: 2.36 M tokens/step

Per experiment (500 steps): 1.18 B tokens generated and scored.
⇒ Retention at 5% sampling + all flagged steps (§1.3). Keeping everything is ~4.7 TB of text
  per experiment at 4 B/token, × 20 experiments/week — not viable, and not necessary:
  the evidence is the aggregate metrics plus the flagged rollouts.
```

### 1.6.2 The memory budget — and why it decides GRPO vs PPO

```
8B policy. KV cache per token (L=32, 8 KV heads × 128, BF16):
  2 × 32 × 8 × 128 × 2 B = 131,072 B = 128 KB/token
Per rollout sequence (512 prompt + 640 gen = 1,152 tok): 151.0 MB
2,048 concurrent rollouts:                                309 GB of KV cache

Per-GPU budget on an 8 × H100-80GB node, weights time-shared between engines:

  GRPO                                    PPO (adds a critic + reward model)
  ────────────────────────────────        ─────────────────────────────────────
  policy train state 16N/8   16.0 GB      policy train state 16N/8    16.0 GB
  reference BF16 2N/8         2.0 GB      CRITIC train state 16N/8    16.0 GB
  inference weight copy       2.0 GB      reference BF16 2N/8          2.0 GB
  activations + workspace     4.0 GB      inference weight copy        2.0 GB
                                          reward model BF16 2N/8       2.0 GB
                                          activations + workspace      4.0 GB
  ────────────────────────────────        ─────────────────────────────────────
  used                       24.0 GB      used                        42.0 GB
  free for KV          56 GB/GPU          free for KV            38 GB/GPU
                    = 448 GB total                             = 304 GB total
  max concurrent rollouts   2,967         max concurrent rollouts     2,013
```

> **The finding.** The NFR is ≥ 2,048 concurrent rollouts. **GRPO clears it with 45% headroom; PPO
> does not clear it at all.** The critic's *optimizer state* — 16 bytes/param, another 16 GB/GPU — is
> what pushes it under. GRPO's "no critic" is usually presented as an algorithmic simplification; on
> this hardware at this group size it is the difference between the configuration existing and not.
>
> This is the same structural insight as [`27/04`](../../27_ai-platform-system-design/04_llm_inference_platform/README.md):
> **KV cache, not weights, caps concurrency.** It shows up on the training side too, and it shows up
> as an algorithm choice.

### 1.6.3 Cost

```
One 8B experiment: 500 steps × 89.8 s = 12.5 h × 8 GPUs = 99.8 GPU-hr = $299
  (at $3.00/GPU-hr, assumption A1)

20 experiments/week × 4.33 weeks = 86.6/month × $299 =  $25,900/month
70B tier: compute × 8.8, generation disproportionately slower ⇒ assume × 9
  10 experiments/month × $2,690                        =  $26,900/month
Data curation (CPU: dedup + decontam, ~200 CPU-hr/month) ≈     $200/month
Verifier sandbox fleet (256 vCPU sustained)              ≈   $2,800/month
                                                            ─────────────
                                                    TOTAL  ≈ $55,800/month   ✅ under $60k
```

**Where this is fragile, stated plainly:** the 70B tier is 48% of the bill from 10% of the
experiments. If 70B demand doubles, the ceiling breaks. The lever is **not** cheaper 70B runs — it is
a **promotion gate**: an experiment reaches 70B only after a `clean` verdict at 8B (FR-13). Assumption
A3 below is the one to re-measure monthly.

### 1.6.4 Data pipeline sizing

```
SFT corpus: 500k examples × 1,200 tokens = 600 M tokens

Near-dedup (MinHash + LSH):
  128 permutations × 4 B × 500k docs = 256 MB of signatures — fits in RAM
  LSH with b=16 bands × r=8 rows: P(candidate | J=0.8) = 0.947
                                  P(candidate | J=0.5) = 0.061
  ⇒ catches ~95% of true near-duplicates while admitting ~6% of genuinely distinct pairs
    as candidates for exact checking. That asymmetry is the point of tuning (b, r).

Decontamination (13-gram Bloom filter over eval suites):
  40 suites × 5k items × 200 tokens = 40 M tokens ⇒ ~40 M 13-gram shingles
  Bloom at FPR 1%:  m = −n·ln(p)/(ln2)² = 48 MB, k = 7 hashes
  Bloom at FPR 0.1%:                      72 MB, k = 10 hashes  ← use this
  Checking 600 M training shingles ≈ 10 CPU-minutes single-threaded, trivially parallel
```

> **The cheapest requirement in the whole document.** Decontamination costs ~10 CPU-minutes and a
> 72 MB filter. Skipping it makes every eval number downstream — including the reward-hacking
> detector's held-out pass rate — unfalsifiable. There is no cost argument for sampling here, which is
> why FR-1 demands 100% coverage.

---

## 1.7 Assumptions and open questions

| # | Assumption | If wrong, what changes |
|---|---|---|
| **A1** | **Decode throughput 8,000 tok/s/GPU** for 8B at batch ≥ 256 | This is **15% of the 53,600 tok/s weight-bound roofline** and the largest known inefficiency in the design. At 16,000 the decode stage halves (20.5 s → 10.3 s) and the step drops to ~79 s. **This is the first place to profile**, not a settled number |
| **A2** | 640-token mean response length | Length drives decode time and KV footprint linearly. A policy that learns to be longer makes its own steps slower — a feedback loop that must be monitored, not assumed away (§[02_hld 2.5](02_hld.md)) |
| **A3** | 10 × 70B experiments/month | 48% of the cost from 10% of experiments. At 20/month the budget breaks. Mitigated by the 8B→70B promotion gate, not by cheaper 70B runs |
| **A4** | Verifier wall time 2 s mean, 256 parallel sandboxes | A 10 s mean verifier makes verify 80 s and it dominates the step. Verifier latency is a **first-class budget line**, and slow verifiers must be rejected at task-authoring time |
| **A5** | 25% of the promotion-eligible experiments actually promote | Same knob as design 01's screening rate |
| **A6** | 1,500 held-out prompts is a useful floor (2 SE = 3.7 points) | Arithmetic is exact (§00_concepts 6); what's assumed is that a ~4-point gap is early enough to catch a hack before it consumes the run. Unverified — see Q2 |
| **A8** | **The gap's SE is dominated by the *training* side, not the held-out side** | With 2,048 rollouts/step split across prompts, the training pass rate is measured on ~192 samples per prompt-set — SE 0.036 versus 0.013 for 1,500 held-out. **Buying held-out prompts past ~1,500 barely moves the CI**; computing the gap over a rolling 8-step window (≈1,536 training samples) is what actually balances it. This was found by writing [`project/run.py`](project/run.py) part 5, not by the original arithmetic |
| **A7** | Reward is roughly balanced mid-training (pass rate near 0.5) | The SE arithmetic in §00_concepts 6 is worst-case at p=0.5, so it is conservative at the extremes — but at pass rate 0.02 or 0.98 the *gap* itself becomes hard to interpret and `frac_zero_std_groups` is the better signal |

### Open questions

1. **What is the actual gap to the decode roofline?** A1 says 15% of theoretical. Whether the gap is
   kernel efficiency, KV-cache paging overhead, scheduler stalls, or the prefill/decode mix is
   *measurable in an afternoon with a profiler* and worth up to a 2× on 23% of the step. Flagged as
   the highest-value unanswered question in this design.
2. **At what divergence does reward hacking become irreversible?** The design detects a 3-point gap;
   nobody knows whether 3 points is early or already too late. The platform should *record* the gap
   trajectory of every confirmed hack, which within a quarter gives the lab an empirical answer instead
   of a guess.
3. **Who authors the held-out verifier?** FR-7 requires an independent *implementation*. If the same
   engineer writes both, they share mental models and therefore share blind spots. This is an
   organizational answer, and it determines whether the system's central safeguard actually works.
4. **Is one-step-off-policy staleness (FR-11) acceptable for this task mix?** It buys 15 s/step (17%).
   Standard practice says yes at staleness 1; the honest answer is that it is task-dependent and should
   be A/B'd through [design 01](../01_research_experiment_platform/README.md) rather than assumed.

---

← [00_concepts.md](00_concepts.md) · [system README](README.md) · → [02_hld.md](02_hld.md)
