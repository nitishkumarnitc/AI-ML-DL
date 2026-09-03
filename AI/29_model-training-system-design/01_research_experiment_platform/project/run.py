#!/usr/bin/env python3
"""
Research Experiment Platform - runnable core.

This is the verdict engine and power calculator from
  ../03_lld.md  §3.3.1 (power), §3.3.2 (pairing), §3.3.3 (verdict)
running against REAL training runs, not synthetic numbers.

It answers the question the design is built around:

    "How many seeds do I actually need, and what can 3 seeds even see?"

by MEASURING sigma and rho from real runs of a tiny character-level LM,
then feeding the measured values into the same power arithmetic the design
specifies (00_concepts.md §3-4).

    pip install torch
    python run.py                 # ~30 s on CPU (24 real training runs)
    python run.py --seeds 12 --steps 600
    python run.py --csv results.csv
    python run.py --help

Everything printed is computed from the runs performed in this process.
No number below is hard-coded.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import statistics as st
import sys
import time
from dataclasses import dataclass, field

# ----------------------------------------------------------------------------
# Statistics: exact t-distribution, no scipy dependency.
# ----------------------------------------------------------------------------


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    TINY, EPS, ITMAX = 1e-30, 3e-16, 300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < TINY:
        d = TINY
    d = 1.0 / d
    h = d
    for m in range(1, ITMAX + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_sf(t: float, df: float) -> float:
    """P(T > t) for Student's t with df degrees of freedom."""
    x = df / (df + t * t)
    tail = 0.5 * betainc(df / 2.0, 0.5, x)
    return tail if t > 0 else 1.0 - tail


def t_two_sided_p(t: float, df: float) -> float:
    return 2.0 * t_sf(abs(t), df)


def t_ppf(p: float, df: float) -> float:
    """Inverse t-CDF by bisection. Adequate and dependency-free."""
    lo, hi = -200.0, 200.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if (1.0 - t_sf(mid, df)) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


NORM_Z = {0.80: 0.8416212336, 0.975: 1.9599639845, 0.95: 1.6448536270, 0.90: 1.2815515655}
K_POWER = (NORM_Z[0.975] + NORM_Z[0.80]) ** 2  # 7.8489 at alpha=0.05, power=0.80


# ----------------------------------------------------------------------------
# 03_lld.md §3.3.1 - the power calculator, verbatim in spirit.
# ----------------------------------------------------------------------------


def required_n(sigma: float, delta: float, design: str, rho: float | None = None) -> tuple[int, str]:
    if design == "unpaired":
        return math.ceil(2 * K_POWER * sigma**2 / delta**2), "runs_per_arm"
    if rho is None:
        raise ValueError("paired design requires a measured rho")
    if rho < 0.5:
        return (-1, f"pairing_not_beneficial(rho={rho:.2f})")
    sigma_d = sigma * math.sqrt(2 * (1 - rho))
    return math.ceil(K_POWER * sigma_d**2 / delta**2), "pairs"


def detectable_delta(sigma: float, n: int, design: str, rho: float | None = None) -> float:
    """THE INVERSION - ask this first. Smallest effect n runs can see at power 0.80."""
    if design == "unpaired":
        return sigma * math.sqrt(2 * K_POWER / n)
    sigma_d = sigma * math.sqrt(2 * (1 - rho))
    return sigma_d * math.sqrt(K_POWER / n)


def required_pairs_from_sigma_d(sigma_d: float, delta: float) -> int:
    """Pairs needed when sigma_d is already known directly (no rho round-trip)."""
    return max(1, math.ceil(K_POWER * sigma_d**2 / delta**2))


def achieved_power(sigma: float, delta: float, n: int, design: str,
                   rho: float | None = None, alpha: float = 0.05) -> float:
    """Power actually attained by the runs that completed (03_lld §3.3.3 step 4)."""
    if n < 2:
        return 0.0
    if design == "unpaired":
        se = sigma * math.sqrt(2.0 / n)
        df = 2 * n - 2
    else:
        sigma_d = sigma if rho is None else sigma * math.sqrt(2 * (1 - rho))
        se = sigma_d / math.sqrt(n)
        df = n - 1
    if se <= 0:
        return 1.0
    crit = t_ppf(1 - alpha / 2, df)
    ncp = abs(delta) / se
    return t_sf(crit - ncp, df)  # normal-approx to the noncentral t; fine at these df


