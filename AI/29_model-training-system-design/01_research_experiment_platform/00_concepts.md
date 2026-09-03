# 00 — Concepts primer: what you need to know before reading this design

> **Read this first if you have not run experiments in a research lab.** Everything here is a
> prerequisite for the design, taught from scratch. If you already know what a paired t-test and a
> scaling law are, skip to [`01_requirements.md`](01_requirements.md).
>
> ← [system README](README.md) · → [01_requirements.md](01_requirements.md)

---

## The three-sentence version

1. Training the same model twice with different random seeds gives **different final losses** — and
   the size of that spread is usually larger than the effect you are trying to measure.
2. Statistics has an exact answer for "how many runs do I need to see an effect of size δ", and the
   answer for realistic ML numbers is **shockingly large** — 63 runs per arm, not 3.
3. The single trick that fixes it is **pairing**: hold everything constant except the one variable, so
   the shared noise cancels. That is what this platform is built to enforce.

---

## 1. What "loss" is, and what a nat is

A language model outputs a probability distribution over the next token. Its training objective is
**cross-entropy loss**: the average negative log-probability it assigned to the token that actually
came next.

```
loss = −(1/T) · Σ_t log P(token_t | tokens_<t)
```

When the log is natural (base *e*), the unit is a **nat**. When it is base 2, the unit is **bits**,
and `bits = nats / ln 2`. **Perplexity** is just `exp(loss)` — the effective number of equally-likely
choices the model is deciding between.

| Loss (nats) | Perplexity | Reading |
|---|---|---|
| 4.60 | 100 | ≈ picking from 100 options |
| 2.99 | 20 | a small model, mid-training |
| 2.30 | 10 | a decent small model |
| 2.00 | 7.4 | a strong small model |

**Why the unit matters for this design:** a "0.01-nat improvement" sounds tiny and is in fact a
perfectly normal size for a real architectural win. At loss 2.30, a 0.01-nat gain moves perplexity
from 9.97 to 9.87 — about 1%. Meanwhile **seed-to-seed variation is often 0.02 nats**, i.e. *twice as
large as the effect*. That inversion is the entire problem this system exists to solve.

---

## 2. Where the randomness comes from

Two runs of "the same" training differ because of:

| Source | What varies | Controllable? |
|---|---|---|
| **Weight initialization** | The starting point in parameter space | Yes — fix the init seed |
| **Data order** | Which examples land in which batch, in what order | Yes — fix the shuffle seed |
| **Dropout / augmentation masks** | Which units are dropped each step | Yes — fix the dropout seed |
| **Non-deterministic GPU kernels** | Floating-point reduction order in `atomicAdd`-based kernels | Mostly — `torch.use_deterministic_algorithms(True)`, at a throughput cost |
| **Hardware/numeric drift** | Different GPU models, different cuDNN/cuBLAS versions pick different kernels | Only by pinning the container digest and GPU SKU |

**The key insight:** the first three are *seeds you control*, and the last two are *nuisance you must
pin*. A platform that lets a researcher compare a run from a container built in March against one from
June is not measuring their hypothesis — it is measuring a cuBLAS upgrade.

`σ` (sigma) in this document means **the standard deviation of final validation loss across seeds, at
otherwise identical config.** It is one number, it is measurable in an afternoon, and almost no lab
has it written down.

---

## 3. Statistical power, from scratch

You have two variants, A and B. You run each `n` times, get two sets of final losses, and want to
answer: *is B genuinely better, or did I get lucky?*

### 3.1 The test

The **two-sample t-test** compares the difference of means against the noise:

```
t = (mean_A − mean_B) / (σ_pooled · √(2/n))
```

If `|t|` exceeds a critical value (≈1.96 for large `n`, α=0.05 two-sided), you call it significant.

### 3.2 Two ways to be wrong

| | B is truly better | B is truly not better |
|---|---|---|
| **You call it significant** | ✅ correct | **Type I error** (false positive) — rate α, conventionally 0.05 |
| **You call it not significant** | **Type II error** (false negative) — rate β | ✅ correct |

**Power** = `1 − β` = the probability you *detect* a real effect. The convention is 0.80.

**Almost all ML experimentation controls α and completely ignores power.** That is why so many
ablations are "inconclusive": not because the effect isn't there, but because `n` was never large
enough to see it.

### 3.3 The formula, and why it is brutal

To get power 0.80 at α=0.05 two-sided, for a true effect δ:

