# 03 · Sample project — ML Systems & Training-Infrastructure Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

🏗️ **Then design the platform version:** [Distributed Training Platform](../../29_model-training-system-design/03_distributed_training_platform/README.md) — full Requirements → HLD → LLD for the system a lab would actually run this on ([folder index](../../29_model-training-system-design/README.md)).

> ▶ **Run the real code:** `pip install torch && python project/run.py` (~1-2 min) -- runs the actual benchmark sweep across 3 model sizes (small/medium/large), prints ms/step + speedup + peak-memory tables, and can export results to CSV plus a real `torch.profiler` op-level breakdown with `--csv`/`--profile`. See [`project/`](project/) for the full source.

## 🎯 What you'll build
A **benchmark report**: take a plain training loop, measure its throughput precisely, then apply three standard systems optimizations one at a time and measure the delta each one buys — the exact "squeeze throughput" work this job does at massive scale, just on one machine.

## 🧠 Why this mirrors the real job
- "Squeeze throughput: kernels/CUDA/Triton, memory, communication overlap" → you'll apply the single-GPU analogues (AMP, `torch.compile`, gradient accumulation) and *measure*, not guess.
- "Build the training platform other engineers run experiments on" → the deliverable is a benchmark table someone else could act on, not just a number you remember.
- Systems engineering here is a discipline of **measure → change one thing → measure again**, not intuition.

## 🧰 Prerequisites
- Python, PyTorch (GPU strongly preferred — CPU works but gains will be smaller/noisier).
- ~3–4 hours.

