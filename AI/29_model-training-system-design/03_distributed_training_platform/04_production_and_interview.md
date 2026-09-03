# 04 — Production & interview: Distributed Training Platform

> ← [03_lld.md](03_lld.md) · [system README](README.md) · [00_concepts.md](00_concepts.md)

**Three-sentence compression:** Almost none of the serving-side AI concern list applies here, and the
training-side list that replaces it is dominated by **numerics, determinism and fault economics**. The
operational centre of gravity is the **loss-spike runbook**, because it is the only decision in the
platform that is worth six figures and cannot be automated. The mistake I see most: reporting MFU
without its six-factor decomposition, which turns a diagnosable regression into an unexplained number.

---

## 4.1 AI-specific concerns

### Applies — translated to the training side

| Concern | What this design specifies |
|---|---|
| **Compute cost** | [§1.6.3](01_requirements.md): $1.11M on-demand / $664k reserved, +15% contingency. The important part is the *lever analysis*: at 40% MFU the run misses by 3.9 days, and **more GPUs is the wrong fix** — it costs $140k more *and* raises the global batch, which changes the optimization. FP8 costs nothing and gives 1.33× |
| **The budget that must sum** | The MFU budget (§1.5) is this design's latency budget. Six multiplicative factors → 45.9% against 45.2% required. **0.7 points of headroom**, stated plainly rather than padded |
| **Evaluation / regression gating** | Two gates: **FR-16** fails any commit that drops step time > 3% on a fixed 50-step benchmark; **FR-12** blocks FP8 unless validation loss matches BF16 over ≥5,000 steps. The second exists because a throughput benchmark cannot see a quality regression |
| **Non-determinism** | The dominant correctness concern here. Bit-exact resume requires model + optimizer + LR schedule + RNG **+ the data cursor**, all `NOT NULL` in the checkpoint. Loss continuity is *asserted* at resume, because a silent state loss produces a run nobody can reason about |
| **Numerics** (the training analogue of hallucination) | BF16 default (no loss scaling); FP8 confined to MLP GEMMs with per-tensor scaling, master weights and optimizer state at higher precision, gated on a loss check. **Silent data corruption** is the worst case: a rank producing wrong numbers with no error, mitigated by a deterministic self-check plus cross-replica gradient-norm comparison — and honestly flagged as possibly undetectable at the margin |
| **Drift** | **Environment drift** — a rebuilt base image changes cuBLAS/NCCL kernel selection, which changes numerics. Pinned by digest per run, never applied to a running run. **Hardware drift** — a degrading NVLink presents as a straggler, not an error |
| **Observability** | Per-rank at ≥0.1 Hz with the **comm/compute split** (`compute_ms`, `tp_comm_ms`, `pp_wait_ms`, `dp_comm_ms`, `optim_ms`, `data_wait_ms`). The `delta_explains` API block ([§3.2](03_lld.md)) turns "MFU is 44.1%" into "`data_wait_frac` is 2.8× its budget" |
| **Data governance** | Consumes a manifest from [design 02](../02_post_training_pipeline/README.md) and **refuses one marked `usable=false`** — this platform must not be the hole in the decontamination gate |
| **Cold start & capacity** | Gang scheduling (all ranks or none); a reserved ablation partition so [design 01](../01_research_experiment_platform/README.md)'s 30-minute queue budget is achievable; autoscale is irrelevant — the run has a fixed shape for 30 days |
| **Untrusted input** | Minimal, and worth saying so: training data is untrusted *content* (hence design 02's PII scan and decontamination) but it is never executed. There is no model-generated code here — that risk lives entirely in [design 02's verifier sandbox](../02_post_training_pipeline/04_production_and_interview.md) |

### Does not apply

