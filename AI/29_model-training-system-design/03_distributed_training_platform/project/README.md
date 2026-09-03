# Runnable core — Distributed Training Platform

The tool a training-infra engineer actually writes *before* asking for a cluster.

```bash
pip install torch
python run.py                       # ~3 s including the torch measurements
python run.py --no-measure          # pure arithmetic, no torch, <1 s
python run.py --gpus 256            # watch the deadline stop closing
python run.py --model 8b --gpus 64
python run.py --csv plans.csv       # every feasible plan
python run.py --help
```

## What it actually runs

| Part | What it does | Design section |
|---|---|---|
| **1 · Params + FLOPs** | The parameter formula, **validated against a real `nn.Module`'s parameter count** at reduced scale | [`03_lld.md`](../03_lld.md) §3.3.1 |
| **2 · Memory** | The `16N` rule, the per-layer activation split, and **activation bytes MEASURED** via `saved_tensors_hooks` on a real transformer layer, plus real `torch.utils.checkpoint` timing | [`00_concepts.md`](../00_concepts.md) §3 |
| **3 · Planner** | Enumerates `(TP, PP, DP, micro_bs, m, recompute)`, **rejects with reasons and arithmetic**, ranks survivors, ties broken on memory headroom | [`03_lld.md`](../03_lld.md) §3.3.1 |
| **4 · MFU budget** | Six multiplicative factors, the required-MFU inversion, the **double-count trap**, and the shortfall-attribution table | [`03_lld.md`](../03_lld.md) §3.3.2 |
| **5 · Fault economics** | Checkpoint cadence, retention cost as a share of the compute budget, and the **$5,474 timeout** | [`01_requirements.md`](../01_requirements.md) §1.6.4–5 |

## Four things to look at in the output

1. **`MFU REQUIRED for the 30-day SLO = 45.2%`.** Run it with `--gpus 256` and it becomes 90.3% — impossible. That one line reframes a deadline as an MFU requirement, which is the whole design.
2. **The `REJECTED` list.** More useful than the feasible one: `TP=16 spans 2 nodes; TP comm would be 456% of compute vs 57% intra-node`. A planner that hides its reasoning invites people to route around constraints instead of arguing with them.
3. **The plans differ by <1% in days and 4× in DP headroom.** So the choice among them is operational — spare HBM to raise `micro_bs` later, spare DP replicas for elastic recovery and cross-replica SDC screening — not a throughput choice. The script says so.
4. **The double-count trap**, shown three ways: FLOP model, step model, and step model × `(1 + bubble)` — the last being ~3% too slow because MFU already contains the bubble.

## Three design errors this code found

Written honestly, because all three survived the prose:

1. **The TP-comm figure divided by the wrong denominator.** The docs said "19.7% of compute", derived by dividing comm time by an *MFU-derived* wall time. But MFU already contains the comm penalty, so that is partly circular — **the same double-count trap §4 warns about.** Against pure matmul time the real figure is **26.6% intra-node and 213% inter-node**. Fixed throughout; the script now prints all three framings side by side.
2. **"95.3 GB of activations forces the recompute policy" was a misread.** 95.3 GB is what *one un-sharded GPU* would need — it is the reason you must **shard**. At TP=8/PP=8/SP the same activations are **11.9 GB/GPU** and `none` fits fine. Recompute's real role is as the lever that buys `micro_bs > 1` (11.9 → 4.9 GB/GPU), and micro-batch is the free MFU win. Reframed in [`00_concepts.md §3.3`](../00_concepts.md) and [`§1.6.1`](../01_requirements.md).
3. **The planner was missing two constraints that the design's own requirements imply.** `pp` must divide the layer count (PP=32 gives 2.5 layers/stage with L=80, yet the mesh arithmetic still checks out), and `DP ≥ 2` is required by **FR-13** (cross-replica gradient-norm comparison for SDC screening) and **FR-14** (elastic recovery). Without them the planner's top pick was TP8/PP64/**DP1** — optimal on memory and throughput, operationally indefensible. Added as edge cases 3b and 3c in [`§3.6`](../03_lld.md).

Also a plain factor-of-2 bug in the full-recompute term (10.7 vs the correct 5.37 GB), caught by making the sharded-vs-replicated split explicit.

## Honest limitations

- **The perf model is analytic, not measured.** Comm times come from a ring-all-reduce cost model with an assumed 400 GB/s effective NVLink bus; real NCCL has protocol, chunking and topology effects. Assumption A2, and the design says to probe it at startup rather than trust it.
- **The measured activation bytes are ~2.7× the analytic model** — and the script explains why rather than hiding it. The analytic model counts the tensors a *fused* implementation must keep; a stock `nn.Linear`/`LayerNorm` stack also saves normalization statistics and intermediates a fused kernel wouldn't. **That gap is the value of fused kernels**, and it is why the design carries a ≥6 GB safety margin instead of trusting the formula.
- **Recompute timing is measured on CPU**, where the compute/memory balance differs from an H100. The sign and rough magnitude transfer; the exact +33% does not.
- `KERNEL_EFF = 0.62` is assumption A4 — the largest and least certain factor in the MFU budget, and the design says to measure it on a 50-step benchmark before accepting a deadline.

## What a real platform adds

| Here | In production |
|---|---|
| Analytic comm model | NCCL bandwidth probes on all three mesh dimensions at startup ([§2.3](../02_hld.md)) |
| A ranked list | Gang scheduler with topology awareness; TP groups pinned inside a node, asserted before step 1 |
| `Plan` dataclass | `parallelism_plans` table with `tp_within_nvlink` and `fits_memory` as `CHECK` constraints ([§3.1.1](../03_lld.md)) |
| Printed fault arithmetic | 10 s heartbeats, a 10-min NCCL watchdog, drain-not-kill authority, elastic DP holding the global batch invariant ([§3.3.4](../03_lld.md)) |
| Retention arithmetic | A retention job that never prunes a checkpoint referenced by an open anomaly ([§3.3.3](../03_lld.md)) |

---

← [system README](../README.md) · [00_concepts.md](../00_concepts.md) · [03_lld.md](../03_lld.md)
