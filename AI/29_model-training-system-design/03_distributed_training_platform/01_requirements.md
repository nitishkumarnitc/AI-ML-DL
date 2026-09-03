# 01 — Requirements: Distributed Training Platform

> ← [00_concepts.md](00_concepts.md) · [system README](README.md) · → [02_hld.md](02_hld.md)
> · [shared assumptions register](../00_requirements_all_systems.md)

**Three-sentence compression:** The 30-day deadline is not a GPU-count requirement, it is an **MFU
requirement of ≥ 45.2%**, and the multiplicative MFU budget lands at 45.9% — **0.7 points of
headroom**, against a published-practice range of 38–43%. The choice that matters most is the
parallelism hierarchy **TP=8 inside the node, PP and DP across nodes**, because tensor parallelism that
crosses a node boundary spends 213% of compute time in communication versus 26.6% inside it. The failure
I would volunteer: **I would challenge the deadline before accepting it** — if "30 days" is really a
proxy for "before the next hardware generation," the right answer may be to wait rather than to buy MFU.

---

## 1.1 Problem statement and users

**What breaks today.** A lab wants to train a 70B-class dense model on 1.4T tokens and has 512 H100s and
30 days. The naive plan — "use FSDP on 512 GPUs" — fails three ways at once: 1,129 GB of optimizer state
does not fit anywhere near 80 GB per GPU without a parallelism plan; 95.3 GB of activations for a
*single* sequence does not fit in an H100 even with zero weights; and the default NCCL watchdog means
each of the ~7 expected hardware interruptions idles 512 GPUs for 30 minutes before anyone notices.

Then there is the failure that costs the most: at hour 300, loss jumps from 2.1 to 6.8 and nobody can
say whether it was a bad data shard, an FP8 overflow, or a GPU producing silently wrong numbers — and
whether the last usable checkpoint still exists depends on a retention policy nobody wrote.

**Primary user:** a systems / training-infrastructure engineer
([role 03](../../00_jobs/03_ml-systems-and-training-infra/README.md)) who owns whether the run finishes
on time, and the research engineers who submit jobs to the platform.

**Primary job:** *keep 512 GPUs in productive lockstep for 30 days, and make every interruption cost
minutes rather than hours.*

**"Working" means:** the run finishes inside the deadline at or above the MFU floor; every interruption
is detected in under 60 seconds and recovered from a checkpoint within 20 minutes; and any loss anomaly
can be rolled back to a known-good checkpoint with the offending data range identified and skipped.

### 1.1.1 The question I would ask before designing anything

**Is the 30-day deadline real, or a proxy?** The arithmetic below shows it requires 45.2% MFU against a
published range of 38–43% — achievable, but only just. Three very different situations hide behind the
same number:

| If the deadline is really… | Then the right answer is… |
|---|---|
| A model-launch commitment | Buy MFU: FP8 on the MLP GEMMs (§1.6.3) |
| "Before the next GPU generation ships" | **Wait.** A generation jump beats a 10% MFU win, and the engineering cost is zero |
| A budget-cycle boundary | Reduce `D` below Chinchilla-optimal and take the loss penalty knowingly |

Answering this changes the design. Asking it is the first requirement.

---

## 1.2 Functional requirements

### P0 — the run does not finish without these