| Serving-side concern | Why absent |
|---|---|
| **TTFT / p95 latency / streaming** | No requests and no users waiting. The analogue is a 30-day *deadline* and an MFU floor — a fundamentally different shape of constraint, and conflating them is how a training design gets written as a serving design |
| **Token cost per request · prompt/semantic caching** | No requests. Cost is capital: a fixed $1.11M for one run. There is nothing to cache — every token is seen once |
| **Model routing / provider fallback** | Nothing to route to. The nearest analogue — GPU-SKU fallback — is **deliberately rejected**: mixing H100 and A100 in one mesh means the slowest SKU gates every collective, so it is strictly worse than queueing |
| **Guardrails · groundedness · citations** | The output is a checkpoint, not text |
| **Prompt injection** | No prompts, no tool calls, no retrieved context. Claiming otherwise would be checklist-matching |
| **Multi-tenancy** | One run owns its mesh for 30 days. The isolation that matters is *placement* (a TP group must not share a node with another job), which is a scheduler property, not a tenancy model |

---

## 4.2 Operations and runbook

### 4.2.1 Dashboards, in priority order

| Dashboard | Panels | Alert on |
|---|---|---|
| **1. Is the run going to finish?** | Projected completion date vs deadline · measured MFU vs the 45.9% budget · tokens/day trend | Projected date slips past the deadline for 2 consecutive hours |
| **2. MFU decomposition (the diagnostic one)** | Stacked per-step ms: compute · tp_comm · pp_wait · dp_comm · optim · data_wait — each with its budgeted factor overlaid | Any factor > 1.3× its budget |
| **3. Fault economics** | Time since last interruption · interruptions this run vs the 7.2 expected · mean detection time · mean recovery time · GPU-hours lost to faults | Detection p95 > 60 s · recovery p95 > 20 min |
| **4. Straggler** | Per-rank step-time distribution (box plot over the last 100 steps) · slowest-rank identity over time | Any rank > 1.15× median for 10 consecutive steps |
| **5. Numerics health** | Loss · grad-norm with the trailing ±kσ band · loss-spike count · FP8 scaling-factor overflows · SDC probe results | Loss > kσ · any SDC probe mismatch (page) |
| **6. Checkpoint health** | Time since last verified checkpoint · upload backlog · retention bytes vs budget · **count of resumable checkpoints** | No verified checkpoint in 90 min · resumable count < 2 |
| **7. Memory** | Per-rank high-water vs the 74 GB budget, trended | High-water within 3 GB of budget |

**Deliberately not dashboard #1: GPU utilization percentage.** `nvidia-smi` utilization counts a GPU
spinning in a collective as "busy." A cluster at 99% utilization and 30% MFU is the exact failure this
platform exists to prevent, and utilization renders it as success.

### 4.2.2 The loss-spike runbook

The one runbook that matters, and it must exist **before** the run starts (§1.7 Q4).

```
TRIGGER: loss > k-sigma of the trailing 200 steps, or grad_norm above its band.

AUTOMATIC (already done by the time you are paged):
  1. The data range is LOGGED  <- unrecoverable once the cursor moves; done first
  2. The batch is SKIPPED      <- safe and cheap for a single batch
  3. If it persisted n steps: run HALTED, resumable checkpoints listed WITH COSTS

HUMAN DECISION TREE:
  Did the loss recover within a few steps of the skip?
    YES -> transient. Resume. Record the anomaly; watch for a pattern in the same shard range.
    NO  -> is grad_norm also anomalous?
      NO  (loss up, grad_norm normal)
          -> suspect DATA. Roll back to the most recent pre-onset checkpoint and SKIP
             the logged range. Cheapest option, and the data range is why it is available.
      YES (both anomalous)
          -> suspect NUMERICS or HARDWARE. Check, in this order:
             a. FP8 scaling-factor overflow counters -> if set, disable FP8 and resume
             b. XID errors and the SDC probe on every rank -> drain any suspect rank
             c. Neither -> genuine optimization instability. Roll back FURTHER than
                you think you need to (the divergence may have started before it was
                visible), and consider lowering the LR for the remainder.

COST THE OPTIONS BEFORE CHOOSING. The page includes them:
  roll back 0.6 h =    $922       roll back 8.3 h = $12,746
  continue and lose the run = up to $1.11M

ESCALATION: any rollback discarding > 24 h of training needs a second approver.
  This is a six-figure decision made at 3 a.m. by one tired person -- that is the risk
  the second approver exists to reduce.
```

