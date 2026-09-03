# Run it

```bash
pip install torch
python run.py                          # all 3 model sizes
python run.py --sizes small medium     # skip the large model, faster
python run.py --clients 16             # more simulated concurrent load
python run.py --help
```

Takes ~15-30s on CPU for all 3 sizes. For each of small/medium/large:

1. Reports real memory footprint (param count + KB) for fp32 vs int8.
2. Runs a real INT8 dynamic-quantization benchmark (batch sizes 1/8/32) with a $/1K-requests cost estimate.
3. Runs a **concurrent load test** (multiple simulated clients via threads) and reports throughput + p50/p95/max latency — the numbers that actually matter under real traffic, not just single-request latency.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