def benjamini_hochberg(pvals: list[float], q: float = 0.05) -> list[float]:
    """Step-up BH adjusted p-values (03_lld §3.3.3 step 5)."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        k = m - rank + 1
        prev = min(prev, pvals[idx] * m / k)
        adj[idx] = min(1.0, prev)
    return adj


def paired_t(diffs: list[float], alpha: float = 0.05):
    n = len(diffs)
    mean_d = st.mean(diffs)
    sd = st.stdev(diffs) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else float("inf")
    t = mean_d / se if se > 0 else 0.0
    df = n - 1
    crit = t_ppf(1 - alpha / 2, df)
    return mean_d, (mean_d - crit * se, mean_d + crit * se), t_two_sided_p(t, df), sd


def welch_p(a: list[float], b: list[float]) -> float:
    """p-value only. Skips the CI, and therefore the bisection in t_ppf -- which is
    the whole cost when running thousands of Monte Carlo trials (part 5)."""
    na, nb = len(a), len(b)
    va, vb = st.variance(a), st.variance(b)
    se = math.sqrt(va / na + vb / nb)
    if se <= 0:
        return 1.0
    t = (st.mean(a) - st.mean(b)) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return t_two_sided_p(t, df)


def welch_t(a: list[float], b: list[float], alpha: float = 0.05):
    na, nb = len(a), len(b)
    ma, mb = st.mean(a), st.mean(b)
    va, vb = st.variance(a), st.variance(b)
    se = math.sqrt(va / na + vb / nb)
    t = (ma - mb) / se if se > 0 else 0.0
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    crit = t_ppf(1 - alpha / 2, df)
    return (ma - mb), ((ma - mb) - crit * se, (ma - mb) + crit * se), t_two_sided_p(t, df), df


# ----------------------------------------------------------------------------
# The real training runs.
# ----------------------------------------------------------------------------

CORPUS_SEED = 20260901


def make_corpus(n_chars: int = 60_000) -> str:
    """A learnable synthetic corpus: a 2nd-order Markov chain over a small alphabet.

    Real structure (so loss actually falls) and a real entropy floor (so runs
    converge to a comparable place) -- which is what makes sigma meaningful.
    """
    rng = random.Random(CORPUS_SEED)
    alpha = "abcdefghijklmnop "
    table: dict[tuple[str, str], list[float]] = {}
    for c1 in alpha:
        for c2 in alpha:
            w = [rng.random() ** 3 for _ in alpha]
            s = sum(w)
            table[(c1, c2)] = [x / s for x in w]
    out = [rng.choice(alpha), rng.choice(alpha)]
    for _ in range(n_chars):
        out.append(rng.choices(alpha, weights=table[(out[-2], out[-1])], k=1)[0])
    return "".join(out)


@dataclass
class RunResult:
    """One row of the `runs` table from 03_lld.md §3.1.3, minus the provenance columns."""
    arm: str
    pair_index: int
    seed_init: int
    seed_shuffle: int
    final_metric: float
    steps: int
    seconds: float
    curve: list[float] = field(default_factory=list)


def train_one(corpus: str, *, seed_init: int, seed_shuffle: int, warmup_steps: int,
              steps: int, n_embd: int = 48, block: int = 32, batch: int = 24,
              lr: float = 3e-3) -> tuple[float, list[float], float]:
    """One real training run. Returns (final val loss in nats, curve, seconds).

    seed_init and seed_shuffle are SEPARATE (03_lld §3.1.3) so a paired design can
    hold them equal while only `warmup_steps` differs.
    """
    import torch
    import torch.nn as nn

    t0 = time.perf_counter()
    chars = sorted(set(corpus))
    stoi = {c: i for i, c in enumerate(chars)}
    data = torch.tensor([stoi[c] for c in corpus], dtype=torch.long)
    n_train = int(0.9 * len(data))
    train_data, val_data = data[:n_train], data[n_train:]

    torch.manual_seed(seed_init)  # weight init

    class TinyLM(nn.Module):
        def __init__(self, vocab: int):
            super().__init__()
            self.tok = nn.Embedding(vocab, n_embd)
            self.pos = nn.Embedding(block, n_embd)
            self.ln = nn.LayerNorm(n_embd)
            self.attn = nn.MultiheadAttention(n_embd, 4, batch_first=True)
            self.mlp = nn.Sequential(nn.Linear(n_embd, 4 * n_embd), nn.GELU(),
                                     nn.Linear(4 * n_embd, n_embd))
            self.head = nn.Linear(n_embd, vocab)

        def forward(self, x):
            t = x.shape[1]
            h = self.tok(x) + self.pos(torch.arange(t))
            mask = torch.triu(torch.ones(t, t, dtype=torch.bool), diagonal=1)
            a, _ = self.attn(self.ln(h), self.ln(h), self.ln(h), attn_mask=mask,
                             need_weights=False)
            h = h + a
            h = h + self.mlp(self.ln(h))
            return self.head(h)

    model = TinyLM(len(chars))
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    shuffler = torch.Generator().manual_seed(seed_shuffle)  # data order

    def batch_from(src: torch.Tensor, gen: torch.Generator | None):
        ix = torch.randint(len(src) - block - 1, (batch,), generator=gen)
        x = torch.stack([src[i:i + block] for i in ix])
        y = torch.stack([src[i + 1:i + block + 1] for i in ix])
        return x, y

    curve: list[float] = []
    for step in range(steps):
        cur_lr = lr * min(1.0, (step + 1) / warmup_steps) if warmup_steps > 0 else lr
        for g in opt.param_groups:
            g["lr"] = cur_lr
        x, y = batch_from(train_data, shuffler)
        logits = model(x)
        loss = torch.nn.functional.cross_entropy(
            logits.reshape(-1, logits.size(-1)), y.reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if (step + 1) % max(1, steps // 8) == 0:
            curve.append(float(loss.item()))

    # Deterministic validation: FIXED eval batches, identical across every run
    # (03_lld §3.6 -- eval noise would otherwise be counted as seed noise).
    model.eval()
    eval_gen = torch.Generator().manual_seed(999_777)
    tot, nb = 0.0, 12
    with torch.no_grad():
        for _ in range(nb):
            x, y = batch_from(val_data, eval_gen)
            logits = model(x)
            tot += float(torch.nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)), y.reshape(-1)).item())
    return tot / nb, curve, time.perf_counter() - t0


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------

BAR = "=" * 78


def hdr(title: str) -> None:
    print(f"\n{BAR}\n{title}\n{BAR}")


def part1_variance_census(corpus: str, seeds: int, steps: int) -> tuple[list[RunResult], float]:
    """01_requirements.md FR-3 / §1.7 Q1 - the $81 job that makes every power number real."""
    hdr(f"PART 1 - VARIANCE CENSUS: measuring sigma from {seeds} identical runs")
    print("Identical config, identical data, ONLY the seed tuple differs.")
    print("This is the number the entire design is most sensitive to (§1.7 A1).\n")
    print(f"{'run':>4} {'seed':>6} {'final val loss (nats)':>24} {'sec':>7}")
    runs: list[RunResult] = []
    for i in range(seeds):
        loss, curve, secs = train_one(corpus, seed_init=1000 + i, seed_shuffle=2000 + i,
                                      warmup_steps=0, steps=steps)
        runs.append(RunResult("census", i, 1000 + i, 2000 + i, loss, steps, secs, curve))
        print(f"{i:>4} {1000 + i:>6} {loss:>24.5f} {secs:>7.1f}")
    vals = [r.final_metric for r in runs]
    sigma = st.stdev(vals)
    print(f"\n  mean  = {st.mean(vals):.5f} nats")
    print(f"  SIGMA = {sigma:.5f} nats   <-- measured, not assumed")
    print(f"  range = [{min(vals):.5f}, {max(vals):.5f}]  (spread {max(vals)-min(vals):.5f})")
    print(f"  perplexity spread = {math.exp(min(vals)):.3f} .. {math.exp(max(vals)):.3f}")
    return runs, sigma


def part2_paired_ablation(corpus: str, seeds: int, steps: int, warmup: int
                          ) -> tuple[list[RunResult], list[RunResult], float]:
    """03_lld.md §3.3.2 - paired arms by construction. Measures rho."""
    hdr(f"PART 2 - PAIRED ABLATION: warmup_steps 0 vs {warmup}")
    print("Within each pair: SAME seed_init, SAME seed_shuffle, SAME eval batches.")
    print("Only `optim.warmup_steps` differs -- pairing by construction (FR-4).\n")
    print(f"{'pair':>5} {'control':>12} {'treatment':>12} {'diff':>12}")
    ctrl: list[RunResult] = []
    trt: list[RunResult] = []
    for i in range(seeds):
        si, ss = 1000 + i, 2000 + i  # <-- IDENTICAL across the two arms
        c, _, cs = train_one(corpus, seed_init=si, seed_shuffle=ss, warmup_steps=0, steps=steps)
        t, _, ts = train_one(corpus, seed_init=si, seed_shuffle=ss, warmup_steps=warmup, steps=steps)
        ctrl.append(RunResult("control", i, si, ss, c, steps, cs))
        trt.append(RunResult(f"warmup_{warmup}", i, si, ss, t, steps, ts))
        print(f"{i:>5} {c:>12.5f} {t:>12.5f} {c - t:>+12.5f}")

    a = [r.final_metric for r in ctrl]
    b = [r.final_metric for r in trt]
    ma, mb = st.mean(a), st.mean(b)
    sa, sb = st.stdev(a), st.stdev(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (len(a) - 1)
    rho = cov / (sa * sb) if sa > 0 and sb > 0 else 0.0
    sigma_pooled = math.sqrt((sa**2 + sb**2) / 2)
    sigma_d = st.stdev([x - y for x, y in zip(a, b)])
    print(f"\n  sigma (pooled across arms) = {sigma_pooled:.5f}")
    print(f"  RHO (paired correlation)   = {rho:+.3f}   <-- measured, not assumed (§1.7 A2)")
    print(f"  sigma_d (of the pairwise difference) = {sigma_d:.5f}")
    pred = sigma_pooled * math.sqrt(max(0.0, 2 * (1 - rho)))
    print(f"  predicted sigma_d = sigma*sqrt(2(1-rho)) = {pred:.5f}")
    gap = abs(pred - sigma_d) / sigma_d * 100 if sigma_d else 0.0
    print(f"    (identity check: {gap:.0f}% off the measured value. At n={len(a)} both "
          f"sigma and rho\n     carry ~{100/math.sqrt(2*(len(a)-1)):.0f}% sampling error, "
          f"so a gap this size is expected,\n     not a broken identity. Raise --seeds to "
          f"tighten it.)")
    if rho > 0.5:
        print(f"  => pairing shrinks the noise {sigma_pooled / sigma_d:.2f}x "
              f"({(sigma_pooled/sigma_d)**2:.1f}x fewer runs for the same power)")
        if rho > 0.95:
            print(f"\n  CAVEAT, stated because it matters: rho={rho:.3f} is HIGHER than a real")
            print("  lab sees. This toy setup is close to the best case for pairing -- a tiny")
            print("  model, a mild ablation, fixed eval batches, and few steps, so the two arms")
            print("  track each other almost exactly. Published-scale runs land nearer")
            print("  rho = 0.7-0.9, which is why the design assumes 0.80 (§1.7 A2) and gets")
            print("  4.8x rather than the number above. Do not quote this run's speedup.")
    else:
        print("  => rho <= 0.5: pairing buys nothing here. The design REFUSES to "
              "pair (03_lld §3.3.1) rather than silently applying it.")
    return ctrl, trt, rho


def part3_power_table(sigma: float, rho: float, delta: float) -> None:
    hdr("PART 3 - POWER: what the measured sigma actually costs")
    print("From 00_concepts.md §3.3-3.4, using the sigma and rho measured above.")
    print("The primary axis is delta/sigma, because that ratio -- not the absolute")
    print("nats -- is what determines run count. It transfers across scales; the")
    print("toy model's absolute sigma does not.\n")

    print("(a) Runs needed for power 0.80 at alpha 0.05:")
    print(f"    {'delta/sigma':>12} {'delta (nats)':>14} {'unpaired n/arm':>16} "
          f"{'runs':>7} {'paired pairs':>14} {'runs':>7}")
    for ratio in (2.0, 1.0, 0.5, 0.25, 0.1):
        d = ratio * sigma
        nu, _ = required_n(sigma, d, "unpaired")
        np_, _ = required_n(sigma, d, "paired", rho)
        pstr = f"{np_:>14}" if np_ > 0 else f"{'refused':>14}"
        ptot = f"{2 * np_:>7}" if np_ > 0 else f"{'-':>7}"
        mark = "  <-- your --delta" if abs(d - delta) < 1e-9 else ""
        print(f"    {ratio:>12.2f} {d:>14.5f} {nu:>16} {2 * nu:>7} {pstr} {ptot}{mark}")

    print("\n(b) THE INVERSION - smallest effect n seeds can see at all:")
    print(f"    {'seeds/arm':>10} {'unpaired delta_min':>20} {'in sigma units':>16} "
          f"{'paired delta_min':>18}")
    for n in (2, 3, 5, 10, 20):
        du = detectable_delta(sigma, n, "unpaired")
        dp = detectable_delta(sigma, n, "paired", rho) if rho > 0.5 else float("nan")
        dps = f"{dp:>18.5f}" if dp == dp else f"{'refused':>18}"
        mark = "  <-- the industry default" if n == 3 else ""
        print(f"    {n:>10} {du:>20.5f} {du / sigma:>15.2f}s {dps}{mark}")
    d3 = detectable_delta(sigma, 3, "unpaired")
    print(f"\n    With 3 seeds you are blind to anything below {d3 / sigma:.2f} sigma "
          f"({d3:.5f} nats here).")
    print("    That ratio is scale-free: it is 2.29 sigma for ANY sigma, at n=3.")

    print("\n(c) The frontier-lab regime the DESIGN is sized for (00_concepts §3.3):")
    print("    sigma = 0.02 nats (a 200M-param model), delta = 0.01 nats -> delta/sigma = 0.50")
    nu, _ = required_n(0.02, 0.01, "unpaired")
    np8, _ = required_n(0.02, 0.01, "paired", 0.8)
    print(f"      unpaired: {nu} runs/arm = {2 * nu} runs")
    print(f"      paired (rho=0.80): {np8} pairs = {2 * np8} runs   "
          f"({2 * nu / (2 * np8):.1f}x cheaper)")
    print(f"      at n=3: detectable delta = {detectable_delta(0.02, 3, 'unpaired'):.4f} nats "
          f"-- 4.6x larger than the effect sought")
    print("    This is the arithmetic behind 01_requirements.md §1.6.2's two-tier policy.")


def part4_verdict(ctrl: list[RunResult], trt: list[RunResult], sigma: float, rho: float,
                  delta: float, alpha: float = 0.05) -> None:
    """03_lld.md §3.3.3 - the verdict engine, including the power gate."""
    hdr("PART 4 - VERDICT ENGINE (03_lld §3.3.3)")
    a = [r.final_metric for r in ctrl]
    b = [r.final_metric for r in trt]
    diffs = [x - y for x, y in zip(a, b)]
    n = len(diffs)

    eff_p, ci_p, p_p, sd_p = paired_t(diffs, alpha)
    eff_u, ci_u, p_u, df_u = welch_t(a, b, alpha)

    print(f"  pre-registered delta = {delta:.5f} nats, alpha = {alpha}, "
          f"target power = 0.80\n")
    print(f"  {'test':>12} {'effect':>10} {'95% CI':>24} {'p_raw':>10}")
    print(f"  {'paired_t':>12} {eff_p:>+10.5f} {f'[{ci_p[0]:+.5f},{ci_p[1]:+.5f}]':>24} {p_p:>10.4f}")
    print(f"  {'welch_t':>12} {eff_u:>+10.5f} {f'[{ci_u[0]:+.5f},{ci_u[1]:+.5f}]':>24} {p_u:>10.4f}")
    print(f"\n  Same data. Pairing narrowed the CI by "
          f"{((ci_u[1]-ci_u[0])/(ci_p[1]-ci_p[0])):.2f}x -- for free.")

    # BH across arms (one treatment arm here; the correction is shown as the design applies it)
    p_adj = benjamini_hochberg([p_p], q=alpha)[0]
    ach = achieved_power(sd_p, delta, n, "paired")

    print(f"\n  achieved power (from OBSERVED sigma_d={sd_p:.5f}, n={n}) = {ach:.3f}")
    print(f"  p_adjusted (BH, 1 arm)                                  = {p_adj:.4f}")

    # THE RULE: power gates the verdict BEFORE significance does.
    if ach < 0.80:
        kind = "inconclusive"
        why = (f"achieved power {ach:.2f} < 0.80 -- this is NOT evidence against the "
               f"hypothesis. Need n={required_pairs_from_sigma_d(sd_p, delta)} "
               f"pairs at this sigma_d.")
    elif p_adj < alpha:
        kind = "supported"
        why = f"p_adj={p_adj:.4f} < {alpha} at adequate power"
    else:
        kind = "not_supported"
        why = f"p_adj={p_adj:.4f} >= {alpha} at adequate power {ach:.2f}"
    print(f"\n  VERDICT: {kind.upper()}")
    print(f"           {why}")
    if kind == "inconclusive":
        print("\n  Note: a two-outcome system would have printed 'not supported' here")
        print("        and a real effect would have been abandoned. That is the")
        print("        false negative this design exists to prevent (04 §4.3).")


def part5_multiple_comparisons(trials: int = 4000, arms: int = 20, n: int = 5,
                              alpha: float = 0.05) -> None:
    """00_concepts.md §5.1 - Monte Carlo the false-winner rate, both designs."""
    hdr(f"PART 5 - MULTIPLE COMPARISONS: {arms}-arm sweep under the NULL")
    print(f"Simulating {trials:,} sweeps where EVERY arm is identical (no real effect).")
    print("Purely statistical -- no training needed, so this is exact and fast.\n")
    rng = random.Random(4242)
    shared_raw = shared_bh = indep_raw = indep_bh = 0
    for _ in range(trials):
        # (i) ONE control compared against all arms -- what a real sweep does.
        ctrl = [rng.gauss(0, 1) for _ in range(n)]
        ps = [welch_p(ctrl, [rng.gauss(0, 1) for _ in range(n)]) for _ in range(arms)]
        shared_raw += any(p < alpha for p in ps)
        shared_bh += any(q < alpha for q in benjamini_hochberg(ps, q=alpha))
        # (ii) A FRESH control per arm -- statistically independent tests.
        qs = [welch_p([rng.gauss(0, 1) for _ in range(n)],
                      [rng.gauss(0, 1) for _ in range(n)]) for _ in range(arms)]
        indep_raw += any(p < alpha for p in qs)
        indep_bh += any(q < alpha for q in benjamini_hochberg(qs, q=alpha))

    theo = 1 - (1 - alpha) ** arms
    print(f"  {'design':>34} {'raw p-values':>14} {'with BH':>10}")
    print(f"  {'shared control (real sweeps)':>34} {shared_raw / trials:>13.1%} "
          f"{shared_bh / trials:>10.1%}")
    print(f"  {'independent control per arm':>34} {indep_raw / trials:>13.1%} "
          f"{indep_bh / trials:>10.1%}")
    print(f"  {'theory 1-(1-alpha)^k (independent)':>34} {theo:>13.1%} {'-':>10}")
    print(f"\n  Two things worth noticing:")
    print(f"  1. BH pulls both designs back to roughly alpha ({alpha:.0%}). That is its job.")
    print(f"  2. The shared-control sweep ({shared_raw/trials:.0%}) sits BELOW the")
    print(f"     independent-arms theory ({theo:.0%}) -- because every arm is compared")
    print(f"     against the SAME control draw, so the {arms} p-values are positively")
    print(f"     correlated and the tests are not {arms} independent chances.")
    print(f"     An unlucky control makes every arm look good at once, which shifts risk")
    print(f"     from 'a false winner' to 'the whole sweep is shifted'. Both need BH;")
    print(f"     quoting 1-(1-a)^k for a shared-control sweep OVERSTATES the rate.")
    print(f"  3. Even the independent case ({indep_raw/trials:.0%}) undershoots the {theo:.0%}")
    print(f"     theory slightly: the Welch t-test is mildly conservative at n={n}, so its")
    print(f"     realized false-positive rate is a little under the nominal {alpha:.0%}.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Research Experiment Platform - power, pairing and verdict engine "
                    "on real training runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=8,
                    help="seeds for the census and pairs for the ablation (default 8)")
    ap.add_argument("--steps", type=int, default=300, help="training steps per run (default 300)")
    ap.add_argument("--warmup", type=int, default=100, help="treatment arm warmup steps (default 100)")
    ap.add_argument("--delta", type=float, default=None,
                    help="pre-registered effect size in nats "
                         "(default: 0.5 x the MEASURED sigma, so the demo lands in the "
                         "same delta/sigma regime the design is sized for)")
    ap.add_argument("--corpus-chars", type=int, default=60000, help="synthetic corpus size")
    ap.add_argument("--csv", metavar="PATH", help="write every per-run result to CSV")
    ap.add_argument("--skip-mc", action="store_true", help="skip the Monte Carlo in part 5")
    args = ap.parse_args()

    try:
        import torch  # noqa: F401
    except ImportError:
        print("This demo needs PyTorch:  pip install torch", file=sys.stderr)
        return 1

    import torch
    torch.set_num_threads(min(8, torch.get_num_threads()))

    print(BAR)
    print("RESEARCH EXPERIMENT PLATFORM - runnable core")
    print("  AI/29_model-training-system-design/01_research_experiment_platform")
    print(BAR)
    print(f"  seeds={args.seeds}  steps={args.steps}  warmup(treatment)={args.warmup}")
    print(f"  total training runs: {args.seeds} (census) + {2 * args.seeds} (ablation) "
          f"= {3 * args.seeds}")

    t0 = time.perf_counter()
    corpus = make_corpus(args.corpus_chars)
    print(f"  corpus: {len(corpus):,} chars, {len(set(corpus))} symbols "
          f"(2nd-order Markov -- real structure, real entropy floor)")

    census, sigma = part1_variance_census(corpus, args.seeds, args.steps)
    ctrl, trt, rho = part2_paired_ablation(corpus, args.seeds, args.steps, args.warmup)

    delta = args.delta if args.delta is not None else 0.5 * sigma
    if args.delta is None:
        print(f"\n  --delta not given -> using 0.5 x measured sigma = {delta:.5f} nats")
        print("     (delta/sigma = 0.50, the same regime as the design's 0.01/0.02)")

    part3_power_table(sigma, rho, delta)
    part4_verdict(ctrl, trt, sigma, rho, delta)
    if not args.skip_mc:
        part5_multiple_comparisons()

    hdr("SUMMARY")
    nu, _ = required_n(sigma, delta, "unpaired")
    np_, _ = required_n(sigma, delta, "paired", rho)
    print(f"  measured sigma                       = {sigma:.5f} nats")
    print(f"  measured rho (paired)                = {rho:+.3f}")
    print(f"  3 seeds can only detect              = {detectable_delta(sigma,3,'unpaired'):.5f} nats "
          f"(= {detectable_delta(sigma,3,'unpaired')/sigma:.2f} sigma)")
    print(f"  delta used (0.5 sigma)               = {delta:.5f} nats")
    print(f"  runs needed, unpaired                = {2*nu}")
    if np_ > 0:
        print(f"  runs needed, paired                  = {2*np_}"
              f"   ({2*nu/(2*np_):.1f}x cheaper)")
    else:
        print(f"  paired design refused (rho={rho:+.3f} <= 0.5)")
    print(f"\n  wall clock: {time.perf_counter()-t0:.1f} s")
    print("\n  Read next: ../01_requirements.md §1.6 (why this forces a two-tier policy)")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["phase", "arm", "pair_index", "seed_init", "seed_shuffle",
                        "final_metric_nats", "steps", "seconds"])
            for phase, rows in (("census", census), ("ablation", ctrl + trt)):
                for r in rows:
                    w.writerow([phase, r.arm, r.pair_index, r.seed_init, r.seed_shuffle,
                                f"{r.final_metric:.6f}", r.steps, f"{r.seconds:.2f}"])
        print(f"  wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