## 🧰 Tools, libraries & skills used here
- **PyTorch performance APIs**: `torch.autocast`/`torch.amp.GradScaler` (mixed precision), `torch.compile` (graph compilation/kernel fusion), manual gradient accumulation — the exact primitives systems engineers reach for before touching custom CUDA.
- **Benchmarking methodology**: warmup iterations before timing, `torch.cuda.synchronize()` around GPU timing (a very common correctness bug when it's omitted), and reporting ms/step + samples/sec together rather than a single number.
- **What a real infra team adds on top**: `torch.profiler`/NVIDIA Nsight Systems for kernel-level profiling, DeepSpeed/Megatron-LM/FSDP for multi-GPU sharding, NCCL for cross-GPU communication, and Triton for writing custom fused kernels when standard ops aren't fast enough.
- **Core skill**: never trusting a speedup number without knowing *why* it happened (compute-bound vs memory-bound, and which hardware you measured on) — the difference between a systems engineer and someone who just ran a script.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| torch | pip install torch | `torch.autocast`/`torch.amp.GradScaler` (mixed precision), `torch.compile`, `AdamW`, CUDA sync calls |
| time (stdlib) | built in | wall-clock benchmarking with warmup iterations |

## 🪜 Step-by-step

### 1. Baseline loop + a real timer
```python
import torch, torch.nn as nn, time

device = "cuda" if torch.cuda.is_available() else "cpu"
model = nn.Sequential(
    nn.Linear(1024, 4096), nn.ReLU(),
    nn.Linear(4096, 4096), nn.ReLU(),
    nn.Linear(4096, 1024),
).to(device)
opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
x = torch.randn(256, 1024, device=device)
y = torch.randn(256, 1024, device=device)

def benchmark(step_fn, n_warmup=10, n_iters=50):
    for _ in range(n_warmup):
        step_fn()
    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(n_iters):
        step_fn()
    if device == "cuda":
        torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    return dt / n_iters  # seconds/step

def baseline_step():
    opt.zero_grad()
    loss = nn.functional.mse_loss(model(x), y)
    loss.backward()
    opt.step()

baseline_s_per_step = benchmark(baseline_step)
print(f"baseline: {baseline_s_per_step*1000:.2f} ms/step, "
      f"{x.shape[0]/baseline_s_per_step:.0f} samples/sec")
```

### 2. Optimization 1 — mixed precision (AMP)
```python
scaler = torch.cuda.amp.GradScaler(enabled=(device == "cuda"))

def amp_step():
    opt.zero_grad()
    with torch.autocast(device_type=device, dtype=torch.float16, enabled=(device == "cuda")):
        loss = nn.functional.mse_loss(model(x), y)
    scaler.scale(loss).backward()
    scaler.step(opt)
    scaler.update()

amp_s_per_step = benchmark(amp_step)
```

### 3. Optimization 2 — `torch.compile`
```python
compiled_model = torch.compile(model)

def compiled_step():
    opt.zero_grad()
    loss = nn.functional.mse_loss(compiled_model(x), y)
    loss.backward()
    opt.step()

compiled_s_per_step = benchmark(compiled_step)
```

### 4. Optimization 3 — gradient accumulation (simulate a bigger effective batch on the same memory)
```python
micro_x, micro_y = x.chunk(4), y.chunk(4)

def grad_accum_step():
    opt.zero_grad()
    for mx, my in zip(micro_x, micro_y):
        loss = nn.functional.mse_loss(model(mx), my) / 4
        loss.backward()
    opt.step()

accum_s_per_step = benchmark(grad_accum_step)
```

### 5. Tabulate and explain, don't just report numbers
| Config | ms/step | samples/sec | Δ vs baseline |
|---|---|---|---|
| baseline | | | — |
| + AMP | | | |
| + torch.compile | | | |
| + grad accumulation (4x effective batch) | | | |

For each row, write **one sentence on why** the number moved (or didn't) — e.g. "AMP gave ~1.4x because this workload is compute-bound on matmuls, which benefit most from fp16 tensor cores" or "no GPU available, so AMP/compile show little/no gain — this is expected and worth stating, not hiding."

## ✅ Deliverable
The benchmark table + one paragraph per optimization explaining the mechanism (not just the number) + a recommendation for which combination you'd ship, and why.

## ⏱️ Time box
An afternoon.

## 🏗️ Scale this to a real lab — the system design

This project measures one GPU. The job is 512 of them staying in productive lockstep for 30 days, and
at that scale **the deadline stops being a GPU-count question and becomes an MFU question.**
[`29/03 · Distributed Training Platform`](../../29_model-training-system-design/03_distributed_training_platform/README.md)
is the full Requirements → HLD → LLD.

**The inversion to internalize:**

```
MFU_required = C / (G · PEAK · T)
             = 5.926e23 / (512 × 989e12 × 30 × 86400)
             = 45.2%

MFU budget -- MULTIPLICATIVE, every inefficiency is a factor:
  kernel efficiency (real shapes, FlashAttention)  ×0.62
  TP comm residual after overlap                   ×0.92
  PP bubble (interleaved 1F1B, m=128, v=2)         ×0.95
  DP reduce-scatter/all-gather residual            ×0.97
  non-matmul ops + optimizer step                  ×0.92
  data stalls + straggler jitter                   ×0.95
                                                   ───── = 45.9%
```

**0.7 points of headroom**, against a published-practice range of 38–43%. And note what the budget is
*for*: it is the same "measure → change one thing → measure again" discipline as step 5 of this project,
but the table also tells you **which factor to profile** when measured MFU comes in at 38% — which a
single number never can.

| What this project measures | What the platform adds | Why |
|---|---|---|
| AMP, `torch.compile`, grad accumulation on one GPU | **A 3-D mesh: TP=8 × PP=8 × DP=8** | TP is the highest-frequency, least-hideable comm. Inside the node it is **26.6% of compute**; across a node boundary **213%** — communication exceeds arithmetic, so overlap cannot help. `TP ≤ 8` is the NVLink domain size, not a heuristic |
| Peak memory from `torch.cuda.max_memory_allocated` | **The `16N` rule and the activation split** | 16 bytes/param of model + optimizer state = **1,129 GB for 70B — 14.1 H100s before a single activation.** Plain DDP is impossible; sharding is the precondition |
| — | **Selective recompute + sequence parallelism** | 95.3 GB of activations is the reason to **shard**, not to recompute — at TP=8/PP=8 it's 11.9 GB/GPU. Recompute's real role is buying `micro_bs > 1`, which improves the largest MFU factor. SP separately recovers 14.1 GB/GPU for free |
| A speedup number | **The MFU attribution table** | "MFU is 38%" is not actionable. "`stalls_stragglers` is 0.88× its budget" is |
| A script that runs to completion | **Async sharded checkpointing** (0.11 s blocking vs 8.8 s) + retention policy | Keeping every checkpoint costs **3.4% of the entire compute budget** in storage |
| — | **Fault economics** | Cluster MTBF is 97.7 h, so a 708 h run sees ~7.4 interruptions. NCCL's ~30-min default watchdog costs **$9,248** of idle cluster per run; a 60-s heartbeat costs $3,775. **~$5,474 from one config value, at zero engineering cost** |
| — | **Straggler detection** | One rank at 1.15× median gates every collective, so it gates all 512 GPUs — the most under-appreciated large-scale failure |

**Two traps this project's methodology directly prepares you for, and one it can't:**

- You already know to `torch.cuda.synchronize()` before timing. The distributed analogue is the
  **double-count trap**: multiplying an MFU-derived step time by `(1 + bubble)` when MFU *already
  contains* the bubble. It gives 31.0 days instead of 29.5 — small enough to look plausible.
- You already report "what hardware, and why the number moved." The design's version is refusing to use
  H100's **1,979 TFLOP/s sparse** figure as peak (dense is 989) and refusing NVLink's 900 GB/s spec in a
  collective model (effective ring bus is ~400) — the latter understates comm cost by 2.2×, enough to
  make an unworkable plan look fine.
- What a single GPU cannot show you: **the loss spike at hour 300.** Loss goes 2.1 → 6.8 and the correct
  response is a judgement call worth six figures. The platform's job is to make that decision
  *possible* — log the data range before acting, retain a pre-onset checkpoint, and present rollback
  options **with costs** — not to automate it.

**Run the platform's core:**

```bash
python ../../29_model-training-system-design/03_distributed_training_platform/project/run.py
python ../../29_model-training-system-design/03_distributed_training_platform/project/run.py --gpus 256
```

It's the parallelism planner: enumerates the `(TP, PP, DP, micro_bs, m, recompute)` space and **rejects
plans with their arithmetic attached**. Pass `--gpus 256` and watch `MFU REQUIRED` jump to 90.3%.

## 🔁 Where to go deeper
[`AI/04_llm-serving-and-inference-optimization`](../../04_llm-serving-and-inference-optimization/README.md) — same profiling mindset applied to inference (KV-cache, batching, quantization) · [`DL/02_pytorch`](../../../DL/02_pytorch/README.md) — framework internals · [`Shared/02_mlops`](../../../Shared/02_mlops/README.md) — ops/reliability.

**Design-level:** [`29/03_distributed_training_platform`](../../29_model-training-system-design/03_distributed_training_platform/README.md) — the platform version of this project, with quantified NFRs, rejected alternatives, failure modes and runnable code.