```
n per arm = 2·(z_0.975 + z_0.80)² · σ²/δ²
          = 2·(1.960 + 0.842)² · σ²/δ²
          = 15.70 · σ²/δ²
```

The `σ²/δ²` is the whole story: **halving the effect you want to detect quadruples the runs you need.**

With σ = 0.02 nats:

| Effect δ you want to detect | Runs per arm | Total runs (2 arms) |
|---|---|---|
| 0.050 nats (a huge win) | 3 | 6 |
| 0.020 nats (a good win) | 16 | 32 |
| **0.010 nats (a normal win)** | **63** | **126** |
| 0.005 nats (a marginal win) | 252 | 504 |

Inverted — the question people should ask first:

```
δ_min = σ · √(15.70 / n)      "the smallest effect n seeds can see at all"
```

| Seeds per arm | Smallest visible effect |
|---|---|
| 2 | 0.056 nats |
| **3** (the industry default) | **0.046 nats** |
| 5 | 0.035 nats |
| 10 | 0.025 nats |

> **This is the finding the whole design is built around.** A 3-seed ablation is blind to anything
> smaller than 0.046 nats. Most real architectural changes are 0.005–0.02 nats. **The default
> experimental protocol in ML cannot see the effects it is looking for.**

---

## 4. Pairing — the fix that costs nothing

Notice that most of σ is *shared nuisance*: a bad init or an unlucky data order hurts **both** variants
about equally. So don't let them differ.

**Paired design:** for pair `i`, run arm A and arm B with the *same* init seed, the *same* data order,
the *same* eval batches — differing **only** in the ablated variable. Then test the *differences*
`d_i = loss_A,i − loss_B,i` against zero:

```
n pairs = (z_0.975 + z_0.80)² · σ_d²/δ²  =  7.85 · σ_d²/δ²

σ_d = σ·√(2(1−ρ))       ρ = correlation between paired arms
```

Two things improved at once: the constant halved (7.85 vs 15.70, because a one-sample test is used),
**and** σ_d < σ whenever ρ > 0.5.

| ρ (paired correlation) | σ_d | Pairs needed for δ=0.01 | Total runs | Saving vs 126 |
|---|---|---|---|---|
| 0.5 | 0.0200 | 32 | 64 | 2.0× |
| **0.8** | **0.0127** | **13** | **26** | **4.8×** |
| 0.9 | 0.0089 | 7 | 14 | 9.0× |
| 0.95 | 0.0063 | 4 | 8 | 15.8× |

**ρ is measurable from your existing run history.** You do not have to guess it. This is why the
platform's `01_requirements.md` treats "measure σ and ρ" as a P0 requirement rather than an assumption.

**When pairing is invalid:** if the ablated variable *changes the shape of the randomness* — e.g. you
changed the initialization scheme itself, or the data pipeline — then "same seed" no longer means
"same nuisance draw", and ρ collapses. The platform must therefore *check* whether pairing is legal
for a given ablation rather than assume it.

---

## 5. Two ways rigor leaks even with enough seeds

### 5.1 Multiple comparisons

You sweep 20 hyperparameter settings and pick the best. Under the null hypothesis (nothing works),
each test still fires with probability α=0.05:

```
P(at least one false winner) = 1 − (1 − 0.05)^20 = 64%
E[false winners] = 20 × 0.05 = 1.0
```

| Arms in the sweep | P(≥1 false winner) | E[false winners] |
|---|---|---|
| 5 | 22.6% | 0.25 |
| 10 | 40.1% | 0.50 |
| **20** | **64.2%** | **1.00** |
| 50 | 92.3% | 2.50 |

**A 20-arm sweep hands you a "winner" two times out of three even when every arm is identical.**

Fixes, in increasing order of strength:
- **Bonferroni** — test at α/k. Correct but very conservative; kills power.
- **Benjamini–Hochberg (BH)** — controls the *false discovery rate*: of the things you call
  significant, at most q (say 5%) are expected to be false. The right default for exploratory sweeps.
- **A confirmation run** — take the winner and re-test it, alone, pre-registered, at full power. This
  is the only one that fully restores the guarantee, and it is cheap relative to the sweep.

### 5.2 Sequential peeking

You watch the loss curves live and stop when the gap "looks significant." Every time you look, you get
another chance to cross the threshold by luck. Ten naive looks inflates the effective α from 0.05 to
roughly **0.20**.

