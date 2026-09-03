# 00 — Shared requirements & assumptions register (all three systems)

> **Read this first.** Every number in the three designs either lives here or is derived here. The
> per-system `01_requirements.md` files **reference** this file and add only system-specific depth —
> so when a price or a hardware assumption changes, it changes in **one** place and re-propagates.
>
> ← [folder README](README.md)

---

## Why this folder exists — and how it differs from 21 / 27 / 28

| Folder | Side of the model | Primary constraint family |
|---|---|---|
| [`21_ai-system-design-deep-dives`](../21_ai-system-design-deep-dives/README.md) | **Consume** a model (fintech domain) | Token cost, domain correctness |
| [`27_ai-platform-system-design`](../27_ai-platform-system-design/README.md) | **Consume / serve** a model (product-agnostic) | p95 latency, token cost, GPU serving |
| [`28_ai-system-design-by-industry`](../28_ai-system-design-by-industry/README.md) | **Consume** a model (per-industry) | Regulatory, domain SLAs |
| **`29` (this folder)** | **Produce** the model | **GPU-hours, memory, statistical power, MFU** |

Those three folders design systems whose unit of work is a **request**. This folder designs systems
whose unit of work is a **training run** — and almost nothing transfers:

- There is **no p95 latency SLO** on a training run. There is a *deadline* and an *MFU floor*.
- There is **no token cost per request**. There is a fixed capital cost of $0.6M–1.2M per flagship run.
- The dominant failure is not a 5xx. It is a **loss spike at hour 300**, a **silently wrong result**,
  or **a conclusion drawn from seed noise**.
- Cost is not reduced by caching. It is reduced by **raising MFU** and by **not running the experiment
  you cannot read the answer to**.

**Read this folder if you are targeting roles [01](../00_jobs/01_ai-research-scientist/README.md),
[02](../00_jobs/02_research-engineer-model-training/README.md), or
[03](../00_jobs/03_ml-systems-and-training-infra/README.md).** Those three roles *are* the frontier
lab, and their system-design interviews are training-side, not serving-side.

---

## A. Hardware & price assumptions

**All prices are assumptions as of 2026-09 and vary 2× by provider, region, and commitment.** They are
labelled so that a reader can substitute their own and re-run the arithmetic. Every derived figure in
this folder is a function of this table.

| Symbol | Assumption | Value | Note |
|---|---|---|---|
| `P_h100_od` | H100 80GB SXM, on-demand | **$3.00 / GPU-hr** | Assumption. Range seen: $2.00–$4.50 |
| `P_h100_res` | H100 80GB SXM, 1-yr reserved | **$1.80 / GPU-hr** | Assumption. ≈40% off on-demand |
| `P_a100` | A100 80GB, on-demand | $1.60 / GPU-hr | Assumption |
| `PEAK_bf16` | H100 BF16 dense tensor-core peak | **989 TFLOP/s** | Vendor spec (dense, *not* the 1,979 sparse figure) |
| `PEAK_fp8` | H100 FP8 dense peak | 1,979 TFLOP/s | Vendor spec |
| `BW_hbm` | H100 HBM3 bandwidth | 3.35 TB/s | Vendor spec |
| `BW_nvlink` | NVLink 4 intra-node, **effective ring bus** | **400 GB/s** | Assumption. Spec is 900 GB/s bidirectional; collectives realize ~45% |
| `BW_ib` | InfiniBand NDR 400 Gb/s per GPU | **50 GB/s** | Spec, ideal |
| `NODE` | GPUs per node / NVLink domain | **8** | The single most load-bearing number in design 03 |
| `P_s3` | Object storage | $0.023 / GB-month | Assumption |
| `BW_obj` | Sustained object-store write per node | 2 GB/s | Assumption |
| `MTBF_gpu` | Mean time between GPU-attributable interruptions | **50,000 GPU-hours** | Assumption; includes ECC/XID/NVLink/host. Cross-checked in §D |

> **Why `BW_nvlink` is an assumption and not a spec:** the 900 GB/s figure is bidirectional
> per-GPU link bandwidth. A ring all-reduce realizes roughly 400–480 GB/s of *useful* bus bandwidth
> after protocol and chunking overhead. Designs that plug in 900 understate communication cost by
> **2.2×** — and that error is exactly large enough to make an unworkable parallelism plan look fine.

---

## B. Model & compute arithmetic primitives

