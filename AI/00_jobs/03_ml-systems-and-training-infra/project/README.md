# Run it

```bash
pip install torch
python run.py                                   # all 3 model sizes, full sweep
python run.py --sizes small medium              # skip the large model, faster
python run.py --csv bench.csv --profile          # export results + a torch.profiler op breakdown
python run.py --help
```

Takes ~1-2 minutes for all 3 sizes on CPU (faster with `--sizes small`). Benchmarks baseline vs AMP vs torch.compile vs gradient accumulation at 3 model sizes (small/medium/large), reports ms/step, samples/sec, speedup, and peak memory for each, and optionally runs a real `torch.profiler` pass showing the top CPU-time ops.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