Fixes: declare a **fixed horizon** at pre-registration, or use an **alpha-spending boundary**
(O'Brien–Fleming: a very strict threshold early, relaxing toward the planned end) so that early
stopping is legal.

> **Both leaks are why "pre-registration" appears in a systems design document.** They cannot be fixed
> after the fact by better statistics — only by having declared the hypothesis, the arms, the horizon
> and the metric *before* seeing data. That declaration is a database row, which makes it a systems
> problem.

---

## 6. Scaling laws — and why the ladder is cheap insurance

Empirically, loss falls as a power law in compute, parameters, and data:

```
L(N, D) ≈ E + A/N^α + B/D^β
```

Fit it on a **ladder** of small runs, then extrapolate to predict the flagship's loss before paying
for the flagship. The Chinchilla result gives the compute-optimal allocation:

```
D ≈ 20·N      ⇒  C_optimal = 6·N·D = 120·N²
```

**Why the ladder is nearly free:** because compute scales as `N²`, the largest rung dominates and
everything below it is rounding error.

| Rung `N` | `C = 120N²` | Hours on 64 × H100 @ 40% MFU |
|---|---|---|
| 20 M | 4.8e16 | 0.002 |
| 80 M | 7.7e17 | 0.01 |
| 320 M | 1.2e19 | 0.13 |
| 640 M | 4.9e19 | 0.54 |
| **1.3 B** | **2.0e20** | **2.22** |
| **Ladder total** | **2.7e20** | **2.9 h → 188 GPU-hr → $565** |

With 3 seeds and 2 learning rates per rung: **$3,391 — 0.31% of the $1.1M flagship it de-risks.**

**The honest caveat, which the design states explicitly:** ablations do not always transfer across
scale. A trick that helps at 200M can be neutral or harmful at 70B (the classic case is
regularization, which matters less as data grows). A scaling ladder tells you *whether the effect
survives scale*, which is strictly more information than a single small-scale ablation — and that is
exactly what makes it worth the $3k.

---

## 7. Reproducibility — what actually has to be pinned

A run is reproducible only if **all five** of these are captured:

| Thing | Captured as | Why it breaks results if unpinned |
|---|---|---|
| Config | **Content hash** of the fully-resolved config tree | Two runs "with the same config" that differ in one default are the most common silent confound |
| Code | Git SHA **+ dirty-tree flag** | An uncommitted local edit is invisible and unreproducible |
| Environment | **Container image digest** (not tag — tags move) | A cuBLAS/PyTorch upgrade changes kernels, and kernels change numerics |
| Data | **Dataset manifest hash** (revision + shard list + tokenizer version) | A silently re-tokenized corpus changes loss by more than most ablations |
| Randomness | Seed **tuple** (init, shuffle, dropout) recorded separately | One combined seed makes paired designs impossible to construct |

**The design's core data-model claim:** a metric time series that is not joinable to all five of these
is not evidence. That is why the LLD's `runs` table makes every one of them `NOT NULL` — a nullable
provenance column is a nullable conclusion.

---

## 8. Vocabulary you need for the rest of the design

| Term | Meaning |
|---|---|
| **Ablation** | Remove or change *one* component and measure the effect. The atomic unit of research |
| **Arm** | One variant within an ablation (control vs treatment) |
| **Sweep** | Many arms varying a hyperparameter, usually to find a best value |
| **σ (sigma)** | Std-dev of the target metric across seeds at fixed config |
| **δ (delta)** | The effect size you want to detect |
| **ρ (rho)** | Correlation between paired arms; determines how much pairing buys |
| **Power** | P(detecting a real effect). Convention: 0.80 |
| **α (alpha)** | P(false positive). Convention: 0.05 |
| **FDR** | False discovery rate — the fraction of your "significant" results that are wrong |
| **Pre-registration** | Declaring hypothesis, arms, horizon and metric *before* running |
| **Nat / bit** | Units of loss (natural / base-2 log). `perplexity = exp(loss_nats)` |
| **MFU** | Model FLOPs Utilization — see [`00_requirements_all_systems.md §B.4`](../00_requirements_all_systems.md) |
| **Chinchilla-optimal** | `D ≈ 20N`: the token budget that minimizes loss for a fixed compute budget |
| **Config hash** | Content-addressed identity of a fully-resolved config; the join key of the whole system |

---

← [system README](README.md) · → [01_requirements.md](01_requirements.md) ·
[shared assumptions](../00_requirements_all_systems.md)