### 4.2.3 On-call triage order

1. **Is the cluster stalled?** 512 idle GPUs cost $1,536/hour. Check heartbeats before anything else.
2. **Is there a loss anomaly?** Follow §4.2.2. Do **not** raise the σ threshold to silence it — that is how a divergent run gets carried to completion.
3. **Is MFU below budget?** Open dashboard #2 and profile the worst-ratio factor. **Never** respond by adding GPUs (§1.6.3).
4. **Is a rank a straggler?** Drain it. A 15% straggler costs more than the drain-and-restart.
5. **Are checkpoints healthy?** Fewer than 2 resumable checkpoints is a latent P0 — the next fault becomes unrecoverable.

### 4.2.4 Rollback

| Change | Rollback |
|---|---|
| **Base container image** | Pinned by digest per run; never applied to a running run. A cuBLAS/NCCL change alters numerics, and a mid-run change makes the loss curve incomparable across the boundary |
| **Parallelism plan** | Plans are immutable objects. A "change" is a new plan and a new placement, which means a restart from checkpoint |
| **FP8 enable/disable** | Disabling mid-run is safe (BF16 is the fallback) and creates a visible discontinuity in step time — record it, because a later MFU comparison across that boundary is otherwise nonsense |
| **NCCL timeout / heartbeat config** | Safe to change between restarts. **Never raise it to silence a flapping detector** — investigate why detection is firing |
| **Retention policy** | Loosening is safe. **Tightening must never delete a checkpoint referenced by an open anomaly** ([§3.3.3](03_lld.md)) |
| **A checkpoint discovered to be corrupt** | Manifest verification catches it on read. Keeping 3 recent means one bad checkpoint is never fatal — which is the entire reason the number is 3 and not 1 |

---

## 4.3 Common mistakes

