# Runnable core — Research Experiment Platform

```bash
pip install torch
python run.py                          # ~30 s on CPU, 24 real training runs
python run.py --seeds 12 --steps 600   # tighter sigma/rho estimates, ~2 min
python run.py --skip-mc --seeds 4      # fastest sanity check, ~6 s
python run.py --csv results.csv        # every per-run result to CSV
python run.py --help
```

**Nothing printed is hard-coded.** σ and ρ are measured from real training runs performed in the
process, then fed into the same power arithmetic the design specifies.

## What it actually runs

| Part | What it does | Which design section it implements |
|---|---|---|
| **1 · Variance census** | Trains `--seeds` identical runs, differing *only* in the seed tuple, and computes σ | [`01_requirements.md`](../01_requirements.md) FR-3 · §1.7 Q1 — the "$81 job" |
| **2 · Paired ablation** | Trains control and `warmup_steps=100` arms **sharing seed_init, seed_shuffle and eval batches**, then measures ρ and σ_d | [`03_lld.md`](../03_lld.md) §3.3.2 `verify_pairing` · FR-4 |
| **3 · Power table** | Required `n` and the inverted `δ_min`, on a **δ/σ** axis so it transfers across scale, plus the frontier-lab regime for comparison | [`00_concepts.md`](../00_concepts.md) §3–4 |
| **4 · Verdict engine** | Paired t vs Welch on the same data, BH adjustment, **achieved** power, three-outcome verdict | [`03_lld.md`](../03_lld.md) §3.3.3 |
| **5 · Multiple comparisons** | Monte Carlo of a 20-arm null sweep, shared-control **and** independent-control | [`00_concepts.md`](../00_concepts.md) §5.1 |

Exact Student-t p-values come from a hand-rolled regularized incomplete beta (Lentz continued
fraction) — **no scipy**, so `pip install torch` really is the whole dependency list.

## The four things to look at in the output

1. **σ is measured, not assumed.** The design's most load-bearing assumption ([§1.7 A1](../01_requirements.md)) becomes a number you watched get produced.
2. **`δ_min` at n=3 is always 2.29σ.** That ratio is scale-free — it holds for any σ, which is why "3 seeds" is the wrong default *everywhere*, not just at toy scale.
3. **Pairing narrows the CI several-fold on identical data.** Part 4 prints both tests on the same numbers; the paired interval is strictly tighter for free.
4. **BH pulls a 20-arm null sweep back to ~α.** And the shared-control row sits *below* the textbook `1−(1−α)^k` — because the arms share a control draw, so their p-values are correlated. The script explains it rather than glossing over the gap.

## Honest limitations

- **ρ often comes out ≥0.95 here** — higher than a real lab sees. A tiny model, a mild ablation and fixed eval batches make the arms track each other almost exactly. The script prints a caveat when this happens; published-scale runs land nearer ρ = 0.7–0.9, which is why the design assumes 0.80. **Do not quote this run's speedup as a general figure.**
- **Absolute σ (~0.003 nats) is far smaller than the design's 0.02** because the model is ~50k params, not 200M, and converges into a tight basin. This is exactly why part 3's primary axis is δ/σ.
- `achieved_power` uses a normal approximation to the noncentral t. Accurate to ~0.01 at these df; a production implementation should use the true noncentral distribution.
- The corpus is a 2nd-order Markov chain, not natural language — chosen so there is real learnable structure and a real entropy floor, which is what makes σ meaningful at this size.

## What a real lab adds on top

| Here | In production |
|---|---|
| In-process loop | Signed job specs → a GPU scheduler ([design 03](../../03_distributed_training_platform/README.md)) |
| Values in memory | Postgres + Timescale, five `NOT NULL` provenance columns ([§3.1](../03_lld.md)) |
| `--delta` flag | Immutable pre-registration rows with `CHECK` constraints ([§3.1.2](../03_lld.md)) |
| Printed verdict | Immutable, `engine_version`-stamped verdict rows + quarterly FDR audit ([§4.2.2](../04_production_and_interview.md)) |
| One ablation | Two-tier screen→confirm policy with fresh-seed enforcement ([§1.6.2](../01_requirements.md)) |
| Hand-rolled t-test | `scipy.stats`, and a Bayesian verdict alongside the frequentist one |

---

← [system README](../README.md) · [00_concepts.md](../00_concepts.md) · [03_lld.md](../03_lld.md)
