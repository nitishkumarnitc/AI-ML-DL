# Run it

```bash
python run.py
python run.py --report-file eval_report.md    # export the full comparison as markdown
python run.py --help
```

No dependencies, runs instantly. Compares TWO judges (naive, biased toward confident phrasing vs. an improved reference-first judge) against human labels on the SAME 20 transcripts, reporting both raw agreement AND Cohen's kappa (agreement corrected for chance) — the naive judge's kappa (~0.47) exposes that it's barely better than chance despite 75%+ raw agreement, while the improved judge hits kappa=1.0.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