These four identities generate most of the numbers in this folder. Memorize them; they are the
back-of-envelope toolkit for any training-side interview.

### B.1 Parameter count

```
Dense transformer, per layer:
  attention (GQA)  = h·(n_q·d_h) + 2·h·(n_kv·d_h) + (n_q·d_h)·h
  MLP (SwiGLU)     = 3·h·d_ff
  N ≈ L·(attn + mlp) + 2·V·h                     ← the 2 is input + output embedding

Fast approximation for MHA + 4h MLP:   N ≈ 12·L·h²
```

**Reference model used throughout design 03** — a 70B-class dense decoder:

| Field | Value |
|---|---|
| Layers `L` | 80 |
| Hidden `h` | 8,192 |
| Query / KV heads | 64 / 8 (GQA), `d_h` = 128 |
| MLP hidden `d_ff` | 28,672 (SwiGLU) |
| Vocab `V` | 128,256 |
| Sequence `s` | 4,096 |
| **Parameters `N`** | **70.55 B** (attn 151.0M + MLP 704.6M = 855.6M/layer × 80, + 2.1B embeddings) |

### B.2 Training FLOPs

```
C ≈ 6·N·D          forward 2N + backward 4N, per token
                   (the attention-score term 12·L·s·h is <5% at s=4k and is folded into MFU)

Chinchilla-compute-optimal:  D ≈ 20·N
⇒ C_optimal ≈ 120·N²        ← the whole scaling ladder in one expression
```

For the reference model at `D` = 1.4T tokens: **C = 6 × 70.55e9 × 1.4e12 = 5.93 × 10²³ FLOPs.**

### B.3 Memory — the `16N` rule

```
BF16 mixed precision + Adam, per parameter:
  fp32 master weights   4 bytes
  Adam m (fp32)         4
  Adam v (fp32)         4
  BF16 weights          2
  BF16 gradients        2
  ─────────────────────────
                       16 bytes/param   ⇒  16N bytes of model+optimizer state
```

For `N` = 70.55B: **1,129 GB — 14.1 × H100-80GB before a single activation is stored.**

> **This is the number that ends the "can we just use data parallelism?" conversation.** Plain DDP
> replicates all 16N on every GPU. 1,129 GB does not fit in 80 GB. Sharding is not an optimization
> here; it is the precondition for the run existing at all.

### B.4 MFU (Model FLOPs Utilization)

```
MFU = (6·N·D) / (G · PEAK · T)          G = GPUs, T = wall-clock seconds

Equivalently, the planning form:
T = C / (G · PEAK · MFU)
```

**MFU is the currency of design 03.** A deadline is not a GPU-count requirement — it is an MFU
requirement, and MFU is bounded by a *multiplicative* budget (see
[`03/01_requirements.md §1.5`](03_distributed_training_platform/01_requirements.md)).

### B.5 Statistical power — the primitive for design 01

```
Two-sample (unpaired), power 0.80, α=0.05 two-sided:
  n per arm = 2(z_0.975 + z_0.80)² · σ²/δ²  =  15.70 · σ²/δ²

Paired (same init seed, same data order, only the ablated variable differs):
  n pairs   =    (z_0.975 + z_0.80)² · σ_d²/δ²  =   7.85 · σ_d²/δ²
  where σ_d = σ·√(2(1−ρ)),  ρ = correlation between paired arms

Inverted — the question people should ask and don't:
  δ_min = σ · √(15.70 / n)     "what is the smallest effect n seeds can even see?"
```

**This identity is to design 01 what `16N` is to design 03.** It is the reason a 3-seed ablation is
usually a coin flip dressed as a result — see §D.

---

## C. The three systems — scope contract

Each system gets a full Requirements → HLD → LLD treatment in its own folder. This table is the
**contract**: the boundary each design must respect so the three compose rather than overlap.

