"""
Sample project — ML Systems & Training-Infrastructure Engineer
Benchmarks a training step across THREE model sizes, measures the delta from
three standard systems optimizations (AMP, torch.compile, gradient
accumulation), profiles peak memory, and dumps a detailed op-level breakdown
with torch.profiler for the biggest model -- the actual toolkit a systems
engineer reaches for before touching custom CUDA.

Run:  python run.py
      python run.py --sizes small medium          (skip the large model, faster)
      python run.py --csv bench.csv --profile      (export results + profiler trace)
Dependencies:
  - torch (pip install torch) -- autocast/GradScaler, torch.compile, AdamW, torch.profiler
  - time (stdlib) -- perf_counter() timing with warmup iterations
  - resource (stdlib, POSIX only) -- peak RSS memory measurement
  - argparse, csv (stdlib) -- CLI config and results export
"""
import argparse
import csv
import sys
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    import resource
    HAVE_RESOURCE = True
except ImportError:
    HAVE_RESOURCE = False  # not available on Windows

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODEL_SIZES = {
    "small": (512, 512),
    "medium": (1024, 2048),
    "large": (2048, 4096),
}


def build_model(in_dim: int, hidden: int):
    torch.manual_seed(0)
    return nn.Sequential(
        nn.Linear(in_dim, hidden), nn.ReLU(),
        nn.Linear(hidden, hidden), nn.ReLU(),
        nn.Linear(hidden, in_dim),
    ).to(DEVICE)


def peak_memory_mb() -> float:
    """Peak resident set size in MB since process start (CPU) or peak CUDA
    allocation (GPU) -- the two real memory metrics systems engineers watch."""
    if DEVICE == "cuda":
        return torch.cuda.max_memory_allocated() / (1024 ** 2)
    if HAVE_RESOURCE:
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # ru_maxrss units differ by OS: bytes on macOS, KB on Linux.
        return raw / (1024 * 1024) if sys.platform == "darwin" else raw / 1024
    return float("nan")


def benchmark(step_fn, n_warmup=5, n_iters=30):
    for _ in range(n_warmup):
        step_fn()
    if DEVICE == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    for _ in range(n_iters):
        step_fn()
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / n_iters
    return dt, peak_memory_mb()


def benchmark_size(size_name: str, in_dim: int, hidden: int, csv_writer=None):
    print(f"\n=== Model size: {size_name} (in_dim={in_dim}, hidden={hidden}) ===")
    x = torch.randn(128, in_dim, device=DEVICE)
    y = torch.randn(128, in_dim, device=DEVICE)
    results = {}

    model = build_model(in_dim, hidden)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)

    def baseline_step():
        opt.zero_grad()
        loss = F.mse_loss(model(x), y)
        loss.backward()
        opt.step()

    results["baseline"] = benchmark(baseline_step)

    model_amp = build_model(in_dim, hidden)
    opt_amp = torch.optim.AdamW(model_amp.parameters(), lr=1e-3)
    scaler = torch.amp.GradScaler(enabled=(DEVICE == "cuda"))

    def amp_step():
        opt_amp.zero_grad()
        with torch.autocast(device_type=DEVICE, dtype=torch.bfloat16, enabled=True):
            loss = F.mse_loss(model_amp(x), y)
        scaler.scale(loss).backward()
        scaler.step(opt_amp)
        scaler.update()

    results["+ AMP (autocast bf16)"] = benchmark(amp_step)

    try:
        model_c = torch.compile(build_model(in_dim, hidden))
        opt_c = torch.optim.AdamW(model_c.parameters(), lr=1e-3)

        def compiled_step():
            opt_c.zero_grad()
            loss = F.mse_loss(model_c(x), y)
            loss.backward()
            opt_c.step()

        results["+ torch.compile"] = benchmark(compiled_step)
    except Exception as e:
        results["+ torch.compile"] = (None, None)
        print(f"torch.compile unavailable/failed on this machine: {e}")

    model_ga = build_model(in_dim, hidden)
    opt_ga = torch.optim.AdamW(model_ga.parameters(), lr=1e-3)
    micro_x, micro_y = x.chunk(4), y.chunk(4)

    def grad_accum_step():
        opt_ga.zero_grad()
        for mx, my in zip(micro_x, micro_y):
            loss = F.mse_loss(model_ga(mx), my) / 4
            loss.backward()
        opt_ga.step()

    results["+ grad accumulation (4x)"] = benchmark(grad_accum_step)

    print(f"{'config':<28}{'ms/step':>10}{'samples/sec':>14}{'x vs baseline':>16}{'peak mem (MB)':>16}")
    base_s = results["baseline"][0]
    for name, (s, mem) in results.items():
        if s is None:
            print(f"{name:<28}{'n/a':>10}")
            continue
        speedup = base_s / s
        print(f"{name:<28}{s * 1000:10.2f}{x.shape[0] / s:14.0f}{speedup:16.2f}{mem:16.1f}")
        if csv_writer:
            csv_writer.writerow([size_name, name, s * 1000, x.shape[0] / s, speedup, mem])

    return model  # return the baseline-sized model for the optional profiler pass


