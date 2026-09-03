# 00 — Concepts primer: what you need to know before reading this design

> **Read this first if you have not worked on a large training run.** Everything here is a
> prerequisite, taught from scratch. If you already know why `TP ≤ 8` and what sequence parallelism
> buys, skip to [`01_requirements.md`](01_requirements.md).
>
> ← [system README](README.md) · → [01_requirements.md](01_requirements.md)

---

## The three-sentence version

1. A 70B model needs **1,129 GB just for weights and optimizer state** — 14 H100s before a single
   activation is stored — so splitting the model across GPUs is not an optimization, it is the
   precondition for the run existing.
2. There are four ways to split it, they have completely different communication costs, and the right
   combination is decided by **which network link the traffic crosses** — NVLink inside a node is 8×
   faster than InfiniBand between nodes.
3. Everything is then measured in one number, **MFU**, and a deadline is not a GPU-count requirement —
   it is an MFU requirement.

---

## 1. Counting parameters

A dense decoder-only transformer, per layer:

```
attention (grouped-query):  h·(n_q·d_h) + 2·h·(n_kv·d_h) + (n_q·d_h)·h
                            ^Wq          ^Wk, Wv           ^Wo
MLP (SwiGLU, 3 matrices):   3·h·d_ff

N ≈ L·(attn + mlp) + 2·V·h        the 2 is input + output embedding
```

**The reference model used throughout this design** — a 70B-class dense decoder:

| Field | Value |
|---|---|
| Layers `L` | 80 |
| Hidden `h` | 8,192 |
| Query / KV heads | 64 / 8, head dim `d_h` = 128 |
| MLP hidden `d_ff` | 28,672 (SwiGLU) |
| Vocab `V` | 128,256 |
| Sequence `s` | 4,096 |

```
attn/layer = 8192·8192 + 2·8192·1024 + 8192·8192          = 151.0 M
mlp/layer  = 3·8192·28672                                  = 704.6 M
per layer                                                  = 855.6 M
N = 80 × 855.6M + 2 × 128,256 × 8192                       = 70.55 B
```

**Note the MLP is 82% of each layer** (80% of all parameters once embeddings are counted). That matters
twice later: it is where FP8 pays off most, and its intermediate activations are 59% of activation memory.

**A useful shortcut** for multi-head attention with a `4h` MLP: `N ≈ 12·L·h²`. Good to ~10%; use the
real config when memory is the question.

---

## 2. Counting FLOPs

```
Training FLOPs per token ≈ 6N          (forward 2N + backward 4N)
Total  C ≈ 6·N·D                       D = training tokens
```

Why 6: a matmul with `p` parameters costs `2p` FLOPs per token forward (one multiply, one add).
Backward computes gradients w.r.t. both inputs and weights, roughly `4p`. The attention-score term
(`12·L·s·h`) is under 5% at `s`=4,096 and is conventionally folded into MFU rather than counted.

**Chinchilla-compute-optimal** allocation: `D ≈ 20·N`, giving `C_optimal ≈ 120·N²`.

For the reference model at `D` = 1.4T tokens: **C = 6 × 70.55e9 × 1.4e12 = 5.93 × 10²³ FLOPs.**

*(Modern practice often over-trains well past 20N to reduce later inference cost. At 15× Chinchilla the
run is 15× longer and becomes a multi-month, multi-thousand-GPU project — covered as the 10× case in
[`02_hld.md §2.6`](02_hld.md).)*

---

## 3. Memory: the two numbers that decide the design

### 3.1 Weights and optimizer state — the `16N` rule

BF16 mixed precision with Adam, per parameter:

| Item | Bytes |
|---|---|
| fp32 master weights | 4 |
| Adam first moment `m` (fp32) | 4 |
| Adam second moment `v` (fp32) | 4 |
| BF16 weights (for compute) | 2 |
| BF16 gradients | 2 |
| **Total** | **16 bytes/param** |

For `N` = 70.55B: **1,129 GB — 14.1 × H100-80GB before any activations.**