| # | System | Primary user | Unit of work | Defining constraint | In scope | **Out of scope** (owned elsewhere) |
|---|---|---|---|---|---|---|
| [01](01_research_experiment_platform/README.md) | **Research experiment platform** | Research scientist ([role 01](../00_jobs/01_ai-research-scientist/README.md)) | An *ablation* (a hypothesis + arms + seeds) | **Statistical power** — can the result be read at all? | Pre-registration, power calc, config lineage, metric store, verdict engine, scaling-law ladder | *Executing* the run (that's 03); post-training algorithms (that's 02) |
| [02](02_post_training_pipeline/README.md) | **Post-training pipeline** | Research engineer ([role 02](../00_jobs/02_research-engineer-model-training/README.md)) | A *post-training experiment* (SFT → DPO/RLVR) | **Generation, not gradients** — the rollout phase dominates and needs a different engine | Data curation/decontam, SFT, preference & RLVR loops, reward hacking detection, eval gating | Pre-training a base model (03); statistical verdicts (01) |
| [03](03_distributed_training_platform/README.md) | **Distributed training platform** | Systems engineer ([role 03](../00_jobs/03_ml-systems-and-training-infra/README.md)) | A *flagship run* (70B × 1.4T tokens) | **MFU** — the deadline is an MFU requirement, not a GPU-count one | Parallelism plan, collectives, checkpointing, fault tolerance, throughput, scheduler | What to train and why (01/02); inference serving ([27/04](../27_ai-platform-system-design/04_llm_inference_platform/README.md)) |

**Systems 01 and 03 are deliberately two sides of the same cluster.** 01 decides *which* runs are
worth GPU-hours; 03 makes those GPU-hours count. A lab that builds only 03 burns a well-utilized
cluster on unreadable experiments. A lab that builds only 01 has rigorous verdicts about runs that
take 3× too long.

---

## D. Shared NFR contract

Numbers that bind **all three** systems. System-specific NFRs live in each `01_requirements.md`.

| NFR | Target | Why this number |
|---|---|---|
| **Cluster** | 512 × H100-80GB (64 nodes × 8), NDR IB non-blocking within an island | Assumed lab scale: large enough that sharding and fault tolerance are mandatory, small enough to reason about |
| **Availability of the *platform*** | 99.5% control plane | A control-plane outage must never kill an in-flight run — runs survive it (see 03 §2.5) |
| **Reproducibility** | Bit-exact rerun from `(config_hash, code_sha, data_manifest_hash, seed)` for **all** runs | A result that cannot be reproduced cannot be defended, and an irreproducible regression cannot be bisected |
| **Provenance** | Every artifact traces to the exact dataset revision, tokenizer version, and eval-suite revision | Silent tokenizer/data changes are the single most common cause of "the model got worse and nobody knows why" |
| **Eval decontamination** | 13-gram overlap check against **all** eval suites before any corpus enters training | An unchecked corpus makes every downstream number a lie — cost is ~10 CPU-minutes (02 §1.6) |
| **Cost visibility** | GPU-hours attributed per experiment, per owner, per day, within 1 h | Without attribution the cluster silently fills with abandoned jobs |
| **Interruption budget** | ≤ 1% of wall-clock lost to faults on a 30-day run | Derived below |
| **Security** | Training data and checkpoints never leave the tenancy; sandboxed code execution for RLVR verifiers is **network-isolated** | RLVR verifiers execute model-generated code — that is arbitrary code execution by design (02 §4.1) |

### D.1 The interruption budget, derived

```
Assume MTBF_gpu = 50,000 GPU-hours (per-GPU, all causes)
Cluster MTBF at G=512:   50,000 / 512 = 97.7 hours ≈ 4.1 days
A 29.5-day (708 h) run:  708 / 97.7 = 7.2 expected interruptions

Cost per interruption = detect + reschedule + reload + redo-lost-work
  with NCCL's ~30-min default watchdog:  30 + 3 + 1 + 15 = 49 min
    ⇒ 7.2 × 49 min = 5.9 h lost = 0.84% of the run = $9,094 of idle cluster
  with a 60-s heartbeat health-check:     1 + 3 + 1 + 15 = 20 min
    ⇒ 7.2 × 20 min = 2.4 h lost = 0.34% of the run = $3,712

⇒ The single highest-ROI line of config in the whole platform is the failure-detection timeout.
  It is worth ~$5,400 per flagship run and costs nothing.
```

**Cross-check on the MTBF assumption:** publicly reported large runs put unexpected interruptions at
roughly *one per few hours* on 16k-GPU clusters. Scaling by GPU count (16,384 / 512 = 32×) puts a
512-GPU cluster at one per ~4 days — which is what the 50,000-hour assumption predicts. The
assumption is therefore the right *order of magnitude*; treat ±2× as the honest error bar.

---

## E. What the arithmetic revealed