| ID | Requirement | Acceptance criterion |
|---|---|---|
| **FR-1** | **Parallelism planner**: given a model config, GPU count and topology, emit a validated `(TP, PP, DP, micro_bs, m, recompute)` plan with predicted per-GPU memory and step time | Refuses any plan with `TP > NVLink domain (8)` and refuses any plan whose predicted per-GPU memory exceeds 80 GB minus a declared safety margin. Returns the **top-k feasible plans ranked by predicted step time**, not one answer |
| **FR-2** | **Sharded model + optimizer state** across the TP×PP×DP mesh | No rank holds more than `16N/(TP·PP)` of state. Verified at startup against the plan, not assumed |
| **FR-3** | **Activation recomputation** with a *selective* policy targeting the SwiGLU intermediates | Selective measured at ≤ 40 GB un-sharded (≤ 5 GB/GPU at TP=8/PP=8) and ≤ +10% step time. **Note this is a lever, not a necessity at this parallelism degree** (§1.6.1) — its purpose is to free HBM for `micro_bs > 1`. Full recompute available as a fallback for longer sequences |
| **FR-4** | **Sequence parallelism** enabled whenever TP > 1 | Per-GPU memory measured ≥ 12 GB lower than the same plan with SP off (the 16.1 → 2.0 GB recovery, §00_concepts 4.5) |
| **FR-5** | **Sharded asynchronous checkpointing** | p95 blocking time < 1 s for a 1,129 GB checkpoint; overhead < 0.05% at a 30-minute cadence. Checkpoint validity verified by a manifest of per-shard hashes |
| **FR-6** | **Bit-exact resume** restoring model, optimizer, LR schedule, RNG state **and the data cursor** | A resumed run's loss curve is continuous across the boundary. **Losing the data cursor is a hard failure, not a warning** — a run that silently re-reads the same shards looks like fast progress |
| **FR-7** | **Fast fault detection**: per-rank heartbeat plus NCCL watchdog set well below its default | Detection p95 < 60 s. **The NCCL timeout is an explicit, reviewed config value** with its cost recorded (§1.6.5) |
| **FR-8** | **Automatic restart** onto healthy capacity with the faulty node drained | End-to-end recovery p95 < 20 min including redone work. Restart attempts are bounded and a repeated-failure loop escalates rather than retrying forever |
| **FR-9** | **Checkpoint retention policy** enforced by the platform | 3 most recent + 1/day + declared milestones. Keep-everything is refused with the $37.4k/month arithmetic in the error (§1.6.4) |
| **FR-10** | **Loss-anomaly detection and rollback**: gradient-norm and loss monitors with skip-batch and roll-back-to-checkpoint actions | A spike above `k`σ of the trailing window triggers: log the exact data range, skip the batch, and if the spike persists for `n` steps, halt for human decision. The data range must be recoverable from the run state alone |
| **FR-11** | **Straggler detection** | Per-rank step-time distribution published; a rank persistently above p99 is flagged and drainable. **A straggler gates every collective, so it gates the cluster** |

### P1 — the platform is materially worse without these

