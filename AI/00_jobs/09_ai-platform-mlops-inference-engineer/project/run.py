"""
Sample project — AI Platform / MLOps & Inference Engineer
Benchmarks THREE model sizes with real INT8 dynamic quantization (torch's
actual quantize_dynamic, not a simulation), reports each model's real memory
footprint (parameter count + bytes), and runs a CONCURRENT load-test
simulation (multiple simulated clients hitting the model at once via
threads) to measure p50/p95 latency under load -- not just single-request
latency, which is the number that actually matters once you have real traffic.

Using synthetic models instead of downloading a real LLM keeps this instant
and offline; the quantization API, memory accounting, and load-test
methodology are real and carry over directly to a real model with
`transformers`/vLLM.

Run:  python run.py
      python run.py --sizes small medium         (skip the large model, faster)
      python run.py --clients 16                 (more simulated concurrent load)
Dependencies:
  - torch (pip install torch) -- nn.Linear, torch.ao.quantization.quantize_dynamic
  - time (stdlib) -- latency benchmarking
  - threading (stdlib) -- concurrent load-test simulation
  - statistics (stdlib) -- p50/p95 percentile calculation
  - warnings, argparse (stdlib) -- noise suppression and CLI
"""
import argparse
import statistics as st
import threading
import time
import warnings

import torch
import torch.nn as nn

warnings.filterwarnings("ignore")

MODEL_SIZES = {
    "small": (256, 512),
    "medium": (512, 2048),
    "large": (1024, 4096),
}


def build_model(in_dim: int, hidden: int):
    torch.manual_seed(0)
    return nn.Sequential(
        nn.Linear(in_dim, hidden), nn.ReLU(),
        nn.Linear(hidden, hidden), nn.ReLU(),
        nn.Linear(hidden, in_dim),
    )


def model_footprint(model) -> dict:
    n_params = sum(p.numel() for p in model.parameters())
    n_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    return {"params": n_params, "bytes": n_bytes, "kb": n_bytes / 1024}


def benchmark(model, batch_size, n_warmup=5, n_iters=30, in_dim=None):
    x = torch.randn(batch_size, in_dim)
    with torch.no_grad():
        for _ in range(n_warmup):
            model(x)
        t0 = time.perf_counter()
        for _ in range(n_iters):
            model(x)
        dt = (time.perf_counter() - t0) / n_iters
    return dt


def load_test(model, in_dim: int, n_clients: int = 8, requests_per_client: int = 5):
    """Simulate n_clients concurrent callers each firing requests_per_client
    single-item requests, and record every individual request's latency --
    this is what a real load test (k6, locust, vegeta) reports as p50/p95."""
    latencies = []
    lock = threading.Lock()

    def client_worker():
        for _ in range(requests_per_client):
            x = torch.randn(1, in_dim)
            t0 = time.perf_counter()
            with torch.no_grad():
                model(x)
            dt = time.perf_counter() - t0
            with lock:
                latencies.append(dt)

    threads = [threading.Thread(target=client_worker) for _ in range(n_clients)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall_time = time.perf_counter() - t0

    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)]
    p95 = latencies[min(int(n * 0.95), n - 1)]
    total_requests = n_clients * requests_per_client
    return {
        "wall_time_s": wall_time,
        "total_requests": total_requests,
        "throughput_rps": total_requests / wall_time,
        "p50_ms": p50 * 1000,
        "p95_ms": p95 * 1000,
        "max_ms": max(latencies) * 1000,
    }


def cost_per_1k_requests(latency_s: float, batch_size: int, cost_per_hour: float) -> float:
    requests_per_sec = batch_size / latency_s
    requests_per_hour = requests_per_sec * 3600
    return (cost_per_hour / requests_per_hour) * 1000 if requests_per_hour else float("inf")