Following the discipline of [`27`'s requirements doc](../27_ai-platform-system-design/00_requirements_all_systems.md),
here is where doing the arithmetic **changed the design** rather than confirming it. This is the most
useful table in the folder.

| System | What the numbers revealed |
|---|---|
| **01 Experiment platform** | **A 3-seed ablation can only detect a 0.046-nat effect** (σ=0.02). Almost no architectural change moves loss that much — so the standard practice measures noise. Getting to δ=0.01 needs **63 seeds per arm (126 runs)**. Pairing seeds cuts that to **13 pairs (26 runs)** at ρ=0.8 — a **4.8× saving that costs nothing but discipline**. And a 20-arm sweep at α=0.05 produces a "winner" **64% of the time under the null**. |
| **01 Experiment platform** | **The dollar cost of rigor is trivial and the cost of skipping it is not.** Full-power ablations cost $52.6k/quarter vs $12.1k for the underpowered version — **+$40k**. A full scaling-law ladder (20M→1.3B, 7 points, 6 configs each) costs **$3,391 = 0.31% of the $1.1M flagship** it de-risks. |
| **02 Post-training** | **Generation, not the gradient step, sets the shape of the system.** Rollout is 29% of a GRPO step and *cannot* run on the training engine's memory layout. Syncing weights via an object-store checkpoint round-trip costs **~56 s against an 89 s step — a 63% tax**; in-memory broadcast costs **0.04 s**. This one decision is the difference between a working platform and a 1.6× slower one. |
| **02 Post-training** | **Verify is 18% of every step with the GPUs completely idle** (sandboxed test execution is CPU work). Closing it requires one-step-off-policy pipelining — a *real algorithmic* concession (staleness) bought with a systems win, which is exactly the trade this role is paid to make. |
| **02 Post-training** | **Reward-hack detection with 100 held-out samples is theater** — 2 SE is **14.1 points**, and hacking announces itself at 2–5. **~1,500 held-out prompts scored by an independently implemented verifier** is the practical floor (3.7 points; resolving 3.0 needs n≈2,223). |
| **02 Post-training** | **And the gap's noise is dominated by the *training* side, not the held-out side** — a single step's training pass rate rests on ~192 rollouts (SE 0.036) against 0.013 for 1,500 held-out. So buying held-out prompts past ~1,500 barely tightens the interval; **computing the gap over a rolling 8-step window is what actually balances it.** Found by writing the runnable demo, not by the original arithmetic. |
| **03 Distributed training** | **The 30-day deadline is an MFU requirement: ≥ 45.2%.** The multiplicative MFU budget lands at **45.9% — 0.7 points of headroom.** Commonly reported large-run MFU is 38–43%. So the requirement is *achievable but not comfortably*, and **adding GPUs is the wrong lever** — FP8 for the MLP GEMMs is. |
| **03 Distributed training** | **Tensor parallelism across nodes costs 213% of compute time in communication** (94.0 ms comm vs 44.2 ms of pure matmul per micro-step) versus **26.6% intra-node**. Comm *exceeds* arithmetic, so no amount of overlap hides it. `TP ≤ 8` is not a heuristic; it is the NVLink domain size, and violating it is an 8× cliff. |
| **03 Distributed training** | **The 95.3 GB activation figure is the reason to shard, not the reason to recompute** — a distinction the runnable planner caught. One un-sharded micro-batch of seq-4096 activations is 95.3 GB and does not fit an 80 GB H100 even with FlashAttention and zero weights; but at TP=8/PP=8 the same activations are **11.9 GB/GPU**, so `none` fits. Recompute's actual role is as the **lever that buys `micro_bs > 1`** (11.9 → 4.9 GB/GPU for ~+8% compute), and micro-batch is the free MFU win. |
| **03 Distributed training** | **Keeping every checkpoint costs 3.4% of the entire compute budget** ($37.4k/month of storage against $1.11M of compute). A retention policy is a *design requirement*, not housekeeping. |

> **Five of these corrections came from writing the runnable code, not from the arithmetic.** The
> folder [`README.md`](README.md#-the-runnable-code-found-five-errors-in-these-designs) lists them; three
> are the same species — *a threshold or ratio stated without the denominator it depends on.*

**And once, the arithmetic said "you were worrying about the wrong thing."** Data-loading bandwidth
for the 70B run is **2.2 MB/s** (1.4T tokens × 4 bytes over 29.5 days). There is no data-loading
throughput problem at this scale — the real risk is *shuffle quality and determinism*, not bytes/s.
Design 03 says so explicitly rather than adding a streaming-data tier nobody needs.

---

## F. Cross-system requirement matrix

| Dimension | 01 Experiment platform | 02 Post-training | 03 Distributed training |
|---|---|---|---|
| Unit of work | Ablation (arms × seeds) | Post-training experiment | Flagship run |
| Wall-clock target | **hypothesis → verdict p95 < 2.5 h** | 8B experiment < 14 h | 70B × 1.4T tokens ≤ 30 days |
| Binding resource | **Statistical power** (seeds) | **Generation throughput** | **MFU** |
| Scale | 5,000 runs/quarter, 6×10⁹ metric points/quarter | 20 experiments/week | 512 GPUs, 334k optimizer steps |
| Cost ceiling | ≤ $60k/quarter incl. confirmation runs | ≤ $60k/month | ≤ $1.5M per flagship run |
| Dominant failure | A conclusion drawn from noise | **Reward hacking** (silent) | **Loss spike / silent divergence at hour 300** |
| Correctness metric | Verdict calibration (FDR ≤ 0.05) | Held-out verifier gap < 3 pts | Bit-exact resume; loss curve continuity |
| Hardest thing | Making researchers *pre-register* | Detecting a reward hack **before** it looks like progress | Keeping 512 GPUs in lockstep for 30 days |
| GPU-bound? | No — control plane. GPU cost is in the runs it authorizes | Partly — generation is bandwidth-bound, training compute-bound | Entirely |

**Note the diagonal:** each system's *dominant failure* is silent. None of the three fails with a
5xx. That is the single biggest mental shift from the serving-side designs in
[`27`](../27_ai-platform-system-design/README.md) — **detection is the design problem**, and it is why
every one of the three has an observability section that is load-bearing rather than decorative.

---

## G. Assumptions & open questions (folder-wide)

| # | Assumption | If it's wrong |
|---|---|---|
| A1 | H100 at $3.00/GPU-hr on-demand | All cost figures scale linearly. At $2.00 the flagship is $737k, not $1.11M — the ≤$1.5M ceiling stops being the binding constraint and the 30-day deadline becomes the only one |
| A2 | Effective NVLink ring bus = 400 GB/s | At 250 GB/s, intra-node TP comm rises from 26.6% to 42.6% of compute; budgeted MFU falls to 44.3% against the 45.2% floor and **the SLO breaks** — the design would move to TP=4 (11.4% comm) + PP=16 |
| A3 | Per-GPU MTBF = 50,000 h | At 15,000 h the cluster MTBF drops to 29 h, giving 24 interruptions per run; checkpoint cadence must tighten from 30 to ~10 min and async checkpointing stops being optional |
| A4 | Seed-to-seed σ of final val loss = 0.02 nats at 200M params | This is *the* number design 01 is most sensitive to and it is **measurable in an afternoon** — 01 §1.7 says measure it before trusting any power calculation |
| A5 | Paired-arm correlation ρ ≈ 0.8 | Also measurable from run history. At ρ=0.5 pairing only buys 2×, not 4.8×, and the platform's ROI story weakens |
| A6 | Achieved decode throughput 8,000 tok/s/GPU for an 8B model (15% of the 53,600 tok/s weight-bound roofline) | The gap to roofline is large enough that 02's generation tier is the first place to look for a 2× win — flagged as an open question, not a solved one |
| A7 | Chinchilla-optimal `D = 20N` | Modern practice over-trains well past 20N for inference-cost reasons. At `D = 15×` Chinchilla (21T tokens) the run is 15× longer and this becomes a multi-month, multi-thousand-GPU design — 03 §2.6 covers that as the 10× case |

**Open questions that would change a design, not just a number:**

1. **Is the 30-day deadline real, or is it a proxy for "before the next hardware generation"?** If the
   latter, the right answer may be to wait rather than to buy MFU. Design 03 asks this in §1.1.
2. **Does the lab actually have ρ (paired correlation) measured?** Design 01's entire ROI rests on it
   and it is nobody's job to measure it.
3. **Who owns the eval suites?** If the same team authors the eval and optimizes against it, 02's
   held-out verifier is not independent and the reward-hack detector is compromised at the root.

---

← [folder README](README.md) ·
→ [01 Research experiment platform](01_research_experiment_platform/README.md) ·
[02 Post-training pipeline](02_post_training_pipeline/README.md) ·
[03 Distributed training platform](03_distributed_training_platform/README.md)