| ID | Requirement | Acceptance criterion |
|---|---|---|
| **FR-12** | **FP8 for MLP GEMMs** with per-tensor scaling, master weights and optimizer state at higher precision | ≥ 1.25× blended step-time improvement with validation loss within noise of the BF16 run over ≥ 5,000 steps. **Ships only if that loss check passes** |
| **FR-13** | **Silent-data-corruption screening** | A periodic deterministic self-check (fixed input, expected output hash) per rank, plus cross-DP-replica gradient-norm comparison. Any mismatch drains the rank |
| **FR-14** | **Elastic DP**: continue at reduced DP width after a node loss rather than blocking for replacement | Run continues within 5 min at reduced width; global batch held constant by raising `m` so the optimization is unchanged |
| **FR-15** | **Job scheduler** with gang scheduling, topology awareness, and a reserved partition for the ablation tier | A job requiring TP=8 is never placed across a node boundary. Ablation partition honoured (design 01's §1.5 queue budget depends on it) |
| **FR-16** | **Throughput regression gate in CI** | A commit that drops step-time by > 3% on a fixed 50-step benchmark fails the build |

### P2 — deliberately deferred

| ID | Requirement |
|---|---|
| **FR-17** | Expert parallelism / MoE support (different comm pattern: all-to-all; different failure mode: expert load imbalance) |
| **FR-18** | Multi-region / multi-cluster training (the collective cost across regions makes this a different design) |
| **FR-19** | Custom Triton/CUDA kernels beyond FlashAttention and fused optimizers |
| **FR-20** | Automatic hyperparameter transfer across the scaling ladder (that is design 01's ladder, not this platform) |

---

## 1.3 Non-functional requirements

Cluster, hardware, price and interruption-budget NFRs are in
[`00_requirements_all_systems.md §A, §D`](../00_requirements_all_systems.md) and not repeated.

| NFR | Target | Why this number |
|---|---|---|
| **Time to train** | **70.55B × 1.4T tokens in ≤ 30 days on 512 × H100** | The business deadline — and §1.1.1 questions whether it is real |
| **MFU floor** | **≥ 45.2%** | **Derived, not chosen.** `C/(G·PEAK·T)` with T = 30 days. The budget lands at 45.9% (§1.5) — 0.7 points of headroom against a 38–43% published range |
| Per-GPU memory | ≤ 80 GB with a **≥ 6 GB** declared safety margin | Fragmentation and transient allocations are real; a plan that fits at 79.8 GB predicted will OOM at hour 200 |
| Checkpoint blocking | p95 < 1 s; overhead < 0.05% at 30-min cadence | Async sharded measures 0.11 s (§1.6.4); synchronous is 8.8 s = 0.49%, which is 20× worse for no reason |
| **Fault detection** | **p95 < 60 s** | NCCL's ~30-min default costs $9,094 per flagship run in idle cluster; 60 s costs $3,712 (§1.6.5) |
| Recovery (detect → training again) | **p95 < 20 min** incl. redone work | Gives 7.2 × 20 min = 2.4 h = 0.34% of a 708 h run, inside the ≤1% interruption budget |
| Checkpoint cadence | 30 min | Bounds expected redone work to 15 min. Tighter only if MTBF is worse than assumed (A3) |
| Resume correctness | **Bit-exact**, data cursor included | A discontinuous loss curve across a resume means the run is no longer the run you designed |
| Straggler tolerance | No rank > 1.15× median step time for > 10 consecutive steps | Above ~15% the straggler costs more than draining and restarting it |
| Retention | 3 recent + 1/day + milestones ≈ 39.5 TB | Keep-all is 1.63 PB = **3.4% of the entire compute budget** (§1.6.4) |
| Utilization | ≥ 92% of GPU-hours in productive training | The remaining 8% is checkpointing, restarts, drains and the ablation partition |
| Data-loader throughput | ≥ 10 MB/s aggregate | **Deliberately loose.** The real requirement is 2.2 MB/s (§1.6.6) — there is no data-throughput problem here, and saying so beats building a tier nobody needs |
| Availability of the *control plane* | 99.5% | A control-plane outage must never kill an in-flight run (same principle as design 01 §2.5) |
| **Cost ceiling** | ≤ **$1.5M** per flagship run | §1.6.3 → $1.11M on-demand, $664k reserved |
| Observability | Per-rank step time, MFU, comm/compute split, grad norm, loss, memory, XID errors — at ≥ 0.1 Hz | An MFU number without the six-factor split cannot be debugged (§1.5) |

---

## 1.4 Explicit non-goals

| Not building | Why |
|---|---|
| **Deciding what to train** | [Design 01](../01_research_experiment_platform/README.md) authorizes runs; this platform executes them. The boundary is the signed job spec |
| **Post-training (SFT/DPO/RLVR)** | [Design 02](../02_post_training_pipeline/README.md). This platform produces the base checkpoint 02 consumes |
| **Inference serving** | [`27/04`](../../27_ai-platform-system-design/04_llm_inference_platform/README.md). Note it shares this design's structural lesson — a memory term, not FLOPs, caps the achievable configuration |
| **MoE / expert parallelism** (FR-17) | Dense model in v1. EP replaces the dominant collective with all-to-all and introduces expert load imbalance — a different design, not an increment |
| **Multi-region training** (FR-18) | Cross-region collective latency changes the parallelism hierarchy fundamentally |
| **Custom kernels beyond FlashAttention + fused optimizers** | The MFU budget's ×0.62 kernel-efficiency factor is the *first* thing to profile, but writing kernels is a follow-on project once the budget says it is the binding factor |
| **Procuring the cluster** | 512 H100s in one non-blocking IB island is an assumption (§1.7 A1), and the design breaks in a specific, stated way if it is false |
| **Training data curation** | [Design 02](../02_post_training_pipeline/README.md) §1.6.4 owns dedup and decontamination; this platform consumes a manifest and must not silently accept one marked unusable |

---

## 1.5 The MFU budget

This is the latency-budget analogue, and it is the most important table in the document. MFU is
**multiplicative** — every inefficiency is a factor.

| Loss source | Factor | Running MFU | What it is |
|---|---|---|---|
| Peak BF16 dense | — | 100% | 989 TFLOP/s (the dense figure, **not** the 1,979 sparse one) |
| Matmul/kernel efficiency on real shapes | ×0.62 | 62.0% | Includes FlashAttention (bandwidth-bound) and TP's narrower GEMMs |
| TP comm residual after overlap | ×0.92 | 57.0% | **26.6% of compute raw** (§00_concepts 5.3), ~70% hidden behind compute |
| PP bubble, interleaved 1F1B, m=128, v=2 | ×0.95 | 54.2% | 2.7% theoretical + schedule imperfection |
| DP reduce-scatter / all-gather residual | ×0.97 | 52.6% | Overlapped with backward |
| Non-matmul ops + optimizer step | ×0.92 | 48.4% | LayerNorm, softmax, elementwise, Adam |
| Data stalls + straggler jitter | ×0.95 | **45.9%** | The tail |
| **Budgeted MFU** | | **45.9%** | |
| **Required for the 30-day SLO** | | **45.2%** | **0.7 points of headroom** |

```
Required MFU = C / (G · PEAK · T_slo)
             = 5.926e23 / (512 × 989e12 × 30 × 86400)
             = 45.2%
```

**What this table is actually for.** Not to promise 45.9% — published large-run MFU is 38–43%, so this
budget is optimistic and the headroom is thin. Its value is **diagnostic**: if the measured MFU comes in
at 35%, one of those six factors is roughly 2× worse than budgeted, and the table says which to profile
first. An MFU number without this decomposition is a number you cannot act on.

**And the honest conclusion:** with 0.7 points of headroom, **any single factor 2% worse than budgeted
misses the deadline.** The design therefore treats FP8 (FR-12) as the planned margin rather than as an
optimization, and §1.6.3 shows why adding GPUs is the wrong lever.

**Cross-check via the step model** — and the double-count trap:

```
Two different per-micro-step times, and they measure different things:
  pure matmul time  (peak x 0.62 kernel efficiency)     = 44.2 ms   <- comm compares to THIS
  WALL time         (peak x 0.459 budgeted MFU)          = 59.7 ms   <- the step is built from THIS

step = m × wall = 128 × 59.7 ms                          = 7.64 s
global batch = DP(8) × m(128) × micro_bs(1) × s(4096)   = 4.19 M tokens
steps = 1.4e12 / 4.19e6                                 = 333,786
T = 333,786 × 7.64 s = 2.55e6 s                         = 29.5 days   ✅ agrees with the FLOP model

WRONG: multiplying by (1 + bubble) as well -> 8.04 s/step -> 31.0 days.
MFU ALREADY CONTAINS the bubble. The 5% error is small enough to look plausible.
```

---

## 1.6 Capacity and cost estimation

### 1.6.1 The memory arithmetic that sizes everything

```
Model + optimizer state (16N rule, BF16 + Adam):
  16 × 70.55e9 = 1,129 GB  =  14.1 × H100-80GB  BEFORE any activation
  ⇒ plain DDP is impossible. Sharding is the precondition, not an optimization.

Activations, ONE micro-batch, seq 4096, BF16, FlashAttention, no recompute:
  1,191 MB per layer × 80 layers = 95.3 GB
  ⇒ does not fit in an 80 GB H100 even with ZERO weights loaded.
  ⇒ ACTIVATION memory, not weights, forces the recompute policy.

  SwiGLU gate + up + product = 705 MB of the 1,191 MB = 59%
    selective recompute (SwiGLU only):  38.9 GB   ~+8% compute
    full recompute (layer input only):   5.37 GB  ~+33% compute

Sequence parallelism, the free 14 GB:
  TP shards the GEMMs but leaves LayerNorm/dropout regions replicated:
    3 × 67.1 MB × 80 layers = 16.1 GB on EVERY TP rank
    with SP: 16.1 / 8 = 2.0 GB
  ⇒ same collective volume, 14.1 GB recovered per GPU. Always on with TP.
```

**The chosen plan: TP=8, PP=8, DP=8 (=512 GPUs), micro_bs=1, m=128, SP on.**

```
per-GPU state:       16N/(TP·PP) = 1,129/64                        = 17.6 GB
per-GPU activations, 10 layers, /TP with SP, ×PP in-flight (1F1B):
                     no recompute                                   = 11.9 GB
                     selective recompute                            =  4.9 GB
workspace/fragmentation margin                                      =  6.0 GB
                                                                      ────────
  no recompute, micro_bs=1                                          = 35.5 GB of 80  ✅
  selective,    micro_bs=1                                          = 28.5 GB
  selective,    micro_bs=4                                          = 43.1 GB  ✅
  no recompute, micro_bs=4                                          = 71.3 GB  ⚠ at the margin

  ⇒ Recompute is NOT what makes this run possible -- sharding already did that.
    It is what makes micro_bs=4 comfortable, and micro_bs is the free MFU lever
    (it improves the ×0.62 kernel-efficiency factor). That is the first thing to try.
```

**Why not TP=8 / PP=16 / DP=4, which needs only 26.7 GB/GPU?** It is 0.1 days faster and uses 9 GB less.
Rejected on *operational* grounds, which the planner surfaces as notes: DP=4 leaves only 3 spare replicas
for elastic recovery (FR-14) and a thin base for cross-replica SDC comparison (FR-13), and PP=16 means
5 layers per stage, so a single stage fault stalls a longer pipeline. **The feasible plans differ by under
1% in throughput and by 4× in DP headroom — so the choice is an operational one, not a performance one.**

### 1.6.2 Why the parallelism hierarchy is what it is

```
TP all-reduce payload = s·b·h·2 B = 4096 × 1 × 8192 × 2 = 67.1 MB
Ring bus volume = 2·(7/8)·67.1 MB = 117 MB, four times per layer per micro-step

per-GPU PURE MATMUL time per micro-step (10 layers, peak x 0.62) = 44.2 ms
  TP=8 over NVLink @ 400 GB/s:  0.29 ms × 40 = 11.7 ms  =  26.6% of compute  ✅
  TP=8 over IB    @  50 GB/s:   2.35 ms × 40 = 94.0 ms  =   213% of compute  ✗

(Against per-micro-step WALL time of 59.7 ms the intra-node figure reads 20.1%, but
 wall time is MFU-derived and MFU already contains the comm penalty -- so compute is
 the honest denominator. Same trap as §1.5.)

⇒ TP <= 8 is the NVLink domain size. Crossing it is an 8x cliff, not a gradient.
⇒ PP and DP go across nodes: PP sends one activation tensor per stage boundary,
  DP does one reduce-scatter/all-gather per step, and both overlap with compute.
```

### 1.6.3 Cost — and why more GPUs is the wrong lever

```
368,640 GPU-hours (512 × 30 × 24)
  on-demand @ $3.00  = $1.106 M      ✅ under the $1.5M ceiling
  reserved  @ $1.80  = $664 k
  + ~15% for restarts, the scaling ladder, and failed attempts ≈ $1.27M on-demand

If MFU comes in at the published-practice 40% instead of 45.9%:
  T = 5.926e23 / (512 × 989e12 × 0.40) = 33.9 days     ← MISSES the 30-day SLO by 3.9 days

Two ways to close it:
  (a) MORE GPUs: 512 → 580 at 40% MFU.
      Cost rises to $1.25M, and DP grows 8 → 9.06 (not integral), so the mesh must be
      re-planned. Worse, adding DP width RAISES the global batch, which changes the
      optimization -- a different training run, not a faster one.
  (b) FP8 on the MLP GEMMs (82% of each layer, 80% of all params, ~2/3 of FLOPs):
      blended = 1/(1/3 + (2/3)/1.6) = 1.33×  →  33.9/1.33 = 25.5 days   ✅ 4.5 days spare
      Cost: unchanged. Risk: numerics -- which is why FR-12 gates on a validation-loss
      check over >=5,000 steps rather than shipping on a throughput number.

⇒ The lever is NUMERICS, not capacity. Adding GPUs costs money AND changes the run.
```

### 1.6.4 Checkpointing and retention

```
Checkpoint size = 16N = 1,129 GB

Sharded synchronous: 512 ranks × 2.2 GB; 64 nodes × 2 GB/s = 128 GB/s aggregate
  1,129/128 = 8.8 s blocking  → 0.49% overhead at 30-min cadence
Sharded ASYNC: device→host copy of 2.2 GB/GPU at ~20 GB/s
  0.11 s blocking             → 0.006% overhead     ⇒ 80× better, for a background thread

Retention:
  keep-everything, 30 days at 30-min cadence = 1,440 × 1,129 GB = 1.63 PB
    = $37.4k/month of storage against $1.11M of compute = 3.4% OF THE ENTIRE BUDGET
  policy (3 recent + 30 daily + 2 milestones) = 35 × 1,129 GB = 39.5 TB = $909/month

⇒ Retention is a DESIGN REQUIREMENT (FR-9), not housekeeping. And note what it buys:
  the ability to roll back past a loss spike (FR-10) is the reason to keep dailies at all.
```

### 1.6.5 The interruption budget

```
Cluster MTBF = 50,000 / 512 = 97.7 h ; 708 h run ⇒ 7.2 expected interruptions

  with NCCL's ~30-min default watchdog: 30+3+1+15 = 49 min each
    ⇒ 5.9 h lost (0.84% of the run) = $9,094 of idle cluster
  with a 60-s heartbeat health check:    1+3+1+15 = 20 min each
    ⇒ 2.4 h lost (0.34%)                          = $3,712

⇒ ~$5,400 per flagship run, from one config value, at zero engineering cost.
  This is FR-7, and it is the highest-ROI line in the platform.
```

### 1.6.6 Data loading — the bottleneck that isn't

```
1.4T tokens over 29.5 days (2.55e6 s) = 549k tokens/s
As uint32 (vocab 128,256 > 65,535, so uint16 won't do): 549k × 4 B = 2.2 MB/s

Dataset on disk: 1.4e12 × 4 B = 5.6 TB = $129/month of object storage.
```

> **Called out because it inverts the intuition:** there is **no data-throughput problem** at this scale.
> 2.2 MB/s is nothing. A design that adds a streaming-data tier, a caching layer and a shuffle service
> here has solved a problem it doesn't have. The real data risks are **shuffle quality** (a poorly
> shuffled corpus produces correlated batches and a worse model) and **cursor determinism** on resume
> (FR-6) — neither of which is a bandwidth problem.
>
> *For a 1B model at the same GPU count, tokens/s is ~70× higher — still only 155 MB/s. Data bandwidth
> becomes interesting for small models, not large ones.*

---

## 1.7 Assumptions and open questions

| # | Assumption | If wrong, what changes |
|---|---|---|
| **A1** | 512 H100s in **one non-blocking InfiniBand island**, 8 GPUs/node with NVLink | If the fabric is oversubscribed 2:1 between leaf switches, DP and PP collectives slow proportionally and the MFU budget's ×0.97 and ×0.95 factors degrade — the 0.7-point headroom vanishes immediately. **The topology must be verified, not assumed** |
| **A2** | **Effective NVLink ring bandwidth 400 GB/s** (45% of the 900 GB/s spec) | At 250 GB/s, TP comm goes from 26.6% to 42.6% of compute; at the same ~70% overlap the ×0.92 factor becomes ×0.887, budgeted MFU falls to **44.3%** against the 45.2% required and **the SLO breaks**. The plan would move to TP=4 (11.4% comm) with PP=16 |
| **A3** | Per-GPU MTBF 50,000 h | At 15,000 h, cluster MTBF is 29 h → 24 interruptions per run. Checkpoint cadence must tighten from 30 to ~10 min, and async checkpointing stops being optional |
| **A4** | Matmul/kernel efficiency 0.62 | The single largest and least-certain factor in the MFU budget. **Measurable in a day** on a 50-step benchmark, and it should be measured before the deadline is accepted |
| **A5** | FP8 delivers 1.6× on MLP GEMMs at neutral loss | If loss degrades, FR-12 does not ship and the deadline needs option (a) — more GPUs, a bigger global batch, and a different training run |
| **A6** | Chinchilla-optimal `D = 20N` | Over-training past 20N is now common for inference-cost reasons. At 15× Chinchilla (21T tokens) this is a multi-month, multi-thousand-GPU design |
| **A7** | Object-store write 2 GB/s per node sustained | At 500 MB/s, async checkpointing still hides the latency but the background upload may not finish before the next checkpoint — cadence becomes storage-bound |
| **A8** | `micro_bs=1` in the plan | §1.6.1 shows headroom for 2–4, which would improve the ×0.62 kernel factor. **This is the cheapest MFU lever and it is listed as an assumption precisely because it should be tuned, not assumed** |

### Open questions

1. **Is the deadline real?** (§1.1.1.) It determines whether the answer is FP8, waiting for the next
   hardware generation, or reducing `D`. Nothing else in the design matters as much, and it is not a
   technical question.
2. **What is the actual kernel efficiency (A4)?** The MFU budget's largest factor is a 0.62 assumption.
   A 50-step benchmark answers it in a day. **Accepting a 30-day deadline before measuring this is
   accepting a deadline you cannot cost.**
3. **Is the IB fabric genuinely non-blocking (A1)?** Ask for the topology, not the peak numbers. An
   oversubscribed spine invalidates the parallelism plan and there is no software fix.
4. **Who owns the loss-spike decision at 3 a.m.?** FR-10 can skip a batch and can roll back, but
   "resume from the hour-280 checkpoint and skip shards 4,102–4,140" is a judgement call with a
   six-figure cost. That runbook and its escalation path need naming before the run starts, not during
   it ([§4.2](04_production_and_interview.md)).
5. **Does silent data corruption (FR-13) actually get caught?** Cross-replica gradient-norm comparison
   catches gross divergence; subtle SDC that shifts loss by 0.5% may not be detectable at all. This is
   an honest gap, and the mitigation is checkpoint retention wide enough to roll back to before the
   suspected onset.

---

← [00_concepts.md](00_concepts.md) · [system README](README.md) · → [02_hld.md](02_hld.md)