| Mistake | Why it's wrong | Do instead |
|---|---|---|
| **Using the sparse TFLOP/s figure for peak** | H100 BF16 dense is 989 TFLOP/s; the 1,979 figure requires structured sparsity that dense LLM training does not use. It **halves your apparent MFU** and makes a good run look broken | 989 for BF16, 1,979 for FP8 dense |
| **Using NVLink's 900 GB/s spec in a comm model** | Collectives realize ~400 GB/s. Using 900 understates TP communication cost by **2.2×** — exactly enough to make an unworkable plan look fine | Measure effective ring bandwidth; treat it as an assumption (A2) and probe it at startup |
| **Letting TP cross a node boundary** | **213%** of compute time in communication versus **26.6%** inside the node — comm exceeds arithmetic, so none of it can be hidden. It presents as "training is slow," not as an error, and can run for days | `TP ≤ NVLink domain`, enforced as a `CHECK` constraint and a startup assertion |
| **Multiplying an MFU-derived step time by (1 + bubble)** | MFU **already contains** the bubble and comm residual. Double-counting gives 31.0 days instead of 29.5 — a 5% error, small enough to look plausible | Pick one model. If you use the step model, use raw kernel efficiency, not MFU |
| **Sizing memory from weights alone** | 95.3 GB of activations for a *single* un-sharded micro-batch does not fit an 80 GB GPU with zero weights | Do the per-layer activation arithmetic. Note the SwiGLU intermediates are 59% of it |
| **Concluding from that 95 GB that recompute is mandatory** | It is the reason you must **shard**, not the reason you must recompute. At TP=8/PP=8 the same activations are 11.9 GB/GPU and `none` fits fine | Compute activations *after* sharding. Then use recompute as the lever for `micro_bs > 1`, which is the free MFU win |
| **Full recompute by default** | +33% compute, which alone breaks the MFU floor | Selective recompute of the SwiGLU intermediates: 11.9 → 4.9 GB/GPU for ~+8% |
| **Running TP without sequence parallelism** | Leaves 16.1 GB/GPU of LayerNorm/dropout activations replicated across TP ranks | SP always with TP: 14.1 GB/GPU recovered at zero collective cost |
| **Leaving the NCCL watchdog at its default** | ~30 minutes of 512 idle GPUs per failure, ~7 times per run: **$9,094**. Everyone leaves it at the default | 10 min watchdog + a 10 s heartbeat. Worth ~$5,400/run at zero engineering cost |
| **Relying on the NCCL watchdog alone** | A hang may never time out at all, and then nothing fires | An independent heartbeat is the only signal for that class of fault |
| **Synchronous checkpointing** | 8.8 s blocking per checkpoint — 80× worse than async, for the cost of a background thread | Async sharded: 0.11 s device→host, then background upload |
| **Writing the checkpoint manifest first (or not at all)** | A truncated upload becomes an unbootable checkpoint discovered at the worst possible moment | Manifest **last**; it is what makes the checkpoint valid. Refuse to resume without it |
| **Forgetting the data cursor in the checkpoint** | The resumed run silently re-reads the same shards — and **looks like fast progress** | Cursor `NOT NULL` in the checkpoint; hard failure if missing; assert loss continuity at resume |
| **Adding GPUs to hit a deadline** | Costs money **and** raises the global batch, which changes the optimization. It is a different training run, not a faster one | Buy MFU: micro-batch size first (free), then FP8 (1.33×, gated on a loss check) |
| **Shipping FP8 on a throughput benchmark** | A throughput number cannot see a quality regression | Gate on validation loss vs the BF16 reference over ≥5,000 steps |
| **Giving the health monitor kill authority** | One false positive at hour 300 costs 300 hours. A monitor that can kill a run is an availability risk to the run | Drain authority, freely. Kill authority, never |
| **Reporting `nvidia-smi` utilization as progress** | A GPU spinning in a collective reads as "busy." 99% utilization at 30% MFU is precisely the failure mode | Report MFU **with its six-factor decomposition** |
| **Auto-rollback on a loss spike** | A false positive discards hours of good training automatically, and nobody knows it happened | Skip the batch automatically; escalate a persistent spike to a human with **costed** rollback options |
| **Reducing the global batch during elastic recovery** | Silently becomes a different training run wearing the same name | Raise `m` to hold `DP × m × micro_bs × seq` invariant; halt if it cannot be preserved |
| **Building a data streaming/caching tier** | The requirement is 2.2 MB/s. It solves a problem that does not exist at this scale | Say so, and spend the effort on shuffle quality and cursor determinism instead |

---

## 4.4 Interview follow-ups

**Q: "You have 512 H100s and 30 days. Walk me through sizing."**
Three numbers first. `N` = 70.55B from the real config, not the `12Lh²` shortcut, because memory is the
question. `C` = 6ND = 5.93×10²³. Then the one that decides everything: `MFU_required = C/(G·PEAK·T)` =
**45.2%**. So the deadline is not a GPU-count requirement, it is an MFU requirement — and published
large-run MFU is 38–43%. Before drawing anything I would say: *this deadline needs above-typical MFU, and
here is the budget that gets there with 0.7 points to spare.* Then the memory arithmetic: 16N = 1,129 GB
kills plain DDP; 95.3 GB of activations for one micro-batch kills no-recompute. Only then the mesh.

**Q: "Why TP=8 exactly?"**
Because 8 is the NVLink domain on an H100 node, and TP is the highest-frequency, least-hideable
communication in the design — 4 all-reduces of a 67 MB tensor per layer per micro-step. Over NVLink at
an *effective* 400 GB/s that is 11.7 ms against **44.2 ms of pure matmul time, so 26.6%.** Over
InfiniBand at 50 GB/s it is 94 ms — **213% of compute: communication exceeds arithmetic, so no amount
of overlap can hide it.** (And be careful with the denominator: against per-micro-step *wall* time the
intra-node figure reads a flattering 20.1%, but wall time is MFU-derived and MFU already contains the
comm penalty — that is circular.) It is an 8× cliff at the node boundary, not a gradient.
And I would flag the trap: using NVLink's 900 GB/s spec instead of the ~400 GB/s a collective actually
realizes understates that by 2.2×, which is enough to make TP=16 look fine on a spreadsheet.