> **This is what ends the "can't we just use data parallelism?" conversation.** Plain DDP replicates
> all 16N on every GPU, and 1,129 GB does not fit in 80 GB. Sharding is mandatory.

### 3.2 Activations — the number people forget

Every tensor needed for the backward pass must be kept. For **one** layer of the reference model, with
micro-batch 1, sequence 4,096, BF16, and FlashAttention (so the `s×s` attention matrix is never
materialized):

| Saved tensor | Size |
|---|---|
| Layer input | 67.1 MB |
| LayerNorm 1 output | 67.1 MB |
| Q / K / V | 67.1 / 8.4 / 8.4 MB |
| Attention output | 67.1 MB |
| `Wo` output | 67.1 MB |
| LayerNorm 2 output | 67.1 MB |
| **SwiGLU gate projection (28,672 wide)** | **234.9 MB** |
| **SwiGLU up projection** | **234.9 MB** |
| **SwiGLU product** | **234.9 MB** |
| Down projection output | 67.1 MB |
| **Per layer** | **1,191 MB** |

**× 80 layers = 95.3 GB.** For a *single* sequence, with *no* weights loaded.

> **It does not fit in an 80 GB H100 even with zero weights.** Activation memory, not weights, is what
> forces the recompute policy — and the three SwiGLU tensors are **59%** of it.

### 3.3 Activation recomputation (gradient checkpointing)

Don't save it; recompute it in the backward pass. Trade memory for FLOPs.