def run_profiler(model, in_dim: int):
    """A torch.profiler pass -- the actual op-level tool a systems engineer
    reaches for once a benchmark number alone isn't enough to explain WHY."""
    x = torch.randn(128, in_dim, device=DEVICE)
    y = torch.randn(128, in_dim, device=DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)

    with torch.profiler.profile(
        activities=[torch.profiler.ProfilerActivity.CPU]
        + ([torch.profiler.ProfilerActivity.CUDA] if DEVICE == "cuda" else []),
    ) as prof:
        for _ in range(5):
            opt.zero_grad()
            loss = F.mse_loss(model(x), y)
            loss.backward()
            opt.step()

    print("\n=== torch.profiler: top 8 ops by CPU time (largest model) ===")
    print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=8))


def main():
    parser = argparse.ArgumentParser(description="Training-step systems benchmark")
    parser.add_argument("--sizes", nargs="+", choices=list(MODEL_SIZES), default=list(MODEL_SIZES))
    parser.add_argument("--csv", default=None, help="write per-config results to this CSV path")
    parser.add_argument("--profile", action="store_true", help="also run a torch.profiler pass")
    args = parser.parse_args()

    print(f"device: {DEVICE}")
    if DEVICE == "cpu" and HAVE_RESOURCE:
        print("(CPU peak-mem column is the process's cumulative peak RSS since start, not a "
              "per-config delta -- it only ever goes up. On CUDA it correctly resets per-config "
              "via torch.cuda.reset_peak_memory_stats().)")
    elif not HAVE_RESOURCE:
        print("(peak memory reporting unavailable on this platform -- will show as nan)")

    csv_file = open(args.csv, "w", newline="") if args.csv else None
    writer = None
    last_model = None
    last_in_dim = None
    try:
        if csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["model_size", "config", "ms_per_step", "samples_per_sec", "speedup_vs_baseline", "peak_mem_mb"])

        for size_name in args.sizes:
            in_dim, hidden = MODEL_SIZES[size_name]
            last_model = benchmark_size(size_name, in_dim, hidden, writer)
            last_in_dim = in_dim
    finally:
        if csv_file:
            csv_file.close()
            print(f"\nresults written to {args.csv}")

    if args.profile and last_model is not None:
        run_profiler(last_model, last_in_dim)

    print("\nNote: on CPU, AMP/compile gains are typically small or negative -- the real "
          "payoff shows up on GPU tensor cores. That's a legitimate systems-engineering "
          "finding, not a bug: always report the hardware AND model size you measured on, "
          "since the best config for 'small' is not necessarily the best for 'large'.")


if __name__ == "__main__":
    main()