**Q: "MFU comes in at 38% instead of 45.9%. What do you do?"**
Open the decomposition, not the purchase order. The budget is six multiplicative factors, so I rank them
by measured/budgeted and profile the worst. In practice the order I'd expect: kernel efficiency (the
×0.62, the largest and least certain — and the cheapest fix is raising micro-batch from 1 to 4, which the
memory budget already allows for free), then `data_wait`, then TP comm overlap. What I would **not** do is
add GPUs: 512→580 costs $140k *and* raises the global batch, which changes the optimization. The
principled lever is FP8 on the MLP GEMMs — 82% of each layer, 1.33× blended, zero extra cost, gated on a
validation-loss check because a throughput benchmark cannot see a quality regression.

**Q: "What's the most expensive line of configuration in the platform?"**
The NCCL watchdog timeout. Cluster MTBF at 512 GPUs is 97.7 hours, so a 708-hour run sees ~7.2
interruptions. At the ~30-minute default, each one idles 512 GPUs for 30 minutes before anything notices:
5.9 hours lost, **$9,094**. With a 10-second heartbeat and a 10-minute watchdog it is 2.4 hours, $3,712.
That is ~$5,400 per flagship run for a config change, and almost everyone leaves it at the default. I'd
also keep the heartbeat *in addition to* the watchdog, because an NCCL hang may never time out at all —
and then the heartbeat is the only signal that exists.

**Q: "One failure mode you'd volunteer?"**
The loss spike at hour 300. Loss goes 2.1 → 6.8 and it may or may not recover. What makes it the
interesting one is that the correct response is a judgement call worth six figures — roll back 0.6 hours
for $922, roll back 8.3 hours for $12,746, or continue and risk $1.11M — so the platform's job is to make
that decision *possible*, not to make it. Concretely: log the exact data range **before** acting (the
cursor moves on and it becomes unrecoverable), skip the batch automatically, and on persistence halt and
page with the rollback options **costed**. And retention must never prune a checkpoint referenced by an
open anomaly, or the option vanishes while someone is still deciding. I deliberately do not auto-roll
back: a false positive would discard good training automatically and silently.

**Q: "Why not just use FSDP on all 512 GPUs?"**
It's the right instinct at 8 GPUs and it breaks at 512 for two reasons. Comm: ZeRO-3 all-gathers each
layer's parameters, and at DP=512 that traffic crosses InfiniBand for a 70B model every layer, every
step — comm dominates. Optimization: the global batch becomes `512 × micro_bs × 4096`, which is far past
where large-batch training still helps, so you'd have to cut micro-batch to 1 and still be too large.
FSDP is right *within* the DP group — DP=8 here — which is exactly what the design does.

**Q: "How do you know a checkpoint is good?"**
A per-shard hash manifest, written **last**. The manifest is what makes the checkpoint valid: if the
upload truncates, you get a visibly incomplete checkpoint rather than a silently unbootable one, and
resume returns `409 manifest_incomplete` rather than loading garbage. Then three things are asserted at
resume: manifest verified, data cursor present, and loss continuity against the recorded
`loss_at_step`. The cursor one matters most — a resume that loses it silently re-reads the same shards
and *looks like fast progress*.

**Q: "What breaks first at 10× GPUs?"**
Not throughput — **fault rate.** At 5,120 GPUs the cluster MTBF falls to 9.8 hours, so a run sees ~72
interruptions instead of 7. Restart speed, not MFU, becomes the thing the platform is worth. Elastic DP
moves from P1 to mandatory, checkpoint cadence tightens to ~10 minutes, and DP needs hierarchical
reduction trees. And a research problem appears: the global batch grows 10× unless `m` shrinks, so batch
scaling stops being an infra decision.