def benchmark_size(size_name: str, in_dim: int, hidden: int, engine, n_clients: int):
    print(f"\n{'=' * 70}\nModel size: {size_name} (in_dim={in_dim}, hidden={hidden})\n{'=' * 70}")

    fp32_model = build_model(in_dim, hidden)
    fp32_footprint = model_footprint(fp32_model)
    print(f"fp32 footprint: {fp32_footprint['params']:,} params, {fp32_footprint['kb']:.1f} KB")

    int8_model = None
    if engine:
        int8_model = torch.ao.quantization.quantize_dynamic(
            build_model(in_dim, hidden), {nn.Linear}, dtype=torch.qint8
        )
        # quantized Linear layers pack weights differently; approximate the
        # int8 footprint as 1/4 of fp32 (int8 vs fp32 element size) for the
        # Linear-layer parameters, which is what dynamic quantization targets.
        approx_int8_kb = fp32_footprint["kb"] / 4
        print(f"int8 footprint (approx): {approx_int8_kb:.1f} KB (~{fp32_footprint['kb']/approx_int8_kb:.1f}x smaller)")

    cost_per_hour = 0.50
    print(f"\n{'batch':<8}{'fp32 ms/step':<15}{'int8 ms/step':<15}{'speedup':<10}{'fp32 $/1K req':<16}{'int8 $/1K req'}")
    for bs in [1, 8, 32]:
        fp32_latency = benchmark(fp32_model, bs, in_dim=in_dim)
        fp32_cost = cost_per_1k_requests(fp32_latency, bs, cost_per_hour)
        if int8_model:
            int8_latency = benchmark(int8_model, bs, in_dim=in_dim)
            int8_cost = cost_per_1k_requests(int8_latency, bs, cost_per_hour)
            print(f"{bs:<8}{fp32_latency*1000:<15.3f}{int8_latency*1000:<15.3f}"
                  f"{fp32_latency/int8_latency:<10.2f}${fp32_cost:<15.6f}${int8_cost:.6f}")
        else:
            print(f"{bs:<8}{fp32_latency*1000:<15.3f}{'n/a':<15}{'n/a':<10}${fp32_cost:<15.6f}n/a")

    print(f"\n--- Load test: {n_clients} concurrent clients, 5 requests each ---")
    fp32_load = load_test(fp32_model, in_dim, n_clients=n_clients)
    print(f"fp32: {fp32_load['throughput_rps']:.1f} req/s, p50={fp32_load['p50_ms']:.2f}ms, "
          f"p95={fp32_load['p95_ms']:.2f}ms, max={fp32_load['max_ms']:.2f}ms")
    if int8_model:
        int8_load = load_test(int8_model, in_dim, n_clients=n_clients)
        print(f"int8: {int8_load['throughput_rps']:.1f} req/s, p50={int8_load['p50_ms']:.2f}ms, "
              f"p95={int8_load['p95_ms']:.2f}ms, max={int8_load['max_ms']:.2f}ms")


def main():
    parser = argparse.ArgumentParser(description="Serving benchmark: quantization + load test")
    parser.add_argument("--sizes", nargs="+", choices=list(MODEL_SIZES), default=list(MODEL_SIZES))
    parser.add_argument("--clients", type=int, default=8, help="concurrent simulated clients (default: 8)")
    args = parser.parse_args()

    supported = torch.backends.quantized.supported_engines
    engine = "qnnpack" if "qnnpack" in supported else ("fbgemm" if "fbgemm" in supported else None)
    if engine:
        torch.backends.quantized.engine = engine
        print(f"using quantized engine: {engine}")
    else:
        print(f"no quantized CPU engine available on this build ({supported}); int8 columns will show n/a.")

    for size_name in args.sizes:
        in_dim, hidden = MODEL_SIZES[size_name]
        benchmark_size(size_name, in_dim, hidden, engine, args.clients)

    print(f"\n{'=' * 70}")
    print("Note: p95 latency under concurrent load is what actually determines user-facing "
          "tail latency in production -- a great mean/p50 with a bad p95 still means a chunk "
          "of real users have a slow experience. Always report both, and at realistic "
          "concurrency, not just single-request latency.")


if __name__ == "__main__":
    main()
