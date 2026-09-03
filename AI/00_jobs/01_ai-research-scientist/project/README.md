# Run it

```bash
pip install torch
python run.py                              # both experiments, defaults (5 seeds, 300 steps)
python run.py --seeds 8 --steps 500        # less noisy, slower
python run.py --experiment warmup          # just the LR-warmup experiment
python run.py --experiment positional      # just the positional-encoding experiment
python run.py --help                       # all options
```

Takes ~1-2 minutes on CPU at the defaults. Runs two ablation studies on a tiny transformer LM:

1. **LR warmup** (0 steps vs 50 steps) — 5 seeds each, mean/stdev + verdict.
2. **Positional encoding** (learned embeddings vs fixed sinusoidal) — same treatment.

Every per-seed result is written to `ablation_results.csv` so you can plot the real distributions instead of trusting the terminal's ASCII bars.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