**Q: "Is there a scenario where you'd tell them not to build this?"**
Yes, and it's the first thing in my requirements. If "30 days" is really a proxy for "before the next GPU
generation ships," then waiting beats a 10% MFU win at zero engineering cost. If it's a budget boundary,
the honest move is to reduce `D` below Chinchilla-optimal and take a known loss penalty rather than
pretend the arithmetic works. The design changes completely depending on which it is, and it is not a
technical question — so I'd ask it before drawing a single box.

---

## 4.5 Glossary

| Term | Meaning | Where it bites |
|---|---|---|
| **1F1B / interleaved 1F1B** | Pipeline schedules; interleaved uses `v` virtual stages | v=2, m=128 → 2.7% bubble vs 17.9% at m=32 |
| **`16N` rule** | 16 bytes/param of model + optimizer state (BF16 + Adam) | 1,129 GB = 14.1 H100s before activations |
| **All-reduce / reduce-scatter / all-gather** | The collectives; ring all-reduce moves ~2S of bus volume | 117 MB × 40 per micro-step for TP=8 |
| **Bubble** | Pipeline idle time: `(p−1)/(m+p−1)`, or `(p−1)/(v·m)` | Needs `m ≥ 4p` to stay under ~6% |
| **Chinchilla-optimal** | `D ≈ 20N`; `C_optimal = 120N²` | Sizes the 1.4T-token budget |
| **Context parallelism** | Sharding the sequence dimension across ranks | Needed at 10× sequence length |
| **Data cursor** | `{shard, offset, epoch, perm_seed}` | Losing it silently re-trains the same shards |
| **DP / TP / PP / EP** | Data / tensor / pipeline / expert parallelism | The hierarchy is set by which link the traffic crosses |
| **FlashAttention** | Tiled attention; never materializes the `s×s` matrix | Removes the `O(s²)` activation term |
| **FP8 (E4M3/E5M2)** | 8-bit float; ~2× peak on H100 | 1.33× blended on MLP GEMMs; gated on a loss check |
| **FSDP / ZeRO-3** | Shard params + grads + optimizer state | Right *within* the DP group, wrong at DP=512 |
| **Gang scheduling** | All ranks start together or none do | Partial starts waste the cluster |
| **Global batch** | `DP × m × micro_bs × seq` tokens per step | **Held invariant** through elastic recovery |
| **HFU vs MFU** | HFU counts recompute FLOPs; MFU doesn't | Report MFU — HFU flatters a recompute-heavy config |
| **Manifest** | Per-shard hash file, written **last** | What makes a checkpoint valid |
| **MFU** | Achieved ÷ peak FLOP/s | The currency; 45.2% required, 45.9% budgeted |
| **Micro-batch / `m`** | The pipeline's unit / how many per step | `micro_bs` 1→4 is the cheapest MFU lever |
| **NCCL watchdog** | Collective timeout, ~30 min by default | Worth ~$5,400/run to lower |
| **NVLink domain** | GPUs with NVLink between them — 8 per H100 node | **The number that fixes `TP ≤ 8`** |
| **Selective recompute** | Recompute only the SwiGLU intermediates | 11.9 → 4.9 GB/GPU at TP=8/PP=8 (95.3 → 38.9 GB un-sharded) for ~+8% compute; the lever for `micro_bs > 1` |
| **Sequence parallelism** | Shards the LN/dropout regions TP leaves replicated | Free 14.1 GB/GPU |
| **Silent data corruption (SDC)** | Wrong numbers, no error | Hardest fault class; possibly undetectable at the margin |
| **Straggler** | One slow rank gating every collective | 1.15× median for 10 steps → drain |
| **XID error** | NVIDIA driver fault code | A primary health signal |

---

← [03_lld.md](03_lld.md) · [system README](README.md) · → [folder README](../README.md)