| Policy | Activation memory (un-sharded) | …and at TP=8, PP=8, SP, `micro_bs`=1 | Extra compute |
|---|---|---|---|
| None | 95.3 GB | **11.9 GB/GPU** | 0% |
| **Selective** (recompute only the SwiGLU intermediates) | 38.9 GB | **4.9 GB/GPU** | ~+8% |
| Full (store only each layer's input, redo the layer) | 5.4 GB | 0.2 GB/GPU | ~+33% |

**Read the second column carefully, because it corrects a natural misreading.** The 95.3 GB figure is
what *one un-sharded GPU* would need — it is the reason you **must shard**, not the reason you must
recompute. Once TP=8 shards the tensors and PP=8 splits the layers, even `none` fits in 11.9 GB/GPU.

**So recompute's real role here is as a lever, not a necessity:** selective recompute frees ~7 GB/GPU,
which is what makes `micro_bs = 4` comfortable — and raising micro-batch improves the kernel-efficiency
factor, the largest term in the MFU budget (§6). Selective is the right lever because the SwiGLU
intermediates are simultaneously the largest tensors (59%) *and* among the cheapest to recompute (two
matmuls and an elementwise product).

*Recompute becomes mandatory again at longer sequences: activation memory grows linearly in `s`, so at
16k it is 4× these numbers.*

---

## 4. The four ways to split a model

### 4.1 Data parallelism (DP) — split the *batch*

Every GPU has the whole model, processes different data, and gradients are averaged with an
**all-reduce** at the end of the step.

- **Comm:** one all-reduce of all gradients per step. Overlappable with backward.
- **Limit:** every GPU needs the full `16N`. Dead at 70B.

**ZeRO / FSDP** fixes that by *sharding* the state across the DP group: each GPU holds `16N/DP` and
**all-gathers** the weights for a layer just before using it, then discards them.

- **ZeRO-1** shards optimizer state · **ZeRO-2** adds gradients · **ZeRO-3 / FSDP** adds parameters.
- **Comm:** all-gather weights per layer (forward and backward) + reduce-scatter gradients. More traffic than DDP, and it is what makes DP usable at scale.

### 4.2 Tensor parallelism (TP) — split each *matrix*

Split individual weight matrices across GPUs. For an MLP: shard the first matrix column-wise, the
second row-wise, and the result needs **one all-reduce** to recombine.

- **Comm:** ~4 all-reduces of the activation tensor **per layer per micro-step** (2 forward, 2 backward). This is *inside* the layer and cannot be hidden behind compute the way DP's can.
- **This is the highest-frequency, least-hideable communication in the design** — which is why §5 matters so much.

### 4.3 Pipeline parallelism (PP) — split the *layers*

GPU 0 gets layers 1–10, GPU 1 gets 11–20, and micro-batches flow through.

- **Comm:** send one activation tensor between adjacent stages. Tiny.
- **Cost:** the **bubble** — stages idle while the pipeline fills and drains.

```
GPipe / 1F1B bubble fraction = (p − 1) / (m + p − 1)      p = stages, m = micro-batches
Interleaved 1F1B with v virtual stages ≈ (p − 1) / (v · m)
```

| `p` | `m` | `v` | Bubble |
|---|---|---|---|
| 8 | 32 | 1 | **17.9%** |
| 8 | 128 | 1 | 5.2% |
| 8 | 32 | 2 | 10.9% |
| **8** | **128** | **2** | **2.7%** |

**Rule of thumb: `m ≥ 4p` keeps the bubble under ~6%.** `1F1B` (one-forward-one-backward) has the same
bubble as GPipe but far less activation memory, because it starts backward passes early instead of
holding every micro-batch's activations.

### 4.4 Expert parallelism (EP) — for mixture-of-experts

Route tokens to different experts on different GPUs via **all-to-all**. Out of scope for this dense
design, but worth naming: it replaces the highest-cost collective with a different one, and load
imbalance across experts becomes the new failure mode.

### 4.5 Sequence parallelism (SP) — the cheap win alongside TP

TP shards the big matmuls, but LayerNorm and dropout regions are **replicated** on every TP rank.

```
Replicated per layer without SP: layer input + LN1 out + LN2 out = 3 × 67.1 MB = 201 MB
  × 80 layers = 16.1 GB on EVERY TP rank
With SP (shard those regions along the sequence dimension): 16.1 / 8 = 2.0 GB
```

**Sequence parallelism recovers 14 GB per GPU for free** — the collective volume is unchanged, it just
becomes reduce-scatter + all-gather pairs instead of all-reduce. There is essentially no reason not to
run it with TP.

---

## 5. Collectives and why `TP ≤ 8`

### 5.1 The cost of a ring all-reduce

```
Bus volume moved = 2·(n−1)/n · S ≈ 2S for large n     (S = tensor bytes, n = ranks)
Time ≈ bus_volume / effective_bandwidth
```

### 5.2 The two links, and the 8× cliff

| Link | Spec | **Effective ring bandwidth** |
|---|---|---|
| NVLink 4, intra-node | 900 GB/s bidirectional per GPU | **~400 GB/s** (collectives realize ~45%) |
| InfiniBand NDR, inter-node | 400 Gb/s per GPU | **50 GB/s** |

> **Plugging in 900 GB/s instead of 400 understates communication cost by 2.2×** — and that error is
> exactly large enough to make an unworkable parallelism plan look fine on paper.

### 5.3 The arithmetic that fixes `TP = 8`

TP all-reduces the activation tensor `s × b × h` = 4,096 × 1 × 8,192 × 2 B = **67.1 MB**, four times per
layer per micro-step. Ring bus volume per all-reduce = 2·(7/8)·67.1 = 117 MB.

With TP=8, PP=8 (so 10 layers per GPU), against **44.2 ms of pure matmul time** (peak × 0.62 kernel
efficiency):

| | Per all-reduce | 4/layer × 10 layers | **% of compute** | % of per-micro-step wall time |
|---|---|---|---|---|
| **NVLink** (intra-node) | 0.29 ms | **11.7 ms** | **26.6%** | 20.1% |
| **InfiniBand** (inter-node) | 2.35 ms | **94.0 ms** | **213%** | — |

**Tensor parallelism that crosses a node boundary spends more time communicating than computing.**
`TP ≤ 8` is not a heuristic — it is the size of the NVLink domain, and exceeding it is a cliff, not a
gradient.

> **Which denominator?** Compare comm against *compute* (matmul time at kernel efficiency) to answer
> "does communication dominate arithmetic?" — that is the design question, and the answer is 26.6%.
> Comparing it against per-micro-step *wall* time gives a flattering 20.1%, because wall time is derived
> from MFU and **MFU already contains the comm penalty**. Dividing by it is partly circular — the same
> double-count trap as §6.1.

**The resulting hierarchy, which is the whole parallelism design:**

```
TP   -> INSIDE the node    (highest comm frequency, needs NVLink)
PP   -> ACROSS nodes       (tiny comm: one activation tensor per stage boundary)
DP   -> ACROSS nodes       (one reduce-scatter/all-gather per step, overlappable)
```

---

## 6. MFU — the currency

```
MFU = (6·N·D) / (G · PEAK · T)              G = GPUs, PEAK = per-GPU peak FLOP/s
Planning form:  T = C / (G · PEAK · MFU)
```

MFU is **multiplicative**: every inefficiency is a factor, not a subtraction.

| Loss source | Factor |
|---|---|
| Matmul/kernel efficiency on realistic shapes (incl. FlashAttention) | ×0.62 |
| TP comm residual after overlap | ×0.92 |
| PP bubble (interleaved 1F1B, m=128, v=2) | ×0.95 |
| DP reduce-scatter/all-gather residual | ×0.97 |
| Non-matmul ops + optimizer step | ×0.92 |
| Data stalls + straggler jitter | ×0.95 |
| **Product** | **×0.459 → 45.9% MFU** |

Publicly reported large-run MFU is typically **38–43%**, so 45.9% is a *budget*, not a promise. Its real
value is diagnostic: **if measured MFU is 35%, one of those six factors is ~2× worse than budgeted, and
the budget tells you which to profile first.**

### 6.1 The double-counting trap

There are two ways to compute time-to-train, and mixing them is a common error:

```
(a) FLOP model:  T = C / (G · PEAK · MFU)
(b) Step model:  T = n_steps × m × per_micro_step_time × (1 + bubble)
```

**MFU already includes the bubble and the comm residual.** Applying `(1 + bubble)` on top of an
MFU-derived micro-step time double-counts it:

```
correct:        128 × 59.7 ms = 7.64 s/step × 333,786 steps = 29.5 days   ✅ matches (a)
double-counted: × 1.052 more  = 8.04 s/step                 = 31.0 days   ✗ 5% too slow
```

Small enough to look plausible, which is what makes it dangerous.

---

## 7. Numerics: BF16, FP8, and loss spikes

- **BF16** (8-bit exponent, 7-bit mantissa) — same range as fp32, so no loss scaling needed. The default.
- **FP16** — more mantissa, far less range; needs a `GradScaler` and still overflows at scale. Largely displaced by BF16 for LLM training.
- **FP8** (E4M3 / E5M2) — ~2× the peak FLOP/s on H100. Applied to the big MLP GEMMs (82% of parameters) with per-tensor scaling; master weights and optimizer state stay higher precision.

```
If FP8 gives 1.6× on the ~2/3 of FLOPs that are MLP GEMMs:
  blended speedup = 1 / (1/3 + (2/3)/1.6) = 1.33×
```

**Loss spikes** are the characteristic large-run failure: loss jumps from 2.1 to 6.8 at hour 300 and may
or may not recover. Causes include a bad data shard, an fp16/fp8 overflow, a hardware fault producing
silently wrong numerics, or genuine optimization instability. The mitigations are all operational:
gradient-norm monitoring, skip-batch-on-anomaly, and the ability to **roll back to a checkpoint and
skip the offending data range** — which is why checkpoint retention is a design requirement rather than
housekeeping.

---

## 8. Checkpointing and fault tolerance

### 8.1 Size and cadence

A full training checkpoint is the `16N` state: **1,129 GB** for the reference model.

| Strategy | Blocking time | Overhead at 30-min cadence |
|---|---|---|
| Single-rank gather + write | minutes | unusable |
| **Sharded synchronous** (each of 512 ranks writes 2.2 GB) | 8.8 s | 0.49% |
| **Sharded asynchronous** (device→host copy, then background upload) | **0.11 s** | **0.006%** |

### 8.2 Retention is a cost decision

```
Keep every checkpoint for 30 days: 1,440 × 1,129 GB = 1.63 PB = $37.4k/month
  Against $1.11M of compute for that run, that is 3.4% of the entire budget -- in storage.

Retention policy (3 most recent + 1/day + milestones) = ~35 × 1,129 GB = 39.5 TB = $909/month
```

### 8.3 Failures are certain, so budget for them

```
Assume per-GPU MTBF = 50,000 GPU-hours (all causes: ECC, XID, NVLink, host)
Cluster MTBF at G=512:  50,000 / 512 = 97.7 hours ≈ 4.1 days
Over a 29.5-day (708 h) run:  7.2 expected interruptions
```

Cost per interruption = detect + reschedule + reload + redo-lost-work:

| Detection mechanism | Per failure | Total lost | Cost of idle cluster |
|---|---|---|---|
| **NCCL's ~30-minute default watchdog** | 49 min | 5.9 h (0.84%) | **$9,094** |
| **60-second heartbeat health check** | 20 min | 2.4 h (0.34%) | $3,712 |

> **The single highest-ROI line of configuration in the platform is the failure-detection timeout.** It
> is worth ~$5,400 per flagship run and costs nothing. Everyone leaves it at the default.

---

## 9. Vocabulary

| Term | Meaning |
|---|---|
| **MFU** | Model FLOPs Utilization: achieved ÷ peak FLOP/s. The currency of this design |
| **HFU** | Hardware FLOPs Utilization — counts recompute FLOPs too, so it flatters a recompute-heavy config. Report MFU |
| **DP / TP / PP / EP** | Data / tensor / pipeline / expert parallelism |
| **FSDP / ZeRO-3** | Fully-sharded data parallelism: shard params, grads and optimizer state; all-gather per layer |
| **SP** | Sequence parallelism — shards the LayerNorm/dropout regions TP leaves replicated |
| **1F1B** | One-forward-one-backward pipeline schedule; same bubble as GPipe, far less activation memory |
| **Interleaved 1F1B** | Multiple non-contiguous layer chunks per GPU (`v` virtual stages) to shrink the bubble |
| **Bubble** | Pipeline idle time: `(p−1)/(m+p−1)`, or `(p−1)/(v·m)` interleaved |
| **Micro-batch** | The unit a pipeline stage processes; `m` of them make a global batch |
| **Global batch** | `DP × m × micro_bs × seq` tokens per optimizer step |
| **All-reduce / reduce-scatter / all-gather / all-to-all** | The collectives. Ring all-reduce moves ~2S of bus volume |
| **NVLink domain** | The set of GPUs with NVLink between them — 8 on an H100 node. **The number that fixes `TP ≤ 8`** |
| **NCCL** | NVIDIA's collective library; its watchdog timeout is the fault-detection default worth changing |
| **Activation recomputation** | Recompute instead of store; selective (SwiGLU only) vs full |
| **FlashAttention** | Tiled attention that never materializes the `s×s` matrix — removes the `O(s²)` activation term |
| **`16N` rule** | 16 bytes/param of model + optimizer state under BF16 + Adam |
| **Chinchilla-optimal** | `D ≈ 20N`; `C_optimal = 120N²` |
| **Loss spike** | Sudden large loss increase mid-run; may not recover |
| **Straggler** | One slow rank that gates every collective, so it gates the whole cluster |
| **Sharded checkpoint** | Each rank writes its own shard; no single-rank gather |
| **XID error** | NVIDIA driver-reported GPU fault code; a primary health signal |
| **Silent data corruption (SDC)** | Hardware producing wrong numbers without an error — the hardest fault class to detect |

---

← [system README](README.md) · → [01_requirements.md](01_requirements.md) ·
[shared assumptions](../00_requirements_all_systems.md)
